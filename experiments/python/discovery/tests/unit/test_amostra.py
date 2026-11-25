import json

import pytest

from inventario_fontes.amostra import ErroAmostra, inferir_estrutura
from inventario_fontes.modelos import Formato, TipoCampo
from tests.conftest import ler_fixture

T = TipoCampo


def campos(estrutura) -> dict[str, tuple[TipoCampo, ...]]:
    return {c.caminho: c.tipos for c in estrutura.campos}


def test_lista_json_do_ibge():
    e = inferir_estrutura(ler_fixture("ibge_estados.json"), Formato.JSON, truncada=False)
    assert e.caminho_registros is None
    assert e.registros_inspecionados == 3
    assert campos(e) == {
        "id": (T.INTEIRO,),
        "nome": (T.TEXTO,),
        "regiao": (T.OBJETO,),
        "regiao.id": (T.INTEIRO,),
        "regiao.nome": (T.TEXTO,),
        "regiao.sigla": (T.TEXTO,),
        "sigla": (T.TEXTO,),
    }
    assert [c.caminho for c in e.campos] == sorted(c.caminho for c in e.campos)


def test_no_maximo_cinco_registros():
    corpo = json.dumps([{"i": i} for i in range(27)]).encode()
    assert inferir_estrutura(corpo, Formato.JSON, truncada=False).registros_inspecionados == 5


def test_objeto_com_lista_de_registros_da_camara():
    e = inferir_estrutura(ler_fixture("camara_deputados.json"), Formato.JSON, truncada=False)
    assert e.caminho_registros == "dados"
    assert e.registros_inspecionados == 2
    c = campos(e)
    assert c["email"] == (T.TEXTO,)
    assert c["urlFoto"] == (T.TEXTO, T.NULO)
    assert "links" not in c


def test_uniao_de_tipos_e_tipos_basicos():
    corpo = json.dumps(
        [
            {"n": 1, "d": "2026-11-24", "dh": "2026-11-24T10:00:00", "x": 1.5, "b": True, "t": "abc"},
            {"n": None, "d": "2026-11-25", "dh": "2026-11-24 10:00", "x": 2, "b": False, "t": "def"},
        ]
    ).encode()
    c = campos(inferir_estrutura(corpo, Formato.JSON, truncada=False))
    assert c["n"] == (T.INTEIRO, T.NULO)
    assert c["d"] == (T.DATA,)
    assert c["dh"] == (T.DATA,)
    assert c["x"] == (T.INTEIRO, T.DECIMAL)
    assert c["b"] == (T.BOOLEANO,)
    assert c["t"] == (T.TEXTO,)


def test_listas_aninhadas():
    corpo = json.dumps([{"itens": [{"id": 1, "tags": ["a"]}, {"id": 2, "tags": []}]}]).encode()
    c = campos(inferir_estrutura(corpo, Formato.JSON, truncada=False))
    assert c["itens"] == (T.LISTA,)
    assert c["itens[]"] == (T.OBJETO,)
    assert c["itens[].id"] == (T.INTEIRO,)
    assert c["itens[].tags[]"] == (T.TEXTO,)


def test_profundidade_maxima():
    valor: dict = {"fim": 1}
    for nivel in range(8):
        valor = {f"n{nivel}": valor}
    c = campos(inferir_estrutura(json.dumps([valor]).encode(), Formato.JSON, truncada=False))
    assert max(caminho.count(".") + 1 for caminho in c) == 5
    assert not any(caminho.endswith("fim") for caminho in c)


def test_chaves_que_parecem_dados_sao_mascaradas():
    corpo = json.dumps([{"12345678900": {"nome": "x"}, "2026-01-01": 3, "normal": 1}]).encode()
    c = campos(inferir_estrutura(corpo, Formato.JSON, truncada=False))
    assert "12345678900" not in json.dumps(list(c))
    assert "2026-01-01" not in json.dumps(list(c))
    assert "<chave>.nome" in c
    assert "normal" in c


def test_lista_vazia():
    e = inferir_estrutura(ler_fixture("vazia.json"), Formato.JSON, truncada=False)
    assert e.vazia is True
    assert e.campos == ()
    assert e.registros_inspecionados == 0


def test_json_truncado_fica_indisponivel():
    e = inferir_estrutura(b'[{"a": 1}, {"a"', Formato.JSON, truncada=True)
    assert e.indisponivel_motivo == "resposta truncada"
    assert e.campos == ()


def test_csv():
    e = inferir_estrutura(ler_fixture("dados.csv"), Formato.CSV, truncada=False)
    assert e.registros_inspecionados == 5
    assert campos(e) == {
        "atualizado_em": (T.DATA,),
        "codigo": (T.INTEIRO,),
        "municipio": (T.TEXTO,),
        "populacao_mil": (T.DECIMAL,),
    }


def test_csv_truncado_ignora_a_ultima_linha_partida():
    corpo = ler_fixture("dados.csv")[:-8]
    e = inferir_estrutura(corpo, Formato.CSV, truncada=True)
    assert e.indisponivel_motivo is None
    assert "municipio" in campos(e)


def test_xml():
    e = inferir_estrutura(ler_fixture("dados.xml"), Formato.XML, truncada=False)
    assert e.caminho_registros == "registros"
    assert e.registros_inspecionados == 5
    assert campos(e) == {"codigo": (T.INTEIRO,), "nome": (T.TEXTO,), "situacao": (T.TEXTO,)}


@pytest.mark.parametrize(
    ("corpo", "formato"),
    [(ler_fixture("json_quebrado.txt"), Formato.JSON), (b"<raiz><aberto></raiz>", Formato.XML)],
)
def test_conteudo_malformado(corpo, formato):
    with pytest.raises(ErroAmostra):
        inferir_estrutura(corpo, formato, truncada=False)


@pytest.mark.parametrize("formato", [Formato.HTML, Formato.TEXTO, Formato.VAZIO, Formato.OUTRO])
def test_formatos_sem_estrutura(formato):
    assert inferir_estrutura(b"<html></html>", formato, truncada=False) is None


def test_estrutura_nao_guarda_valores():
    texto = repr(inferir_estrutura(ler_fixture("pessoas_ficticias.json"), Formato.JSON, truncada=False))
    for valor in ["Fulana", "fulana.exemplo@teste.invalid", "000.111.222-33", "1990-04-12", "4321.5"]:
        assert valor not in texto
