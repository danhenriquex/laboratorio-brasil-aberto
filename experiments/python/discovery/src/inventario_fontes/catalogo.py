"""Leitura e validação do catálogo de fontes (`discovery/sources.json`).

O catálogo é validado por inteiro antes de qualquer consulta (FR-002) e nunca
é alterado pela ferramenta (FR-003).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from inventario_fontes.modelos import Catalogo, Fonte, Grau

_ID = re.compile(r"^[a-z0-9-]+$")
_URL = re.compile(r"^https?://\S+$")
_OBRIGATORIOS = ("id", "name", "domain", "docs_url", "data_type", "access_hypothesis", "auth", "verification", "round")


class ErroCatalogo(Exception):
    def __init__(self, problemas: list[str]) -> None:
        self.problemas = problemas
        super().__init__("catálogo inválido:\n" + "\n".join(f"  - {p}" for p in problemas))


def carregar_catalogo(caminho: str | Path) -> Catalogo:
    caminho = Path(caminho)
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErroCatalogo([f"catálogo não encontrado: {caminho}"]) from None
    except (OSError, UnicodeDecodeError) as erro:
        raise ErroCatalogo([f"catálogo ilegível ({caminho}): {erro}"]) from None
    except json.JSONDecodeError as erro:
        raise ErroCatalogo([f"JSON inválido em {caminho}: {erro}"]) from None

    if not isinstance(bruto, dict) or not isinstance(bruto.get("sources"), list):
        raise ErroCatalogo([f"{caminho}: esperado um objeto com a lista 'sources'"])
    schema_version = bruto.get("schema_version")
    if not isinstance(schema_version, int):
        raise ErroCatalogo([f"{caminho}: 'schema_version' ausente ou não inteiro"])

    problemas: list[str] = []
    fontes: list[Fonte] = []
    vistos: set[str] = set()
    for i, item in enumerate(bruto["sources"]):
        fonte, erros = _validar_fonte(i, item, vistos)
        problemas.extend(erros)
        if fonte is not None:
            fontes.append(fonte)
            vistos.add(fonte.id)

    if problemas:
        raise ErroCatalogo(problemas)
    return Catalogo(caminho=str(caminho), schema_version=schema_version, fontes=tuple(fontes))


def _validar_fonte(i: int, item: object, vistos: set[str]) -> tuple[Fonte | None, list[str]]:
    if not isinstance(item, dict):
        return None, [f"fonte[{i}] (?): esperado um objeto"]
    ident = item.get("id") if isinstance(item.get("id"), str) else "?"
    prefixo = f"fonte[{i}] ({ident})"
    erros: list[str] = []

    for campo in _OBRIGATORIOS:
        if campo not in item:
            erros.append(f"{prefixo}: campo {campo} ausente")
    if erros:
        return None, erros

    def texto(campo: str) -> None:
        if not isinstance(item[campo], str) or not item[campo].strip():
            erros.append(f"{prefixo}: campo {campo} deve ser texto não vazio")

    if not isinstance(item["id"], str) or not _ID.match(item["id"]):
        erros.append(f"{prefixo}: campo id deve seguir [a-z0-9-]+")
    elif item["id"] in vistos:
        erros.append(f"{prefixo}: campo id duplicado")
    for campo in ("name", "domain", "access_hypothesis", "auth"):
        texto(campo)
    docs = item["docs_url"]
    if docs is not None and (not isinstance(docs, str) or not _URL.match(docs)):
        erros.append(f"{prefixo}: campo docs_url deve começar com http(s):// ou ser nulo")
    probe = item.get("probe_url")
    if probe is not None and (not isinstance(probe, str) or not _URL.match(probe)):
        erros.append(f"{prefixo}: campo probe_url deve começar com http(s):// ou ser nulo")
    tipos = item["data_type"]
    if not isinstance(tipos, list) or not tipos or not all(isinstance(t, str) for t in tipos):
        erros.append(f"{prefixo}: campo data_type deve ser lista de texto não vazia")
    if item["verification"] not in {g.value for g in Grau}:
        erros.append(f"{prefixo}: campo verification deve ser confirmado, parcial ou nao_verificado")
    rodada = item["round"]
    if not isinstance(rodada, int) or isinstance(rodada, bool) or rodada < 1:
        erros.append(f"{prefixo}: campo round deve ser inteiro >= 1")
    notas = item.get("notes")
    if notas is not None and not isinstance(notas, str):
        erros.append(f"{prefixo}: campo notes deve ser texto")

    if erros:
        return None, erros
    return (
        Fonte(
            id=item["id"],
            nome=item["name"],
            dominio=item["domain"],
            url_documentacao=docs,
            url_teste=probe,
            tipos_dado=tuple(tipos),
            hipotese_acesso=item["access_hypothesis"],
            auth_esperada=item["auth"],
            verificacao=Grau(item["verification"]),
            rodada=rodada,
            notas=notas,
        ),
        [],
    )
