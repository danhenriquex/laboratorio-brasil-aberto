"""Cópia guardada com validade, consulta única por chave e cópia vencida quando a fonte falha.

Estados de uma entrada (data-model.md): ausente → válida → vencida. "Não encontrado" e erros nunca entram
na cópia. Em memória do processo (research.md, R5; Constituição X: sem Redis enquanto houver um processo).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from localidades.erros import ERROS_DE_FONTE

Buscar = Callable[[], Awaitable[tuple[Any, str]]]


@dataclass(frozen=True)
class Entrada:
    dados: Any
    url_fonte: str
    coletado_em: datetime
    desatualizado: bool = False
    resultado: str = "falta"  # acerto | falta | desatualizado


@dataclass(frozen=True)
class _Guardada:
    dados: Any
    url_fonte: str
    coletado_em: datetime
    expira_em: float  # relógio monotônico


class CacheComValidade:
    def __init__(self, relogio, validade_s: float) -> None:
        self._relogio = relogio
        self._validade_s = validade_s
        self._guardadas: dict[str, _Guardada] = {}
        self._travas: dict[str, asyncio.Lock] = {}

    def _valida(self, chave: str) -> _Guardada | None:
        guardada = self._guardadas.get(chave)
        if guardada is not None and self._relogio.monotonic() < guardada.expira_em:
            return guardada
        return None

    async def obter(self, chave: str, buscar: Buscar) -> Entrada:
        if (guardada := self._valida(chave)) is not None:
            return Entrada(guardada.dados, guardada.url_fonte, guardada.coletado_em, resultado="acerto")

        trava = self._travas.setdefault(chave, asyncio.Lock())
        async with trava:
            # quem esperou a consulta de outro pedido usa o resultado dela
            if (guardada := self._valida(chave)) is not None:
                return Entrada(guardada.dados, guardada.url_fonte, guardada.coletado_em, resultado="acerto")

            vencida = self._guardadas.get(chave)
            coletado_em = self._relogio.agora()
            try:
                dados, url_fonte = await buscar()
            except ERROS_DE_FONTE:
                if vencida is None:
                    raise
                return Entrada(
                    vencida.dados, vencida.url_fonte, vencida.coletado_em, desatualizado=True, resultado="desatualizado"
                )

            self._guardadas[chave] = _Guardada(
                dados, url_fonte, coletado_em, expira_em=self._relogio.monotonic() + self._validade_s
            )
            return Entrada(dados, url_fonte, coletado_em, resultado="falta")
