"""Laço de execução: uma consulta por fonte, em sequência, com intervalo entre consultas.

Interrupção pelo usuário (R10) não perde o que já foi consultado: as fontes
restantes aparecem como `nao_executada` e a execução volta marcada como interrompida.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

import httpx

from inventario_fontes import __version__
from inventario_fontes.avaliacao import avaliar
from inventario_fontes.modelos import (
    Catalogo,
    Configuracao,
    Execucao,
    Fonte,
    ResultadoSondagem,
    Resumo,
    Situacao,
)
from inventario_fontes.sonda import Relogio, sondar

AVISO = (
    "A sondagem mostra a conectividade de um endereço numa data; licença, limites e termos de uso "
    "só se confirmam na documentação oficial."
)

Progresso = Callable[[int, int, ResultadoSondagem], None]


class RelogioSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()

    def esperar(self, segundos: float) -> None:
        time.sleep(segundos)


def executar(
    catalogo: Catalogo,
    fontes: Sequence[Fonte],
    config: Configuracao,
    cliente: httpx.Client,
    relogio: Relogio,
    ao_progresso: Progresso | None = None,
    filtro_rodadas: Sequence[int] = (),
    filtro_fontes: Sequence[str] = (),
) -> Execucao:
    iniciada_em = relogio.agora()
    resultados: list[ResultadoSondagem] = []
    interrompida = False
    fim_anterior: float | None = None
    total = len(fontes)

    for indice, fonte in enumerate(fontes):
        try:
            if fonte.url_teste is None:
                resultado = ResultadoSondagem.base(fonte, Situacao.SEM_TESTE)
            else:
                if fim_anterior is not None:
                    espera = config.intervalo_s - (relogio.monotonic() - fim_anterior)
                    if espera > 0:
                        relogio.esperar(espera)
                resultado = sondar(fonte, cliente, config, relogio)
                fim_anterior = relogio.monotonic()
        except KeyboardInterrupt:
            interrompida = True
            resultados.extend(
                avaliar(restante, ResultadoSondagem.base(restante, Situacao.NAO_EXECUTADA)) for restante in fontes[indice:]
            )
            break
        resultado = avaliar(fonte, resultado)
        resultados.append(resultado)
        if ao_progresso is not None:
            ao_progresso(indice + 1, total, resultado)

    return Execucao(
        ferramenta=f"inventario-fontes {__version__}",
        catalogo_caminho=catalogo.caminho,
        catalogo_schema_version=catalogo.schema_version,
        iniciada_em=iniciada_em,
        finalizada_em=relogio.agora(),
        interrompida=interrompida,
        configuracao=config,
        aviso=AVISO,
        resumo=Resumo.de_resultados(resultados),
        resultados=tuple(resultados),
        filtro_rodadas=tuple(filtro_rodadas),
        filtro_fontes=tuple(filtro_fontes),
    )
