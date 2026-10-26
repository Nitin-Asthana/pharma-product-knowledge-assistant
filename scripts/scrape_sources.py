"""Scrape all enabled sources into structured datasets.

Pipeline per source:
    registry -> scraper -> build products -> products.json + products.xlsx

No source URL is hardcoded; everything comes from the source registry.

Usage:
    python scripts/scrape_sources.py [--source SOURCE_ID]
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

import _bootstrap  # noqa: F401  (sets up sys.path)

from app.services.dataset import (
    PIPELINE_VERSION,
    read_ingestion_report,
    write_ingestion_report,
    write_products_json,
    write_products_xlsx,
)
from app.services.product_builder import build_products
from app.services.scrapers import get_scraper
from app.services.scrapers.base import ScraperError
from app.services.source_registry import source_registry


def scrape_source(source) -> dict:
    print(f"\n=== Scraping: {source.source_id} ({source.url}) ===")
    started = datetime.now(timezone.utc).isoformat()
    scraper = get_scraper(source)
    result = scraper.scrape(source)
    print(f"  fetched '{result.source_title}' -> {len(result.rows)} rows")
    for w in result.warnings:
        print(f"  warning: {w}")

    products, quality = build_products(
        source=source,
        source_title=result.source_title,
        scraped_at=result.fetched_at,
        rows=result.rows,
    )
    print(f"  built {len(products)} products (duplicates skipped: {quality['duplicates']})")

    metadata = {
        "source_id": source.source_id,
        "source_url": source.url,
        "source_title": result.source_title,
        "scraped_at": result.fetched_at,
        "product_count": len(products),
        "category_count": len({p.therapeutic_category for p in products if p.therapeutic_category}),
        "pipeline_version": PIPELINE_VERSION,
    }
    json_path = write_products_json(source.source_id, products)
    xlsx_path = write_products_xlsx(source.source_id, products, metadata)
    print(f"  wrote {json_path.name}, {xlsx_path.name}")

    # Preserve embedding/index counts from a prior full ingestion if present.
    prior = read_ingestion_report(source.source_id) or {}
    report = {
        "source_id": source.source_id,
        "source_url": source.url,
        "started_at": started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "products_discovered": len(result.rows),
        "products_added": len(products),
        "products_updated": 0,
        "products_removed": 0,
        "duplicates": quality["duplicates"],
        "missing_composition": quality["missing_composition"],
        "missing_category": quality["missing_category"],
        "embedding_count": prior.get("embedding_count", 0),
        "search_documents_indexed": prior.get("search_documents_indexed", 0),
        "pipeline_version": PIPELINE_VERSION,
        "status": "scraped",
    }
    write_ingestion_report(source.source_id, report)

    return {
        "source_id": source.source_id,
        "product_count": len(products),
        "quality": quality,
        "scraped_at": result.fetched_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape enabled sources.")
    parser.add_argument("--source", help="Only scrape this source_id")
    args = parser.parse_args()

    source_registry.validate_sources()
    sources = source_registry.get_enabled_sources()
    if args.source:
        sources = [s for s in sources if s.source_id == args.source]
        if not sources:
            print(f"No enabled source matches '{args.source}'.")
            return 1

    failures = 0
    for source in sources:
        try:
            scrape_source(source)
        except ScraperError as exc:
            failures += 1
            print(f"  ERROR scraping {source.source_id}: {exc}")

    print(f"\nDone at {datetime.now(timezone.utc).isoformat()} — {failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
