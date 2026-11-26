import pytest

from localidades.dominio import (
    UFS_OFICIAIS,
    MunicipioResumido,
    chave_ordenacao,
    dobrar,
    filtrar_por_nome,
    ordenar,
    paginar,
    resolver_uf,
    validar_codigo_municipio,
    validar_nome,
    validar_paginacao,
)
from localidades.erros import EntradaInvalida, NaoEncontrado


def m(codigo: str, nome: str) -> MunicipioResumido:
    return MunicipioResumido(codigo=codigo, nome=nome)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("Niterói", "niteroi"), ("SÃO", "sao"), ("Santa Bárbara d'Oeste", "santa barbara d'oeste"), ("Açu", "acu")],
)
def test_dobrar(entrada, esperado):
    assert dobrar(entrada) == esperado


def test_ufs_oficiais_tem_27():
    assert len(UFS_OFICIAIS) == 27
    assert UFS_OFICIAIS["33"] == "RJ"
    assert UFS_OFICIAIS["53"] == "DF"
    assert len(set(UFS_OFICIAIS.values())) == 27


def test_ordenar_ignora_acento_e_caixa_e_desempata_pelo_codigo():
    itens = [m("3300001", "Óbidos"), m("3300003", "abc"), m("3300002", "Abc"), m("3300004", "Niterói")]
    ordenados = ordenar(itens)
    assert [x.codigo for x in ordenados] == ["3300002", "3300003", "3300004", "3300001"]
    assert chave_ordenacao(m("1", "Á")) == ("a", "1")


def test_filtrar_por_nome():
    itens = [m("1", "São Gonçalo"), m("2", "Niterói"), m("3", "Paraíso")]
    assert [x.codigo for x in filtrar_por_nome(itens, "  SAO ")] == ["1"]
    assert [x.codigo for x in filtrar_por_nome(itens, "ni")] == ["2"]
    assert filtrar_por_nome(itens, "zzz") == []


def test_paginar():
    itens = [m(str(i), f"n{i}") for i in range(7)]
    p = paginar(itens, pagina=2, itens=3)
    assert [x.codigo for x in p.itens] == ["3", "4", "5"]
    assert (p.pagina, p.tamanho, p.total, p.paginas) == (2, 3, 7, 3)
    ultima = paginar(itens, pagina=3, itens=3)
    assert [x.codigo for x in ultima.itens] == ["6"]
    alem = paginar(itens, pagina=10, itens=3)
    assert alem.itens == [] and alem.total == 7 and alem.paginas == 3
    vazia = paginar([], pagina=1, itens=100)
    assert (vazia.total, vazia.paginas) == (0, 0)


@pytest.mark.parametrize(("entrada", "codigo"), [(" rj ", "33"), ("RJ", "33"), ("33", "33"), ("df", "53"), (" 35", "35")])
def test_resolver_uf(entrada, codigo):
    assert resolver_uf(entrada) == codigo


@pytest.mark.parametrize("entrada", ["XX", "99", "zz", "10"])
def test_resolver_uf_inexistente(entrada):
    with pytest.raises(NaoEncontrado):
        resolver_uf(entrada)


@pytest.mark.parametrize("entrada", ["R1", "123", "", "   ", "R", "RJX", "3"])
def test_resolver_uf_mal_formada(entrada):
    with pytest.raises(EntradaInvalida):
        resolver_uf(entrada)


@pytest.mark.parametrize("codigo", ["3304557", "5300108"])
def test_codigo_municipio_valido(codigo):
    assert validar_codigo_municipio(codigo) == codigo


@pytest.mark.parametrize("codigo", ["12ab", "123456", "12345678", "", "330455７"])
def test_codigo_municipio_invalido(codigo):
    with pytest.raises(EntradaInvalida):
        validar_codigo_municipio(codigo)


def test_validar_paginacao():
    validar_paginacao(1, 1, 500)
    validar_paginacao(3, 500, 500)
    with pytest.raises(EntradaInvalida, match="500"):
        validar_paginacao(1, 501, 500)
    with pytest.raises(EntradaInvalida, match="500"):
        validar_paginacao(1, 0, 500)
    with pytest.raises(EntradaInvalida, match="pagina"):
        validar_paginacao(0, 10, 500)


def test_validar_nome():
    assert validar_nome("  niteroi ") == "niteroi"
    assert validar_nome("sã") == "sã"
    with pytest.raises(EntradaInvalida, match="2"):
        validar_nome(" a ")
    with pytest.raises(EntradaInvalida, match="60"):
        validar_nome("x" * 61)
