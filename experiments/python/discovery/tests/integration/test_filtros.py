import json

import httpx
import pytest
import respx

from inventario_fontes.catalogo import carregar_catalogo, filtrar
from inventario_fontes.cli import main
from tests.conftest import fonte_dict

FONTES = [
    fonte_dict(id="r1-a", round=1, probe_url="https://r1-a.gov.br/api"),
    fonte_dict(id="r1-b", round=1, probe_url="https://r1-b.gov.br/api"),
    fonte_dict(id="r2-a", round=2, probe_url="https://r2-a.gov.br/api"),
    fonte_dict(id="r3-a", round=3, probe_url=None),
]


@pytest.fixture
def catalogo(catalogo_tmp):
    return catalogo_tmp(FONTES)


def rodar(catalogo, saida, relogio, *filtros):
    with respx.mock(assert_all_called=False) as mock:
        rotas = {
            f["id"]: mock.get(f["probe_url"]).mock(return_value=httpx.Response(200, json=[]))
            for f in FONTES
            if f["probe_url"]
        }
        codigo = main(["--catalogo", str(catalogo), "--saida", str(saida), *filtros], relogio=relogio)
    chamadas = {fid: rota.call_count for fid, rota in rotas.items()}
    relatorios = sorted(saida.glob("inventario-*.json"))
    dados = json.loads(relatorios[0].read_text(encoding="utf-8")) if relatorios else None
    return codigo, chamadas, dados


def test_uma_rodada(catalogo, tmp_path, relogio):
    codigo, chamadas, dados = rodar(catalogo, tmp_path, relogio, "--rodada", "1")
    assert codigo == 0
    assert chamadas == {"r1-a": 1, "r1-b": 1, "r2-a": 0}
    assert [r["fonte_id"] for r in dados["resultados"]] == ["r1-a", "r1-b"]
    assert dados["filtros"] == {"rodadas": [1], "fontes": []}
    assert dados["resumo"]["total"] == 2


def test_varias_rodadas(catalogo, tmp_path, relogio):
    codigo, chamadas, dados = rodar(catalogo, tmp_path, relogio, "--rodada", "1", "--rodada", "3")
    assert codigo == 0
    assert chamadas["r2-a"] == 0
    assert [r["fonte_id"] for r in dados["resultados"]] == ["r1-a", "r1-b", "r3-a"]
    assert dados["filtros"]["rodadas"] == [1, 3]


def test_fontes_especificas(catalogo, tmp_path, relogio):
    codigo, chamadas, dados = rodar(catalogo, tmp_path, relogio, "--fonte", "r2-a", "--fonte", "r1-b")
    assert codigo == 0
    assert chamadas == {"r1-a": 0, "r1-b": 1, "r2-a": 1}
    # mantém a ordem do catálogo
    assert [r["fonte_id"] for r in dados["resultados"]] == ["r1-b", "r2-a"]
    assert dados["filtros"]["fontes"] == ["r2-a", "r1-b"]


def test_rodada_e_fonte_combinam_por_intersecao(catalogo, tmp_path, relogio):
    codigo, chamadas, dados = rodar(catalogo, tmp_path, relogio, "--rodada", "1", "--fonte", "r1-a", "--fonte", "r2-a")
    assert codigo == 0
    assert chamadas == {"r1-a": 1, "r1-b": 0, "r2-a": 0}
    assert [r["fonte_id"] for r in dados["resultados"]] == ["r1-a"]


def test_fonte_inexistente_sai_com_dois(catalogo, tmp_path, relogio, capsys):
    codigo, chamadas, dados = rodar(catalogo, tmp_path, relogio, "--fonte", "nao-existe")
    assert codigo == 2
    assert set(chamadas.values()) == {0}
    assert dados is None
    assert "nao-existe" in capsys.readouterr().err


def test_filtro_sem_nenhuma_fonte_sai_com_dois(catalogo, tmp_path, relogio, capsys):
    codigo, chamadas, dados = rodar(catalogo, tmp_path, relogio, "--rodada", "9")
    assert codigo == 2
    assert set(chamadas.values()) == {0}
    assert dados is None
    assert "nenhuma fonte" in capsys.readouterr().err


def test_filtrar_direto(catalogo):
    fontes = carregar_catalogo(catalogo).fontes
    assert [f.id for f in filtrar(fontes, [], [])] == ["r1-a", "r1-b", "r2-a", "r3-a"]
    assert [f.id for f in filtrar(fontes, [2], [])] == ["r2-a"]
    with pytest.raises(ValueError, match="x, y"):
        filtrar(fontes, [], ["x", "r1-a", "y"])
