import json
import logging

import httpx
import pytest

from localidades.registro import FormatoJSON, LOGGER
from tests.conftest import item_da_uf


@pytest.fixture
def linhas(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER.name)
    LOGGER.addHandler(caplog.handler)
    yield lambda: [json.loads(FormatoJSON().format(r)) for r in caplog.records if r.name == LOGGER.name]
    LOGGER.removeHandler(caplog.handler)


def test_health_nao_depende_do_ibge(cliente, mock_ibge):
    mock_ibge.route().mock(side_effect=httpx.ConnectError("fora"))
    assert cliente.get("/health").status_code == 200
    assert len(mock_ibge.calls) == 0


def test_metricas(cliente, mock_ibge, relogio):
    rota = mock_ibge.get("/municipios/3304557").mock(return_value=httpx.Response(200, json=item_da_uf("33", 3304557)))
    mock_ibge.get("/municipios/3303302").mock(side_effect=httpx.ReadTimeout("lento"))
    cliente.get("/v1/municipios/3304557")  # falta
    cliente.get("/v1/municipios/3304557")  # acerto
    relogio.avancar(86400 + 1)
    rota.mock(side_effect=httpx.ConnectError("fora"))
    cliente.get("/v1/municipios/3304557")  # desatualizado
    cliente.get("/v1/municipios/3303302")  # fonte-lenta
    cliente.get("/v1/municipios/12ab")  # entrada-invalida

    r = cliente.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    texto = r.text
    for esperado in (
        'localidades_pedidos_total{rota="/v1/municipios/{codigo}",status="200"} 3.0',
        'localidades_pedidos_total{rota="/v1/municipios/{codigo}",status="504"} 1.0',
        'localidades_erros_total{tipo="fonte-lenta"} 1.0',
        'localidades_erros_total{tipo="entrada-invalida"} 1.0',
        'localidades_cache_total{resultado="falta"} 1.0',
        'localidades_cache_total{resultado="acerto"} 1.0',
        'localidades_cache_total{resultado="desatualizado"} 1.0',
        'localidades_fonte_duracao_segundos_count{recurso="municipio"} 3.0',
    ):
        assert esperado in texto, esperado


def test_rota_inexistente_nao_multiplica_series(cliente):
    for i in range(3):
        cliente.get(f"/nada/{i}")
    texto = cliente.get("/metrics").text
    assert 'localidades_pedidos_total{rota="nao-encontrado",status="404"} 3.0' in texto
    assert "/nada/" not in texto


def test_registro_json_por_pedido(cliente, mock_ibge, linhas):
    mock_ibge.get("/municipios/3304557").mock(return_value=httpx.Response(200, json=item_da_uf("33", 3304557)))
    cliente.get("/v1/municipios/3304557", headers={"X-Correlation-Id": "pedido-1"})
    cliente.get("/v1/municipios/3304557", headers={"X-Correlation-Id": "pedido-2"})
    registros = {r["correlacao_id"]: r for r in linhas()}
    primeiro, segundo = registros["pedido-1"], registros["pedido-2"]
    assert set(primeiro) == {"momento", "nivel", "correlacao_id", "metodo", "rota", "status", "duracao_ms", "cache", "fonte_ms"}
    assert (primeiro["metodo"], primeiro["rota"], primeiro["status"], primeiro["nivel"]) == ("GET", "/v1/municipios/{codigo}", 200, "info")
    assert (primeiro["cache"], segundo["cache"]) == ("falta", "acerto")
    assert primeiro["fonte_ms"] is not None and segundo["fonte_ms"] is None
    assert primeiro["momento"].endswith("Z")
    texto = json.dumps(list(registros.values()))
    assert "127.0.0.1" not in texto and "testclient" not in texto
