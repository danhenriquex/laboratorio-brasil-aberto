"""Paridade de ordenação e busca entre implementações (E4: FR-004, SC-005).

A ordem esperada é calculada aqui, a partir das fixtures, com a regra R8 do E1: NFKD, sem marcas
diacríticas (categoria Mn), casefold e desempate pelo código. Qualquer implementação precisa devolver
exatamente essa ordem.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from contrato import validar

ROTA = "/v1/ufs/{uf}/municipios"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures-ibge"


def dobrar(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn").casefold()


def esperados_sp(nome: str | None = None) -> list[str]:
    itens = json.loads((FIXTURES / "municipios-uf-35.json").read_text(encoding="utf-8"))
    if nome is not None:
        alvo = dobrar(nome.strip())
        itens = [m for m in itens if alvo in dobrar(m["nome"])]
    ordenados = sorted(itens, key=lambda m: (dobrar(m["nome"]), str(m["id"])))
    return [str(m["id"]) for m in ordenados]


def todos_os_codigos(servico, **params) -> list[str]:
    codigos: list[str] = []
    pagina = 1
    while True:
        r = servico.get("/v1/ufs/SP/municipios", params={**params, "itens": 500, "pagina": pagina})
        validar(r, "GET", ROTA)
        assert r.status_code == 200
        corpo = r.json()
        codigos += [m["codigo"] for m in corpo["dados"]]
        if pagina >= corpo["paginacao"]["paginas"]:
            return codigos
        pagina += 1


def test_ordem_dos_645_municipios_de_sp_e_a_da_regra_r8(servico):
    esperados = esperados_sp()
    assert len(esperados) == 645
    assert todos_os_codigos(servico) == esperados


@pytest.mark.parametrize("nome", ["são", "SAO", "d'oeste", "ITÁ"])
def test_busca_por_nome_devolve_o_mesmo_conjunto_na_mesma_ordem(servico, nome):
    assert todos_os_codigos(servico, nome=nome) == esperados_sp(nome)
