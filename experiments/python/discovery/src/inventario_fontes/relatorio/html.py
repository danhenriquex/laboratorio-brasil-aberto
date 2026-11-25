"""Relatório HTML autocontido (R7): sem JavaScript nem recursos externos.

Todo texto que vem do catálogo ou da observação passa por `_e()` (escape HTML).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from string import Template

from inventario_fontes.modelos import Execucao, ResultadoSondagem, Situacao

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        _BRASILIA = ZoneInfo("America/Sao_Paulo")
    except ZoneInfoNotFoundError:  # sistemas sem base de fusos (ex.: Windows sem tzdata)
        _BRASILIA = timezone(timedelta(hours=-3))
except ImportError:  # pragma: no cover
    _BRASILIA = timezone(timedelta(hours=-3))


def _e(texto: object) -> str:
    return escape("" if texto is None else str(texto), quote=True)


def _horario(momento: datetime | None) -> str:
    if momento is None:
        return "—"
    utc = momento.astimezone(UTC)
    br = momento.astimezone(_BRASILIA)
    return f"{utc:%Y-%m-%d %H:%M:%S} UTC<br><small>{br:%H:%M:%S} (Brasília)</small>"


def _link(url: str | None, rotulo: str) -> str:
    if not url:
        return ""
    return f'<a href="{_e(url)}" rel="noopener noreferrer">{_e(rotulo)}</a>'


_PAGINA = Template(
    """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inventário de fontes — $data</title>
<style>
:root { --fundo:#ffffff; --texto:#1f2328; --suave:#59636e; --borda:#d1d9e0; --linha:#f6f8fa;
        --ok:#1a7f37; --falha:#cf222e; --aviso:#9a6700; --destaque:#fff8c5; }
@media (prefers-color-scheme: dark) {
  :root { --fundo:#0d1117; --texto:#e6edf3; --suave:#9198a1; --borda:#3d444d; --linha:#151b23;
          --ok:#3fb950; --falha:#f85149; --aviso:#d29922; --destaque:#2e2a1a; }
}
* { box-sizing: border-box; }
body { margin:0; padding:24px 16px; background:var(--fundo); color:var(--texto);
       font:14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width:1400px; margin:0 auto; }
h1 { font-size:22px; margin:0 0 4px; }
.meta, small { color:var(--suave); }
.aviso { border-left:4px solid var(--aviso); padding:8px 12px; background:var(--linha); margin:16px 0; }
.interrompida { border-left-color:var(--falha); }
.resumo { display:flex; flex-wrap:wrap; gap:8px; margin:16px 0; padding:0; list-style:none; }
.resumo li { border:1px solid var(--borda); border-radius:6px; padding:6px 10px; }
.tabela { overflow-x:auto; }
table { border-collapse:collapse; width:100%; min-width:1000px; }
th, td { border-bottom:1px solid var(--borda); padding:8px; text-align:left; vertical-align:top; }
th { background:var(--linha); position:sticky; top:0; }
tr.divergente td { background:var(--destaque); }
.respondeu { color:var(--ok); font-weight:600; }
.falhou { color:var(--falha); font-weight:600; }
.sem_teste, .nao_executada { color:var(--suave); font-weight:600; }
.div { margin:4px 0 0; padding-left:16px; }
code { font-size:12px; }
details summary { cursor:pointer; }
</style>
</head>
<body>
<main>
<h1>Inventário de fontes</h1>
<p class="meta">$ferramenta · catálogo <code>$catalogo</code> (schema $schema) · execução de $inicio a $fim</p>
$interrompida
<p class="aviso">$aviso</p>
<ul class="resumo">
<li><strong>$total fontes</strong></li>
<li>$responderam responderam</li>
<li>$falharam falharam$causas</li>
<li>$sem_teste sem teste</li>
<li>$com_divergencia com divergência</li>
</ul>
<div class="tabela">
<table>
<thead><tr>
<th>Fonte</th><th>Situação</th><th>Resposta</th><th>Autenticação</th><th>Verificação</th><th>Coleta</th><th>Estrutura</th>
</tr></thead>
<tbody>
$linhas
</tbody>
</table>
</div>
<p class="meta">Configuração: intervalo $intervalo s · tempo limite $tempo_limite s · teto de leitura $teto bytes · até $redirecionamentos redirecionamentos.</p>
</main>
</body>
</html>
"""
)


def _situacao(r: ResultadoSondagem) -> str:
    if r.situacao is Situacao.SEM_TESTE:
        return '<span class="sem_teste">sem teste automatizado</span><br><small>verificar na documentação</small>'
    if r.situacao is Situacao.NAO_EXECUTADA:
        return '<span class="nao_executada">não executada</span>'
    if r.situacao is Situacao.FALHOU:
        return f'<span class="falhou">falhou</span><br><code>{_e(r.causa.value)}</code><br><small>{_e(r.detalhe_causa)}</small>'
    return '<span class="respondeu">respondeu</span>'


def _resposta(r: ResultadoSondagem) -> str:
    if r.status_http is None and r.latencia_ms is None:
        return "—"
    partes = []
    if r.status_http is not None:
        partes.append(f"status <strong>{r.status_http}</strong>")
    if r.latencia_ms is not None:
        partes.append(f"{r.latencia_ms:.0f} ms")
    if r.formato_detectado is not None:
        formato = _e(r.formato_detectado.value)
        if r.formato_declarado:
            formato += f" <small>(declarado {_e(r.formato_declarado)})</small>"
        partes.append(formato)
    if r.tamanho_bytes is not None:
        partes.append(f"{r.tamanho_bytes} bytes" + (" <small>(truncada)</small>" if r.truncada else ""))
    for redirecionamento in r.redirecionamentos:
        partes.append(f"<small>→ {redirecionamento.status} {_e(redirecionamento.url)}</small>")
    if r.retry_after:
        partes.append(f"<small>Retry-After: {_e(r.retry_after)}</small>")
    return "<br>".join(partes)


def _autenticacao(r: ResultadoSondagem) -> str:
    texto = f"<small>hipótese:</small> {_e(r.auth_esperada)}<br><small>observado:</small> {_e(r.auth_observada.value)}"
    if r.indicio_autenticacao:
        texto += f" <small>({_e(r.indicio_autenticacao)})</small>"
    return texto


def _verificacao(r: ResultadoSondagem) -> str:
    sugerido = r.verificacao_sugerida.value if r.verificacao_sugerida else r.verificacao_catalogo.value
    texto = f"<small>catálogo:</small> {_e(r.verificacao_catalogo.value)}<br><small>sugerido:</small> <strong>{_e(sugerido)}</strong>"
    if r.justificativa_verificacao:
        texto += f"<br><small>{_e(r.justificativa_verificacao)}</small>"
    if r.divergencias:
        itens = "".join(
            f"<li><strong>{_e(d.aspecto.value)}</strong>: {_e(d.hipotese)} → {_e(d.observado)}</li>" for d in r.divergencias
        )
        texto += f'<ul class="div">{itens}</ul>'
    return texto


def _estrutura(r: ResultadoSondagem) -> str:
    amostra = r.amostra
    if amostra is None:
        return "—"
    if amostra.indisponivel_motivo:
        return f"<small>indisponível ({_e(amostra.indisponivel_motivo)})</small>"
    if amostra.vazia:
        return "<small>sem registros na amostra</small>"
    onde = f" em <code>{_e(amostra.caminho_registros)}</code>" if amostra.caminho_registros else ""
    itens = "".join(
        f"<li><code>{_e(c.caminho)}</code>: {_e(', '.join(t.value for t in c.tipos))}</li>" for c in amostra.campos
    )
    return (
        f"<details><summary>{len(amostra.campos)} campos · {amostra.registros_inspecionados} registros{onde}</summary>"
        f"<ul>{itens}</ul></details>"
    )


def _linha(r: ResultadoSondagem) -> str:
    classes = [r.situacao.value] + (["divergente"] if r.divergencias else [])
    documentacao = (
        _link(r.url_documentacao, "documentação") if r.url_documentacao else "<small>documentação oficial não localizada</small>"
    )
    teste = f" · {_link(r.url_teste, 'endereço de teste')}" if r.url_teste else ""
    fonte = (
        f"<strong>{_e(r.nome)}</strong><br><code>{_e(r.fonte_id)}</code> · {_e(r.dominio)} · rodada {r.rodada}"
        f"<br><small>acesso: {_e(r.hipotese_acesso)}</small><br>{documentacao}{teste}"
    )
    celulas = [fonte, _situacao(r), _resposta(r), _autenticacao(r), _verificacao(r), _horario(r.coletado_em), _estrutura(r)]
    return f'<tr class="{" ".join(classes)}" data-fonte="{_e(r.fonte_id)}">' + "".join(f"<td>{c}</td>" for c in celulas) + "</tr>"


def renderizar_html(execucao: Execucao) -> str:
    resumo = execucao.resumo
    causas = ", ".join(f"{_e(c)}: {n}" for c, n in resumo.falhas_por_causa.items())
    config = execucao.configuracao
    interrompida = (
        f'<p class="aviso interrompida"><strong>Execução interrompida pelo usuário:</strong> '
        f"{resumo.nao_executadas} fontes não executadas.</p>"
        if execucao.interrompida
        else ""
    )
    return _PAGINA.substitute(
        data=_e(f"{execucao.iniciada_em.astimezone(UTC):%Y-%m-%d %H:%M} UTC"),
        ferramenta=_e(execucao.ferramenta),
        catalogo=_e(execucao.catalogo_caminho),
        schema=execucao.catalogo_schema_version,
        inicio=_horario(execucao.iniciada_em).replace("<br>", " "),
        fim=_horario(execucao.finalizada_em).replace("<br>", " "),
        interrompida=interrompida,
        aviso=_e(execucao.aviso),
        total=resumo.total,
        responderam=resumo.responderam,
        falharam=resumo.falharam,
        causas=f" <small>({causas})</small>" if causas else "",
        sem_teste=resumo.sem_teste,
        com_divergencia=resumo.com_divergencia,
        linhas="\n".join(_linha(r) for r in execucao.resultados),
        intervalo=config.intervalo_s,
        tempo_limite=config.tempo_limite_s,
        teto=config.teto_bytes,
        redirecionamentos=config.max_redirecionamentos,
    )


def gravar_html(execucao: Execucao, caminho: Path) -> None:
    caminho.write_text(renderizar_html(execucao), encoding="utf-8")
