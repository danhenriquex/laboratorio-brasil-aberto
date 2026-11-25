import json

import httpx
import pytest
import respx

from inventario_fontes import __version__
from inventario_fontes.cli import main
from tests.conftest import fonte_dict


def _interromper(request):
    raise KeyboardInterrupt


def url(nome: str) -> str:
    return f"https://{nome}.gov.br/api"


@pytest.fixture
def catalogo(catalogo_tmp):
    return catalogo_tmp(
        [
            fonte_dict(id="ibge-teste", probe_url=url("ibge")),
            fonte_dict(id="fora-do-ar", probe_url=url("fora")),
            fonte_dict(id="sem-probe", probe_url=None),
        ]
    )


def rodar(argv, relogio):
    return main([str(a) for a in argv], relogio=relogio)


def test_execucao_normal_com_falha_sai_com_zero(catalogo, tmp_path, relogio, capsys):
    saida = tmp_path / "reports" / "novo"
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url("ibge")).mock(return_value=httpx.Response(200, json=[{"id": 1}]))
        mock.get(url("fora")).mock(side_effect=httpx.ConnectError("recusada"))
        codigo = rodar(["--catalogo", catalogo, "--saida", saida], relogio)

    assert codigo == 0
    relatorios = sorted(saida.glob("inventario-*.json"))
    assert len(relatorios) == 1
    dados = json.loads(relatorios[0].read_text(encoding="utf-8"))
    assert dados["resumo"]["total"] == 3

    out = capsys.readouterr().out
    linhas = out.splitlines()
    assert linhas[0].startswith("[1/3] ibge-teste ")
    assert "respondeu" in linhas[0] and "200" in linhas[0] and "json" in linhas[0] and " ms" in linhas[0]
    assert linhas[1].startswith("[2/3] fora-do-ar ") and "falhou" in linhas[1] and "indisponivel" in linhas[1]
    assert linhas[2].startswith("[3/3] sem-probe ") and "sem teste automatizado" in linhas[2]
    assert "3 fontes: 1 responderam, 1 falharam, 1 sem teste" in out
    assert str(relatorios[0]) in out


def test_catalogo_inexistente_sai_com_um(tmp_path, relogio, capsys):
    saida = tmp_path / "saida"
    with respx.mock(assert_all_called=False) as mock:
        codigo = rodar(["--catalogo", tmp_path / "nao-existe.json", "--saida", saida], relogio)
        assert len(mock.calls) == 0
    assert codigo == 1
    assert "não encontrado" in capsys.readouterr().err
    assert not saida.exists()


def test_catalogo_invalido_sai_com_um(catalogo_tmp, tmp_path, relogio, capsys):
    caminho = catalogo_tmp([fonte_dict(round=0)])
    codigo = rodar(["--catalogo", caminho, "--saida", tmp_path / "saida"], relogio)
    assert codigo == 1
    assert "fonte[0] (fonte-teste): campo round" in capsys.readouterr().err


@pytest.mark.parametrize("args", [["--intervalo", "0.5"], ["--tempo-limite", "61"], ["--tempo-limite", "0"], ["--opcao-inexistente"]])
def test_uso_incorreto_sai_com_dois(catalogo, tmp_path, relogio, args):
    with respx.mock(assert_all_called=False) as mock:
        codigo = rodar(["--catalogo", catalogo, "--saida", tmp_path, *args], relogio)
        assert len(mock.calls) == 0
    assert codigo == 2


def test_versao(relogio, capsys):
    assert rodar(["--versao"], relogio) == 0
    assert __version__ in capsys.readouterr().out


def test_interrupcao_sai_com_130_e_grava_relatorio(catalogo, tmp_path, relogio):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url("ibge")).mock(return_value=httpx.Response(200, json=[]))
        mock.get(url("fora")).mock(side_effect=_interromper)
        codigo = rodar(["--catalogo", catalogo, "--saida", tmp_path], relogio)
    assert codigo == 130
    dados = json.loads(next(tmp_path.glob("inventario-*.json")).read_text(encoding="utf-8"))
    assert dados["interrompida"] is True
