"""IBGE falso: serve as fixtures gravadas da API de localidades em 127.0.0.1.

Usado pela verificação de caixa-preta (research.md, R4). Imita o comportamento real observado em
2026-11-26 (R1): recurso inexistente devolve 200 com `[]`.
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PREFIXO = "/api/v1/localidades"
FIXTURES_PADRAO = Path(__file__).resolve().parents[3] / "fixtures-ibge"

_MUNICIPIOS_DA_UF = re.compile(r"/estados/(\d+)/municipios")
_MUNICIPIO = re.compile(r"/municipios/(\d+)")


class Fixtures:
    def __init__(self, pasta: Path) -> None:
        self.pasta = pasta
        self.estados = (pasta / "estados.json").read_bytes()
        self.listas_por_uf: dict[str, bytes] = {}
        self.municipios: dict[str, bytes] = {}
        for arquivo in sorted(pasta.glob("municipios-uf-*.json")):
            uf = arquivo.stem.removeprefix("municipios-uf-")
            corpo = arquivo.read_bytes()
            self.listas_por_uf[uf] = corpo
            for item in json.loads(corpo):
                self.municipios[str(item["id"])] = json.dumps(item, ensure_ascii=False).encode()
        for arquivo in sorted(pasta.glob("municipio-[0-9]*.json")):
            self.municipios[arquivo.stem.removeprefix("municipio-")] = arquivo.read_bytes()

    def resolver(self, caminho: str) -> bytes | None:
        if not caminho.startswith(PREFIXO):
            return None
        resto = caminho[len(PREFIXO) :]
        if resto == "/estados":
            return self.estados
        if m := _MUNICIPIOS_DA_UF.fullmatch(resto):
            return self.listas_por_uf.get(m.group(1), b"[]")
        if m := _MUNICIPIO.fullmatch(resto):
            return self.municipios.get(m.group(1), b"[]")
        return None


MODOS = {"normal", "fora", "lento", "invalido"}


class Estado:
    """Estado compartilhado entre as threads do servidor, controlado por /_controle."""

    def __init__(self, fixtures: Fixtures) -> None:
        self.fixtures = fixtures
        self.erro_html = (fixtures.pasta / "erro.html").read_bytes()
        self.trava = threading.Lock()
        self.modo = "normal"
        self.segundos = 0.0
        self.contagem: Counter[str] = Counter()

    def definir(self, modo: str, segundos: float) -> None:
        with self.trava:
            self.modo, self.segundos = modo, segundos

    def registrar(self, caminho: str) -> tuple[str, float]:
        with self.trava:
            self.contagem[caminho] += 1
            return self.modo, self.segundos


def _criar_manipulador(estado: Estado):
    class Manipulador(BaseHTTPRequestHandler):
        server_version = "IBGEFalso/0.1"
        protocol_version = "HTTP/1.1"

        def log_message(self, formato, *args):  # silencioso
            pass

        def _responder(self, status: int, corpo: bytes, tipo: str = "application/json; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            caminho = self.path.split("?", 1)[0]
            if caminho == "/_controle/contagem":
                with estado.trava:
                    corpo = json.dumps(dict(estado.contagem)).encode()
                return self._responder(200, corpo)
            if not caminho.startswith(PREFIXO):
                return self._responder(404, b'{"erro": "rota inexistente no IBGE falso"}')

            modo, segundos = estado.registrar(caminho)
            if modo == "fora":
                return self._responder(503, b'{"erro": "IBGE falso fora do ar"}')
            if modo == "invalido":
                return self._responder(200, estado.erro_html, "text/html; charset=utf-8")
            if modo == "lento":
                time.sleep(segundos)
            corpo = estado.fixtures.resolver(caminho)
            if corpo is None:
                return self._responder(404, b'{"erro": "rota inexistente no IBGE falso"}')
            try:
                self._responder(200, corpo)
            except (BrokenPipeError, ConnectionResetError):
                pass  # o serviço desistiu antes (prazo esgotado)

        def do_POST(self):
            caminho = self.path.split("?", 1)[0]
            tamanho = int(self.headers.get("Content-Length") or 0)
            bruto = self.rfile.read(tamanho) if tamanho else b"{}"
            if caminho == "/_controle/zerar":
                with estado.trava:
                    estado.contagem.clear()
                return self._responder(200, b'{"ok": true}')
            if caminho != "/_controle":
                return self._responder(404, b'{"erro": "rota de controle inexistente"}')
            try:
                pedido = json.loads(bruto or b"{}")
                modo = pedido.get("modo", "normal")
                segundos = float(pedido.get("segundos", 0) or 0)
            except (ValueError, AttributeError, TypeError):
                return self._responder(400, b'{"erro": "corpo invalido"}')
            if modo not in MODOS:
                return self._responder(400, json.dumps({"erro": f"modo desconhecido: {modo}"}).encode())
            estado.definir(modo, segundos)
            return self._responder(200, json.dumps({"modo": modo, "segundos": segundos}).encode())

    return Manipulador


def criar_servidor(porta: int, pasta_fixtures: Path = FIXTURES_PADRAO, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    estado = Estado(Fixtures(pasta_fixtures))
    servidor = ThreadingHTTPServer((host, porta), _criar_manipulador(estado))
    servidor.daemon_threads = True
    servidor.estado = estado  # type: ignore[attr-defined]
    return servidor
