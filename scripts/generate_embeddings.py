"""Generate embeddings for structured product content.

Reads ``products.json`` per source, builds source-grounded embedding content and
calls Azure OpenAI. Reuses existing embeddings for unchanged content (keyed by a
content hash) to avoid unnecessary regeneration.

Usage:
    python scripts/generate_embeddings.py [--source SOURCE_ID] [--force]
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone

import _bootstrap  # noqa: F401

from app.config import settings
from app.services import azure_clients
from app.services.dataset import read_embeddings, read_products_json, write_embeddings
from app.services.source_registry import source_registry


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_for_source(source, force: bool = False) -> dict:
    products = read_products_json(source.source_id)
    if not products:
        print(f"  no products for {source.source_id}; skipping")
        return {"embedding_count": 0, "reused": 0, "generated": 0}

    existing = read_embeddings(source.source_id) if not force else {}

    to_embed: list[tuple[str, str]] = []  # (product_id, content)
    records: dict[str, dict] = {}
    reused = 0

    for p in products:
        content = p.content()
        chash = _content_hash(content)
        prev = existing.get(p.product_id)
        if prev and prev.get("content_hash") == chash and prev.get("embedding"):
            records[p.product_id] = prev
            reused += 1
        else:
            to_embed.append((p.product_id, content))
            records[p.product_id] = {
                "product_id": p.product_id,
                "source_id": p.source_id,
                "content": content,
                "content_hash": chash,
                "embedding_model": settings.azure_openai_embedding_deployment,
                "embedding_dimensions": settings.embedding_dimensions,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    generated = 0
    # Batch embed new/changed content.
    BATCH = 64
    for i in range(0, len(to_embed), BATCH):
        batch = to_embed[i : i + BATCH]
        vectors = azure_clients.embed_texts([c for _, c in batch])
        for (pid, _), vec in zip(batch, vectors):
            records[pid]["embedding"] = vec
            generated += 1
        print(f"  embedded {min(i + BATCH, len(to_embed))}/{len(to_embed)}")

    ordered = [records[p.product_id] for p in products if p.product_id in records]
    write_embeddings(source.source_id, ordered)
    print(f"  {source.source_id}: generated={generated} reused={reused} total={len(ordered)}")
    return {"embedding_count": len(ordered), "reused": reused, "generated": generated}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate embeddings for enabled sources.")
    parser.add_argument("--source", help="Only process this source_id")
    parser.add_argument("--force", action="store_true", help="Regenerate all embeddings")
    args = parser.parse_args()

    sources = source_registry.get_enabled_sources()
    if args.source:
        sources = [s for s in sources if s.source_id == args.source]

    for source in sources:
        print(f"\n=== Embeddings: {source.source_id} ===")
        try:
            generate_for_source(source, force=args.force)
        except azure_clients.AzureOpenAIUnavailable as exc:
            print(f"  ERROR: Azure OpenAI unavailable: {exc}")
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
