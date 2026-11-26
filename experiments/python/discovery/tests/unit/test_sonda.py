import ssl
from datetime import UTC

import httpx
import pytest
import respx

from inventario_fontes.modelos import Auth, Causa, Configuracao, Fonte, Formato, Grau, Situacao
from inventario_fontes.sonda import criar_cliente, sondar
from tests.conftest import ler_fixture

URL = "https://exemplo.gov.br/api/dados"
CONFIG = Configuracao()


def fonte(url: str = URL) -> Fonte:
    return Fonte(
        id="fonte-teste",
        nome="Fonte de teste",
        dominio="teste",
        url_documentacao="https://exemplo.gov.br/docs",
        url_teste=url,
        tipos_dado=("api",),
        hipotese_acesso="facil",
        auth_esperada="nenhuma (hipótese)",
        verificacao=Grau.PARCIAL,
        rodada=1,
    )


@pytest.fixture
def mock():
    with respx.mock(assert_all_called=False) as router:
        yield router


def sondar_com(relogio, url: str = URL):
    with criar_cliente(CONFIG) as cliente:
        return sondar(fonte(url), cliente, CONFIG, relogio)


def test_resposta_normal(mock, relogio):
    corpo = ler_fixture("ibge_estados.json")
    rota = mock.get(URL).mock(
        return_value=httpx.Response(200, content=corpo, headers={"Content-Type": "application/json; charset=utf-8"})
    )
    r = sondar_com(relogio)
    assert r.situacao is Situacao.RESPONDEU
    assert r.causa is None
    assert r.status_http == 200
    assert r.latencia_ms is not None and r.latencia_ms >= 0
    assert r.coletado_em is not None and r.coletado_em.tzinfo == UTC
    assert r.tamanho_bytes == len(corpo)
    assert r.tamanho_declarado_bytes == len(corpo)
    assert r.formato_declarado == "application/json"
    assert r.formato_detectado is Formato.JSON
    assert r.formato_divergente is False
    assert r.truncada is False
    assert r.auth_observada is Auth.NAO_EXIGE
    assert r.url_final == URL
    assert r.redirecionamentos == ()
    assert rota.call_count == 1


@pytest.mark.parametrize("erro", [httpx.ConnectTimeout("t"), httpx.ReadTimeout("t")])
def test_tempo_esgotado(mock, relogio, erro):
    rota = mock.get(URL).mock(side_effect=erro)
    r = sondar_com(relogio)
    assert (r.situacao, r.causa) == (Situacao.FALHOU, Causa.TEMPO_ESGOTADO)
    assert r.status_http is None
    assert r.auth_observada is Auth.INDETERMINADO
    assert r.coletado_em is not None
    assert rota.call_count == 1


def test_indisponivel(mock, relogio):
    mock.get(URL).mock(side_effect=httpx.ConnectError("[Errno 8] nodename nor servname provided"))
    r = sondar_com(relogio)
    assert r.causa is Causa.INDISPONIVEL


def test_erro_tls_pela_mensagem(mock, relogio):
    # é assim que o httpx real entrega a falha de certificado
    mensagem = "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate"
    mock.get(URL).mock(side_effect=httpx.ConnectError(mensagem))
    assert sondar_com(relogio).causa is Causa.ERRO_TLS


def test_erro_tls_pela_causa():
    from inventario_fontes.sonda import _eh_erro_tls

    erro = httpx.ConnectError("falha na conexão")
    erro.__cause__ = ssl.SSLCertVerificationError(1, "verify failed")
    assert _eh_erro_tls(erro) is True
    assert _eh_erro_tls(httpx.ConnectError("[Errno 61] Connection refused")) is False


def test_401_exige_autenticacao(mock, relogio):
    mock.get(URL).mock(return_value=httpx.Response(401, json={"erro": "x"}))
    r = sondar_com(relogio)
    assert (r.situacao, r.causa) == (Situacao.FALHOU, Causa.EXIGE_AUTENTICACAO)
    assert r.auth_observada is Auth.EXIGE
    assert r.indicio_autenticacao == "status 401"


def test_www_authenticate_exige_autenticacao(mock, relogio):
    mock.get(URL).mock(return_value=httpx.Response(403, headers={"WWW-Authenticate": 'Bearer realm="api"'}))
    r = sondar_com(relogio)
    assert r.causa is Causa.EXIGE_AUTENTICACAO
    assert "WWW-Authenticate" in r.indicio_autenticacao


def test_redirecionamento_para_login_gov_br(mock, relogio):
    mock.get(URL).mock(return_value=httpx.Response(302, headers={"Location": "https://sso.acesso.gov.br/login"}))
    mock.get("https://sso.acesso.gov.br/login").mock(
        return_value=httpx.Response(200, content=ler_fixture("erro.html"), headers={"Content-Type": "text/html"})
    )
    r = sondar_com(relogio)
    assert r.causa is Causa.EXIGE_AUTENTICACAO
    assert r.auth_observada is Auth.EXIGE
    assert "sso.acesso.gov.br" in r.indicio_autenticacao
    assert r.url_final == "https://sso.acesso.gov.br/login"
    assert [(x.status, x.url) for x in r.redirecionamentos] == [(302, "https://sso.acesso.gov.br/login")]


def test_redirecionamento_comum_e_registrado(mock, relogio):
    destino = "https://exemplo.gov.br/v2/dados"
    mock.get(URL).mock(return_value=httpx.Response(301, headers={"Location": "/v2/dados"}))
    mock.get(destino).mock(return_value=httpx.Response(200, json=[{"a": 1}]))
    r = sondar_com(relogio)
    assert r.situacao is Situacao.RESPONDEU
    assert r.url_final == destino
    assert [(x.status, x.url) for x in r.redirecionamentos] == [(301, destino)]


def test_caminho_parecido_com_auth_nao_e_login(mock, relogio):
    destino = "https://exemplo.gov.br/api/authors"
    mock.get(URL).mock(return_value=httpx.Response(302, headers={"Location": destino}))
    mock.get(destino).mock(return_value=httpx.Response(200, json=[]))
    assert sondar_com(relogio).situacao is Situacao.RESPONDEU


def test_403_acesso_negado(mock, relogio):
    mock.get(URL).mock(return_value=httpx.Response(403))
    r = sondar_com(relogio)
    assert r.causa is Causa.ACESSO_NEGADO
    assert r.auth_observada is Auth.INDETERMINADO


def test_429_limite_sem_nova_tentativa(mock, relogio):
    rota = mock.get(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "120"}))
    r = sondar_com(relogio)
    assert r.causa is Causa.LIMITE_REQUISICOES
    assert r.retry_after == "120"
    assert rota.call_count == 1


@pytest.mark.parametrize(("status", "causa"), [(503, Causa.ERRO_FONTE), (500, Causa.ERRO_FONTE), (404, Causa.ERRO_REQUISICAO), (400, Causa.ERRO_REQUISICAO)])
def test_status_de_erro(mock, relogio, status, causa):
    rota = mock.get(URL).mock(return_value=httpx.Response(status, content=b"segredo-do-corpo"))
    r = sondar_com(relogio)
    assert r.causa is causa
    assert r.status_http == status
    assert "segredo-do-corpo" not in (r.detalhe_causa or "")
    assert rota.call_count == 1


def test_excesso_de_redirecionamentos(mock, relogio):
    def proximo(request):
        n = int(request.url.path.strip("/") or 0)
        return httpx.Response(302, headers={"Location": f"https://loop.gov.br/{n + 1}"})

    mock.get(url__regex=r"https://loop\.gov\.br/\d+").mock(side_effect=proximo)
    r = sondar_com(relogio, "https://loop.gov.br/0")
    assert r.causa is Causa.ERRO_REQUISICAO
    assert "redirecionamentos" in r.detalhe_causa


def test_json_quebrado_e_resposta_invalida(mock, relogio):
    mock.get(URL).mock(
        return_value=httpx.Response(200, content=ler_fixture("json_quebrado.txt"), headers={"Content-Type": "application/json"})
    )
    r = sondar_com(relogio)
    assert (r.situacao, r.causa) == (Situacao.FALHOU, Causa.RESPOSTA_INVALIDA)
    assert r.status_http == 200
    assert r.auth_observada is Auth.NAO_EXIGE


def test_resposta_grande_e_truncada(mock, relogio):
    corpo = b"[" + b"1," * 1_100_000 + b"1]"
    mock.get(URL).mock(return_value=httpx.Response(200, content=corpo, headers={"Content-Type": "application/json"}))
    r = sondar_com(relogio)
    assert r.truncada is True
    assert r.tamanho_bytes <= CONFIG.teto_bytes
    assert r.situacao is Situacao.RESPONDEU
    assert r.formato_detectado is Formato.JSON


def test_html_declarado_como_json(mock, relogio):
    mock.get(URL).mock(
        return_value=httpx.Response(200, content=ler_fixture("erro.html"), headers={"Content-Type": "application/json"})
    )
    r = sondar_com(relogio)
    assert r.situacao is Situacao.RESPONDEU
    assert r.formato_detectado is Formato.HTML
    assert r.formato_divergente is True


def test_cabecalhos_enviados(mock, relogio):
    rota = mock.get(URL).mock(return_value=httpx.Response(200, json=[]))
    sondar_com(relogio)
    enviado = rota.calls.last.request.headers
    assert enviado["User-Agent"].startswith("laboratorio-brasil-aberto-inventario/")
    assert "Authorization" not in enviado
    assert "Cookie" not in enviado


def test_latencia_medida_pelo_relogio(mock, relogio):
    def lento(request):
        relogio.avancar(0.25)
        return httpx.Response(200, json=[])

    mock.get(URL).mock(side_effect=lento)
    inicio = relogio.agora()
    r = sondar_com(relogio)
    assert r.latencia_ms == pytest.approx(250.0)
    assert r.coletado_em == inicio


# --- Convergência (T037, T038) ---


def test_corpo_comprimido_corrompido_e_resposta_invalida(mock, relogio):
    mock.get(URL).mock(side_effect=httpx.DecodingError("Error -3 while decompressing data: incorrect header check"))
    r = sondar_com(relogio)
    assert (r.situacao, r.causa) == (Situacao.FALHOU, Causa.RESPOSTA_INVALIDA)
    assert "DecodingError" in r.detalhe_causa


def test_json_aninhado_demais_e_resposta_invalida(mock, relogio):
    corpo = b"[" * 200_000 + b"]" * 200_000
    mock.get(URL).mock(return_value=httpx.Response(200, content=corpo, headers={"Content-Type": "application/json"}))
    r = sondar_com(relogio)
    assert (r.situacao, r.causa) == (Situacao.FALHOU, Causa.RESPOSTA_INVALIDA)
    assert "aninhad" in r.detalhe_causa


def test_prazo_total_excedido_durante_a_leitura(mock, relogio):
    def gotejando():
        for _ in range(100):
            relogio.avancar(1.0)  # cada bloco chega 1 s depois do anterior
            yield b"x" * 10

    mock.get(URL).mock(return_value=httpx.Response(200, content=gotejando()))
    r = sondar_com(relogio)
    assert (r.situacao, r.causa) == (Situacao.FALHOU, Causa.TEMPO_ESGOTADO)
    assert "prazo total" in r.detalhe_causa
    assert r.latencia_ms <= (CONFIG.tempo_limite_s + 1) * 1000


def test_leitura_dentro_do_prazo_nao_e_interrompida(mock, relogio):
    def rapido():
        for _ in range(5):
            relogio.avancar(1.0)
            yield b'[1]' if _ == 0 else b""

    mock.get(URL).mock(return_value=httpx.Response(200, content=rapido(), headers={"Content-Type": "application/json"}))
    assert sondar_com(relogio).situacao is Situacao.RESPONDEU
