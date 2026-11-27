import pytest

from localidades.dominio import dobrar
from tests.conftest import fixture_json
from tests.integration.conftest import assert_problema, fixture_resp


@pytest.fixture
def rj(mock_ibge):
    return mock_ibge.get("/estados/33/municipios").mock(return_value=fixture_resp("municipios-uf-33.json"))


@pytest.mark.parametrize("termo", ["niteroi", "NITERÓI", "  Niterói  "])
def test_busca_sem_acento_e_sem_caixa(cliente, rj, termo):
    r = cliente.get("/v1/ufs/RJ/municipios", params={"nome": termo})
    assert r.status_code == 200
    assert r.json()["dados"] == [{"codigo": "3303302", "nome": "Niterói"}]
    assert r.json()["paginacao"] == {"pagina": 1, "itens": 100, "total": 1, "paginas": 1}


def test_busca_com_varios_resultados(cliente, rj):
    esperados = sorted(
        (m for m in fixture_json("municipios-uf-33.json") if "sao" in dobrar(m["nome"])),
        key=lambda m: (dobrar(m["nome"]), str(m["id"])),
    )
    r = cliente.get("/v1/ufs/RJ/municipios", params={"nome": "são", "itens": 5})
    corpo = r.json()
    assert corpo["paginacao"]["total"] == len(esperados) > 5
    assert [m["nome"] for m in corpo["dados"]] == [m["nome"] for m in esperados[:5]]
    pagina_2 = cliente.get("/v1/ufs/RJ/municipios", params={"nome": "são", "itens": 5, "pagina": 2}).json()
    assert [m["nome"] for m in pagina_2["dados"]] == [m["nome"] for m in esperados[5:10]]


def test_busca_sem_resultado(cliente, rj):
    r = cliente.get("/v1/ufs/RJ/municipios", params={"nome": "xyzw"})
    assert r.status_code == 200
    assert r.json()["dados"] == []
    assert r.json()["paginacao"] == {"pagina": 1, "itens": 100, "total": 0, "paginas": 0}


@pytest.mark.parametrize(("termo", "trecho"), [("a", "2"), ("  a  ", "2"), ("", "2"), ("x" * 61, "60")])
def test_busca_invalida_e_400_sem_consultar(cliente, mock_ibge, termo, trecho):
    corpo = assert_problema(cliente.get("/v1/ufs/RJ/municipios", params={"nome": termo}), 400, "entrada-invalida")
    assert trecho in corpo["detail"]
    assert len(mock_ibge.calls) == 0


def test_duas_buscas_uma_consulta(cliente, rj):
    cliente.get("/v1/ufs/RJ/municipios", params={"nome": "niteroi"})
    cliente.get("/v1/ufs/RJ/municipios", params={"nome": "são"})
    assert rj.call_count == 1
