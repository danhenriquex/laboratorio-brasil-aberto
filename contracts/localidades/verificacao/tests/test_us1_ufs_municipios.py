"""US1 — listar estados e os municípios de um estado (caixa-preta)."""

import pytest

from contrato import validar

UFS = "/v1/ufs"
UF = "/v1/ufs/{uf}"
MUNICIPIOS = "/v1/ufs/{uf}/municipios"


def test_cenario_1_lista_as_27_ufs_com_procedencia(servico):
    r = servico.get("/v1/ufs")
    validar(r, "GET", UFS)
    assert r.status_code == 200
    corpo = r.json()
    assert len(corpo["dados"]) == 27
    assert {u["sigla"] for u in corpo["dados"]} >= {"RJ", "SP", "DF", "AC"}
    assert corpo["meta"]["fonte"] == "IBGE — API de localidades"


@pytest.mark.parametrize("param", ["RJ", "rj", "33", "%20RJ%20"])
def test_obter_uf_por_sigla_ou_codigo(servico, param):
    r = servico.get(f"/v1/ufs/{param}")
    validar(r, "GET", UF)
    assert r.status_code == 200
    assert r.json()["dados"]["codigo"] == "33"


@pytest.mark.parametrize("param", ["RJ", "rj", "33", "%20rj%20"])
def test_cenario_2_municipios_da_uf_em_ordem(servico, param):
    r = servico.get(f"/v1/ufs/{param}/municipios")
    validar(r, "GET", MUNICIPIOS)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["paginacao"]["total"] == 92
    nomes = [m["nome"] for m in corpo["dados"]]
    assert nomes[0] == "Angra dos Reis"
    assert "Niterói" in nomes


def test_cenario_3_paginacao_de_uf_grande(servico):
    r1 = servico.get("/v1/ufs/SP/municipios", params={"itens": 500})
    r2 = servico.get("/v1/ufs/SP/municipios", params={"itens": 500, "pagina": 2})
    for r in (r1, r2):
        validar(r, "GET", MUNICIPIOS)
    assert r1.json()["paginacao"] == {"pagina": 1, "itens": 500, "total": 645, "paginas": 2}
    assert len(r1.json()["dados"]) == 500
    assert len(r2.json()["dados"]) == 145
    codigos = [m["codigo"] for m in r1.json()["dados"] + r2.json()["dados"]]
    assert len(set(codigos)) == 645


@pytest.mark.parametrize("param", ["XX", "99"])
def test_cenario_4_uf_inexistente(servico, param):
    r = servico.get(f"/v1/ufs/{param}/municipios")
    validar(r, "GET", MUNICIPIOS)
    assert r.status_code == 404
    assert r.json()["type"] == "urn:brasil-aberto:problema:nao-encontrado"


def test_uf_mal_formada(servico):
    r = servico.get("/v1/ufs/R1/municipios")
    validar(r, "GET", MUNICIPIOS)
    assert r.status_code == 400


def test_df_tem_um_municipio(servico):
    r = servico.get("/v1/ufs/DF/municipios")
    validar(r, "GET", MUNICIPIOS)
    assert r.json()["dados"] == [{"codigo": "5300108", "nome": "Brasília"}]


def test_pagina_alem_do_fim(servico):
    r = servico.get("/v1/ufs/RJ/municipios", params={"pagina": 99})
    validar(r, "GET", MUNICIPIOS)
    assert r.status_code == 200
    assert r.json()["dados"] == []
    assert r.json()["paginacao"]["total"] == 92


@pytest.mark.parametrize("params", [{"itens": 501}, {"itens": 0}, {"pagina": 0}])
def test_paginacao_fora_dos_limites(servico, params):
    r = servico.get("/v1/ufs/RJ/municipios", params=params)
    validar(r, "GET", MUNICIPIOS)
    assert r.status_code == 400
    assert r.json()["type"] == "urn:brasil-aberto:problema:entrada-invalida"


def test_rota_sem_versao(servico):
    r = servico.get("/ufs")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")


def test_pagina_muito_grande_e_pagina_alem_do_fim(servico):
    """Convergência do E4 (T045): o contrato não limita `pagina`; um número enorme é só uma página vazia."""
    r = servico.get("/v1/ufs/RJ/municipios", params={"pagina": "99999999999"})
    validar(r, "GET", MUNICIPIOS)
    assert r.status_code == 200
    assert r.json()["dados"] == []
    assert r.json()["paginacao"]["pagina"] == 99999999999
    assert r.json()["paginacao"]["total"] == 92


def test_parametro_repetido_vale_o_ultimo(servico):
    """Convergência do E4 (T045): com `itens` repetido, vale o último valor, como no E1."""
    r = servico.get("/v1/ufs/RJ/municipios", params=[("itens", "10"), ("itens", "20")])
    validar(r, "GET", MUNICIPIOS)
    assert r.status_code == 200
    assert r.json()["paginacao"]["itens"] == 20
    assert len(r.json()["dados"]) == 20
