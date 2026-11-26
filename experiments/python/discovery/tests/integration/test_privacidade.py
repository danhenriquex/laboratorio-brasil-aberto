"""SC-004: nenhum valor das respostas aparece nos relatórios."""

import json

import httpx
import respx

from inventario_fontes.catalogo import carregar_catalogo
from inventario_fontes.execucao import executar
from inventario_fontes.modelos import Configuracao, Situacao
from inventario_fontes.relatorio.html import renderizar_html
from inventario_fontes.relatorio.json_ import para_dict
from inventario_fontes.sonda import criar_cliente
from tests.conftest import fonte_dict, ler_fixture

FIXTURES = ["pessoas_ficticias.json", "camara_deputados.json"]


def valores_folha(dado, chaves: set[str]) -> set[str]:
    """Strings com 4+ caracteres e números com 4+ dígitos que não são nomes de chave."""
    encontrados: set[str] = set()
    if isinstance(dado, dict):
        for k, v in dado.items():
            chaves.add(k)
            encontrados |= valores_folha(v, chaves)
    elif isinstance(dado, list):
        for item in dado:
            encontrados |= valores_folha(item, chaves)
    elif isinstance(dado, bool) or dado is None:
        pass
    elif isinstance(dado, (int, float)):
        if len(str(dado).replace(".", "")) >= 4:
            encontrados.add(str(dado))
    elif isinstance(dado, str) and len(dado) >= 4:
        encontrados.add(dado)
    return encontrados


def executar_com_fixtures(catalogo_tmp, relogio):
    fontes = [fonte_dict(id=f"f{i}", probe_url=f"https://f{i}.gov.br/api") for i in range(len(FIXTURES))]
    catalogo = carregar_catalogo(catalogo_tmp(fontes))
    config = Configuracao()
    with respx.mock(assert_all_called=False) as mock:
        for i, nome in enumerate(FIXTURES):
            mock.get(f"https://f{i}.gov.br/api").mock(
                return_value=httpx.Response(200, content=ler_fixture(nome), headers={"Content-Type": "application/json"})
            )
        with criar_cliente(config) as cliente:
            return executar(catalogo, catalogo.fontes, config, cliente, relogio)


def test_relatorio_json_nao_contem_valores(catalogo_tmp, relogio):
    execucao = executar_com_fixtures(catalogo_tmp, relogio)
    assert all(r.situacao is Situacao.RESPONDEU for r in execucao.resultados)
    assert all(r.amostra is not None and r.amostra.campos for r in execucao.resultados)

    serializado = json.dumps(para_dict(execucao), ensure_ascii=False)
    chaves: set[str] = set()
    valores: set[str] = set()
    for nome in FIXTURES:
        valores |= valores_folha(json.loads(ler_fixture(nome)), chaves)
    vazados = {v for v in valores - chaves if v in serializado}
    assert vazados == set()
    # os nomes dos campos aparecem
    assert '"email"' in serializado and '"cpf"' in serializado


def test_relatorio_html_nao_contem_valores(catalogo_tmp, relogio):
    execucao = executar_com_fixtures(catalogo_tmp, relogio)
    html = renderizar_html(execucao)
    chaves: set[str] = set()
    valores: set[str] = set()
    for nome in FIXTURES:
        valores |= valores_folha(json.loads(ler_fixture(nome)), chaves)
    vazados = {v for v in valores - chaves if v in html}
    assert vazados == set()
    assert "email" in html and "cpf" in html
