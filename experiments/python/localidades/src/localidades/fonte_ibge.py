"""Cliente da API de localidades do IBGE: prazo total, classificação de falhas e normalização.

Decisões em specs/002-servico-localidades/research.md: R1 (comportamento real do IBGE), R6 (prazo e
classificação), R7 (códigos como texto). Uma chamada por consulta, sem nova tentativa (FR-017). As mensagens
de erro nunca carregam o corpo devolvido pelo IBGE (FR-013).
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Callable
from typing import Any

import httpx

from localidades import __version__
from localidades.config import Configuracao
from localidades.dominio import (
    Municipio,
    MunicipioResumido,
    Regiao,
    RegiaoImediata,
    RegiaoIntermediaria,
    Uf,
    UfResumida,
)
from localidades.erros import FonteIndisponivel, FonteLenta, NaoEncontrado, RespostaInesperadaDaFonte

USER_AGENT = f"laboratorio-brasil-aberto-localidades/{__version__}"

AoMedir = Callable[[str, float], None]


class _FormaInesperada(Exception):
    """A resposta do IBGE não tem a forma descrita no data-model."""


def _campo(objeto: Any, chave: str) -> Any:
    if not isinstance(objeto, dict) or chave not in objeto or objeto[chave] is None:
        raise _FormaInesperada(f"campo obrigatório ausente: {chave}")
    return objeto[chave]


def _codigo(objeto: Any, digitos: int) -> str:
    valor = _campo(objeto, "id")
    if isinstance(valor, bool) or not isinstance(valor, int | str):
        raise _FormaInesperada("id com tipo inesperado")
    texto = str(valor).strip()
    # Tamanho exato: completar com zeros inventaria um código que o IBGE não publicou (T048).
    if not texto.isascii() or not texto.isdigit() or len(texto) != digitos:
        raise _FormaInesperada(f"id fora do formato de {digitos} dígitos")
    return texto


def _texto(objeto: Any, chave: str) -> str:
    valor = _campo(objeto, chave)
    if not isinstance(valor, str) or not valor.strip():
        raise _FormaInesperada(f"campo {chave} vazio ou não textual")
    return valor


# Regras do data-model para as siglas expostas (T049).
_SIGLA_UF = re.compile(r"[A-Z]{2}", re.ASCII)
_SIGLA_REGIAO = re.compile(r"[A-Z]{1,2}", re.ASCII)


def _sigla(objeto: Any, formato: re.Pattern[str]) -> str:
    valor = _texto(objeto, "sigla")
    if not formato.fullmatch(valor):
        raise _FormaInesperada("sigla fora do formato esperado")
    return valor


def _lista(dados: Any) -> list:
    if not isinstance(dados, list):
        raise _FormaInesperada("esperava uma lista")
    return dados


def _uf(objeto: Any) -> Uf:
    regiao = _campo(objeto, "regiao")
    return Uf(
        codigo=_codigo(objeto, 2),
        sigla=_sigla(objeto, _SIGLA_UF),
        nome=_texto(objeto, "nome"),
        regiao=Regiao(codigo=_codigo(regiao, 1), sigla=_sigla(regiao, _SIGLA_REGIAO), nome=_texto(regiao, "nome")),
    )


def _municipio_resumido(objeto: Any) -> MunicipioResumido:
    return MunicipioResumido(codigo=_codigo(objeto, 7), nome=_texto(objeto, "nome"))


def _municipio(objeto: Any) -> Municipio:
    imediata = _campo(objeto, "regiao-imediata")
    intermediaria = _campo(imediata, "regiao-intermediaria")
    uf = _campo(intermediaria, "UF")
    return Municipio(
        codigo=_codigo(objeto, 7),
        nome=_texto(objeto, "nome"),
        uf=UfResumida(codigo=_codigo(uf, 2), sigla=_sigla(uf, _SIGLA_UF), nome=_texto(uf, "nome")),
        regiao_imediata=RegiaoImediata(codigo=_codigo(imediata, 6), nome=_texto(imediata, "nome")),
        regiao_intermediaria=RegiaoIntermediaria(codigo=_codigo(intermediaria, 4), nome=_texto(intermediaria, "nome")),
    )


class ClienteIBGE:
    def __init__(
        self,
        config: Configuracao,
        cliente_http: httpx.AsyncClient | None = None,
        ao_medir: AoMedir | None = None,
    ) -> None:
        self._config = config
        self._base = config.ibge_url.rstrip("/")
        self._ao_medir = ao_medir
        self._http = cliente_http or httpx.AsyncClient(
            timeout=config.prazo_fonte_s,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            transport=httpx.AsyncHTTPTransport(retries=0),
            follow_redirects=False,
        )

    async def fechar(self) -> None:
        await self._http.aclose()

    def url(self, caminho: str) -> str:
        return f"{self._base}/{caminho}"

    async def _buscar_json(self, caminho: str, recurso: str) -> tuple[Any, str]:
        url = self.url(caminho)
        inicio = time.monotonic()
        try:
            async with asyncio.timeout(self._config.prazo_fonte_s):
                resposta = await self._http.get(url)
                corpo = await resposta.aread()
        except TimeoutError:
            raise FonteLenta(f"o IBGE não respondeu em {self._config.prazo_fonte_s:g} s") from None
        except httpx.TimeoutException:
            raise FonteLenta(f"o IBGE não respondeu em {self._config.prazo_fonte_s:g} s") from None
        except httpx.TransportError:
            raise FonteIndisponivel("não foi possível conectar ao IBGE") from None
        finally:
            if self._ao_medir is not None:
                self._ao_medir(recurso, time.monotonic() - inicio)

        status = resposta.status_code
        if status >= 500 or status == 429:
            raise FonteIndisponivel(f"o IBGE respondeu com status {status}")
        if status != 200:
            raise RespostaInesperadaDaFonte(f"o IBGE respondeu com status {status}")
        try:
            return json.loads(corpo), url
        except ValueError:
            raise RespostaInesperadaDaFonte("o IBGE respondeu um conteúdo que não é JSON") from None

    async def obter_estados(self) -> tuple[list[Uf], str]:
        dados, url = await self._buscar_json("estados", "estados")
        try:
            itens = _lista(dados)
            if not itens:
                raise _FormaInesperada("lista de UFs vazia")
            return [_uf(item) for item in itens], url
        except _FormaInesperada as erro:
            raise RespostaInesperadaDaFonte(f"a lista de UFs do IBGE veio fora do formato esperado ({erro})") from None

    async def obter_municipios_da_uf(self, codigo_uf: str) -> tuple[list[MunicipioResumido], str]:
        dados, url = await self._buscar_json(f"estados/{codigo_uf}/municipios", "municipios_da_uf")
        try:
            itens = _lista(dados)
            if not itens:
                raise _FormaInesperada("lista vazia para uma UF existente")
            return [_municipio_resumido(item) for item in itens], url
        except _FormaInesperada as erro:
            raise RespostaInesperadaDaFonte(
                f"a lista de municípios da UF {codigo_uf} veio fora do formato esperado ({erro})"
            ) from None

    async def obter_municipio(self, codigo: str) -> tuple[Municipio, str]:
        dados, url = await self._buscar_json(f"municipios/{codigo}", "municipio")
        if dados == []:
            raise NaoEncontrado(f"não existe município com o código {codigo}")
        try:
            if isinstance(dados, list):
                if len(dados) != 1:
                    raise _FormaInesperada("esperava um único município")
                dados = dados[0]
            municipio = _municipio(dados)
        except _FormaInesperada as erro:
            raise RespostaInesperadaDaFonte(f"o município {codigo} veio fora do formato esperado ({erro})") from None
        if municipio.codigo != codigo:
            raise RespostaInesperadaDaFonte(f"o IBGE devolveu outro município ao pedir {codigo}")
        return municipio, url
