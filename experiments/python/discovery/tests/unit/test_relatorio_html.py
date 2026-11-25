import json
import re
from datetime import UTC, datetime

import pytest

from inventario_fontes.avaliacao import avaliar
from inventario_fontes.execucao import AVISO
from inventario_fontes.modelos import (
    Auth,
    CampoAmostra,
    Causa,
    Configuracao,
    EstruturaAmostra,
    Execucao,
    Fonte,
    Formato,
    Grau,
    ResultadoSondagem,
    Resumo,
    Situacao,
    TipoCampo,
)
from inventario_fontes.relatorio.html import renderizar_html
from inventario_fontes.relatorio.json_ import para_dict

COLETA = datetime(2026, 11, 25, 13, 5, 7, tzinfo=UTC)


def fonte(id_: str, nome: str | None = None, auth: str = "nenhuma (hipótese)", docs: str | None = "https://exemplo.gov.br/docs") -> Fonte:
    return Fonte(
        id=id_,
        nome=nome or f"Fonte {id_}",
        dominio="economia",
        url_documentacao=docs,
        url_teste=f"https://{id_}.gov.br/api",
        tipos_dado=("api",),
        hipotese_acesso="facil",
        auth_esperada=auth,
        verificacao=Grau.PARCIAL,
        rodada=1,
    )


@pytest.fixture
def execucao() -> Execucao:
    ok = fonte("ok", nome="<script>alert(1)</script>")
    chave = fonte("chave")
    sem = fonte("sem-probe", docs=None)
    resultados = [
        avaliar(
            ok,
            ResultadoSondagem.base(
                ok,
                Situacao.RESPONDEU,
                status_http=200,
                latencia_ms=312.4,
                coletado_em=COLETA,
                formato_declarado="application/json",
                formato_detectado=Formato.JSON,
                tamanho_bytes=2048,
                auth_observada=Auth.NAO_EXIGE,
                amostra=EstruturaAmostra(
                    3,
                    None,
                    (CampoAmostra("regiao.sigla", (TipoCampo.TEXTO,)), CampoAmostra("id", (TipoCampo.INTEIRO, TipoCampo.NULO))),
                ),
            ),
        ),
        avaliar(
            chave,
            ResultadoSondagem.base(
                chave,
                Situacao.FALHOU,
                causa=Causa.EXIGE_AUTENTICACAO,
                detalhe_causa="status 401",
                status_http=401,
                latencia_ms=90.0,
                coletado_em=COLETA,
                auth_observada=Auth.EXIGE,
                indicio_autenticacao="status 401",
            ),
        ),
        avaliar(sem, ResultadoSondagem.base(sem, Situacao.SEM_TESTE)),
    ]
    return Execucao(
        ferramenta="inventario-fontes 0.1.0",
        catalogo_caminho="discovery/sources.json",
        catalogo_schema_version=1,
        iniciada_em=COLETA,
        finalizada_em=COLETA,
        interrompida=False,
        configuracao=Configuracao(),
        aviso=AVISO,
        resumo=Resumo.de_resultados(resultados),
        resultados=tuple(resultados),
    )


def linhas(html: str) -> dict[str, str]:
    return {m.group(1): m.group(0) for m in re.finditer(r'<tr[^>]*data-fonte="([^"]+)"[^>]*>.*?</tr>', html, re.S)}


def test_uma_linha_por_fonte_com_os_mesmos_ids_do_json(execucao):
    html = renderizar_html(execucao)
    ids_html = list(linhas(html))
    ids_json = [r["fonte_id"] for r in para_dict(execucao)["resultados"]]
    assert ids_html == ids_json
    assert html.count("data-fonte=") == len(execucao.resultados)


def test_linha_traz_os_dados_da_fonte(execucao):
    linha = linhas(renderizar_html(execucao))["chave"]
    for trecho in ["Fonte chave", "economia", "parcial", "confirmado", "facil", "exige_autenticacao", "401", "https://exemplo.gov.br/docs"]:
        assert trecho in linha


def test_divergencia_de_autenticacao_e_destacada(execucao):
    tabela = linhas(renderizar_html(execucao))
    assert re.search(r'class="[^"]*divergente', tabela["chave"])
    assert "nao_exige" in tabela["chave"] and "exige (status 401)" in tabela["chave"]
    assert not re.search(r'class="[^"]*divergente', tabela["ok"])


def test_horario_em_utc_e_brasilia(execucao):
    linha = linhas(renderizar_html(execucao))["ok"]
    assert "2026-11-25 13:05:07 UTC" in linha
    assert "10:05:07 (Brasília)" in linha


def test_aviso_e_resumo(execucao):
    html = renderizar_html(execucao)
    assert AVISO in html
    assert "3 fontes" in html
    assert "1 responderam" in html


def test_texto_do_catalogo_e_escapado(execucao):
    html = renderizar_html(execucao)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_autocontido_sem_recursos_externos(execucao):
    html = renderizar_html(execucao)
    assert "<script" not in html.lower()
    assert "<link" not in html.lower()
    assert "src=" not in html
    permitidos = {"https://exemplo.gov.br/docs", "https://ok.gov.br/api", "https://chave.gov.br/api", "https://sem-probe.gov.br/api"}
    assert set(re.findall(r'href="([^"]+)"', html)) <= permitidos


def test_sem_teste_e_documentacao_nao_localizada(execucao):
    linha = linhas(renderizar_html(execucao))["sem-probe"]
    assert "sem teste automatizado" in linha
    assert "documentação oficial não localizada" in linha


def test_amostra_aparece_como_caminho_e_tipos(execucao):
    linha = linhas(renderizar_html(execucao))["ok"]
    assert "<details>" in linha
    assert "regiao.sigla" in linha and "inteiro, nulo" in linha


def test_execucao_interrompida_e_sinalizada(execucao):
    from dataclasses import replace

    html = renderizar_html(replace(execucao, interrompida=True))
    assert "interrompida" in html.lower()


def test_json_e_html_tem_o_mesmo_conteudo(execucao):
    dados = para_dict(execucao)
    html = renderizar_html(execucao)
    for r in dados["resultados"]:
        assert r["situacao"].replace("_", " ") in html or r["situacao"] in html
    assert json.dumps(dados)  # serializável
