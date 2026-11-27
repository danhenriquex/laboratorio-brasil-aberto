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


def test_entrada_mal_codificada_e_problema(servico):
    """Convergência do E4 (T044): um caminho com codificação inválida também sai em problem+json com correlação.

    O httpx corrigiria o "%" inválido antes de enviar; o pedido vai cru, pela biblioteca padrão.
    """
    import http.client
    import json
    from urllib.parse import urlsplit

    alvo = urlsplit(str(servico.base_url))
    conexao = http.client.HTTPConnection(alvo.hostname, alvo.port, timeout=10)
    conexao.request("GET", "/v1/municipios/%ZZ", headers={"X-Correlation-Id": "mal-codificado"})
    resposta = conexao.getresponse()
    corpo = resposta.read()
    conexao.close()
    assert resposta.status == 400
    assert resposta.getheader("Content-Type", "").startswith("application/problem+json")
    assert resposta.getheader("X-Correlation-Id") == "mal-codificado"
    problema = json.loads(corpo)
    assert problema["type"] == "urn:brasil-aberto:problema:entrada-invalida"
    assert problema["status"] == 400
    assert problema["correlacao_id"] == "mal-codificado"
