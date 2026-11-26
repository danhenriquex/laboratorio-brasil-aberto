"""US2 — consultar um município pelo código oficial (caixa-preta)."""

import pytest

from contrato import validar

ROTA = "/v1/municipios/{codigo}"


def test_cenario_1_municipio_existente(servico):
    r = servico.get("/v1/municipios/3304557")
    validar(r, "GET", ROTA)
    assert r.status_code == 200
    dados = r.json()["dados"]
    assert dados["codigo"] == "3304557"
    assert dados["nome"] == "Rio de Janeiro"
    assert dados["uf"] == {"codigo": "33", "sigla": "RJ", "nome": "Rio de Janeiro"}
    assert len(dados["regiao_imediata"]["codigo"]) == 6
    assert len(dados["regiao_intermediaria"]["codigo"]) == 4
    assert r.json()["meta"]["url_fonte"].endswith("/municipios/3304557")


def test_cenario_2_codigo_inexistente(servico):
    r = servico.get("/v1/municipios/9999999")
    validar(r, "GET", ROTA)
    assert r.status_code == 404
    assert r.json()["type"] == "urn:brasil-aberto:problema:nao-encontrado"


@pytest.mark.parametrize("codigo", ["12ab", "123456", "12345678"])
def test_cenario_3_codigo_mal_formado(servico, ibge, codigo):
    r = servico.get(f"/v1/municipios/{codigo}")
    validar(r, "GET", ROTA)
    assert r.status_code == 400
    assert r.json()["type"] == "urn:brasil-aberto:problema:entrada-invalida"


def test_cenario_4_nome_com_apostrofo(servico):
    r = servico.get("/v1/municipios/3545803")
    validar(r, "GET", ROTA)
    assert r.json()["dados"]["nome"] == "Santa Bárbara d'Oeste"


def test_municipio_sem_microrregiao_no_ibge(servico):
    r = servico.get("/v1/municipios/5101837")
    validar(r, "GET", ROTA)
    assert r.status_code == 200
    assert r.json()["dados"]["uf"]["sigla"] == "MT"


def test_brasilia(servico):
    r = servico.get("/v1/municipios/5300108")
    validar(r, "GET", ROTA)
    assert r.json()["dados"]["uf"]["sigla"] == "DF"
