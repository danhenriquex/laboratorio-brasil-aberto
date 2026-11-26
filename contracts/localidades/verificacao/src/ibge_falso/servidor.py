"""IBGE falso: serve as fixtures gravadas da API de localidades em 127.0.0.1.

Usado pela verificação de caixa-preta (research.md, R4). Imita o comportamento real observado em
2026-11-26 (R1): recurso inexistente devolve 200 com `[]`.
"""

from __future__ import annotations

import json
import re
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


class Estado:
    """Estado compartilhado entre as threads do servidor."""

    def __init__(self, fixtures: Fixtures) -> None:
        self.fixtures = fixtures


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
            corpo = estado.fixtures.resolver(caminho)
            if corpo is None:
                self._responder(404, b'{"erro": "rota inexistente no IBGE falso"}')
            else:
                self._responder(200, corpo)

    return Manipulador


def criar_servidor(porta: int, pasta_fixtures: Path = FIXTURES_PADRAO, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    estado = Estado(Fixtures(pasta_fixtures))
    servidor = ThreadingHTTPServer((host, porta), _criar_manipulador(estado))
    servidor.daemon_threads = True
    servidor.estado = estado  # type: ignore[attr-defined]
    return servidor
