"""Casos de uso do serviço de localidades. Não importa FastAPI (portas e adaptadores)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from localidades.config import Configuracao
from localidades.dominio import (
    Pagina,
    Uf,
    ordenar,
    paginar,
    resolver_uf,
    validar_paginacao,
)
from localidades.erros import RespostaInesperadaDaFonte

FONTE = "IBGE — API de localidades"
URL_DOCUMENTACAO = "https://servicodados.ibge.gov.br/api/docs/localidades"


class RelogioSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        import time

        return time.monotonic()


def formatar_momento(momento: datetime) -> str:
    """ISO 8601 em UTC, com milissegundos e sufixo Z (data-model, Meta)."""
    return momento.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{momento.microsecond // 1000:03d}Z"


@dataclass(frozen=True)
class Meta:
    url_fonte: str
    coletado_em: datetime
    desatualizado: bool = False
    fonte: str = FONTE
    url_documentacao: str = URL_DOCUMENTACAO

    def para_dict(self) -> dict[str, Any]:
        return {
            "fonte": self.fonte,
            "url_fonte": self.url_fonte,
            "url_documentacao": self.url_documentacao,
            "coletado_em": formatar_momento(self.coletado_em),
            "desatualizado": self.desatualizado,
        }


@dataclass(frozen=True)
class Obtido:
    """Um recurso do IBGE já normalizado, com a procedência e o uso da cópia guardada."""

    dados: Any
    meta: Meta
    cache: str = field(default="falta")  # acerto | falta | desatualizado


@dataclass(frozen=True)
class Resultado:
    dados: Any
    meta: Meta
    paginacao: Any = None
    cache: str = "falta"


Buscar = Callable[[], Awaitable[tuple[Any, str]]]


class ServicoLocalidades:
    def __init__(self, cliente_ibge, relogio, config: Configuracao) -> None:
        self._ibge = cliente_ibge
        self._relogio = relogio
        self._config = config

    async def _obter(self, chave: str, buscar: Buscar) -> Obtido:
        coletado_em = self._relogio.agora()
        dados, url_fonte = await buscar()
        return Obtido(dados=dados, meta=Meta(url_fonte=url_fonte, coletado_em=coletado_em))

    # --- US1 ---

    async def listar_ufs(self) -> Resultado:
        obtido = await self._obter("estados", self._ibge.obter_estados)
        return Resultado(dados=ordenar(obtido.dados), meta=obtido.meta, cache=obtido.cache)

    async def obter_uf(self, param: str) -> Resultado:
        codigo = resolver_uf(param)
        obtido = await self._obter("estados", self._ibge.obter_estados)
        uf: Uf | None = next((u for u in obtido.dados if u.codigo == codigo), None)
        if uf is None:
            raise RespostaInesperadaDaFonte(f"a UF {codigo} não veio na lista de UFs do IBGE")
        return Resultado(dados=uf, meta=obtido.meta, cache=obtido.cache)

    async def listar_municipios(self, param_uf: str, pagina: int = 1, itens: int = 100) -> Resultado:
        validar_paginacao(pagina, itens, self._config.itens_max)
        codigo = resolver_uf(param_uf)
        obtido = await self._obter(
            f"estados/{codigo}/municipios", lambda: self._ibge.obter_municipios_da_uf(codigo)
        )
        selecionados = ordenar(obtido.dados)
        pagina_: Pagina = paginar(selecionados, pagina, itens)
        return Resultado(dados=pagina_.itens, meta=obtido.meta, paginacao=pagina_, cache=obtido.cache)
