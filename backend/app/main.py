"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import chat, health, products, search, sources
from .config import settings
from .services.product_service import product_service
from .services.source_registry import SourceRegistryError, source_registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("abc-pharma")

app = FastAPI(
    title="ABC Pharma Product Knowledge Assistant",
    description="Dynamic Multi-Source RAG over Azure AI Search + Azure OpenAI.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    try:
        source_registry.validate_sources()
        product_service.load()
        stats = product_service.stats()
        logger.info(
            "Startup complete: %s source(s), %s product(s).",
            stats["sources"],
            stats["products"],
        )
    except SourceRegistryError as exc:
        logger.error("Source registry invalid at startup: %s", exc)


@app.exception_handler(SourceRegistryError)
def _registry_error_handler(request: Request, exc: SourceRegistryError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": f"Source registry error: {exc}"})


app.include_router(health.router, tags=["health"])
app.include_router(sources.router, tags=["sources"])
app.include_router(products.router, tags=["products"])
app.include_router(search.router, tags=["search"])
app.include_router(chat.router, tags=["chat"])


@app.get("/")
def root() -> dict:
    return {
        "name": "ABC Pharma Product Knowledge Assistant API",
        "version": "0.1.0",
        "docs": "/docs",
    }
