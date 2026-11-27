import httpx
import pytest

from tests.conftest import IBGE, item_da_uf
from tests.integration.conftest import assert_meta, assert_problema, fixture_resp, json_resp


def test_municipio_existente(cliente, mock_ibge):
    rota = mock_ibge.get("/municipios/3304557").mock(return_value=httpx.Response(200, json=item_da_uf("33", 3304557)))
    r = cliente.get("/v1/municipios/3304557")
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"dados", "meta"}
    assert corpo["dados"] == {
        "codigo": "3304557",
        "nome": "Rio de Janeiro",
        "uf": {"codigo": "33", "sigla": "RJ", "nome": "Rio de Janeiro"},
        "regiao_imediata": {"codigo": "330001", "nome": "Rio de Janeiro"},
        "regiao_intermediaria": {"codigo": "3301", "nome": "Rio de Janeiro"},
    }
    assert_meta(corpo["meta"], f"{IBGE}/municipios/3304557")
    assert rota.call_count == 1


def test_codigo_inexistente_e_404(cliente, mock_ibge):
    mock_ibge.get("/municipios/9999999").mock(return_value=json_resp(b"[]"))
    assert_problema(cliente.get("/v1/municipios/9999999"), 404, "nao-encontrado")


@pytest.mark.parametrize("codigo", ["12ab", "123456", "12345678", "330455%EF%BC%97"])
def test_codigo_mal_formado_e_400_sem_consultar(cliente, mock_ibge, codigo):
    assert_problema(cliente.get(f"/v1/municipios/{codigo}"), 400, "entrada-invalida")
    assert len(mock_ibge.calls) == 0


def test_nome_com_apostrofo_sai_como_o_ibge_publica(cliente, mock_ibge):
    item = item_da_uf("35", 3545803)
    mock_ibge.get("/municipios/3545803").mock(return_value=httpx.Response(200, json=item))
    r = cliente.get("/v1/municipios/3545803")
    assert r.json()["dados"]["nome"] == item["nome"] == "Santa Bárbara d'Oeste"


def test_municipio_sem_microrregiao(cliente, mock_ibge):
    mock_ibge.get("/municipios/5101837").mock(return_value=fixture_resp("municipio-5101837.json"))
    r = cliente.get("/v1/municipios/5101837")
    assert r.status_code == 200
    assert r.json()["dados"]["uf"]["sigla"] == "MT"


def test_municipio_sem_regiao_imediata_e_502(cliente, mock_ibge):
    mock_ibge.get("/municipios/3304557").mock(return_value=fixture_resp("municipio-sem-regiao-imediata.json"))
    assert_problema(cliente.get("/v1/municipios/3304557"), 502, "resposta-inesperada-da-fonte")
