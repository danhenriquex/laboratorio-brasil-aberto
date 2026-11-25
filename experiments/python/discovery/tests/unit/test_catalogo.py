from pathlib import Path

import pytest

from inventario_fontes.catalogo import ErroCatalogo, carregar_catalogo
from inventario_fontes.modelos import Auth, Grau
from tests.conftest import fonte_dict

RAIZ = Path(__file__).resolve().parents[5]


def test_catalogo_real_do_repositorio_e_valido():
    catalogo = carregar_catalogo(RAIZ / "discovery" / "sources.json")
    assert catalogo.schema_version == 1
    ids = [f.id for f in catalogo.fontes]
    assert {"ibge-localidades", "bcb-sgs", "bcb-ifdata", "camara-dados-abertos"} <= set(ids)
    ifdata = next(f for f in catalogo.fontes if f.id == "bcb-ifdata")
    assert ifdata.url_teste == "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
    datajud = next(f for f in catalogo.fontes if f.id == "datajud")
    assert datajud.url_documentacao is None


def test_docs_url_nulo_e_aceito(catalogo_tmp):
    fonte = carregar_catalogo(catalogo_tmp([fonte_dict(docs_url=None)])).fontes[0]
    assert fonte.url_documentacao is None


def test_mapeia_campos_do_catalogo(catalogo_tmp):
    caminho = catalogo_tmp([fonte_dict(id="a", notes="obs", data_type=["api", "csv"], round=2)])
    fonte = carregar_catalogo(caminho).fontes[0]
    assert fonte.id == "a"
    assert fonte.nome == "Fonte de teste"
    assert fonte.dominio == "teste"
    assert fonte.url_documentacao == "https://exemplo.gov.br/docs"
    assert fonte.url_teste == "https://exemplo.gov.br/api/dados"
    assert fonte.tipos_dado == ("api", "csv")
    assert fonte.hipotese_acesso == "facil"
    assert fonte.verificacao is Grau.PARCIAL
    assert fonte.rodada == 2
    assert fonte.notas == "obs"


def test_probe_url_nulo_vira_none(catalogo_tmp):
    fonte = carregar_catalogo(catalogo_tmp([fonte_dict(probe_url=None)])).fontes[0]
    assert fonte.url_teste is None


def test_campos_desconhecidos_sao_ignorados(catalogo_tmp):
    fonte = carregar_catalogo(catalogo_tmp([fonte_dict(extra="x", outra=1)])).fontes[0]
    assert fonte.id == "fonte-teste"


@pytest.mark.parametrize(
    ("override", "trecho"),
    [
        ({"id": "Com Espaço"}, "campo id"),
        ({"name": ""}, "campo name"),
        ({"docs_url": "ftp://x"}, "campo docs_url"),
        ({"probe_url": "exemplo.gov.br"}, "campo probe_url"),
        ({"data_type": []}, "campo data_type"),
        ({"verification": "talvez"}, "campo verification"),
        ({"round": 0}, "campo round"),
        ({"round": "1"}, "campo round"),
    ],
)
def test_regras_de_validacao(catalogo_tmp, override, trecho):
    with pytest.raises(ErroCatalogo) as erro:
        carregar_catalogo(catalogo_tmp([fonte_dict(**override)]))
    assert any(p.startswith("fonte[0] (") and trecho in p for p in erro.value.problemas)


def test_campo_obrigatorio_ausente(catalogo_tmp):
    dados = fonte_dict()
    del dados["auth"]
    with pytest.raises(ErroCatalogo) as erro:
        carregar_catalogo(catalogo_tmp([dados]))
    assert erro.value.problemas == ["fonte[0] (fonte-teste): campo auth ausente"]


def test_id_duplicado(catalogo_tmp):
    with pytest.raises(ErroCatalogo) as erro:
        carregar_catalogo(catalogo_tmp([fonte_dict(), fonte_dict()]))
    assert any("fonte[1] (fonte-teste): campo id duplicado" in p for p in erro.value.problemas)


def test_reporta_varios_problemas_de_uma_vez(catalogo_tmp):
    with pytest.raises(ErroCatalogo) as erro:
        carregar_catalogo(catalogo_tmp([fonte_dict(round=0), fonte_dict(id="b", verification="x")]))
    assert len(erro.value.problemas) == 2


def test_arquivo_ausente(tmp_path):
    with pytest.raises(ErroCatalogo) as erro:
        carregar_catalogo(tmp_path / "nao-existe.json")
    assert "não encontrado" in erro.value.problemas[0]


def test_json_invalido(tmp_path):
    caminho = tmp_path / "sources.json"
    caminho.write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(ErroCatalogo) as erro:
        carregar_catalogo(caminho)
    assert "JSON inválido" in erro.value.problemas[0]


def test_sem_lista_de_fontes(tmp_path):
    caminho = tmp_path / "sources.json"
    caminho.write_text('{"schema_version": 1}', encoding="utf-8")
    with pytest.raises(ErroCatalogo):
        carregar_catalogo(caminho)


def test_nao_altera_o_arquivo(catalogo_tmp):
    caminho = catalogo_tmp([fonte_dict()])
    antes = caminho.read_bytes()
    carregar_catalogo(caminho)
    assert caminho.read_bytes() == antes


@pytest.mark.parametrize(
    ("auth", "esperado"),
    [
        ("nenhuma (hipótese)", Auth.NAO_EXIGE),
        ("Nenhuma", Auth.NAO_EXIGE),
        ("chave de API, emitida após autenticação gov.br", Auth.EXIGE),
    ],
)
def test_hipotese_auth(catalogo_tmp, auth, esperado):
    fonte = carregar_catalogo(catalogo_tmp([fonte_dict(auth=auth)])).fontes[0]
    assert fonte.hipotese_auth is esperado
