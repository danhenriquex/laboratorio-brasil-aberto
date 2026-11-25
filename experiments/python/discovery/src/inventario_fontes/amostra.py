"""Estrutura da amostra (R5): nomes de campos e tipos de até 5 registros, nunca os valores.

Cada valor é lido só para inferir o tipo e descartado em seguida; `CampoAmostra`
não tem atributo para guardar valor (FR-015). Chaves de objeto que parecem dados
(só dígitos, datas, documentos) são mascaradas como `<chave>`.
"""

from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

from inventario_fontes.modelos import CampoAmostra, EstruturaAmostra, Formato, TipoCampo

MAX_REGISTROS = 5
MAX_PROFUNDIDADE = 5
_DATA = re.compile(r"^(\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?.*)?|\d{2}/\d{2}/\d{4})$")
_INTEIRO = re.compile(r"^-?\d+$")
_DECIMAL = re.compile(r"^-?\d+[.,]\d+$")
_CHAVE_DADO = re.compile(r"^[\d.\-/:]+$")
_ORDEM = {t: i for i, t in enumerate(TipoCampo)}


class ErroAmostra(Exception):
    """O conteúdo não pode ser interpretado no formato declarado ou detectado."""


class _Coletor:
    def __init__(self) -> None:
        self.tipos: dict[str, set[TipoCampo]] = defaultdict(set)

    def adicionar(self, caminho: str, tipo: TipoCampo) -> None:
        self.tipos[caminho].add(tipo)

    def campos(self) -> tuple[CampoAmostra, ...]:
        return tuple(
            CampoAmostra(caminho, tuple(sorted(tipos, key=_ORDEM.__getitem__)))
            for caminho, tipos in sorted(self.tipos.items())
        )


def _tipo_texto(texto: str) -> TipoCampo:
    t = texto.strip()
    if not t:
        return TipoCampo.NULO
    if _INTEIRO.match(t):
        return TipoCampo.INTEIRO
    if _DECIMAL.match(t):
        return TipoCampo.DECIMAL
    if _DATA.match(t):
        return TipoCampo.DATA
    if t.lower() in {"true", "false"}:
        return TipoCampo.BOOLEANO
    return TipoCampo.TEXTO


def _tipo_json(valor: object) -> TipoCampo:
    if valor is None:
        return TipoCampo.NULO
    if isinstance(valor, bool):
        return TipoCampo.BOOLEANO
    if isinstance(valor, int):
        return TipoCampo.INTEIRO
    if isinstance(valor, float):
        return TipoCampo.DECIMAL
    if isinstance(valor, dict):
        return TipoCampo.OBJETO
    if isinstance(valor, list):
        return TipoCampo.LISTA
    return TipoCampo.DATA if _DATA.match(str(valor)) else TipoCampo.TEXTO


def _chave(nome: str) -> str:
    return "<chave>" if _CHAVE_DADO.match(nome) else nome


def _percorrer(valor: object, caminho: str, profundidade: int, coletor: _Coletor) -> None:
    coletor.adicionar(caminho, _tipo_json(valor))
    if profundidade >= MAX_PROFUNDIDADE:
        return
    if isinstance(valor, dict):
        for k, v in valor.items():
            _percorrer(v, f"{caminho}.{_chave(k)}", profundidade + 1, coletor)
    elif isinstance(valor, list):
        for item in valor[:MAX_REGISTROS]:
            _percorrer(item, f"{caminho}[]", profundidade + 1, coletor)


def _registros_json(dado: object) -> tuple[list, str | None]:
    if isinstance(dado, list):
        return dado, None
    if isinstance(dado, dict):
        for k, v in dado.items():
            if isinstance(v, list) and all(isinstance(item, dict) for item in v):
                return v, _chave(k)
        return [dado], None
    return [dado], None


def _json(corpo: bytes, truncada: bool) -> EstruturaAmostra:
    if truncada:
        return EstruturaAmostra(0, None, (), indisponivel_motivo="resposta truncada")
    try:
        dado = json.loads(corpo)
    except (json.JSONDecodeError, UnicodeDecodeError) as erro:
        raise ErroAmostra(f"JSON inválido: {getattr(erro, 'msg', erro)}") from None
    registros, caminho = _registros_json(dado)
    amostra = registros[:MAX_REGISTROS]
    coletor = _Coletor()
    for registro in amostra:
        if isinstance(registro, dict):
            for k, v in registro.items():
                _percorrer(v, _chave(k), 1, coletor)
        else:
            _percorrer(registro, "[]", 1, coletor)
    return EstruturaAmostra(len(amostra), caminho, coletor.campos(), vazia=not registros)


def _decodificar(corpo: bytes) -> str:
    try:
        return corpo.decode("utf-8-sig")
    except UnicodeDecodeError:
        return corpo.decode("latin-1")


def _csv(corpo: bytes, truncada: bool) -> EstruturaAmostra:
    linhas = _decodificar(corpo).splitlines()
    if truncada and linhas:
        linhas = linhas[:-1]
    linhas = [linha for linha in linhas if linha.strip()][: MAX_REGISTROS + 1]
    if not linhas:
        return EstruturaAmostra(0, None, (), vazia=True)
    try:
        dialeto = csv.Sniffer().sniff("\n".join(linhas), delimiters=",;\t|")
        tabela = list(csv.reader(linhas, dialeto))
    except csv.Error as erro:
        raise ErroAmostra(f"CSV inválido: {erro}") from None
    cabecalho, registros = tabela[0], tabela[1:]
    coletor = _Coletor()
    for linha in registros:
        for coluna, celula in zip(cabecalho, linha):
            coletor.adicionar(_chave(coluna.strip()), _tipo_texto(celula))
    return EstruturaAmostra(len(registros), None, coletor.campos(), vazia=not registros)


def _tag(elemento: ET.Element) -> str:
    return elemento.tag.rsplit("}", 1)[-1]


def _percorrer_xml(elemento: ET.Element, caminho: str, profundidade: int, coletor: _Coletor) -> None:
    filhos = list(elemento)
    coletor.adicionar(caminho, TipoCampo.OBJETO if filhos else _tipo_texto(elemento.text or ""))
    for atributo, valor in elemento.attrib.items():
        coletor.adicionar(f"{caminho}.@{atributo.rsplit('}', 1)[-1]}", _tipo_texto(valor))
    if profundidade >= MAX_PROFUNDIDADE:
        return
    for filho in filhos:
        _percorrer_xml(filho, f"{caminho}.{_tag(filho)}", profundidade + 1, coletor)


def _xml(corpo: bytes, truncada: bool) -> EstruturaAmostra:
    if truncada:
        return EstruturaAmostra(0, None, (), indisponivel_motivo="resposta truncada")
    try:
        raiz = ET.fromstring(corpo)
    except ET.ParseError as erro:
        raise ErroAmostra(f"XML inválido: {erro}") from None
    registros = list(raiz) or [raiz]
    amostra = registros[:MAX_REGISTROS]
    coletor = _Coletor()
    for registro in amostra:
        for atributo, valor in registro.attrib.items():
            coletor.adicionar(f"@{atributo.rsplit('}', 1)[-1]}", _tipo_texto(valor))
        for filho in registro:
            _percorrer_xml(filho, _tag(filho), 1, coletor)
    caminho = _tag(raiz) if list(raiz) else None
    return EstruturaAmostra(len(amostra), caminho, coletor.campos())


def inferir_estrutura(corpo: bytes, formato: Formato, truncada: bool) -> EstruturaAmostra | None:
    """Estrutura da amostra para JSON, CSV e XML; `None` para os demais formatos."""
    if formato is Formato.JSON:
        return _json(corpo, truncada)
    if formato is Formato.CSV:
        return _csv(corpo, truncada)
    if formato is Formato.XML:
        return _xml(corpo, truncada)
    return None
