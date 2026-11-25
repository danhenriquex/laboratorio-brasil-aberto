"""O relatório JSON gerado cumpre o contrato em specs/001-inventario-fontes/contracts/."""

import json
import re
import ssl
from pathlib import Path

import httpx
import jsonschema
import pytest
import respx

from inventario_fontes.catalogo import carregar_catalogo
from inventario_fontes.execucao import executar
from inventario_fontes.modelos import Causa, Configuracao, Situacao
from inventario_fontes.relatorio.json_ import base_relatorio, gravar_json, para_dict
from inventario_fontes.sonda import criar_cliente
from tests.conftest import fonte_dict, ler_fixture

RAIZ = Path(__file__).resolve().parents[5]
SCHEMA = json.loads((RAIZ / "specs/001-inventario-fontes/contracts/relatorio.schema.json").read_text(encoding="utf-8"))
VALIDADOR = jsonschema.Draft202012Validator(SCHEMA)
CONFIG = Configuracao()


def _interromper(request):
    raise KeyboardInterrupt


def _tls():
    erro = httpx.ConnectError("tls")
    erro.__cause__ = ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED")
    return erro


CENARIOS = {
    "ok": httpx.Response(200, content=ler_fixture("ibge_estados.json"), headers={"Content-Type": "application/json"}),
    "tempo": httpx.ReadTimeout("t"),
    "fora": httpx.ConnectError("recusada"),
    "tls": _tls(),
    "chave": httpx.Response(401),
    "negado": httpx.Response(403),
    "limite": httpx.Response(429, headers={"Retry-After": "60"}),
    "erro-fonte": httpx.Response(503),
    "nao-achou": httpx.Response(404),
    "quebrado": httpx.Response(200, content=ler_fixture("json_quebrado.txt")),
    "html": httpx.Response(200, content=ler_fixture("erro.html"), headers={"Content-Type": "application/json"}),
}


def _rodar(catalogo_tmp, relogio, interromper_em: str | None = None):
    fontes = [fonte_dict(id=nome, probe_url=f"https://{nome}.gov.br/api") for nome in CENARIOS]
    fontes.append(fonte_dict(id="sem-probe", probe_url=None, docs_url=None))
    catalogo = carregar_catalogo(catalogo_tmp(fontes))
    with respx.mock(assert_all_called=False) as mock:
        for nome, resposta in CENARIOS.items():
            rota = mock.get(f"https://{nome}.gov.br/api")
            if nome == interromper_em:
                rota.mock(side_effect=_interromper)
            elif isinstance(resposta, Exception):
                rota.mock(side_effect=resposta)
            else:
                rota.mock(return_value=resposta)
        with criar_cliente(CONFIG) as cliente:
            return executar(catalogo, catalogo.fontes, CONFIG, cliente, relogio)


def test_relatorio_cobre_todas_as_causas_e_valida(catalogo_tmp, relogio):
    execucao = _rodar(catalogo_tmp, relogio)
    dados = para_dict(execucao)
    VALIDADOR.validate(dados)
    causas = {r["causa"] for r in dados["resultados"] if r["causa"]}
    assert causas == {c.value for c in Causa}
    assert {r["situacao"] for r in dados["resultados"]} >= {"respondeu", "falhou", "sem_teste"}


def test_relatorio_interrompido_valida(catalogo_tmp, relogio):
    execucao = _rodar(catalogo_tmp, relogio, interromper_em="chave")
    dados = para_dict(execucao)
    VALIDADOR.validate(dados)
    assert dados["interrompida"] is True
    assert any(r["situacao"] == Situacao.NAO_EXECUTADA.value for r in dados["resultados"])


def test_datas_em_utc_com_z(catalogo_tmp, relogio):
    dados = para_dict(_rodar(catalogo_tmp, relogio))
    padrao = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
    assert padrao.match(dados["iniciada_em"])
    assert all(padrao.match(r["coletado_em"]) for r in dados["resultados"] if r["coletado_em"])


def test_nome_do_arquivo_e_sem_sobrescrita(catalogo_tmp, relogio, tmp_path):
    execucao = _rodar(catalogo_tmp, relogio)
    primeiro = base_relatorio(tmp_path, execucao.iniciada_em)
    assert primeiro.name == "inventario-20261125T130000Z"
    gravar_json(execucao, primeiro.with_suffix(".json"))
    segundo = base_relatorio(tmp_path, execucao.iniciada_em)
    assert segundo.name == "inventario-20261125T130000Z-2"
    gravar_json(execucao, segundo.with_suffix(".json"))
    assert base_relatorio(tmp_path, execucao.iniciada_em).name == "inventario-20261125T130000Z-3"
    VALIDADOR.validate(json.loads(primeiro.with_suffix(".json").read_text(encoding="utf-8")))


@pytest.mark.parametrize("extensao", [".json", ".html"])
def test_base_livre_considera_as_duas_extensoes(tmp_path, relogio, extensao):
    (tmp_path / f"inventario-20261125T130000Z{extensao}").write_text("x")
    assert base_relatorio(tmp_path, relogio.agora()).name == "inventario-20261125T130000Z-2"
