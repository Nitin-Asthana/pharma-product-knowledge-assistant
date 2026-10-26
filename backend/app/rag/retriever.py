"""Retrieval orchestration.

Implements the retrieval hierarchy:
    1. Deterministic structured lookup (product/ingredient/category)
    2. Exact lexical search (Azure AI Search keyword)
    3. Hybrid keyword + vector retrieval
    4. Semantic reranking
    5. (Generation happens in generator.py)

Deterministic structured lookups are preferred whenever they can answer the
question, and always work even when Azure Search is unavailable.
"""
from __future__ import annotations

import logging

from ..config import settings
from ..search import client as search_client
from ..services import azure_clients
from ..services.product_service import product_service
from .evidence import EvidenceItem, EvidencePacket
from .query_router import Intent, RouteResult

logger = logging.getLogger("abc-pharma.retriever")


class Retriever:
    def retrieve(self, query: str, route: RouteResult, source_ids: list[str] | None = None) -> EvidencePacket:
        source_ids = source_ids or None

        if route.intent in (Intent.EXACT_PRODUCT, Intent.COMPOSITION_LOOKUP, Intent.PRODUCT_COMPARISON):
            packet = self._by_product_ids(route.products, source_ids)
            if packet.is_sufficient():
                return packet
            # Fall through to fuzzy/semantic if exact IDs were not resolved.

        if route.intent == Intent.INGREDIENT_SEARCH and route.ingredient:
            packet = self._by_ingredient(route.ingredient, source_ids)
            if packet.is_sufficient():
                return packet

        if route.intent == Intent.CATEGORY_SEARCH and route.category:
            packet = self._by_category(route.category, source_ids)
            if packet.is_sufficient():
                return packet

        if route.intent == Intent.PORTFOLIO_OVERVIEW:
            return self._portfolio(source_ids)

        # Semantic / general fallback -> hybrid retrieval (with structured backup).
        return self._hybrid(query, source_ids)

    # ------------------------------------------------------------- deterministic
    def _by_product_ids(self, product_ids: list[str], source_ids: list[str] | None) -> EvidencePacket:
        items: list[EvidenceItem] = []
        for pid in product_ids:
            p = product_service.get_product(pid)
            if p and (not source_ids or p.source_id in source_ids):
                items.append(EvidenceItem.from_product(p, score=1.0, mode="exact"))
        return EvidencePacket(items=items, retrieval_mode="exact")

    def _by_ingredient(self, ingredient: str, source_ids: list[str] | None) -> EvidencePacket:
        products = product_service.find_by_ingredient(ingredient, source_ids)
        items = [EvidenceItem.from_product(p, score=1.0, mode="structured") for p in products]
        return EvidencePacket(items=items, retrieval_mode="structured")

    def _by_category(self, category: str, source_ids: list[str] | None) -> EvidencePacket:
        products = product_service.find_by_category(category, source_ids)
        items = [EvidenceItem.from_product(p, score=1.0, mode="structured") for p in products]
        return EvidencePacket(items=items, retrieval_mode="structured")

    def _portfolio(self, source_ids: list[str] | None) -> EvidencePacket:
        products = product_service.all_products(source_ids)
        items = [EvidenceItem.from_product(p, score=1.0, mode="structured") for p in products]
        return EvidencePacket(items=items, retrieval_mode="structured")

    # -------------------------------------------------------------------- hybrid
    def _hybrid(self, query: str, source_ids: list[str] | None) -> EvidencePacket:
        # Try Azure Search hybrid + semantic; fall back to local lexical search.
        try:
            vector = None
            try:
                vector = azure_clients.embed_query(query)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Embedding unavailable, using keyword-only hybrid: %s", exc)

            results = search_client.hybrid_search(
                query=query,
                vector=vector,
                source_ids=source_ids,
                top=settings.top_k,
                semantic=True,
            )
            if results:
                items = [EvidenceItem.from_search(r) for r in results]
                mode = items[0].retrieval_mode if items else "hybrid"
                return EvidencePacket(items=items, retrieval_mode=mode)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Azure Search unavailable, falling back to local search: %s", exc)

        return self._local_fallback(query, source_ids)

    def _local_fallback(self, query: str, source_ids: list[str] | None) -> EvidencePacket:
        """Deterministic local search when Azure Search is unavailable."""
        # Brand substring, then ingredient, then category term matching.
        products = product_service.search_by_brand_substring(query, source_ids)
        if not products:
            # try token-based matching against composition/category
            from ..services.normalization import normalize_key

            tokens = [t for t in normalize_key(query).split() if len(t) > 3]
            scored: list[tuple[int, object]] = []
            for p in product_service.all_products(source_ids):
                hay = f"{p.brand_name_normalized} {p.composition_normalized} {p.therapeutic_category_normalized}"
                score = sum(1 for t in tokens if t in hay)
                if score:
                    scored.append((score, p))
            scored.sort(key=lambda t: -t[0])
            products = [p for _, p in scored[: settings.top_k]]

        items = [
            EvidenceItem.from_product(p, score=0.5, mode="local")
            for p in products[: settings.top_k]
        ]
        return EvidencePacket(items=items, retrieval_mode="local")


retriever = Retriever()
