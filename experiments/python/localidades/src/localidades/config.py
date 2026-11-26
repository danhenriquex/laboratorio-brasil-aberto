"""Configuração por variáveis de ambiente `LOCALIDADES_*`, comuns ao E1 e ao E4 (research.md, R14)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

IBGE_URL_PADRAO = "https://servicodados.ibge.gov.br/api/v1/localidades"


@dataclass(frozen=True)
class Configuracao:
    host: str = "127.0.0.1"
    porta: int = 8000
    ibge_url: str = IBGE_URL_PADRAO
    prazo_fonte_s: float = 10.0
    validade_s: float = 86400.0
    itens_max: int = 500

    @classmethod
    def do_ambiente(cls, env: Mapping[str, str] | None = None) -> Configuracao:
        env = os.environ if env is None else env
        padrao = cls()

        def texto(nome: str, valor_padrao: str) -> str:
            return env.get(nome, "").strip() or valor_padrao

        def positivo(nome: str, valor_padrao: float, conversor):
            bruto = env.get(nome)
            if bruto is None or not bruto.strip():
                return valor_padrao
            try:
                valor = conversor(bruto.strip())
            except ValueError:
                raise ValueError(f"{nome} precisa ser um número, recebi {bruto!r}") from None
            if valor <= 0:
                raise ValueError(f"{nome} precisa ser maior que zero, recebi {bruto!r}")
            return valor

        ibge_url = texto("LOCALIDADES_IBGE_URL", padrao.ibge_url).rstrip("/")
        if not ibge_url.startswith(("http://", "https://")):
            raise ValueError(f"LOCALIDADES_IBGE_URL precisa começar com http:// ou https://, recebi {ibge_url!r}")

        return cls(
            host=texto("LOCALIDADES_HOST", padrao.host),
            porta=positivo("LOCALIDADES_PORTA", padrao.porta, int),
            ibge_url=ibge_url,
            prazo_fonte_s=positivo("LOCALIDADES_PRAZO_FONTE_S", padrao.prazo_fonte_s, float),
            validade_s=positivo("LOCALIDADES_VALIDADE_S", padrao.validade_s, float),
            itens_max=positivo("LOCALIDADES_ITENS_MAX", padrao.itens_max, int),
        )
