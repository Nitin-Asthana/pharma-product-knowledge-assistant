"""Source registry endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ..models.source import SourceStatus
from ..services.dataset import read_ingestion_report
from ..services.product_service import product_service
from ..services.source_registry import source_registry

router = APIRouter(prefix="/api/sources")


@router.get("")
def list_sources() -> dict:
    sources = source_registry.get_all_sources()
    return {"sources": [s.model_dump(exclude_none=True) for s in sources]}


@router.get("/status")
def sources_status() -> dict:
    product_service.load()
    statuses: list[SourceStatus] = []
    for source in source_registry.get_all_sources():
        report = read_ingestion_report(source.source_id)
        product_count = product_service.source_product_count(source.source_id)
        category_count = product_service.source_category_count(source.source_id)

        if not source.enabled:
            status = "disabled"
        elif report and report.get("status") == "failed":
            status = "error"
        elif product_count > 0:
            status = "ready"
        else:
            status = "not_ingested"

        statuses.append(
            SourceStatus(
                source_id=source.source_id,
                name=source.name,
                enabled=source.enabled,
                status=status,
                product_count=product_count,
                category_count=category_count,
                last_ingested_at=(report or {}).get("completed_at", ""),
                url=source.url,
                source_type=source.source_type,
                message=(report or {}).get("error", "") if status == "error" else "",
            )
        )
    return {"sources": [s.model_dump() for s in statuses]}
