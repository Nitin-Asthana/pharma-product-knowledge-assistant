"""Health and stats endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ..models.chat import StatsResponse
from ..search import client as search_client
from ..services import azure_clients
from ..services.product_service import product_service
from ..services.source_registry import source_registry

router = APIRouter()


@router.get("/health")
def health() -> dict:
    try:
        source_registry.load()
        registry_ok = True
    except Exception:  # noqa: BLE001
        registry_ok = False

    stats = product_service.stats()
    status = "ready" if registry_ok and stats["products"] > 0 else "degraded"
    return {
        "status": status,
        "registry_ok": registry_ok,
        "products": stats["products"],
        "sources": stats["sources"],
    }


@router.get("/api/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    s = product_service.stats()
    return StatsResponse(
        sources=s["sources"],
        products=s["products"],
        categories=s["categories"],
        last_refreshed=s["last_refreshed"],
        status="ready" if s["products"] > 0 else "not_ingested",
        search_available=search_client.search_available(),
        openai_available=azure_clients.openai_available(),
    )
