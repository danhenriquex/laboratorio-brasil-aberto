"""Relatório JSON (contrato: specs/001-inventario-fontes/contracts/relatorio.schema.json)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from inventario_fontes.modelos import EstruturaAmostra, Execucao, ResultadoSondagem


def data_utc(momento: datetime | None) -> str | None:
    if momento is None:
        return None
    utc = momento.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _valor(v: Any) -> Any:
    return v.value if hasattr(v, "value") else v


def _amostra(amostra: EstruturaAmostra | None) -> dict | None:
    if amostra is None:
        return None
    return {
        "registros_inspecionados": amostra.registros_inspecionados,
        "caminho_registros": amostra.caminho_registros,
        "campos": [{"caminho": c.caminho, "tipos": [t.value for t in c.tipos]} for c in amostra.campos],
        "vazia": amostra.vazia,
        "indisponivel_motivo": amostra.indisponivel_motivo,
    }


def _resultado(r: ResultadoSondagem) -> dict:
    return {
        "fonte_id": r.fonte_id,
        "nome": r.nome,
        "dominio": r.dominio,
        "url_documentacao": r.url_documentacao,
        "rodada": r.rodada,
        "hipotese_acesso": r.hipotese_acesso,
        "auth_esperada": r.auth_esperada,
        "verificacao_catalogo": r.verificacao_catalogo.value,
        "verificacao_sugerida": _valor(r.verificacao_sugerida or r.verificacao_catalogo),
        "justificativa_verificacao": r.justificativa_verificacao,
        "situacao": r.situacao.value,
        "causa": _valor(r.causa),
        "detalhe_causa": r.detalhe_causa,
        "url_teste": r.url_teste,
        "url_final": r.url_final,
        "redirecionamentos": [{"status": x.status, "url": x.url} for x in r.redirecionamentos],
        "status_http": r.status_http,
        "latencia_ms": r.latencia_ms,
        "coletado_em": data_utc(r.coletado_em),
        "formato_declarado": r.formato_declarado,
        "formato_detectado": _valor(r.formato_detectado),
        "formato_divergente": r.formato_divergente,
        "tamanho_bytes": r.tamanho_bytes,
        "tamanho_declarado_bytes": r.tamanho_declarado_bytes,
        "truncada": r.truncada,
        "auth_observada": r.auth_observada.value,
        "indicio_autenticacao": r.indicio_autenticacao,
        "retry_after": r.retry_after,
        "amostra": _amostra(r.amostra),
        "divergencias": [
            {"aspecto": d.aspecto.value, "hipotese": d.hipotese, "observado": d.observado} for d in r.divergencias
        ],
    }


def para_dict(execucao: Execucao) -> dict:
    resumo = execucao.resumo
    config = execucao.configuracao
    return {
        "versao_relatorio": execucao.versao_relatorio,
        "ferramenta": execucao.ferramenta,
        "catalogo": {"caminho": execucao.catalogo_caminho, "schema_version": execucao.catalogo_schema_version},
        "iniciada_em": data_utc(execucao.iniciada_em),
        "finalizada_em": data_utc(execucao.finalizada_em),
        "interrompida": execucao.interrompida,
        "filtros": {"rodadas": list(execucao.filtro_rodadas), "fontes": list(execucao.filtro_fontes)},
        "configuracao": {
            "intervalo_s": config.intervalo_s,
            "tempo_limite_s": config.tempo_limite_s,
            "teto_bytes": config.teto_bytes,
            "max_redirecionamentos": config.max_redirecionamentos,
        },
        "aviso": execucao.aviso,
        "resumo": {
            "total": resumo.total,
            "responderam": resumo.responderam,
            "falharam": resumo.falharam,
            "falhas_por_causa": dict(resumo.falhas_por_causa),
            "sem_teste": resumo.sem_teste,
            "nao_executadas": resumo.nao_executadas,
            "com_divergencia": resumo.com_divergencia,
        },
        "resultados": [_resultado(r) for r in execucao.resultados],
    }


def base_relatorio(saida: Path, iniciada_em: datetime) -> Path:
    """Caminho sem extensão, livre para `.json` e `.html`; nunca sobrescreve (sufixo -2, -3...)."""
    nome = "inventario-" + iniciada_em.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    candidato = Path(saida) / nome
    n = 2
    while candidato.with_suffix(".json").exists() or candidato.with_suffix(".html").exists():
        candidato = Path(saida) / f"{nome}-{n}"
        n += 1
    return candidato


def gravar_json(execucao: Execucao, caminho: Path) -> None:
    caminho.write_text(json.dumps(para_dict(execucao), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
