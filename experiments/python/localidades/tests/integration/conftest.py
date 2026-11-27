import re

import httpx
import pytest
from fastapi.testclient import TestClient

from localidades.api import criar_app
from localidades.config import Configuracao
from tests.conftest import ler_fixture

COLETADO_EM = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def json_resp(conteudo: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(status, content=conteudo, headers={"Content-Type": "application/json; charset=utf-8"})


def fixture_resp(nome: str) -> httpx.Response:
    return json_resp(ler_fixture(nome))


def assert_meta(meta: dict, url_fonte: str, desatualizado: bool = False) -> None:
    assert meta["fonte"] == "IBGE — API de localidades"
    assert meta["url_fonte"] == url_fonte
    assert meta["url_documentacao"] == "https://servicodados.ibge.gov.br/api/docs/localidades"
    assert COLETADO_EM.match(meta["coletado_em"])
    assert meta["desatualizado"] is desatualizado


def assert_problema(r, status: int, tipo: str) -> dict:
    assert r.status_code == status, r.text
    assert r.headers["content-type"].startswith("application/problem+json")
    corpo = r.json()
    assert corpo["type"] == f"urn:brasil-aberto:problema:{tipo}"
    assert corpo["status"] == status
    assert corpo["detail"]
    assert corpo["correlacao_id"] == r.headers["X-Correlation-Id"]
    return corpo


@pytest.fixture
def criar_cliente(relogio):
    def _criar(**config) -> TestClient:
        return TestClient(criar_app(Configuracao(**config), relogio=relogio), raise_server_exceptions=False)

    return _criar


@pytest.fixture
def cliente(criar_cliente):
    with criar_cliente() as c:
        yield c
