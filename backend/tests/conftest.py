"""Shared pytest fixtures.

The product/registry singletons are loaded from the real generated dataset so
tests exercise the actual structured-retrieval layer (no Azure calls needed).
"""
from __future__ import annotations

import pytest

from app.services.product_service import product_service
from app.services.source_registry import source_registry


@pytest.fixture(scope="session", autouse=True)
def _load_data() -> None:
    source_registry.load(force=True)
    product_service.load(force=True)


@pytest.fixture(scope="session")
def has_products() -> bool:
    return product_service.stats()["products"] > 0
