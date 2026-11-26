"""Registro de pedidos: uma linha JSON por pedido no stdout (research.md, R12).

Não registra IP nem cabeçalhos além do identificador de correlação (Constituição VII).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

LOGGER = logging.getLogger("localidades.pedidos")


class FormatoJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        momento = datetime.fromtimestamp(record.created, UTC)
        campos = {
            "momento": momento.strftime("%Y-%m-%dT%H:%M:%S.") + f"{momento.microsecond // 1000:03d}Z",
            "nivel": record.levelname.lower(),
            **getattr(record, "campos", {}),
        }
        return json.dumps(campos, ensure_ascii=False)


class _SaidaPadrao(logging.StreamHandler):
    """Escreve no sys.stdout do momento da escrita (útil quando o stdout é trocado)."""

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


def configurar() -> None:
    if not any(isinstance(h, _SaidaPadrao) for h in LOGGER.handlers):
        saida = _SaidaPadrao()
        saida.setFormatter(FormatoJSON())
        LOGGER.addHandler(saida)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def registrar_pedido(
    *,
    correlacao_id: str,
    metodo: str,
    rota: str,
    status: int,
    duracao_ms: float,
    cache: str | None,
    fonte_ms: float | None,
) -> None:
    nivel = logging.ERROR if status >= 500 else logging.INFO
    LOGGER.log(
        nivel,
        "pedido",
        extra={
            "campos": {
                "correlacao_id": correlacao_id,
                "metodo": metodo,
                "rota": rota,
                "status": status,
                "duracao_ms": round(duracao_ms, 1),
                "cache": cache,
                "fonte_ms": None if fonte_ms is None else round(fonte_ms, 1),
            }
        },
    )
