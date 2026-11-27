import httpx
import pytest

from tests.conftest import item_da_uf, ler_fixture
from tests.integration.conftest import assert_problema, fixture_resp

ROTA = "/municipios/3304557"
URL = "/v1/municipios/3304557"


def ok():
    return httpx.Response(200, json=item_da_uf("33", 3304557))


@pytest.mark.parametrize(
    ("efeito", "status", "tipo"),
    [
        ({"side_effect": httpx.ConnectError("[Errno 61] Connection refused to 10.0.0.7")}, 502, "fonte-indisponivel"),
        ({"return_value": httpx.Response(503, text="Traceback interno do IBGE")}, 502, "fonte-indisponivel"),
        ({"side_effect": httpx.ReadTimeout("timed out")}, 504, "fonte-lenta"),
        (
            {"return_value": httpx.Response(200, content=ler_fixture("erro.html"), headers={"Content-Type": "text/html"})},
            502,
            "resposta-inesperada-da-fonte",
        ),
    ],
)
def test_falha_da_fonte_sem_copia(cliente, mock_ibge, efeito, status, tipo):
    mock_ibge.get(ROTA).mock(**efeito)
    corpo = assert_problema(cliente.get(URL), status, tipo)
    texto = str(corpo)
    for proibido in ("Traceback", "<html", "10.0.0.7", "Errno", "Página de erro"):
        assert proibido not in texto


def test_copia_valida_evita_nova_consulta(cliente, mock_ibge, relogio):
    rota = mock_ibge.get(ROTA).mock(return_value=ok())
    primeira = cliente.get(URL).json()
    relogio.avancar(3600)
    segunda = cliente.get(URL).json()
    assert rota.call_count == 1
    assert segunda["meta"]["coletado_em"] == primeira["meta"]["coletado_em"]
    assert segunda["meta"]["desatualizado"] is False


def test_copia_vencida_servida_quando_a_fonte_falha(cliente, mock_ibge, relogio):
    rota = mock_ibge.get(ROTA).mock(return_value=ok())
    primeira = cliente.get(URL).json()
    relogio.avancar(86400 + 1)
    rota.mock(side_effect=httpx.ConnectError("fora"))
    r = cliente.get(URL)
    assert r.status_code == 200
    assert r.json()["meta"]["desatualizado"] is True
    assert r.json()["meta"]["coletado_em"] == primeira["meta"]["coletado_em"]
    assert r.json()["dados"] == primeira["dados"]


def test_copia_vencida_renovada_quando_a_fonte_responde(cliente, mock_ibge, relogio):
    rota = mock_ibge.get(ROTA).mock(return_value=ok())
    primeira = cliente.get(URL).json()
    relogio.avancar(86400 + 1)
    segunda = cliente.get(URL).json()
    assert rota.call_count == 2
    assert segunda["meta"]["desatualizado"] is False
    assert segunda["meta"]["coletado_em"] > primeira["meta"]["coletado_em"]


def test_falha_num_pedido_nao_afeta_o_seguinte(cliente, mock_ibge):
    mock_ibge.get(ROTA).mock(side_effect=httpx.ReadTimeout("lento"))
    mock_ibge.get("/estados/53/municipios").mock(return_value=fixture_resp("municipios-uf-53.json"))
    assert cliente.get(URL).status_code == 504
    assert cliente.get("/v1/ufs/DF/municipios").status_code == 200


def test_listas_tambem_usam_a_copia(cliente, mock_ibge, relogio):
    rota = mock_ibge.get("/estados/33/municipios").mock(return_value=fixture_resp("municipios-uf-33.json"))
    cliente.get("/v1/ufs/RJ/municipios")
    cliente.get("/v1/ufs/rj/municipios", params={"pagina": 2, "itens": 10})
    cliente.get("/v1/ufs/33/municipios")
    assert rota.call_count == 1
