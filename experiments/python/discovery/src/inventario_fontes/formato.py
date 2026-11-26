"""Detecção de formato: o declarado pela fonte (Content-Type) e o observado no conteúdo (R4)."""

from __future__ import annotations

import csv
import re

from inventario_fontes.modelos import Formato

_BOM = b"\xef\xbb\xbf"
_ELEMENTO_XML = re.compile(r"^<[A-Za-z_][\w.:-]*[\s/>]")
_PREFIXO = 8192


def formato_declarado(content_type: str | None) -> str | None:
    """Tipo de mídia sem parâmetros, em minúsculas (`application/json; charset=utf-8` → `application/json`)."""
    if not content_type:
        return None
    tipo = content_type.split(";", 1)[0].strip().lower()
    return tipo or None


def _decodificar(corpo: bytes) -> str | None:
    amostra = corpo[:_PREFIXO]
    if b"\x00" in amostra:
        return None
    try:
        texto = amostra.decode("utf-8")
    except UnicodeDecodeError as erro:
        # um caractere multibyte cortado no fim do prefixo não é erro de verdade
        if erro.start >= len(amostra) - 3:
            texto = amostra[: erro.start].decode("utf-8", errors="strict")
        else:
            texto = amostra.decode("latin-1")
    controles = sum(1 for c in texto if ord(c) < 32 and c not in "\t\n\r\f")
    if texto and controles / len(texto) > 0.05:
        return None
    return texto


def _parece_csv(texto: str) -> bool:
    linhas = [linha for linha in texto.splitlines() if linha.strip()][:6]
    if len(linhas) < 2:
        return False
    try:
        dialeto = csv.Sniffer().sniff("\n".join(linhas), delimiters=",;\t|")
    except csv.Error:
        return False
    contagens = {len(linha) for linha in csv.reader(linhas, dialeto)}
    return len(contagens) == 1 and contagens.pop() > 1


def detectar_formato(corpo: bytes) -> Formato:
    corpo = corpo.removeprefix(_BOM).lstrip()
    if not corpo:
        return Formato.VAZIO
    texto = _decodificar(corpo)
    if texto is None:
        return Formato.OUTRO
    if texto[0] in "{[":
        return Formato.JSON
    inicio = texto[:512].lower()
    if inicio.startswith("<!doctype html") or inicio.startswith("<html") or "<html" in inicio[:256]:
        return Formato.HTML
    if inicio.startswith("<?xml") or _ELEMENTO_XML.match(texto):
        return Formato.XML
    if _parece_csv(texto):
        return Formato.CSV
    return Formato.TEXTO


def _formato_do_tipo(declarado: str) -> set[Formato] | None:
    if declarado == "application/json" or declarado.endswith("+json"):
        return {Formato.JSON}
    if declarado == "text/csv":
        return {Formato.CSV}
    if declarado in {"application/xml", "text/xml"} or declarado.endswith("+xml"):
        return {Formato.XML}
    if declarado == "text/html":
        return {Formato.HTML}
    if declarado == "text/plain":
        return {Formato.TEXTO, Formato.CSV}
    return None


def divergente(declarado: str | None, detectado: Formato | None) -> bool:
    """Verdadeiro quando o tipo declarado é conhecido e não corresponde ao conteúdo."""
    if not declarado or detectado is None or detectado is Formato.VAZIO:
        return False
    esperados = _formato_do_tipo(declarado)
    return esperados is not None and detectado not in esperados
