"""Hipótese do catálogo × observado: grau sugerido (R11) e divergências (R12)."""

from __future__ import annotations

from dataclasses import replace

from inventario_fontes.modelos import (
    Aspecto,
    Auth,
    Causa,
    Divergencia,
    Fonte,
    Grau,
    ResultadoSondagem,
    Situacao,
)

_CAUSAS_QUE_CONFIRMAM = {Causa.EXIGE_AUTENTICACAO, Causa.ACESSO_NEGADO, Causa.LIMITE_REQUISICOES}
_ESCOPO = (
    "Observação direta do endpoint oficial confirma conectividade e autenticação nesta data; "
    "licença, limites e termos de uso dependem da documentação oficial."
)


def grau_sugerido(fonte: Fonte, resultado: ResultadoSondagem) -> tuple[Grau, str]:
    if resultado.situacao is Situacao.RESPONDEU:
        return Grau.CONFIRMADO, _ESCOPO
    if resultado.situacao is Situacao.FALHOU and resultado.causa in _CAUSAS_QUE_CONFIRMAM:
        return Grau.CONFIRMADO, f"A fonte respondeu com {resultado.causa.value}. {_ESCOPO}"
    if resultado.situacao is Situacao.SEM_TESTE:
        return fonte.verificacao, "Sem teste automatizado: verificar manualmente na documentação oficial."
    if resultado.situacao is Situacao.NAO_EXECUTADA:
        return fonte.verificacao, "Execução interrompida antes desta fonte; mantido o grau do catálogo."
    return (
        fonte.verificacao,
        f"A falha ({resultado.causa.value}) não permite confirmar o acesso; mantido o grau do catálogo.",
    )


def divergencias(fonte: Fonte, resultado: ResultadoSondagem) -> tuple[Divergencia, ...]:
    encontradas: list[Divergencia] = []
    observado = resultado.auth_observada
    if observado is not Auth.INDETERMINADO and observado is not fonte.hipotese_auth:
        texto = observado.value
        if resultado.indicio_autenticacao:
            texto += f" ({resultado.indicio_autenticacao})"
        encontradas.append(Divergencia(Aspecto.AUTENTICACAO, fonte.hipotese_auth.value, texto))
    if resultado.situacao is Situacao.FALHOU:
        encontradas.append(Divergencia(Aspecto.DISPONIBILIDADE, "responde", resultado.causa.value))
    if resultado.formato_divergente:
        encontradas.append(
            Divergencia(
                Aspecto.FORMATO,
                resultado.formato_declarado or "",
                resultado.formato_detectado.value if resultado.formato_detectado else "",
            )
        )
    return tuple(encontradas)


def avaliar(fonte: Fonte, resultado: ResultadoSondagem) -> ResultadoSondagem:
    grau, justificativa = grau_sugerido(fonte, resultado)
    return replace(
        resultado,
        verificacao_sugerida=grau,
        justificativa_verificacao=justificativa,
        divergencias=divergencias(fonte, resultado),
    )
