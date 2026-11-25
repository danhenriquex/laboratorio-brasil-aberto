import pytest

from inventario_fontes.avaliacao import avaliar, divergencias, grau_sugerido
from inventario_fontes.modelos import (
    Aspecto,
    Auth,
    Causa,
    Divergencia,
    Fonte,
    Formato,
    Grau,
    ResultadoSondagem,
    Situacao,
)


def fonte(auth: str = "nenhuma (hipótese)", grau: Grau = Grau.PARCIAL) -> Fonte:
    return Fonte(
        id="f",
        nome="F",
        dominio="d",
        url_documentacao="https://exemplo.gov.br/docs",
        url_teste="https://exemplo.gov.br/api",
        tipos_dado=("api",),
        hipotese_acesso="facil",
        auth_esperada=auth,
        verificacao=grau,
        rodada=1,
    )


def resultado(f: Fonte, situacao: Situacao, **campos) -> ResultadoSondagem:
    return ResultadoSondagem.base(f, situacao, **campos)


def test_respondeu_sugere_confirmado_com_escopo():
    f = fonte()
    grau, justificativa = grau_sugerido(f, resultado(f, Situacao.RESPONDEU, auth_observada=Auth.NAO_EXIGE))
    assert grau is Grau.CONFIRMADO
    assert "conectividade e autenticação" in justificativa


@pytest.mark.parametrize("causa", [Causa.EXIGE_AUTENTICACAO, Causa.ACESSO_NEGADO, Causa.LIMITE_REQUISICOES])
def test_falhas_que_confirmam(causa):
    f = fonte()
    grau, _ = grau_sugerido(f, resultado(f, Situacao.FALHOU, causa=causa))
    assert grau is Grau.CONFIRMADO


@pytest.mark.parametrize(
    "causa",
    [Causa.TEMPO_ESGOTADO, Causa.INDISPONIVEL, Causa.ERRO_FONTE, Causa.ERRO_TLS, Causa.ERRO_REQUISICAO, Causa.RESPOSTA_INVALIDA],
)
def test_falhas_que_mantem_o_grau(causa):
    f = fonte(grau=Grau.NAO_VERIFICADO)
    grau, justificativa = grau_sugerido(f, resultado(f, Situacao.FALHOU, causa=causa))
    assert grau is Grau.NAO_VERIFICADO
    assert causa.value in justificativa


@pytest.mark.parametrize("situacao", [Situacao.SEM_TESTE, Situacao.NAO_EXECUTADA])
def test_sem_consulta_mantem_o_grau(situacao):
    f = fonte(grau=Grau.CONFIRMADO)
    grau, justificativa = grau_sugerido(f, resultado(f, situacao))
    assert grau is Grau.CONFIRMADO
    assert justificativa


def test_divergencia_de_autenticacao():
    f = fonte()
    r = resultado(
        f, Situacao.FALHOU, causa=Causa.EXIGE_AUTENTICACAO, auth_observada=Auth.EXIGE, indicio_autenticacao="status 401"
    )
    assert Divergencia(Aspecto.AUTENTICACAO, "nao_exige", "exige (status 401)") in divergencias(f, r)


def test_hipotese_exige_e_observado_nao_exige():
    f = fonte(auth="chave de API")
    r = resultado(f, Situacao.RESPONDEU, auth_observada=Auth.NAO_EXIGE)
    assert divergencias(f, r) == (Divergencia(Aspecto.AUTENTICACAO, "exige", "nao_exige"),)


def test_auth_indeterminada_nao_diverge():
    f = fonte()
    r = resultado(f, Situacao.FALHOU, causa=Causa.TEMPO_ESGOTADO)
    assert all(d.aspecto is not Aspecto.AUTENTICACAO for d in divergencias(f, r))


def test_falha_diverge_da_disponibilidade():
    f = fonte()
    r = resultado(f, Situacao.FALHOU, causa=Causa.TEMPO_ESGOTADO)
    assert divergencias(f, r) == (Divergencia(Aspecto.DISPONIBILIDADE, "responde", "tempo_esgotado"),)


def test_formato_divergente():
    f = fonte()
    r = resultado(
        f,
        Situacao.RESPONDEU,
        auth_observada=Auth.NAO_EXIGE,
        formato_declarado="application/json",
        formato_detectado=Formato.HTML,
        formato_divergente=True,
    )
    assert divergencias(f, r) == (Divergencia(Aspecto.FORMATO, "application/json", "html"),)


def test_respondeu_sem_divergencia():
    f = fonte()
    r = resultado(f, Situacao.RESPONDEU, auth_observada=Auth.NAO_EXIGE, formato_detectado=Formato.JSON)
    assert divergencias(f, r) == ()


def test_avaliar_preenche_os_campos():
    f = fonte()
    r = avaliar(f, resultado(f, Situacao.FALHOU, causa=Causa.TEMPO_ESGOTADO))
    assert r.verificacao_sugerida is Grau.PARCIAL
    assert r.justificativa_verificacao
    assert len(r.divergencias) == 1
