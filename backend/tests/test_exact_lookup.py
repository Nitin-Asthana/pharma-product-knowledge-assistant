"""Deterministic exact/structured lookup tests against the real dataset."""
from __future__ import annotations

import pytest

from app.services.product_service import product_service


@pytest.fixture(autouse=True)
def _skip_without_data(has_products):
    if not has_products:
        pytest.skip("No ingested product data available")


def test_exact_product_lookup_democin():
    matches = product_service.find_by_brand("DEMOCIN")
    assert matches, "DEMOCIN should resolve via exact brand lookup"
    assert matches[0].brand_name.upper() == "DEMOCIN"


def test_democin_and_democin_o_are_distinct():
    democin = product_service.find_by_brand("DEMOCIN")
    democin_o = product_service.find_by_brand("DEMOCIN O")
    assert democin and democin_o
    assert democin[0].product_id != democin_o[0].product_id


def test_ingredient_search_nurobalin():
    results = product_service.find_by_ingredient("Nurobalin")
    # Deterministic: at least detects via normalized composition if present.
    for p in results:
        assert "nurobalin" in p.composition_normalized or any(
            "nurobalin" in (i.ingredient or "").lower() for i in p.ingredients
        )


def test_category_search_anti_infective():
    results = product_service.find_by_category("anti-infective")
    for p in results:
        assert "anti" in p.therapeutic_category_normalized


def test_get_product_by_id_roundtrip():
    all_p = product_service.all_products()
    assert all_p
    first = all_p[0]
    fetched = product_service.get_product(first.product_id)
    assert fetched is not None
    assert fetched.product_id == first.product_id
