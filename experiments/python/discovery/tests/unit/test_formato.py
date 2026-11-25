import pytest

from inventario_fontes.formato import detectar_formato, divergente, formato_declarado
from inventario_fontes.modelos import Formato
from tests.conftest import ler_fixture


@pytest.mark.parametrize(
    ("corpo", "esperado"),
    [
        (b'{"a": 1}', Formato.JSON),
        (b"[1, 2]", Formato.JSON),
        (b'\xef\xbb\xbf  \n {"a": 1}', Formato.JSON),
        (b'<?xml version="1.0"?><raiz/>', Formato.XML),
        (b"<raiz><item/></raiz>", Formato.XML),
        (b"<!DOCTYPE html><html><body></body></html>", Formato.HTML),
        (b"<!doctype HTML>\n<html>", Formato.HTML),
        (b"<HTML><body>oi</body></HTML>", Formato.HTML),
        (b"", Formato.VAZIO),
        (b"   \n ", Formato.VAZIO),
        (b"linha um\nlinha dois\nlinha tres", Formato.TEXTO),
        (bytes(range(256)), Formato.OUTRO),
    ],
)
def test_detectar_formato(corpo, esperado):
    assert detectar_formato(corpo) is esperado


def test_csv():
    assert detectar_formato(ler_fixture("dados.csv")) is Formato.CSV


def test_csv_com_ponto_e_virgula_em_latin1():
    corpo = "município;código\nJoão Pessoa;2507507\nCampina Grande;2504009\n".encode("latin-1")
    assert detectar_formato(corpo) is Formato.CSV


def test_html_e_xml_das_fixtures():
    assert detectar_formato(ler_fixture("erro.html")) is Formato.HTML
    assert detectar_formato(ler_fixture("dados.xml")) is Formato.XML


@pytest.mark.parametrize(
    ("content_type", "esperado"),
    [
        ("application/json; charset=utf-8", "application/json"),
        ("Text/HTML", "text/html"),
        (None, None),
        ("", None),
    ],
)
def test_formato_declarado(content_type, esperado):
    assert formato_declarado(content_type) == esperado


@pytest.mark.parametrize(
    ("declarado", "detectado", "esperado"),
    [
        ("application/json", Formato.HTML, True),
        ("application/json", Formato.JSON, False),
        ("application/vnd.api+json", Formato.JSON, False),
        ("text/csv", Formato.CSV, False),
        ("text/plain", Formato.CSV, False),
        ("application/xml", Formato.XML, False),
        ("text/html", Formato.JSON, True),
        (None, Formato.JSON, False),
        ("application/octet-stream", Formato.CSV, False),
        ("application/json", Formato.VAZIO, False),
    ],
)
def test_divergente(declarado, detectado, esperado):
    assert divergente(declarado, detectado) is esperado
