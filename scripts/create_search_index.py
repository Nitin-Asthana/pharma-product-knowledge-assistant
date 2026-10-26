"""Create or update the Azure AI Search index ``abc-pharma-products``.

Vector dimensions come from ``EMBEDDING_DIMENSIONS`` — never assumed.

Usage:
    python scripts/create_search_index.py
"""
from __future__ import annotations

import _bootstrap  # noqa: F401

from app.config import settings
from app.search.index import create_or_update_index


def main() -> int:
    print(f"Creating/updating index '{settings.azure_search_index}' at {settings.azure_search_endpoint}")
    print(f"Vector dimensions: {settings.embedding_dimensions}")
    try:
        name = create_or_update_index()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not create/update index: {exc}")
        return 1
    print(f"Index ready: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
