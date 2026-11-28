"""US5 — saúde, métricas e correlação (caixa-preta)."""

import re

import pytest

from contrato import pedido_cru, validar

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


def test_entrada_mal_codificada_e_problema(servico):
    """Convergência do E4 (T044): um caminho com codificação inválida também sai em problem+json com correlação."""
    r = pedido_cru(servico, "GET", "/v1/municipios/%ZZ", {"X-Correlation-Id": "mal-codificado"})
    assert r.status_code == 400
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["X-Correlation-Id"] == "mal-codificado"
    problema = r.json()
    assert problema["type"] == "urn:brasil-aberto:problema:entrada-invalida"
    assert problema["status"] == 400
    assert problema["correlacao_id"] == "mal-codificado"


@pytest.mark.parametrize("metodo", ["TRACE", "POST", "PUT", "DELETE", "PATCH"])
def test_metodo_trace_e_problema(servico, metodo):
    """Convergência do E4 (T047): método não suportado, inclusive o TRACE, é 404 em problem+json com correlação."""
    r = servico.request(metodo, "/v1/ufs", headers={"X-Correlation-Id": "metodo-xyz"})
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["X-Correlation-Id"] == "metodo-xyz"
    problema = r.json()
    assert problema["type"] == "urn:brasil-aberto:problema:nao-encontrado"
    assert problema["correlacao_id"] == "metodo-xyz"


@pytest.mark.parametrize("aceita", ["application/xml", "text/html", "text/plain", "application/problem+json"])
@pytest.mark.parametrize("caminho,rota", [
    ("/v1/ufs", "/v1/ufs"),
    ("/v1/ufs/RJ/municipios", "/v1/ufs/{uf}/municipios"),
    ("/health", "/health"),
])
def test_accept_e_ignorado(servico, caminho, rota, aceita):
    """Convergência do E4 (T048): o Accept não muda a resposta; o sucesso é sempre application/json."""
    r = servico.get(caminho, headers={"Accept": aceita})
    assert r.status_code == 200
    assert r.headers["content-type"].split(";")[0].strip() == "application/json"
    validar(r, "GET", rota)


def test_accept_nao_muda_o_formato_do_erro(servico):
    """Convergência do E4 (T048): com qualquer Accept, o erro continua em application/problem+json."""
    r = servico.get("/v1/municipios/12ab", headers={"Accept": "application/xml"})
    validar(r, "GET", "/v1/municipios/{codigo}")
    assert r.status_code == 400


@pytest.mark.parametrize("caminho", [
    "/v1/ufs;jsessionid=x",
    "/v1/ufs/RJ;x=1/municipios",
    "/v1/municipios/3304557;v=1",
    "/health;x",
])
def test_parametro_de_caminho_nao_casa_com_a_rota(servico, caminho):
    """Convergência do E4 (T050): o ";" faz parte do segmento (RFC 3986); o caminho não casa com a rota sem ele.

    O E1 responde 404 ou 400, conforme o segmento; o que não pode é devolver os dados da rota.
    """
    r = pedido_cru(servico, "GET", caminho, {"X-Correlation-Id": "ponto-e-virgula"})
    assert r.status_code in (400, 404)
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["X-Correlation-Id"] == "ponto-e-virgula"
    assert r.json()["correlacao_id"] == "ponto-e-virgula"
