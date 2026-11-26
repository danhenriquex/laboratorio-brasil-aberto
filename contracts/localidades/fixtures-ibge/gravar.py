"""Grava respostas reais da API de localidades do IBGE como fixtures.

Execução manual, rara e fora dos testes (Constituição IV). Uso, a partir da raiz do repositório:

    python3 contracts/localidades/fixtures-ibge/gravar.py

Faz uma chamada por recurso, em sequência, com 2 s de intervalo, e grava o corpo exatamente como recebido.
Depois atualize o README.md desta pasta com a saída impressa.
"""

from __future__ import annotations

import hashlib
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE = "https://servicodados.ibge.gov.br/api/v1/localidades"
USER_AGENT = "laboratorio-brasil-aberto-localidades/0.1.0"
INTERVALO_S = 2.0

RECURSOS = {
    "estados.json": "/estados",
    "municipios-uf-33.json": "/estados/33/municipios",
    "municipios-uf-35.json": "/estados/35/municipios",
    "municipios-uf-53.json": "/estados/53/municipios",
    "municipio-5101837.json": "/municipios/5101837",
}


def main() -> None:
    pasta = Path(__file__).resolve().parent
    print(f"gravado em: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    for i, (arquivo, caminho) in enumerate(RECURSOS.items()):
        if i:
            time.sleep(INTERVALO_S)
        pedido = urllib.request.Request(BASE + caminho, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(pedido, timeout=30) as resposta:
            corpo = resposta.read()
            status = resposta.status
        (pasta / arquivo).write_bytes(corpo)
        sha = hashlib.sha256(corpo).hexdigest()
        print(f"| `{arquivo}` | `{BASE}{caminho}` | {status} | {len(corpo)} | `{sha[:16]}…` |")


if __name__ == "__main__":
    main()
