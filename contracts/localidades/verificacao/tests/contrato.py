"""Validação de respostas contra contracts/localidades/openapi.yaml (OpenAPI 3.1, JSON Schema 2020-12)."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

import httpx
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

OPENAPI = Path(__file__).resolve().parents[2] / "openapi.yaml"
URI_BASE = "urn:contrato:localidades"
_CORRELACAO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@cache
def documento() -> dict:
    return yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))


@cache
def _registro() -> Registry:
    recurso = Resource.from_contents(documento(), default_specification=DRAFT202012)
    return Registry().with_resource(URI_BASE, recurso)


def _resolver_ref(no: dict) -> dict:
    while "$ref" in no:
        caminho = no["$ref"].removeprefix("#/").split("/")
        no = documento()
        for parte in caminho:
            no = no[parte]
    return no


def _ponteiro(no: dict) -> dict:
    """Troca refs locais por refs absolutas no documento registrado."""
    if isinstance(no, dict):
        return {k: (URI_BASE + v if k == "$ref" and v.startswith("#") else _ponteiro(v)) for k, v in no.items()}
    if isinstance(no, list):
        return [_ponteiro(x) for x in no]
    return no


def validar(resposta: httpx.Response, metodo: str, rota_modelo: str) -> None:
    """Falha (AssertionError) se a resposta não estiver de acordo com o contrato."""
    operacao = documento()["paths"][rota_modelo][metodo.lower()]
    status = str(resposta.status_code)
    assert status in operacao["responses"], f"status {status} não declarado para {metodo} {rota_modelo}"
    declarada = _resolver_ref(operacao["responses"][status])

    if "headers" in declarada and "X-Correlation-Id" in declarada["headers"]:
        valor = resposta.headers.get("X-Correlation-Id", "")
        assert _CORRELACAO.match(valor), f"X-Correlation-Id ausente ou inválido: {valor!r}"

    conteudo = declarada.get("content", {})
    tipo_recebido = resposta.headers.get("content-type", "").split(";")[0].strip()
    assert tipo_recebido in conteudo, f"content-type {tipo_recebido!r} não declarado (esperado: {list(conteudo)})"

    schema = conteudo[tipo_recebido].get("schema")
    if schema is None or tipo_recebido == "text/plain":
        return
    validador = Draft202012Validator(_ponteiro(schema), registry=_registro(), format_checker=FormatChecker())
    erros = sorted(validador.iter_errors(resposta.json()), key=lambda e: list(e.absolute_path))
    assert not erros, "resposta fora do contrato:\n" + "\n".join(
        f"- {'/'.join(map(str, e.absolute_path)) or '(raiz)'}: {e.message}" for e in erros[:10]
    )
