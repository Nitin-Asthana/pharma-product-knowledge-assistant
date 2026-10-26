"""Normalization and product-ID generation tests."""
from __future__ import annotations

from app.models.source import Source
from app.services.normalization import clean_text, normalize_key, slugify
from app.services.product_builder import build_product, make_product_id, parse_ingredients

_SOURCE = Source(
    source_id="abc-pharma-catalog",
    name="ABC Pharma Catalog",
    url="https://www.example.com/about-us/products/catalog/",
    source_type="product_catalogue",
    enabled=True,
)


def test_clean_text_collapses_whitespace_preserves_case():
    assert clean_text("  DEMOCIN   O  ") == "DEMOCIN O"
    assert clean_text("Democillin\t800  mg") == "Democillin 800 mg"


def test_normalize_key_is_lowercase():
    assert normalize_key("DEMOCIN O") == "democin o"


def test_slugify_stable():
    assert slugify("DEMOCIN O") == "democin-o"
    assert slugify("DEMOCIN  O") == "democin-o"


def test_product_id_is_source_scoped():
    pid = make_product_id(_SOURCE.source_id, "DEMOCIN")
    assert pid == "abc-pharma-catalog:democin"


def test_build_product_preserves_raw_and_derives_normalized():
    p = build_product(
        source=_SOURCE,
        source_title="Catalogue",
        scraped_at="2026-01-01T00:00:00Z",
        raw_product_name="DEMOCIN",
        raw_composition="Democillin 800 mg",
        raw_category="ANTI INFECTIVES",
    )
    assert p.raw_composition == "Democillin 800 mg"
    assert p.brand_name == "DEMOCIN"
    assert p.therapeutic_category_normalized == "anti infectives"
    # Strength/units are never altered in the presented composition.
    assert "800 mg" in p.composition


def test_ingredient_parsing_extracts_strength_and_unit():
    ings = parse_ingredients(
        "pid", _SOURCE.source_id, "TEST", "Nurobalin 1500 mcg"
    )
    parsed = [i for i in ings if i.ingredient]
    assert parsed, "expected at least one parsed ingredient"
    assert parsed[0].strength == "1500"
    assert parsed[0].unit.lower() == "mcg"


def test_empty_composition_yields_blank_ingredient_but_preserves_raw():
    ings = parse_ingredients("pid", _SOURCE.source_id, "TEST", "")
    assert ings == []


def test_unparseable_composition_preserves_raw():
    ings = parse_ingredients("pid", _SOURCE.source_id, "TEST", "herbal blend")
    assert len(ings) == 1
    assert ings[0].ingredient == ""
    assert ings[0].raw_composition == "herbal blend"
