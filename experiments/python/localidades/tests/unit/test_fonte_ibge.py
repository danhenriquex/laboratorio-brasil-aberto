import asyncio
import time

import httpx
import pytest

from localidades.config import Configuracao
from localidades.dominio import Municipio, MunicipioResumido, Uf
from localidades.erros import FonteIndisponivel, FonteLenta, NaoEncontrado, RespostaInesperadaDaFonte
from localidades.fonte_ibge import USER_AGENT, ClienteIBGE
from tests.conftest import IBGE, fixture_json, item_da_uf, ler_fixture

CONFIG = Configuracao()


def executar(coro_fn, config: Configuracao = CONFIG, medidas: list | None = None):
    async def _rodar():
        ao_medir = (lambda recurso, s: medidas.append((recurso, s))) if medidas is not None else None
        cliente = ClienteIBGE(config, ao_medir=ao_medir)
        try:
            return await coro_fn(cliente)
        finally:
            await cliente.fechar()

    return asyncio.run(_rodar())


def json_resp(conteudo: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(status, content=conteudo, headers={"Content-Type": "application/json; charset=utf-8"})


# --- normalização ---


def test_estados_normalizados(mock_ibge):
    rota = mock_ibge.get("/estados").mock(return_value=json_resp(ler_fixture("estados.json")))
    medidas: list = []
    ufs, url = executar(lambda c: c.obter_estados(), medidas=medidas)
    assert len(ufs) == 27 and all(isinstance(u, Uf) for u in ufs)
    rj = next(u for u in ufs if u.sigla == "RJ")
    assert (rj.codigo, rj.nome, rj.regiao.codigo, rj.regiao.sigla, rj.regiao.nome) == ("33", "Rio de Janeiro", "3", "SE", "Sudeste")
    assert url == f"{IBGE}/estados"
    assert rota.call_count == 1
    assert rota.calls.last.request.headers["User-Agent"] == USER_AGENT
    assert [r for r, _ in medidas] == ["estados"]


def test_municipios_da_uf(mock_ibge):
    mock_ibge.get("/estados/33/municipios").mock(return_value=json_resp(ler_fixture("municipios-uf-33.json")))
    itens, url = executar(lambda c: c.obter_municipios_da_uf("33"))
    assert len(itens) == 92 and all(isinstance(x, MunicipioResumido) for x in itens)
    assert MunicipioResumido(codigo="3303302", nome="Niterói") in itens
    assert url == f"{IBGE}/estados/33/municipios"


def test_municipios_da_uf_vazia_e_inesperada(mock_ibge):
    mock_ibge.get("/estados/33/municipios").mock(return_value=json_resp(b"[]"))
    with pytest.raises(RespostaInesperadaDaFonte):
        executar(lambda c: c.obter_municipios_da_uf("33"))


@pytest.mark.parametrize("como_lista", [False, True])
def test_municipio_objeto_ou_lista_de_um(mock_ibge, como_lista):
    item = item_da_uf("33", 3304557)
    mock_ibge.get("/municipios/3304557").mock(return_value=httpx.Response(200, json=[item] if como_lista else item))
    mun, url = executar(lambda c: c.obter_municipio("3304557"))
    assert isinstance(mun, Municipio)
    assert (mun.codigo, mun.nome) == ("3304557", "Rio de Janeiro")
    assert (mun.uf.codigo, mun.uf.sigla, mun.uf.nome) == ("33", "RJ", "Rio de Janeiro")
    assert (mun.regiao_imediata.codigo, mun.regiao_intermediaria.codigo) == ("330001", "3301")
    assert url == f"{IBGE}/municipios/3304557"


def test_municipio_vazio_e_nao_encontrado(mock_ibge):
    mock_ibge.get("/municipios/9999999").mock(return_value=json_resp(b"[]"))
    with pytest.raises(NaoEncontrado):
        executar(lambda c: c.obter_municipio("9999999"))


def test_municipio_sem_microrregiao_e_aceito(mock_ibge):
    mock_ibge.get("/municipios/5101837").mock(return_value=json_resp(ler_fixture("municipio-5101837.json")))
    mun, _ = executar(lambda c: c.obter_municipio("5101837"))
    assert mun.nome == fixture_json("municipio-5101837.json")["nome"]
    assert mun.uf.sigla == "MT"


def test_lista_com_dois_municipios_e_inesperada(mock_ibge):
    item = item_da_uf("33", 3304557)
    mock_ibge.get("/municipios/3304557").mock(return_value=httpx.Response(200, json=[item, item]))
    with pytest.raises(RespostaInesperadaDaFonte):
        executar(lambda c: c.obter_municipio("3304557"))


# --- classificação das falhas (R6) ---


@pytest.mark.parametrize(
    ("resposta", "erro"),
    [
        (httpx.ConnectError("[Errno 61] Connection refused"), FonteIndisponivel),
        (httpx.Response(503), FonteIndisponivel),
        (httpx.Response(429), FonteIndisponivel),
        (httpx.ReadTimeout("timed out"), FonteLenta),
        (httpx.Response(404), RespostaInesperadaDaFonte),
        (httpx.Response(200, content=ler_fixture("erro.html"), headers={"Content-Type": "text/html"}), RespostaInesperadaDaFonte),
        (json_resp(ler_fixture("estados-sem-regiao.json")), RespostaInesperadaDaFonte),
        (json_resp(b'{"nao": "e lista"}'), RespostaInesperadaDaFonte),
    ],
)
def test_classificacao_das_falhas(mock_ibge, resposta, erro):
    efeito = {"side_effect": resposta} if isinstance(resposta, Exception) else {"return_value": resposta}
    rota = mock_ibge.get("/estados").mock(**efeito)
    with pytest.raises(erro) as info:
        executar(lambda c: c.obter_estados())
    assert rota.call_count == 1  # sem nova tentativa (FR-017)
    assert "<html" not in str(info.value).lower()  # nunca repassa o corpo da fonte


def test_municipio_sem_regiao_imediata_e_inesperado(mock_ibge):
    mock_ibge.get("/municipios/3304557").mock(return_value=json_resp(ler_fixture("municipio-sem-regiao-imediata.json")))
    with pytest.raises(RespostaInesperadaDaFonte):
        executar(lambda c: c.obter_municipio("3304557"))


def test_prazo_total_esgotado_e_fonte_lenta(mock_ibge):
    async def devagar(request):
        await asyncio.sleep(0.3)
        return httpx.Response(200, json=[])

    mock_ibge.get("/estados").mock(side_effect=devagar)
    inicio = time.monotonic()
    with pytest.raises(FonteLenta):
        executar(lambda c: c.obter_estados(), config=Configuracao(prazo_fonte_s=0.05))
    assert time.monotonic() - inicio < 0.3
