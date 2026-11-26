import pytest

from localidades.dominio import dobrar
from tests.conftest import IBGE, fixture_json
from tests.integration.conftest import assert_meta, assert_problema, fixture_resp, json_resp


@pytest.fixture
def estados(mock_ibge):
    return mock_ibge.get("/estados").mock(return_value=fixture_resp("estados.json"))


@pytest.fixture
def rj(mock_ibge):
    return mock_ibge.get("/estados/33/municipios").mock(return_value=fixture_resp("municipios-uf-33.json"))


# --- /v1/ufs ---


def test_lista_as_27_ufs_ordenadas(cliente, estados):
    r = cliente.get("/v1/ufs")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    corpo = r.json()
    assert set(corpo) == {"dados", "meta"}
    ufs = corpo["dados"]
    assert len(ufs) == 27
    assert ufs[0]["sigla"] == "AC"
    assert [dobrar(u["nome"]) for u in ufs] == sorted(dobrar(u["nome"]) for u in ufs)
    rj_ = next(u for u in ufs if u["sigla"] == "RJ")
    assert rj_ == {"codigo": "33", "sigla": "RJ", "nome": "Rio de Janeiro", "regiao": {"codigo": "3", "sigla": "SE", "nome": "Sudeste"}}
    assert_meta(corpo["meta"], f"{IBGE}/estados")
    assert estados.call_count == 1


# --- /v1/ufs/{uf} ---


@pytest.mark.parametrize("param", ["rj", "RJ", "33", "%20RJ%20"])
def test_obter_uf(cliente, estados, param):
    r = cliente.get(f"/v1/ufs/{param}")
    assert r.status_code == 200
    assert r.json()["dados"]["sigla"] == "RJ"
    assert_meta(r.json()["meta"], f"{IBGE}/estados")


@pytest.mark.parametrize("param", ["XX", "99"])
def test_uf_inexistente_e_404_sem_consultar(cliente, mock_ibge, param):
    assert_problema(cliente.get(f"/v1/ufs/{param}"), 404, "nao-encontrado")
    assert len(mock_ibge.calls) == 0


@pytest.mark.parametrize("param", ["R1", "123", "R"])
def test_uf_mal_formada_e_400_sem_consultar(cliente, mock_ibge, param):
    assert_problema(cliente.get(f"/v1/ufs/{param}"), 400, "entrada-invalida")
    assert len(mock_ibge.calls) == 0


def test_uf_da_tabela_ausente_no_ibge_e_inesperada(cliente, mock_ibge):
    sem_rj = [u for u in fixture_json("estados.json") if u["sigla"] != "RJ"]
    mock_ibge.get("/estados").mock(return_value=json_resp(__import__("json").dumps(sem_rj).encode()))
    assert_problema(cliente.get("/v1/ufs/RJ"), 502, "resposta-inesperada-da-fonte")


# --- /v1/ufs/{uf}/municipios ---


def test_municipios_do_rj(cliente, rj):
    r = cliente.get("/v1/ufs/RJ/municipios")
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"dados", "paginacao", "meta"}
    assert corpo["paginacao"] == {"pagina": 1, "itens": 100, "total": 92, "paginas": 1}
    dados = corpo["dados"]
    assert len(dados) == 92
    assert all(set(m) == {"codigo", "nome"} for m in dados)
    assert dados[0] == {"codigo": "3300100", "nome": "Angra dos Reis"}
    assert {"codigo": "3303302", "nome": "Niterói"} in dados
    assert [dobrar(m["nome"]) for m in dados] == sorted(dobrar(m["nome"]) for m in dados)
    assert_meta(corpo["meta"], f"{IBGE}/estados/33/municipios")
    assert rj.call_count == 1  # uma consulta por pedido (FR-017), sem consultar /estados


def test_paginacao(cliente, rj):
    r = cliente.get("/v1/ufs/rj/municipios", params={"itens": 10, "pagina": 10})
    assert r.json()["paginacao"] == {"pagina": 10, "itens": 10, "total": 92, "paginas": 10}
    assert len(r.json()["dados"]) == 2


def test_pagina_alem_do_fim(cliente, rj):
    r = cliente.get("/v1/ufs/33/municipios", params={"pagina": 20})
    assert r.status_code == 200
    assert r.json()["dados"] == []
    assert r.json()["paginacao"]["total"] == 92


@pytest.mark.parametrize(
    ("params", "trecho"),
    [({"itens": 0}, "500"), ({"itens": 501}, "500"), ({"pagina": 0}, "pagina"), ({"itens": "dez"}, "itens")],
)
def test_paginacao_invalida_e_400_sem_consultar(cliente, mock_ibge, params, trecho):
    corpo = assert_problema(cliente.get("/v1/ufs/RJ/municipios", params=params), 400, "entrada-invalida")
    assert trecho in corpo["detail"]
    assert len(mock_ibge.calls) == 0


def test_lista_vazia_para_uf_existente_e_inesperada(cliente, mock_ibge):
    mock_ibge.get("/estados/33/municipios").mock(return_value=json_resp(b"[]"))
    assert_problema(cliente.get("/v1/ufs/RJ/municipios"), 502, "resposta-inesperada-da-fonte")


def test_df_tem_um_municipio(cliente, mock_ibge):
    mock_ibge.get("/estados/53/municipios").mock(return_value=fixture_resp("municipios-uf-53.json"))
    r = cliente.get("/v1/ufs/DF/municipios")
    assert r.json()["dados"] == [{"codigo": "5300108", "nome": "Brasília"}]
    assert r.json()["paginacao"]["paginas"] == 1
