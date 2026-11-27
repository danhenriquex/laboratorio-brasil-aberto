"""Adaptador HTTP (FastAPI): rotas v1, erros em problem+json, correlação e operação.

O contrato é o arquivo escrito à mão em contracts/localidades/openapi.yaml; o OpenAPI automático do FastAPI
fica desligado para não existirem dois contratos (research.md, R3).
"""

from __future__ import annotations

import re
import time
import uuid
from contextvars import ContextVar
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.routing import Match
from starlette.exceptions import HTTPException as StarletteHTTPException

from localidades.config import Configuracao
from localidades.erros import EntradaInvalida, ErroDominio, ErroInterno, NaoEncontrado
from localidades import registro
from localidades.fonte_ibge import ClienteIBGE
from localidades.metricas import Metricas
from localidades.servico import RelogioSistema, Resultado, ServicoLocalidades

CABECALHO_CORRELACAO = "X-Correlation-Id"
# Tempo gasto com o IBGE no pedido atual (a consulta roda dentro da tarefa do pedido).
_TEMPO_FONTE: ContextVar[list[float] | None] = ContextVar("tempo_fonte", default=None)
_CORRELACAO_VALIDA = re.compile(r"[A-Za-z0-9._-]{1,64}", re.ASCII)


def correlacao_de(valor: str | None) -> str:
    if valor and _CORRELACAO_VALIDA.fullmatch(valor):
        return valor
    return str(uuid.uuid4())


def problema(erro: ErroDominio, correlacao_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=erro.status,
        media_type="application/problem+json",
        content={
            "type": erro.urn,
            "title": erro.titulo,
            "status": erro.status,
            "detail": erro.detalhe,
            "correlacao_id": correlacao_id,
        },
        headers={CABECALHO_CORRELACAO: correlacao_id},
    )


def _inteiro(nome: str, valor: str | None, padrao: int) -> int:
    """Parâmetros de paginação são validados pelo domínio, para o detalhe citar o limite configurado."""
    if valor is None or valor.strip() == "":
        return padrao
    try:
        return int(valor)
    except ValueError:
        raise EntradaInvalida(f"{nome} precisa ser um número inteiro, recebi {valor!r}") from None


def envelope(resultado: Resultado, request: Request) -> dict[str, Any]:
    dados = resultado.dados
    corpo: dict[str, Any] = {
        "dados": [asdict(x) for x in dados] if isinstance(dados, list) else asdict(dados),
    }
    if resultado.paginacao is not None:
        p = resultado.paginacao
        corpo["paginacao"] = {"pagina": p.pagina, "itens": p.tamanho, "total": p.total, "paginas": p.paginas}
    corpo["meta"] = resultado.meta.para_dict()
    request.state.cache = resultado.cache
    return corpo


def _correlacao(request: Request) -> str:
    return getattr(request.state, "correlacao_id", None) or correlacao_de(request.headers.get(CABECALHO_CORRELACAO))


def criar_app(config: Configuracao, *, cliente_ibge: ClienteIBGE | None = None, relogio=None) -> FastAPI:
    relogio = relogio or RelogioSistema()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        yield
        await app.state.cliente_ibge.fechar()

    app = FastAPI(
        title="Serviço de localidades (IBGE)",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        lifespan=ciclo_de_vida,
    )
    metricas = Metricas()
    registro.configurar()

    def ao_medir(recurso: str, segundos: float) -> None:
        metricas.observar_fonte(recurso, segundos)
        if (tempos := _TEMPO_FONTE.get()) is not None:
            tempos.append(segundos)

    app.state.config = config
    app.state.metricas = metricas
    app.state.cliente_ibge = cliente_ibge or ClienteIBGE(config, ao_medir=ao_medir)
    app.state.servico = ServicoLocalidades(app.state.cliente_ibge, relogio, config)

    def modelo_da_rota(request: Request) -> str:
        """Modelo da rota (/v1/municipios/{codigo}), para não multiplicar séries de métricas."""
        for rota in app.router.routes:
            correspondencia, _ = rota.matches(request.scope)
            if correspondencia == Match.FULL:
                return getattr(rota, "path", "nao-encontrado")
        return "nao-encontrado"

    @app.middleware("http")
    async def correlacao_e_medicao(request: Request, call_next):
        inicio = time.monotonic()
        request.state.correlacao_id = correlacao_de(request.headers.get(CABECALHO_CORRELACAO))
        tempos: list[float] = []
        marcador = _TEMPO_FONTE.set(tempos)
        try:
            resposta = await call_next(request)
        except Exception:  # falha não tratada vira 500 sem detalhes internos (FR-013)
            request.state.erro_tipo = ErroInterno.tipo
            resposta = problema(ErroInterno("erro interno do serviço"), request.state.correlacao_id)
        finally:
            _TEMPO_FONTE.reset(marcador)
        resposta.headers[CABECALHO_CORRELACAO] = request.state.correlacao_id

        rota = modelo_da_rota(request)
        cache = getattr(request.state, "cache", None)
        metricas.registrar_pedido(rota, resposta.status_code, getattr(request.state, "erro_tipo", None), cache)
        registro.registrar_pedido(
            correlacao_id=request.state.correlacao_id,
            metodo=request.method,
            rota=rota,
            status=resposta.status_code,
            duracao_ms=(time.monotonic() - inicio) * 1000,
            cache=cache,
            fonte_ms=sum(tempos) * 1000 if tempos else None,
        )
        return resposta

    @app.exception_handler(ErroDominio)
    async def _erro_dominio(request: Request, erro: ErroDominio):
        request.state.erro_tipo = erro.tipo
        return problema(erro, _correlacao(request))

    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, erro: RequestValidationError):
        partes = []
        for item in erro.errors():
            campo = ".".join(str(x) for x in item.get("loc", ())[1:]) or "pedido"
            partes.append(f"{campo}: {item.get('msg', 'valor inválido')}")
        request.state.erro_tipo = EntradaInvalida.tipo
        return problema(EntradaInvalida("; ".join(partes) or "pedido inválido"), _correlacao(request))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, erro: StarletteHTTPException):
        if erro.status_code in (404, 405):
            request.state.erro_tipo = NaoEncontrado.tipo
            return problema(NaoEncontrado(f"a rota {request.url.path} não existe"), _correlacao(request))
        request.state.erro_tipo = ErroInterno.tipo
        return problema(ErroInterno("erro interno do serviço"), _correlacao(request))

    servico: ServicoLocalidades = app.state.servico

    @app.get("/v1/ufs")
    async def listar_ufs(request: Request):
        return envelope(await servico.listar_ufs(), request)

    @app.get("/v1/ufs/{uf}")
    async def obter_uf(uf: str, request: Request):
        return envelope(await servico.obter_uf(uf), request)

    @app.get("/v1/ufs/{uf}/municipios")
    async def listar_municipios(uf: str, request: Request):
        q = request.query_params
        return envelope(
            await servico.listar_municipios(
                uf,
                pagina=_inteiro("pagina", q.get("pagina"), 1),
                itens=_inteiro("itens", q.get("itens"), 100),
                nome=q.get("nome"),
            ),
            request,
        )

    @app.get("/v1/municipios/{codigo}")
    async def obter_municipio(codigo: str, request: Request):
        return envelope(await servico.obter_municipio(codigo), request)

    @app.get("/health", include_in_schema=False)
    async def saude():
        return {"status": "ok"}

    @app.get("/metrics", include_in_schema=False)
    async def exportar_metricas():
        conteudo, tipo = metricas.exportar()
        return Response(content=conteudo, media_type=tipo)

    return app
