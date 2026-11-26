"""US5 — saúde, métricas e correlação (caixa-preta)."""

import re

from contrato import validar

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
METRICAS = (
    "localidades_pedidos_total",
    "localidades_erros_total",
    "localidades_cache_total",
    "localidades_fonte_duracao_segundos",
)


def test_cenario_1_saude(servico):
    r = servico.get("/health")
    validar(r, "GET", "/health")
    assert r.json() == {"status": "ok"}


def test_cenario_2_metricas_com_os_nomes_do_contrato(servico):
    servico.get("/v1/ufs")
    servico.get("/v1/municipios/12ab")
    r = servico.get("/metrics")
    validar(r, "GET", "/metrics")
    for nome in METRICAS:
        assert nome in r.text, nome
    assert 'rota="/v1/ufs"' in r.text
    assert 'tipo="entrada-invalida"' in r.text


def test_cenario_3_correlacao_enviada_volta_igual(servico):
    r = servico.get("/v1/ufs", headers={"X-Correlation-Id": "verificacao-123"})
    assert r.headers["X-Correlation-Id"] == "verificacao-123"


def test_correlacao_invalida_e_trocada_por_uuid(servico):
    r = servico.get("/v1/ufs", headers={"X-Correlation-Id": "x" * 65})
    assert UUID4.match(r.headers["X-Correlation-Id"])


def test_correlacao_no_corpo_do_erro(servico):
    r = servico.get("/v1/municipios/12ab", headers={"X-Correlation-Id": "erro-xyz"})
    validar(r, "GET", "/v1/municipios/{codigo}")
    assert r.json()["correlacao_id"] == r.headers["X-Correlation-Id"] == "erro-xyz"
