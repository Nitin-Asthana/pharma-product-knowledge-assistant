"""Query router intent classification tests."""
from __future__ import annotations

from app.rag.query_router import Intent, route


def test_exact_product_intent():
    r = route("Tell me about DEMOCIN")
    assert r.intent == Intent.EXACT_PRODUCT
    assert any("democin" in pid for pid in r.products)


def test_composition_lookup_intent():
    r = route("What is the composition of DEMOCIN?")
    assert r.intent == Intent.COMPOSITION_LOOKUP
    assert r.products


def test_comparison_intent():
    r = route("Compare DEMOCIN and DEMOCIN O")
    assert r.intent == Intent.PRODUCT_COMPARISON
    assert len(r.products) >= 2


def test_ingredient_search_intent():
    r = route("Which products contain Nurobalin?")
    assert r.intent == Intent.INGREDIENT_SEARCH
    assert r.ingredient and "nurobalin" in r.ingredient.lower()


def test_category_search_intent():
    r = route("Show me all anti-infective products")
    assert r.intent == Intent.CATEGORY_SEARCH
    assert r.category


def test_portfolio_overview_intent():
    r = route("Give me an executive overview of the Product Catalog portfolio")
    assert r.intent == Intent.PORTFOLIO_OVERVIEW


def test_out_of_scope_intent():
    r = route("What is ABC Pharma's market share?")
    assert r.intent == Intent.OUT_OF_SCOPE


def test_medical_advice_flagged():
    r = route("What dose should I prescribe for my patient?")
    assert r.is_medical_advice is True


def test_semantic_fallback():
    r = route("Which products are relevant to pain management?")
    # Pain management is a category signal; either category or semantic is acceptable,
    # but it must not be out of scope.
    assert r.intent in {
        Intent.CATEGORY_SEARCH,
        Intent.SEMANTIC_PRODUCT_SEARCH,
        Intent.GENERAL_PRODUCT_QA,
    }
