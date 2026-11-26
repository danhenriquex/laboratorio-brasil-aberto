"""A suíte fala com o serviço e com o IBGE falso só pela rede (FR-021, SC-008).

LOCALIDADES_URL: endereço do serviço em teste (padrão http://127.0.0.1:8090).
IBGE_FALSO_URL: endereço do IBGE falso (padrão http://127.0.0.1:8099).
O serviço precisa ter sido iniciado com o perfil de verificação; use verificar.sh.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

LOCALIDADES_URL = os.environ.get("LOCALIDADES_URL", "http://127.0.0.1:8090")
IBGE_FALSO_URL = os.environ.get("IBGE_FALSO_URL", "http://127.0.0.1:8099")


@pytest.fixture(scope="session")
def servico():
    with httpx.Client(base_url=LOCALIDADES_URL, timeout=10) as cliente:
        yield cliente


@pytest.fixture(scope="session")
def ibge():
    with httpx.Client(base_url=IBGE_FALSO_URL, timeout=10) as cliente:
        yield cliente
