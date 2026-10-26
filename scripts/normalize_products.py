"""Re-derive normalized product fields from raw source text.

The scraper/product-builder already produces normalized fields. This utility
rebuilds them from ``products.json`` without re-scraping — useful if the
normalization rules change. Raw source text is never altered.

Usage:
    python scripts/normalize_products.py [--source SOURCE_ID]
"""
from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from app.services.dataset import read_products_json, write_products_json
from app.services.normalization import normalize_key
from app.services.product_builder import parse_ingredients
from app.services.source_registry import source_registry


def normalize_source(source) -> int:
    products = read_products_json(source.source_id)
    if not products:
        return 0
    for p in products:
        p.brand_name_normalized = normalize_key(p.brand_name)
        p.composition_normalized = normalize_key(p.composition)
        p.therapeutic_category_normalized = normalize_key(p.therapeutic_category)
        p.ingredients = parse_ingredients(
            p.product_id, p.source_id, p.brand_name, p.raw_composition
        )
    write_products_json(source.source_id, products)
    return len(products)


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-normalize product datasets.")
    parser.add_argument("--source", help="Only process this source_id")
    args = parser.parse_args()

    sources = source_registry.get_all_sources()
    if args.source:
        sources = [s for s in sources if s.source_id == args.source]

    for source in sources:
        n = normalize_source(source)
        print(f"{source.source_id}: normalized {n} products")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
