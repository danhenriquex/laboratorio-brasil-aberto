import asyncio

import pytest

from localidades.cache import CacheComValidade
from localidades.erros import FonteIndisponivel, FonteLenta, NaoEncontrado, RespostaInesperadaDaFonte


class BuscarFalso:
    def __init__(self, relogio=None):
        self.chamadas = 0
        self.erro: Exception | None = None
        self.valor = "dados-1"
        self.espera = 0.0

    async def __call__(self):
        self.chamadas += 1
        if self.espera:
            await asyncio.sleep(self.espera)
        if self.erro is not None:
            raise self.erro
        return self.valor, "https://ibge/recurso"


def rodar(coro):
    return asyncio.run(coro)


def test_entrada_valida_atende_sem_consultar(relogio):
    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        primeira = await cache.obter("k", buscar)
        relogio.avancar(59)
        segunda = await cache.obter("k", buscar)
        return primeira, segunda, buscar.chamadas

    primeira, segunda, chamadas = rodar(cenario())
    assert chamadas == 1
    assert (primeira.resultado, segunda.resultado) == ("falta", "acerto")
    assert segunda.coletado_em == primeira.coletado_em
    assert segunda.dados == "dados-1" and segunda.url_fonte == "https://ibge/recurso"
    assert segunda.desatualizado is False


def test_entrada_vencida_renova(relogio):
    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        primeira = await cache.obter("k", buscar)
        relogio.avancar(61)
        buscar.valor = "dados-2"
        segunda = await cache.obter("k", buscar)
        return primeira, segunda, buscar.chamadas

    primeira, segunda, chamadas = rodar(cenario())
    assert chamadas == 2
    assert segunda.dados == "dados-2" and segunda.resultado == "falta"
    assert segunda.coletado_em > primeira.coletado_em


@pytest.mark.parametrize("erro", [FonteIndisponivel("x"), FonteLenta("x"), RespostaInesperadaDaFonte("x")])
def test_vencida_com_falha_serve_copia_desatualizada(relogio, erro):
    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        primeira = await cache.obter("k", buscar)
        relogio.avancar(3600)
        buscar.erro = erro
        segunda = await cache.obter("k", buscar)
        terceira = await cache.obter("k", buscar)  # continua vencida: tenta a fonte de novo
        return primeira, segunda, terceira, buscar.chamadas

    primeira, segunda, terceira, chamadas = rodar(cenario())
    assert segunda.desatualizado is True and segunda.resultado == "desatualizado"
    assert segunda.coletado_em == primeira.coletado_em
    assert segunda.dados == "dados-1"
    assert terceira.desatualizado is True
    assert chamadas == 3


def test_ausente_com_falha_propaga(relogio):
    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        buscar.erro = FonteLenta("lenta")
        await cache.obter("k", buscar)

    with pytest.raises(FonteLenta):
        rodar(cenario())


def test_nao_encontrado_e_erros_nao_entram_na_copia(relogio):
    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        buscar.erro = NaoEncontrado("não existe")
        for _ in range(2):
            with pytest.raises(NaoEncontrado):
                await cache.obter("k", buscar)
        buscar.erro = FonteIndisponivel("fora")
        with pytest.raises(FonteIndisponivel):
            await cache.obter("k", buscar)
        buscar.erro = None
        ok = await cache.obter("k", buscar)
        return ok, buscar.chamadas

    ok, chamadas = rodar(cenario())
    assert chamadas == 4
    assert ok.resultado == "falta"


def test_nao_encontrado_com_copia_vencida_propaga(relogio):
    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        await cache.obter("k", buscar)
        relogio.avancar(61)
        buscar.erro = NaoEncontrado("deixou de existir")
        await cache.obter("k", buscar)

    with pytest.raises(NaoEncontrado):
        rodar(cenario())


def test_consulta_unica_por_chave(relogio):
    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        buscar.espera = 0.05
        resultados = await asyncio.gather(*(cache.obter("k", buscar) for _ in range(10)))
        outra = await cache.obter("outra", buscar)
        return resultados, outra, buscar.chamadas

    resultados, outra, chamadas = rodar(cenario())
    assert chamadas == 2  # uma para "k" e uma para "outra"
    assert sorted(r.resultado for r in resultados) == ["acerto"] * 9 + ["falta"]
    assert outra.resultado == "falta"


# --- Convergência 3 (T050): falha compartilhada entre pedidos simultâneos ---


def test_falha_da_consulta_em_andamento_e_compartilhada(relogio):
    import time

    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        buscar.espera, buscar.erro = 0.1, FonteLenta("lenta")
        inicio = time.monotonic()
        resultados = await asyncio.gather(*(cache.obter("k", buscar) for _ in range(10)), return_exceptions=True)
        return resultados, buscar.chamadas, time.monotonic() - inicio

    resultados, chamadas, duracao = rodar(cenario())
    assert chamadas == 1  # a fonte com problema recebe uma única consulta
    assert all(isinstance(r, FonteLenta) for r in resultados)
    assert duracao < 0.2  # ninguém espera em fila por mais de um prazo


def test_copia_vencida_servida_a_todos_que_esperavam(relogio):
    async def cenario():
        cache, buscar = CacheComValidade(relogio, validade_s=60), BuscarFalso()
        await cache.obter("k", buscar)
        relogio.avancar(61)
        buscar.espera, buscar.erro = 0.05, FonteIndisponivel("fora")
        resultados = await asyncio.gather(*(cache.obter("k", buscar) for _ in range(5)))
        return resultados, buscar.chamadas

    resultados, chamadas = rodar(cenario())
    assert chamadas == 2
    assert all(r.desatualizado and r.resultado == "desatualizado" for r in resultados)
