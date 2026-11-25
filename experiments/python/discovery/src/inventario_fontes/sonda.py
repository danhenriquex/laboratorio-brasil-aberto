"""Consulta única a uma fonte: leitura limitada, redirecionamentos e classificação de falhas.

Decisões em specs/001-inventario-fontes/research.md: R1 (teto de leitura), R2 (login),
R3 (causas). Nenhuma nova tentativa, nenhuma credencial, nenhum corpo gravado em disco.
"""

from __future__ import annotations

import re
import ssl
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from inventario_fontes import __version__
from inventario_fontes.amostra import ErroAmostra, inferir_estrutura
from inventario_fontes.formato import detectar_formato, divergente, formato_declarado
from inventario_fontes.modelos import (
    Auth,
    Causa,
    Configuracao,
    Fonte,
    Redirecionamento,
    ResultadoSondagem,
    Situacao,
)

USER_AGENT = f"laboratorio-brasil-aberto-inventario/{__version__}"
_HOSTS_LOGIN = {"sso.acesso.gov.br"}
_MENSAGEM_TLS = re.compile(r"\[SSL|SSL:|CERTIFICATE_VERIFY_FAILED|\bTLS\b|certificate", re.IGNORECASE)
_CAMINHO_LOGIN = re.compile(r"(^|/)(login|signin|auth|oauth2?|sso)([/._-]|$)", re.IGNORECASE)


class Relogio(Protocol):
    def agora(self): ...
    def monotonic(self) -> float: ...
    def esperar(self, segundos: float) -> None: ...


def criar_cliente(config: Configuracao) -> httpx.Client:
    """Cliente sem novas tentativas, com tempo limite, redirecionamentos limitados e User-Agent genérico."""
    return httpx.Client(
        timeout=config.tempo_limite_s,
        follow_redirects=True,
        max_redirects=config.max_redirecionamentos,
        headers={"User-Agent": USER_AGENT},
        transport=httpx.HTTPTransport(retries=0),
    )


def _ler_limitado(resposta: httpx.Response, teto: int) -> tuple[bytes, bool]:
    partes: list[bytes] = []
    total = 0
    for bloco in resposta.iter_bytes():
        if total + len(bloco) > teto:
            partes.append(bloco[: teto - total])
            return b"".join(partes), True
        partes.append(bloco)
        total += len(bloco)
    return b"".join(partes), False


def _eh_erro_tls(erro: BaseException) -> bool:
    atual: BaseException | None = erro
    vistos = 0
    while atual is not None and vistos < 10:
        if isinstance(atual, ssl.SSLError):
            return True
        atual = atual.__cause__ or atual.__context__
        vistos += 1
    return bool(_MENSAGEM_TLS.search(str(erro)))


def _indicio_de_login(url: str) -> str | None:
    partes = urlsplit(url)
    host = (partes.hostname or "").lower()
    if host in _HOSTS_LOGIN or _CAMINHO_LOGIN.search(partes.path):
        return f"redirecionado para {host}{partes.path}"
    return None


def _detalhe(erro: BaseException) -> str:
    mensagem = str(erro).strip() or type(erro).__name__
    return f"{type(erro).__name__}: {mensagem}"[:200]


def sondar(fonte: Fonte, cliente: httpx.Client, config: Configuracao, relogio: Relogio) -> ResultadoSondagem:
    if not fonte.url_teste:
        raise ValueError(f"a fonte {fonte.id} não tem url_teste")

    coletado_em = relogio.agora()
    inicio = relogio.monotonic()

    def latencia() -> float:
        return round((relogio.monotonic() - inicio) * 1000, 1)

    def falha(causa: Causa, detalhe: str) -> ResultadoSondagem:
        return ResultadoSondagem.base(
            fonte, Situacao.FALHOU, causa=causa, detalhe_causa=detalhe, coletado_em=coletado_em, latencia_ms=latencia()
        )

    try:
        with cliente.stream("GET", fonte.url_teste) as resposta:
            corpo, truncada = _ler_limitado(resposta, config.teto_bytes)
    except httpx.TooManyRedirects:
        return falha(Causa.ERRO_REQUISICAO, f"mais de {config.max_redirecionamentos} redirecionamentos")
    except httpx.TimeoutException as erro:
        return falha(Causa.TEMPO_ESGOTADO, _detalhe(erro))
    except httpx.TransportError as erro:
        causa = Causa.ERRO_TLS if _eh_erro_tls(erro) else Causa.INDISPONIVEL
        return falha(causa, _detalhe(erro))

    lat = latencia()
    cadeia = [*resposta.history, resposta]
    redirecionamentos = tuple(
        Redirecionamento(status=anterior.status_code, url=str(seguinte.url))
        for anterior, seguinte in zip(cadeia, cadeia[1:])
    )
    status = resposta.status_code
    url_final = str(resposta.url)
    declarado = formato_declarado(resposta.headers.get("content-type"))
    detectado = detectar_formato(corpo)
    tamanho_declarado = resposta.headers.get("content-length")

    indicio: str | None = None
    if status == 401:
        indicio = "status 401"
    elif "www-authenticate" in resposta.headers:
        indicio = f"cabeçalho WWW-Authenticate (status {status})"
    elif redirecionamentos:
        indicio = _indicio_de_login(url_final)

    if indicio:
        auth = Auth.EXIGE
    elif 200 <= status < 300:
        auth = Auth.NAO_EXIGE
    else:
        auth = Auth.INDETERMINADO

    comum = dict(
        coletado_em=coletado_em,
        latencia_ms=lat,
        status_http=status,
        url_final=url_final,
        redirecionamentos=redirecionamentos,
        formato_declarado=declarado,
        formato_detectado=detectado,
        formato_divergente=divergente(declarado, detectado),
        tamanho_bytes=len(corpo),
        tamanho_declarado_bytes=int(tamanho_declarado) if tamanho_declarado and tamanho_declarado.isdigit() else None,
        truncada=truncada,
        auth_observada=auth,
        indicio_autenticacao=indicio,
    )

    causa: Causa | None = None
    detalhe: str | None = None
    retry_after: str | None = None
    amostra = None
    if indicio:
        causa, detalhe = Causa.EXIGE_AUTENTICACAO, indicio
    elif status == 403:
        causa, detalhe = Causa.ACESSO_NEGADO, "status 403"
    elif status == 429:
        causa, detalhe = Causa.LIMITE_REQUISICOES, "status 429"
        retry_after = resposta.headers.get("retry-after")
    elif status >= 500:
        causa, detalhe = Causa.ERRO_FONTE, f"status {status}"
    elif status >= 300:
        causa, detalhe = Causa.ERRO_REQUISICAO, f"status {status}"
    else:
        try:
            amostra = inferir_estrutura(corpo, detectado, truncada)
        except ErroAmostra as erro:
            causa, detalhe = Causa.RESPOSTA_INVALIDA, str(erro)[:200]

    if causa is None:
        return ResultadoSondagem.base(fonte, Situacao.RESPONDEU, amostra=amostra, **comum)
    return ResultadoSondagem.base(
        fonte, Situacao.FALHOU, causa=causa, detalhe_causa=detalhe, retry_after=retry_after, **comum
    )
