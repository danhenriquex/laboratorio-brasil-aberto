"""Infraestrutura comum dos testes: sem rede externa, relógio falso e fixtures do IBGE."""

from __future__ import annotations

import json
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import respx

IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades"
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _raiz_do_repositorio() -> Path:
    for pasta in Path(__file__).resolve().parents:
        if (pasta / "contracts" / "localidades").is_dir():
            return pasta
    raise RuntimeError("raiz do repositório não encontrada")


FIXTURES = _raiz_do_repositorio() / "contracts" / "localidades" / "fixtures-ibge"


def ler_fixture(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()


def fixture_json(nome: str):
    return json.loads(ler_fixture(nome))


def item_da_uf(codigo_uf: str, codigo_municipio: int) -> dict:
    """Um item da lista de municípios de uma UF, que tem a mesma forma de /municipios/{codigo}."""
    for item in fixture_json(f"municipios-uf-{codigo_uf}.json"):
        if item["id"] == codigo_municipio:
            return item
    raise KeyError(codigo_municipio)


class RelogioFalso:
    def __init__(self, inicio: datetime | None = None) -> None:
        self._agora = inicio or datetime(2026, 11, 26, 12, 0, 0, 123000, tzinfo=UTC)
        self._mono = 1000.0

    def agora(self) -> datetime:
        return self._agora

    def monotonic(self) -> float:
        return self._mono

    def avancar(self, segundos: float) -> None:
        self._agora += timedelta(seconds=segundos)
        self._mono += segundos


@pytest.fixture
def relogio() -> RelogioFalso:
    return RelogioFalso()


@pytest.fixture(autouse=True)
def _sem_rede_externa(monkeypatch):
    """Recusa qualquer conexão fora do loopback (Constituição IV)."""
    conectar_original = socket.socket.connect
    resolver_original = socket.getaddrinfo

    def _host(endereco) -> str:
        return endereco[0] if isinstance(endereco, tuple) else str(endereco)

    def conectar(self, endereco):
        if self.family in (socket.AF_INET, socket.AF_INET6) and _host(endereco) not in _LOOPBACK:
            raise ConnectionRefusedError(f"rede externa bloqueada nos testes: {_host(endereco)}")
        return conectar_original(self, endereco)

    def resolver(host, *args, **kwargs):
        if host not in _LOOPBACK:
            raise socket.gaierror(f"rede externa bloqueada nos testes: {host}")
        return resolver_original(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", conectar)
    monkeypatch.setattr(socket, "getaddrinfo", resolver)


@pytest.fixture
def mock_ibge():
    with respx.mock(base_url=IBGE, assert_all_called=False) as roteador:
        yield roteador
