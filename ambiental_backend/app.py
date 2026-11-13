# -*- coding: utf-8 -*-
"""Aplicacao FastAPI do backend ambiental.

Duas formas de uso, com o mesmo codigo:

1. no Space principal (Gradio + FastAPI ja existentes):
       from ambiental_backend.api_ambiental import router as ambiental_router
       api.include_router(ambiental_router)

2. como aplicacao independente (local ou Space proprio):
       uvicorn ambiental_backend.app:app --host 0.0.0.0 --port 7860

O esquema do banco e' criado no startup de forma idempotente; `/docs` e
`/openapi.json` ficam disponiveis sem configuracao extra.
"""
from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import api_ambiental, config
from . import persistencia as db
from . import persistencia_remota

#: Interface web (SPA sem etapa de build) publicada junto com a API.
FRONTEND = Path(__file__).resolve().parent / "frontend"

DESCRICAO = (
    "Backend da aplicacao ALEF-TAV Ambiental. Recebe uma pergunta de pesquisa, "
    "mantem a matriz 7Dx4 do material, recupera evidencias nas bases "
    "cientificas existentes, executa os simuladores ja registrados, compara "
    "com a literatura e devolve viabilidade, prova de conceito e relatorios. "
    "Nenhum resultado e' inventado: o que falta volta como ausente."
)


@asynccontextmanager
async def ciclo(app: FastAPI):
    try:
        print("[ambiental] persistencia remota:", persistencia_remota.preparar())
    except Exception as erro:                       # pragma: no cover
        print("[ambiental] falha na persistencia remota:", erro)
    try:
        db.garantir_esquema()
    except Exception as erro:                       # pragma: no cover
        print("[ambiental] falha ao preparar esquema:", erro)
    yield


def create_app() -> FastAPI:
    aplicacao = FastAPI(
        title=config.NOME_SERVICO,
        version=config.VERSAO,
        description=DESCRICAO,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=ciclo,
    )

    origens = config.origens_cors()
    regex = config.origem_regex()
    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=origens,
        allow_origin_regex=regex or None,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "Content-Length",
                        "X-Relatorio-Id"],
        max_age=600,
    )

    def origem_permitida(origem: str, request: Request) -> bool:
        """Decide se a origem pode falar com a API (sem depender do proxy)."""
        if not origem:
            return True                      # chamada servidor-a-servidor
        # A propria interface servida por esta API: o navegador manda `Origin`
        # igual ao host da pagina. Comparar host (e nao esquema) cobre o caso
        # do proxy do Hugging Face, que termina o TLS e entrega http ao app.
        proprio = (urlparse(origem).netloc or "").lower()
        hospedeiros = {str(request.headers.get(nome) or "").lower()
                       for nome in ("host", "x-forwarded-host")}
        if proprio and proprio in {h for h in hospedeiros if h}:
            return True
        if "https://" + proprio in origens or "http://" + proprio in origens:
            return True
        if "*" in origens or origem in origens:
            return True
        if regex:
            try:
                return re.match(regex, origem) is not None
            except re.error:                 # pragma: no cover - regex invalida
                return True
        return False

    @aplicacao.middleware("http")
    async def exigir_origem_conhecida(request: Request, call_next):
        """Aplica a politica de origem na propria aplicacao.

        O proxy do Hugging Face (e de outros provedores) acrescenta
        `Access-Control-Allow-Origin` a resposta; confiar so' no middleware de
        CORS deixaria qualquer site chamar a API. Aqui a origem desconhecida e'
        recusada antes de chegar na rota.
        """
        origem = request.headers.get("origin")
        if not origem_permitida(origem, request):
            return JSONResponse(status_code=403, content={"erro": {
                "codigo": "origem_nao_autorizada",
                "mensagem": "origem nao autorizada: %s" % origem,
                "detalhes": {"origens_permitidas": origens}}})
        return await call_next(request)

    aplicacao.include_router(api_ambiental.router)

    @aplicacao.exception_handler(HTTPException)
    async def http_erro(request: Request, exc: HTTPException):
        detalhe = exc.detail
        if isinstance(detalhe, dict):
            corpo = {"erro": {
                "codigo": detalhe.get("codigo") or "http_%s" % exc.status_code,
                "mensagem": detalhe.get("mensagem") or "",
                "detalhes": detalhe.get("detalhes"),
            }}
        else:
            corpo = {"erro": {"codigo": "http_%s" % exc.status_code,
                              "mensagem": str(detalhe)}}
        return JSONResponse(status_code=exc.status_code, content=corpo)

    @aplicacao.exception_handler(RequestValidationError)
    async def validacao(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"erro": {
            "codigo": "validacao",
            "mensagem": "corpo ou parametros invalidos",
            "detalhes": exc.errors()}})

    @aplicacao.exception_handler(Exception)
    async def inesperado(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"erro": {
            "codigo": "erro_interno",
            "mensagem": "%s: %s" % (type(exc).__name__, exc)}})

    @aplicacao.get("/api/ready", include_in_schema=False)
    def pronto():
        """Resposta minima e imediata: serve para acordar/verificar o servico.

        Nao toca no banco nem nos motores, entao responde mesmo durante a
        inicializacao do Space (o frontend pode usar como sinal de `acordando`
        em vez de tratar a primeira falha como servico fora do ar).
        """
        return {"estado": "pronto", "servico": config.NOME_SERVICO,
                "versao": config.VERSAO}

    @aplicacao.get("/api", include_in_schema=False)
    def indice_api():
        return {
            "servico": config.NOME_SERVICO,
            "versao": config.VERSAO,
            "interface": "/app/",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/api/health",
            "ready": "/api/ready",
            "luna": "/api/luna/status",
            "luna_chat": "POST /api/luna/chat",
            "fluxo": ["POST /api/research",
                      "POST /api/research/{id}/protocol",
                      "POST /api/research/{id}/materials",
                      "POST /api/research/{id}/evidence/search",
                      "POST /api/research/{id}/simulations",
                      "POST /api/research/{id}/viability",
                      "POST /api/research/{id}/proof-of-concept",
                      "POST /api/research/{id}/reports"],
        }

    @aplicacao.get("/", include_in_schema=False)
    def raiz():
        indice = FRONTEND / "index.html"
        if indice.is_file():
            return FileResponse(indice, media_type="text/html")
        return indice_api()

    if FRONTEND.is_dir():
        from fastapi.staticfiles import StaticFiles

        aplicacao.mount("/app", StaticFiles(directory=str(FRONTEND),
                                            html=True), name="interface")

    return aplicacao


app = create_app()


if __name__ == "__main__":                          # pragma: no cover
    import uvicorn

    uvicorn.run("ambiental_backend.app:app", host="0.0.0.0",
                port=int(os.environ.get("PORT", "7860")), reload=False)
