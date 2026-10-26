"""Product catalogue service.

Loads structured product datasets (from ``products.json`` per source) and
provides cached, deterministic lookups used by the API and the RAG retriever.
This is the in-memory structured-retrieval layer (no LLM, no vector search).
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

from ..models.product import Product
from .dataset import read_ingestion_report, read_products_json
from .normalization import normalize_key
from .source_registry import source_registry


class ProductService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._products: dict[str, Product] = {}
        self._by_source: dict[str, list[Product]] = {}
        self._by_brand_key: dict[str, list[Product]] = {}
        self._last_refreshed: str = ""

    # ------------------------------------------------------------------ loading
    def load(self, force: bool = False) -> None:
        with self._lock:
            if self._loaded and not force:
                return
            self._products.clear()
            self._by_source.clear()
            self._by_brand_key.clear()
            last_times: list[str] = []

            for source in source_registry.get_enabled_sources():
                products = read_products_json(source.source_id)
                self._by_source[source.source_id] = products
                for p in products:
                    self._products[p.product_id] = p
                    self._by_brand_key.setdefault(normalize_key(p.brand_name), []).append(p)
                report = read_ingestion_report(source.source_id)
                if report and report.get("completed_at"):
                    last_times.append(report["completed_at"])

            self._last_refreshed = max(last_times) if last_times else ""
            self._loaded = True

    def refresh(self) -> None:
        self.load(force=True)

    # ------------------------------------------------------------------ queries
    def all_products(self, source_ids: list[str] | None = None) -> list[Product]:
        self.load()
        if not source_ids:
            return list(self._products.values())
        result: list[Product] = []
        for sid in source_ids:
            result.extend(self._by_source.get(sid, []))
        return result

    def get_product(self, product_id: str) -> Product | None:
        self.load()
        return self._products.get(product_id)

    def find_by_brand(self, brand: str, source_ids: list[str] | None = None) -> list[Product]:
        """Exact (normalized) brand-name match."""
        self.load()
        matches = self._by_brand_key.get(normalize_key(brand), [])
        if source_ids:
            matches = [p for p in matches if p.source_id in source_ids]
        return matches

    def search_by_brand_substring(self, term: str, source_ids: list[str] | None = None) -> list[Product]:
        self.load()
        key = normalize_key(term)
        if not key:
            return []
        results = [
            p
            for p in self.all_products(source_ids)
            if key in normalize_key(p.brand_name)
        ]
        return results

    def find_by_ingredient(self, ingredient: str, source_ids: list[str] | None = None) -> list[Product]:
        """Deterministic ingredient lookup via structured ingredients + normalized composition."""
        self.load()
        key = normalize_key(ingredient)
        if not key:
            return []
        results: list[Product] = []
        for p in self.all_products(source_ids):
            structured = any(key in normalize_key(i.ingredient) for i in p.ingredients if i.ingredient)
            in_composition = key in p.composition_normalized
            if structured or in_composition:
                results.append(p)
        return results

    def find_by_category(self, category: str, source_ids: list[str] | None = None) -> list[Product]:
        self.load()
        key = normalize_key(category).replace("-", " ")
        tokens = [t for t in key.split() if t]
        if not tokens:
            return []
        results: list[Product] = []
        for p in self.all_products(source_ids):
            target = p.therapeutic_category_normalized.replace("-", " ")
            # Match when every query token appears as a substring in the category
            # (handles plural/singular and hyphen/space variants conservatively).
            if all(any(tok in word or word in tok for word in target.split()) for tok in tokens):
                results.append(p)
        return results

    def categories(self, source_ids: list[str] | None = None) -> list[dict]:
        self.load()
        counts: dict[str, int] = {}
        for p in self.all_products(source_ids):
            cat = p.therapeutic_category or "(uncategorized)"
            counts[cat] = counts.get(cat, 0) + 1
        return [
            {"therapeutic_category": cat, "product_count": n}
            for cat, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

    def ingredients(self, source_ids: list[str] | None = None) -> list[str]:
        self.load()
        seen: set[str] = set()
        ordered: list[str] = []
        for p in self.all_products(source_ids):
            for ing in p.ingredients:
                if ing.ingredient and ing.ingredient.lower() not in seen:
                    seen.add(ing.ingredient.lower())
                    ordered.append(ing.ingredient)
        return sorted(ordered)

    # -------------------------------------------------------------------- stats
    def stats(self) -> dict:
        self.load()
        products = list(self._products.values())
        cats = {p.therapeutic_category for p in products if p.therapeutic_category}
        return {
            "sources": len(source_registry.get_enabled_sources()),
            "products": len(products),
            "categories": len(cats),
            "last_refreshed": self._last_refreshed,
        }

    def source_product_count(self, source_id: str) -> int:
        self.load()
        return len(self._by_source.get(source_id, []))

    def source_category_count(self, source_id: str) -> int:
        self.load()
        cats = {p.therapeutic_category for p in self._by_source.get(source_id, []) if p.therapeutic_category}
        return len(cats)

    @property
    def last_refreshed(self) -> str:
        self.load()
        return self._last_refreshed or datetime.now(timezone.utc).isoformat()


product_service = ProductService()
