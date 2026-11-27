"""Cópia guardada com validade, consulta única por chave e cópia vencida quando a fonte falha.

Estados de uma entrada (data-model.md): ausente → válida → vencida. "Não encontrado" e erros nunca entram
na cópia. Em memória do processo (research.md, R5; Constituição X: sem Redis enquanto houver um processo).

Consulta única (T050): pedidos simultâneos pelo mesmo recurso aguardam a **mesma** consulta em andamento e
recebem o mesmo resultado, inclusive a falha. Assim ninguém espera em fila por mais de um prazo, e a fonte
com problema recebe uma única consulta.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
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
        self._em_andamento: dict[str, asyncio.Task[Entrada]] = {}

    def _valida(self, chave: str) -> _Guardada | None:
        guardada = self._guardadas.get(chave)
        if guardada is not None and self._relogio.monotonic() < guardada.expira_em:
            return guardada
        return None

    async def _consultar(self, chave: str, buscar: Buscar) -> Entrada:
        coletado_em = self._relogio.agora()
        dados, url_fonte = await buscar()
        self._guardadas[chave] = _Guardada(
            dados, url_fonte, coletado_em, expira_em=self._relogio.monotonic() + self._validade_s
        )
        return Entrada(dados, url_fonte, coletado_em, resultado="falta")

    async def obter(self, chave: str, buscar: Buscar) -> Entrada:
        if (guardada := self._valida(chave)) is not None:
            return Entrada(guardada.dados, guardada.url_fonte, guardada.coletado_em, resultado="acerto")

        tarefa = self._em_andamento.get(chave)
        iniciou = tarefa is None
        if tarefa is None:
            tarefa = asyncio.ensure_future(self._consultar(chave, buscar))
            self._em_andamento[chave] = tarefa

            def _liberar(concluida: asyncio.Task, chave: str = chave) -> None:
                if self._em_andamento.get(chave) is concluida:
                    del self._em_andamento[chave]

            tarefa.add_done_callback(_liberar)

        try:
            # shield: um pedido cancelado não cancela a consulta que os outros esperam
            entrada = await asyncio.shield(tarefa)
        except ERROS_DE_FONTE:
            vencida = self._guardadas.get(chave)
            if vencida is None:
                raise
            return Entrada(
                vencida.dados, vencida.url_fonte, vencida.coletado_em, desatualizado=True, resultado="desatualizado"
            )
        return entrada if iniciou else replace(entrada, resultado="acerto")
