"""Erros de domínio e seus tipos de problema (RFC 9457; research.md, R11)."""

from __future__ import annotations

PREFIXO_URN = "urn:brasil-aberto:problema:"


class ErroDominio(Exception):
    tipo = "erro-interno"
    titulo = "Erro interno do serviço"
    status = 500

    def __init__(self, detalhe: str) -> None:
        super().__init__(detalhe)
        self.detalhe = detalhe

    @property
    def urn(self) -> str:
        return PREFIXO_URN + self.tipo


class EntradaInvalida(ErroDominio):
    tipo = "entrada-invalida"
    titulo = "Entrada inválida"
    status = 400


class NaoEncontrado(ErroDominio):
    tipo = "nao-encontrado"
    titulo = "Não encontrado"
    status = 404


class FonteIndisponivel(ErroDominio):
    tipo = "fonte-indisponivel"
    titulo = "Fonte indisponível"
    status = 502


class FonteLenta(ErroDominio):
    tipo = "fonte-lenta"
    titulo = "Fonte lenta"
    status = 504


class RespostaInesperadaDaFonte(ErroDominio):
    tipo = "resposta-inesperada-da-fonte"
    titulo = "Resposta inesperada da fonte"
    status = 502


class ErroInterno(ErroDominio):
    pass


ERROS_DE_FONTE = (FonteIndisponivel, FonteLenta, RespostaInesperadaDaFonte)
