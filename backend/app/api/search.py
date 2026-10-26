"""Search endpoint (POST /api/search)."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ..models.chat import SearchRequest, SearchResponse, SearchResultItem
from ..rag.query_router import route
from ..rag.retriever import retriever

logger = logging.getLogger("abc-pharma.search_api")

router = APIRouter(prefix="/api")


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    source_ids = req.source_ids or None

    # Structured filters take precedence when provided.
    if req.ingredient or req.category:
        from ..services.product_service import product_service

        if req.ingredient:
            products = product_service.find_by_ingredient(req.ingredient, source_ids)
        else:
            products = product_service.find_by_category(req.category, source_ids)
        items = [
            SearchResultItem(
                product_id=p.product_id,
                brand_name=p.brand_name,
                therapeutic_category=p.therapeutic_category,
                composition=p.composition,
                source_id=p.source_id,
                source_name=p.source_name,
                source_url=p.source_url,
                score=1.0,
                retrieval_mode="structured",
            )
            for p in products[: req.top_k]
        ]
        return SearchResponse(
            query=req.query, count=len(items), results=items, retrieval_mode="structured"
        )

    route_result = route(req.query, source_ids)
    packet = retriever.retrieve(req.query, route_result, source_ids)
    items = [
        SearchResultItem(
            product_id=it.product_id,
            brand_name=it.brand_name,
            therapeutic_category=it.therapeutic_category,
            composition=it.composition,
            source_id=it.source_id,
            source_name=it.source_name,
            source_url=it.source_url,
            score=it.score,
            retrieval_mode=it.retrieval_mode,
        )
        for it in packet.items[: req.top_k]
    ]
    return SearchResponse(
        query=req.query,
        count=len(items),
        results=items,
        retrieval_mode=packet.retrieval_mode,
    )
