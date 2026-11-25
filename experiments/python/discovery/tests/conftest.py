"""Infraestrutura comum dos testes. Nenhum teste acessa a rede (princípio IV)."""

from __future__ import annotations

import json
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def bloquear_rede(monkeypatch):
    def proibido(*args, **kwargs):
        raise RuntimeError("rede bloqueada nos testes")

    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket.socket, "connect_ex", proibido)
    monkeypatch.setattr(socket, "create_connection", proibido)
    monkeypatch.setattr(socket, "getaddrinfo", proibido)


class RelogioFalso:
    """Relógio controlável: `esperar` avança o tempo e registra a espera."""

    def __init__(self, inicio: datetime | None = None) -> None:
        self._inicio = inicio or datetime(2026, 11, 25, 13, 0, 0, tzinfo=UTC)
        self._t = 0.0
        self.esperas: list[float] = []
        self.marcas: list[tuple[str, float]] = []

    def agora(self) -> datetime:
        return self._inicio + timedelta(seconds=self._t)

    def monotonic(self) -> float:
        return self._t

    def avancar(self, segundos: float) -> None:
        self._t += segundos

    def esperar(self, segundos: float) -> None:
        self.esperas.append(segundos)
        self._t += segundos


@pytest.fixture
def relogio() -> RelogioFalso:
    return RelogioFalso()


def fonte_dict(**overrides) -> dict:
    base = {
        "id": "fonte-teste",
        "name": "Fonte de teste",
        "domain": "teste",
        "docs_url": "https://exemplo.gov.br/docs",
        "probe_url": "https://exemplo.gov.br/api/dados",
        "data_type": ["api"],
        "access_hypothesis": "facil",
        "auth": "nenhuma (hipótese)",
        "verification": "parcial",
        "round": 1,
    }
    base.update(overrides)
    return base


@pytest.fixture
def catalogo_tmp(tmp_path):
    def criar(fontes: list[dict], schema_version: int = 1) -> Path:
        caminho = tmp_path / "sources.json"
        caminho.write_text(
            json.dumps({"schema_version": schema_version, "sources": fontes}, ensure_ascii=False),
            encoding="utf-8",
        )
        return caminho

    return criar


def ler_fixture(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()
