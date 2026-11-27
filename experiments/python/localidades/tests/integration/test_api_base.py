import re
import uuid

import pytest
from fastapi.testclient import TestClient

from localidades.api import criar_app
from localidades.config import Configuracao

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.fixture
def app(relogio):
    return criar_app(Configuracao(), relogio=relogio)


@pytest.fixture
def cliente(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_health(cliente, mock_ibge):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert len(mock_ibge.calls) == 0


@pytest.mark.parametrize("caminho", ["/v2/ufs", "/ufs", "/nada", "/v1"])
def test_rota_inexistente_e_problema_404(cliente, caminho):
    r = cliente.get(caminho)
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    corpo = r.json()
    assert corpo["type"] == "urn:brasil-aberto:problema:nao-encontrado"
    assert corpo["status"] == 404
    assert corpo["correlacao_id"] == r.headers["X-Correlation-Id"]


def test_correlacao_valida_volta_igual(cliente):
    r = cliente.get("/health", headers={"X-Correlation-Id": "teste-123_a.b"})
    assert r.headers["X-Correlation-Id"] == "teste-123_a.b"


@pytest.mark.parametrize("valor", ["x" * 65, "com espaço", "acentuação"])
def test_correlacao_invalida_e_trocada(cliente, valor):
    r = cliente.get("/health", headers={"X-Correlation-Id": valor.encode("utf-8")})
    assert UUID4.match(r.headers["X-Correlation-Id"])


def test_sem_correlacao_gera_uuid(cliente):
    r = cliente.get("/health")
    assert uuid.UUID(r.headers["X-Correlation-Id"]).version == 4


def test_erro_inesperado_vira_500_sem_detalhes_internos(app):
    @app.get("/v1/_falha_de_teste")
    async def falha():
        raise RuntimeError("segredo interno /etc/passwd")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/v1/_falha_de_teste")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/problem+json")
    texto = r.text
    assert "segredo" not in texto and "Traceback" not in texto and "RuntimeError" not in texto
    assert r.json()["type"] == "urn:brasil-aberto:problema:erro-interno"
    assert r.json()["correlacao_id"] == r.headers["X-Correlation-Id"]
