"""Adaptador HTTP (FastAPI): rotas v1, erros em problem+json, correlação e operação.

O contrato é o arquivo escrito à mão em contracts/localidades/openapi.yaml; o OpenAPI automático do FastAPI
fica desligado para não existirem dois contratos (research.md, R3).
"""

from __future__ import annotations

import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from localidades.config import Configuracao
from localidades.erros import EntradaInvalida, ErroDominio, ErroInterno, NaoEncontrado
from localidades.fonte_ibge import ClienteIBGE
from localidades.servico import RelogioSistema, Resultado, ServicoLocalidades

CABECALHO_CORRELACAO = "X-Correlation-Id"
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
    app.state.config = config
    app.state.cliente_ibge = cliente_ibge or ClienteIBGE(config)
    app.state.servico = ServicoLocalidades(app.state.cliente_ibge, relogio, config)

    @app.middleware("http")
    async def correlacao(request: Request, call_next):
        request.state.correlacao_id = correlacao_de(request.headers.get(CABECALHO_CORRELACAO))
        try:
            resposta = await call_next(request)
        except Exception:  # falha não tratada vira 500 sem detalhes internos (FR-013)
            resposta = problema(ErroInterno("erro interno do serviço"), request.state.correlacao_id)
        resposta.headers[CABECALHO_CORRELACAO] = request.state.correlacao_id
        return resposta

    @app.exception_handler(ErroDominio)
    async def _erro_dominio(request: Request, erro: ErroDominio):
        return problema(erro, _correlacao(request))

    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, erro: RequestValidationError):
        partes = []
        for item in erro.errors():
            campo = ".".join(str(x) for x in item.get("loc", ())[1:]) or "pedido"
            partes.append(f"{campo}: {item.get('msg', 'valor inválido')}")
        return problema(EntradaInvalida("; ".join(partes) or "pedido inválido"), _correlacao(request))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, erro: StarletteHTTPException):
        if erro.status_code in (404, 405):
            return problema(NaoEncontrado(f"a rota {request.url.path} não existe"), _correlacao(request))
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
            ),
            request,
        )

    @app.get("/health", include_in_schema=False)
    async def saude():
        return {"status": "ok"}

    return app
