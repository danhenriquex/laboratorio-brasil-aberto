"""Linha de comando `inventario` (contrato: specs/001-inventario-fontes/contracts/cli.md).

Códigos de saída: 0 concluída (mesmo com fontes falhando), 1 catálogo inválido,
2 uso incorreto, 130 interrompida pelo usuário.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from inventario_fontes import __version__
from inventario_fontes.catalogo import ErroCatalogo, carregar_catalogo, filtrar
from inventario_fontes.execucao import RelogioSistema, executar
from inventario_fontes.modelos import Configuracao, Execucao, ResultadoSondagem, Situacao
from inventario_fontes.relatorio.html import gravar_html
from inventario_fontes.relatorio.json_ import base_relatorio, gravar_json
from inventario_fontes.sonda import Relogio, criar_cliente

SAIDA_OK = 0
SAIDA_CATALOGO = 1
SAIDA_USO = 2
SAIDA_INTERROMPIDA = 130


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventario",
        description="Sonda as fontes do catálogo (uma consulta por fonte) e gera relatórios JSON e HTML.",
    )
    parser.add_argument("--catalogo", default="discovery/sources.json", help="catálogo de fontes")
    parser.add_argument("--saida", default="discovery/reports", help="diretório dos relatórios")
    parser.add_argument(
        "--rodada", type=int, action="append", default=[], metavar="N", help="limita a uma rodada (repetível)"
    )
    parser.add_argument(
        "--fonte", action="append", default=[], metavar="ID", help="limita a uma fonte pelo id (repetível)"
    )
    parser.add_argument("--intervalo", type=float, default=2.0, help="segundos entre consultas (mínimo 1)")
    parser.add_argument("--tempo-limite", type=float, default=15.0, help="tempo limite por consulta, de 1 a 60 s")
    parser.add_argument("--versao", action="version", version=f"inventario-fontes {__version__}")
    return parser


def _linha(i: int, n: int, r: ResultadoSondagem) -> str:
    rotulo = f"[{i}/{n}] {r.fonte_id} ".ljust(36, ".")
    if r.situacao is Situacao.SEM_TESTE:
        return f"{rotulo} sem teste automatizado"
    status = str(r.status_http) if r.status_http is not None else "-"
    formato = r.formato_detectado.value if r.formato_detectado else "-"
    latencia = f"{r.latencia_ms:.0f} ms" if r.latencia_ms is not None else "-"
    if r.situacao is Situacao.FALHOU:
        return f"{rotulo} falhou  {r.causa.value}  {status}  {latencia}"
    return f"{rotulo} respondeu  {status}  {formato}  {latencia}"


def _resumo(execucao: Execucao, caminhos: Sequence[Path]) -> str:
    r = execucao.resumo
    linhas = [
        "",
        f"{r.total} fontes: {r.responderam} responderam, {r.falharam} falharam, "
        f"{r.sem_teste} sem teste, {r.com_divergencia} com divergência",
    ]
    if execucao.interrompida:
        linhas.append(f"Execução interrompida: {r.nao_executadas} fontes não executadas.")
    linhas.append("Relatórios:")
    linhas.extend(f"  {c}" for c in caminhos)
    return "\n".join(linhas)


def main(argv: Sequence[str] | None = None, *, relogio: Relogio | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as saida:
        return int(saida.code or 0)

    try:
        config = Configuracao(intervalo_s=args.intervalo, tempo_limite_s=args.tempo_limite)
    except ValueError as erro:
        print(f"inventario: {erro}", file=sys.stderr)
        return SAIDA_USO

    try:
        catalogo = carregar_catalogo(args.catalogo)
    except ErroCatalogo as erro:
        print(f"inventario: {erro}", file=sys.stderr)
        return SAIDA_CATALOGO

    try:
        fontes = filtrar(catalogo.fontes, args.rodada, args.fonte)
    except ValueError as erro:
        print(f"inventario: {erro}", file=sys.stderr)
        return SAIDA_USO
    if not fontes:
        print("inventario: nenhuma fonte do catálogo atende aos filtros", file=sys.stderr)
        return SAIDA_USO
    relogio = relogio or RelogioSistema()

    def progresso(i: int, n: int, resultado: ResultadoSondagem) -> None:
        print(_linha(i, n, resultado), flush=True)

    with criar_cliente(config) as cliente:
        execucao = executar(
            catalogo,
            fontes,
            config,
            cliente,
            relogio,
            ao_progresso=progresso,
            filtro_rodadas=args.rodada,
            filtro_fontes=args.fonte,
        )

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    base = base_relatorio(saida, execucao.iniciada_em)
    caminho_json = base.with_suffix(".json")
    caminho_html = base.with_suffix(".html")
    gravar_json(execucao, caminho_json)
    gravar_html(execucao, caminho_html)
    print(_resumo(execucao, [caminho_json, caminho_html]))

    return SAIDA_INTERROMPIDA if execucao.interrompida else SAIDA_OK
