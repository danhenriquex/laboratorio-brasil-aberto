"""US4 — encontrar um município pelo nome dentro de um estado (caixa-preta)."""

import pytest

from contrato import validar

ROTA = "/v1/ufs/{uf}/municipios"


@pytest.mark.parametrize("termo", ["niteroi", "NITERÓI"])
def test_cenario_1_busca_sem_acento_nem_caixa(servico, termo):
    r = servico.get("/v1/ufs/RJ/municipios", params={"nome": termo})
    validar(r, "GET", ROTA)
    assert r.json()["dados"] == [{"codigo": "3303302", "nome": "Niterói"}]


def test_cenario_2_varios_resultados_em_ordem_e_paginados(servico):
    r = servico.get("/v1/ufs/SP/municipios", params={"nome": "são", "itens": 500})
    validar(r, "GET", ROTA)
    corpo = r.json()
    nomes = [m["nome"] for m in corpo["dados"]]
    assert corpo["paginacao"]["total"] == len(nomes) > 10
    assert "São Paulo" in nomes and "São José dos Campos" in nomes
    pagina = servico.get("/v1/ufs/SP/municipios", params={"nome": "SAO", "itens": 10, "pagina": 2})
    validar(pagina, "GET", ROTA)
    assert [m["nome"] for m in pagina.json()["dados"]] == nomes[10:20]


def test_cenario_3_busca_sem_resultado(servico):
    r = servico.get("/v1/ufs/SP/municipios", params={"nome": "xyzw"})
    validar(r, "GET", ROTA)
    assert r.status_code == 200
    assert r.json()["dados"] == []
    assert r.json()["paginacao"]["total"] == 0


@pytest.mark.parametrize("termo", ["a", " a ", "x" * 61])
def test_busca_fora_dos_limites(servico, termo):
    r = servico.get("/v1/ufs/SP/municipios", params={"nome": termo})
    validar(r, "GET", ROTA)
    assert r.status_code == 400
