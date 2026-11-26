"""US3 — comportamento previsível quando o IBGE falha ou demora (caixa-preta).

O serviço guarda cópias entre os testes, por isso cada cenário usa um código de município diferente.
Perfil de verificação (verificar.sh): prazo de 1 s e validade de 2 s.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import httpx
import pytest

from conftest import LOCALIDADES_URL
from contrato import validar

ROTA = "/v1/municipios/{codigo}"
PRAZO_S = 1.0
VALIDADE_S = 2.0
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures-ibge"
_CODIGOS_SP = [str(m["id"]) for m in json.loads((FIXTURES / "municipios-uf-35.json").read_text(encoding="utf-8"))]
_proximo = iter(range(10, len(_CODIGOS_SP)))


def codigo_novo() -> str:
    """Um código de SP que nenhum outro teste pediu."""
    return _CODIGOS_SP[next(_proximo)]


def contagem(ibge, codigo: str) -> int:
    return ibge.get("/_controle/contagem").json().get(f"/api/v1/localidades/municipios/{codigo}", 0)


def modo(ibge, nome: str, segundos: float = 0.0) -> None:
    assert ibge.post("/_controle", json={"modo": nome, "segundos": segundos}).status_code == 200


@pytest.fixture(autouse=True)
def _ibge_normal(ibge):
    modo(ibge, "normal")
    yield
    modo(ibge, "normal")


def test_sc004_copia_valida_nao_consulta_a_fonte(servico, ibge):
    codigo = codigo_novo()
    r1 = servico.get(f"/v1/municipios/{codigo}")
    r2 = servico.get(f"/v1/municipios/{codigo}")
    for r in (r1, r2):
        validar(r, "GET", ROTA)
        assert r.status_code == 200
    assert contagem(ibge, codigo) == 1
    assert r2.json()["meta"]["coletado_em"] == r1.json()["meta"]["coletado_em"]


def test_sc003_pedido_com_copia_responde_em_menos_de_meio_segundo(servico):
    codigo = codigo_novo()
    servico.get(f"/v1/municipios/{codigo}")
    inicio = time.monotonic()
    r = servico.get(f"/v1/municipios/{codigo}")
    assert r.status_code == 200
    assert time.monotonic() - inicio < 0.5


@pytest.mark.parametrize(
    ("nome", "segundos", "status", "tipo"),
    [
        ("fora", 0, 502, "fonte-indisponivel"),
        ("lento", 3, 504, "fonte-lenta"),
        ("invalido", 0, 502, "resposta-inesperada-da-fonte"),
    ],
)
def test_sc005_falha_sem_copia_responde_rapido(servico, ibge, nome, segundos, status, tipo):
    codigo = codigo_novo()
    modo(ibge, nome, segundos)
    inicio = time.monotonic()
    r = servico.get(f"/v1/municipios/{codigo}")
    duracao = time.monotonic() - inicio
    validar(r, "GET", ROTA)
    assert r.status_code == status
    assert r.json()["type"] == f"urn:brasil-aberto:problema:{tipo}"
    assert duracao < PRAZO_S + 1.0  # prazo de 1 s mais margem; nenhum pedido fica pendurado
    assert "<html" not in r.text.lower()


def test_copia_vencida_servida_quando_a_fonte_cai(servico, ibge):
    codigo = codigo_novo()
    primeira = servico.get(f"/v1/municipios/{codigo}")
    assert primeira.status_code == 200
    time.sleep(VALIDADE_S + 0.2)
    modo(ibge, "fora")
    r = servico.get(f"/v1/municipios/{codigo}")
    validar(r, "GET", ROTA)
    assert r.status_code == 200
    assert r.json()["meta"]["desatualizado"] is True
    assert r.json()["meta"]["coletado_em"] == primeira.json()["meta"]["coletado_em"]
    assert r.json()["dados"] == primeira.json()["dados"]


def test_consulta_unica_com_pedidos_simultaneos(servico, ibge):
    codigo = codigo_novo()
    modo(ibge, "lento", 0.5)
    respostas: list[httpx.Response] = []
    trava = threading.Lock()

    def pedir():
        with httpx.Client(base_url=LOCALIDADES_URL, timeout=10) as c:
            r = c.get(f"/v1/municipios/{codigo}")
        with trava:
            respostas.append(r)

    threads = [threading.Thread(target=pedir) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [r.status_code for r in respostas] == [200] * 10
    assert contagem(ibge, codigo) == 1
