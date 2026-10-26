"""Retrieval, comparison, grounding, citation, and safety tests.

These exercise the deterministic retrieval path and the fallback (LLM-free)
generation so they run without Azure credentials.
"""
from __future__ import annotations

import pytest

from app.models.chat import ResponseStyle
from app.rag.citations import build_citations, validate_citation_urls
from app.rag.generator import _prepare, generator
from app.rag.query_router import Intent, route
from app.rag.retriever import retriever
from app.services.product_service import product_service
from app.services.source_registry import source_registry


@pytest.fixture(autouse=True)
def _skip_without_data(has_products):
    if not has_products:
        pytest.skip("No ingested product data available")


# --------------------------------------------------------------- retrieval
def test_exact_retrieval_returns_product():
    r = route("Tell me about DEMOCIN")
    packet = retriever.retrieve("Tell me about DEMOCIN", r, None)
    assert packet.is_sufficient()
    assert any("democin" in pid for pid in packet.product_ids())


def test_category_retrieval_returns_multiple():
    r = route("Show me all anti-infective products")
    packet = retriever.retrieve("Show me all anti-infective products", r, None)
    assert packet.is_sufficient()


# --------------------------------------------------------------- comparison
def test_comparison_resolves_both_products():
    r = route("Compare DEMOCIN and DEMOCIN O")
    assert r.intent == Intent.PRODUCT_COMPARISON
    packet = _prepare("Compare DEMOCIN and DEMOCIN O", r, None)
    ids = packet.product_ids()
    assert len(ids) >= 2


# --------------------------------------------------------------- grounding
def test_fallback_answer_is_grounded_in_evidence():
    r = route("Tell me about DEMOCIN")
    packet = _prepare("Tell me about DEMOCIN", r, None)
    answer = generator._fallback_answer(packet)
    # The grounded fallback should mention the retrieved brand and nothing invented.
    assert "DEMOCIN" in answer.upper()


def test_full_generate_runs_without_azure():
    # Even without Azure OpenAI, generate() must return a grounded answer via fallback.
    result = generator.generate("Tell me about DEMOCIN", ResponseStyle.standard)
    assert result.answer
    assert result.products
    assert result.intent == Intent.EXACT_PRODUCT.value


# --------------------------------------------------------------- citations
def test_citations_come_from_registry_only():
    r = route("Tell me about DEMOCIN")
    packet = _prepare("Tell me about DEMOCIN", r, None)
    citations = validate_citation_urls(build_citations(packet))
    assert citations
    valid_urls = {s.url for s in source_registry.get_all_sources()}
    for c in citations:
        assert c.url in valid_urls


def test_invalid_citation_urls_dropped():
    from app.models.chat import Citation

    fake = Citation(
        source_id="x", source_name="X", title="X", url="https://evil.example.com/injected"
    )
    assert validate_citation_urls([fake]) == []


# --------------------------------------------------------------- abstention
def test_out_of_scope_abstains():
    result = generator.generate("What is ABC Pharma's market share?")
    assert result.intent == Intent.OUT_OF_SCOPE.value
    assert "knowledge" in result.answer.lower() or "couldn't" in result.answer.lower()


def test_unknown_product_abstains():
    result = generator.generate("Tell me about Xyzzyqwerty Zxcvblorptium")
    # No real match -> grounded abstention, not a hallucinated product description.
    answer = result.answer.lower()
    abstained = any(
        phrase in answer
        for phrase in ("could not find", "couldn't find", "not find sufficient", "insufficient")
    )
    assert result.products == [] or abstained


# --------------------------------------------------------------- safety
def test_medical_advice_prefixed_with_safety_notice():
    result = generator.generate("What dose of DEMOCIN should I prescribe for my patient?")
    assert "patient-specific" in result.answer.lower() or "can't provide" in result.answer.lower()
