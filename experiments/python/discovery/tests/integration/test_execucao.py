import httpx
import pytest
import respx

from inventario_fontes.catalogo import carregar_catalogo
from inventario_fontes.execucao import executar
from inventario_fontes.modelos import Causa, Configuracao, Situacao
from inventario_fontes.sonda import criar_cliente
from tests.conftest import fonte_dict, ler_fixture

CONFIG = Configuracao(intervalo_s=2.0)


def url(nome: str) -> str:
    return f"https://{nome}.gov.br/api"


@pytest.fixture
def catalogo(catalogo_tmp):
    return carregar_catalogo(
        catalogo_tmp(
            [
                fonte_dict(id="ok", probe_url=url("ok")),
                fonte_dict(id="lenta", probe_url=url("lenta")),
                fonte_dict(id="sem-probe", probe_url=None),
                fonte_dict(id="chave", probe_url=url("chave")),
            ]
        )
    )


def rodar(catalogo, relogio, **kwargs):
    with criar_cliente(CONFIG) as cliente:
        return executar(catalogo, catalogo.fontes, CONFIG, cliente, relogio, **kwargs)


def test_execucao_completa_continua_apos_falha(catalogo, relogio):
    with respx.mock(assert_all_called=False) as mock:
        rotas = {
            "ok": mock.get(url("ok")).mock(return_value=httpx.Response(200, content=ler_fixture("ibge_estados.json"))),
            "lenta": mock.get(url("lenta")).mock(side_effect=httpx.ReadTimeout("t")),
            "chave": mock.get(url("chave")).mock(return_value=httpx.Response(401)),
        }
        progresso = []
        execucao = rodar(catalogo, relogio, ao_progresso=lambda i, n, r: progresso.append((i, n, r.fonte_id)))

    assert [r.fonte_id for r in execucao.resultados] == ["ok", "lenta", "sem-probe", "chave"]
    assert [r.situacao for r in execucao.resultados] == [
        Situacao.RESPONDEU,
        Situacao.FALHOU,
        Situacao.SEM_TESTE,
        Situacao.FALHOU,
    ]
    assert execucao.resultados[1].causa is Causa.TEMPO_ESGOTADO
    assert execucao.resultados[3].causa is Causa.EXIGE_AUTENTICACAO
    assert all(rota.call_count == 1 for rota in rotas.values())
    assert [p[2] for p in progresso] == ["ok", "lenta", "sem-probe", "chave"]
    assert execucao.interrompida is False
    assert all(r.verificacao_sugerida is not None for r in execucao.resultados)


def test_ritmo_respeita_o_intervalo(catalogo, relogio):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__regex=r"https://\w+\.gov\.br/api").mock(return_value=httpx.Response(200, json=[]))
        rodar(catalogo, relogio)
    # 3 sondas: duas esperas, nenhuma para a fonte sem probe_url
    assert relogio.esperas == [pytest.approx(2.0), pytest.approx(2.0)]


def test_tempo_da_consulta_conta_no_intervalo(catalogo, relogio):
    def lenta(request):
        relogio.avancar(1.5)
        return httpx.Response(200, json=[])

    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__regex=r"https://\w+\.gov\.br/api").mock(side_effect=lenta)
        rodar(catalogo, relogio)
    # o intervalo conta do fim de uma consulta ao início da seguinte
    assert relogio.esperas == [pytest.approx(2.0), pytest.approx(2.0)]


def test_sem_probe_nao_gera_requisicao(catalogo_tmp, relogio):
    catalogo = carregar_catalogo(catalogo_tmp([fonte_dict(id="a", probe_url=None), fonte_dict(id="b", probe_url=None)]))
    with respx.mock(assert_all_called=False) as mock:
        execucao = rodar(catalogo, relogio)
        assert len(mock.calls) == 0
    assert relogio.esperas == []
    assert [r.situacao for r in execucao.resultados] == [Situacao.SEM_TESTE, Situacao.SEM_TESTE]


def test_interrupcao_preserva_o_que_ja_foi_feito(catalogo, relogio):
    def interromper(request):
        raise KeyboardInterrupt

    with respx.mock(assert_all_called=False) as mock:
        mock.get(url("ok")).mock(return_value=httpx.Response(200, json=[]))
        mock.get(url("lenta")).mock(side_effect=interromper)
        execucao = rodar(catalogo, relogio)

    assert execucao.interrompida is True
    assert [r.situacao for r in execucao.resultados] == [
        Situacao.RESPONDEU,
        Situacao.NAO_EXECUTADA,
        Situacao.NAO_EXECUTADA,
        Situacao.NAO_EXECUTADA,
    ]
    assert execucao.resumo.nao_executadas == 3


def test_resumo_e_todas_falhando(catalogo, relogio):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__regex=r"https://\w+\.gov\.br/api").mock(side_effect=httpx.ConnectError("recusada"))
        execucao = rodar(catalogo, relogio)
    resumo = execucao.resumo
    assert resumo.total == 4
    assert resumo.falharam == 3
    assert resumo.sem_teste == 1
    assert resumo.responderam == 0
    assert resumo.falhas_por_causa == {"indisponivel": 3}
    assert resumo.total == resumo.responderam + resumo.falharam + resumo.sem_teste + resumo.nao_executadas
    assert resumo.com_divergencia == 3


def test_execucao_registra_procedencia(catalogo, relogio):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__regex=r"https://\w+\.gov\.br/api").mock(return_value=httpx.Response(200, json=[]))
        execucao = rodar(catalogo, relogio)
    assert execucao.ferramenta.startswith("inventario-fontes ")
    assert execucao.catalogo_schema_version == 1
    assert execucao.iniciada_em <= execucao.finalizada_em
    assert "documentação oficial" in execucao.aviso
