"""End-to-end, repeatable ingestion.

For each enabled source:
    scrape -> normalize/build -> structured dataset -> embeddings -> Azure AI
    Search upsert -> ingestion report.

Incremental behaviour:
    - unchanged product content    -> reuse existing embedding
    - changed / new product        -> regenerate embedding
    - removed product              -> delete its search document

If one source fails, others still proceed; the run reports partial success and
never marks a failed source as ready.

Usage:
    python scripts/ingest.py [--source SOURCE_ID] [--skip-azure]
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone

import _bootstrap  # noqa: F401

from app.config import settings
from app.services import azure_clients
from app.services.dataset import (
    PIPELINE_VERSION,
    read_embeddings,
    read_products_json,
    write_ingestion_report,
)
from app.services.source_registry import source_registry
from scrape_sources import scrape_source

# Reuse embedding + index helpers.
from generate_embeddings import generate_for_source  # noqa: E402


def _index_source(source, report: dict) -> None:
    """Upsert documents into Azure AI Search and prune removed products."""
    from app.search import client as search_client

    products = read_products_json(source.source_id)
    embeddings = read_embeddings(source.source_id)
    last_updated = datetime.now(timezone.utc).isoformat()

    documents = []
    for p in products:
        emb = embeddings.get(p.product_id, {})
        vector = emb.get("embedding")
        documents.append(search_client.product_to_document(p, vector, last_updated))

    indexed = search_client.upload_documents(documents)
    report["search_documents_indexed"] = indexed

    # Prune: delete search docs whose product_id no longer exists in the dataset.
    current_ids = {p.product_id.replace(":", "__") for p in products}
    try:
        existing = search_client.get_search_client().search(
            search_text="*",
            filter=f"source_id eq '{source.source_id}'",
            select=["id"],
            top=1000,
        )
        stale = [r["id"] for r in existing if r["id"] not in current_ids]
        removed = search_client.delete_documents(stale)
        report["products_removed"] = removed
    except Exception as exc:  # noqa: BLE001
        report.setdefault("warnings", []).append(f"prune skipped: {exc}")


def ingest_source(source, skip_azure: bool = False) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    report: dict = {
        "source_id": source.source_id,
        "source_url": source.url,
        "started_at": started,
        "products_discovered": 0,
        "products_added": 0,
        "products_updated": 0,
        "products_removed": 0,
        "duplicates": 0,
        "embedding_count": 0,
        "search_documents_indexed": 0,
        "pipeline_version": PIPELINE_VERSION,
        "status": "running",
    }
    try:
        summary = scrape_source(source)
        report["products_discovered"] = summary["quality"]["product_count"] + summary["quality"]["duplicates"]
        report["products_added"] = summary["product_count"]
        report["duplicates"] = summary["quality"]["duplicates"]
        report["missing_composition"] = summary["quality"]["missing_composition"]
        report["missing_category"] = summary["quality"]["missing_category"]

        if not skip_azure:
            emb = generate_for_source(source)
            report["embedding_count"] = emb["embedding_count"]
            report["embeddings_generated"] = emb["generated"]
            report["embeddings_reused"] = emb["reused"]
            _index_source(source, report)
            report["status"] = "success"
        else:
            report["status"] = "scraped"
    except Exception as exc:  # noqa: BLE001
        report["status"] = "failed"
        report["error"] = str(exc)
        print(f"  ERROR ingesting {source.source_id}: {exc}")

    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_ingestion_report(source.source_id, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Repeatable ingestion pipeline.")
    parser.add_argument("--source", help="Only ingest this source_id")
    parser.add_argument(
        "--skip-azure",
        action="store_true",
        help="Scrape and build datasets only (no embeddings / no Azure Search).",
    )
    args = parser.parse_args()

    source_registry.validate_sources()
    sources = source_registry.get_enabled_sources()
    if args.source:
        sources = [s for s in sources if s.source_id == args.source]

    reports = [ingest_source(s, skip_azure=args.skip_azure) for s in sources]

    ok = sum(1 for r in reports if r["status"] in ("success", "scraped"))
    total = len(reports)
    print("\n=== Ingestion summary ===")
    for r in reports:
        print(
            f"  {r['source_id']}: {r['status']} "
            f"(products={r['products_added']}, embeddings={r['embedding_count']}, "
            f"indexed={r['search_documents_indexed']})"
        )
    print(f"Knowledge base updated: {ok} of {total} source(s) succeeded.")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
