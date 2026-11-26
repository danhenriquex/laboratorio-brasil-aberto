import pytest

from localidades.config import Configuracao


def test_padroes():
    c = Configuracao.do_ambiente({})
    assert c.host == "127.0.0.1"
    assert c.porta == 8000
    assert c.ibge_url == "https://servicodados.ibge.gov.br/api/v1/localidades"
    assert c.prazo_fonte_s == 10
    assert c.validade_s == 86400
    assert c.itens_max == 500


def test_leitura_do_ambiente():
    c = Configuracao.do_ambiente(
        {
            "LOCALIDADES_HOST": "0.0.0.0",
            "LOCALIDADES_PORTA": "8090",
            "LOCALIDADES_IBGE_URL": "http://127.0.0.1:8099/api/v1/localidades/",
            "LOCALIDADES_PRAZO_FONTE_S": "1.5",
            "LOCALIDADES_VALIDADE_S": "2",
            "LOCALIDADES_ITENS_MAX": "50",
        }
    )
    assert (c.host, c.porta, c.prazo_fonte_s, c.validade_s, c.itens_max) == ("0.0.0.0", 8090, 1.5, 2, 50)
    assert c.ibge_url == "http://127.0.0.1:8099/api/v1/localidades"  # sem barra final


@pytest.mark.parametrize(
    ("variavel", "valor"),
    [
        ("LOCALIDADES_PORTA", "abc"),
        ("LOCALIDADES_PORTA", "0"),
        ("LOCALIDADES_PRAZO_FONTE_S", "-1"),
        ("LOCALIDADES_PRAZO_FONTE_S", "0"),
        ("LOCALIDADES_VALIDADE_S", "x"),
        ("LOCALIDADES_ITENS_MAX", "0"),
        ("LOCALIDADES_IBGE_URL", "ftp://ibge"),
    ],
)
def test_valores_invalidos(variavel, valor):
    with pytest.raises(ValueError, match=variavel):
        Configuracao.do_ambiente({variavel: valor})
