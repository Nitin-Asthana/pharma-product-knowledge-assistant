"""Build normalized Product records from raw scraped rows.

Responsibilities:
- generate stable, source-scoped product IDs
- preserve raw source text verbatim
- derive conservative normalized fields (never altering quantities/units)
- best-effort structured ingredient extraction (blank when unreliable)
- duplicate detection across a source
"""
from __future__ import annotations

import re

from ..models.product import Ingredient, Product
from ..models.source import Source
from .normalization import clean_text, normalize_key, slugify

# Units we recognize when parsing composition strengths.
_UNIT_PATTERN = r"(mcg|mg|ml|g|iu|%\s*w/w|%\s*w/v|%|iu/ml)"
# Placeholder composition tokens that mean "no composition provided".
_EMPTY_COMPOSITION = {"", "na", "n/a", "-", "nil"}

# Preamble like "Each film coated tablet contains:" carries no ingredient.
_PREAMBLE_RE = re.compile(
    r"(?is)^\s*(?:composition\s*)?each\b.*?contains\s*:?\s*"
)

# Words/phrases that are dosage forms or connectors, never ingredients on their own.
_STOPWORDS = {
    "each", "contains", "composition", "tablet", "capsule", "ml", "vial",
    "film coated tablet", "hard gelatin capsule", "soft gelatin capsule",
    "uncoated tablet", "sugar coated tablet", "enteric coated tablet",
    "as sustained released", "as prolonged release form", "in prolonged release form",
    "in extended release form", "in sustained release form", "equivalent to",
    "eq to", "and", "with", "preservative", "gel base", "cream base", "q.s",
    "as preservative", "pre filled syringe", "prefilled syringe",
}

# Split a multi-ingredient composition on common ingredient boundaries.
_STRENGTH_RE = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9 .,'®()\-/]+?)\s*[.\u2026:]*\s*"
    r"(?P<strength>\d+(?:\.\d+)?)\s*(?P<unit>" + _UNIT_PATTERN + r")",
    re.IGNORECASE,
)

_LEADING_JUNK_RE = re.compile(
    r"(?i)^(?:and|with|eq\.?\s*to|equivalent to|as|containing|in|of|contains)\s+"
)


def _is_empty_composition(raw: str) -> bool:
    return normalize_key(raw) in _EMPTY_COMPOSITION


def _clean_ingredient_name(name: str) -> str:
    name = clean_text(name)
    # Drop trailing parentheticals such as "(As sustained released)".
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip(" .:-")
    # Strip leading connectors repeatedly.
    prev = None
    while prev != name:
        prev = name
        name = _LEADING_JUNK_RE.sub("", name).strip(" .:-")
    return name


def _is_valid_ingredient(name: str) -> bool:
    key = normalize_key(name)
    if not key or len(key) < 3:
        return False
    if key in _STOPWORDS:
        return False
    # Reject names whose every token is a stopword/dosage-form word.
    tokens = [t for t in key.split() if t]
    if tokens and all(t in _STOPWORDS for t in tokens):
        return False
    return True


def parse_ingredients(product_id: str, source_id: str, brand: str, raw_composition: str) -> list[Ingredient]:
    """Best-effort structured ingredient extraction.

    Returns an empty structured ingredient (raw preserved) when the composition
    cannot be reliably parsed. Never invents ingredient names.
    """
    if _is_empty_composition(raw_composition):
        return []

    body = _PREAMBLE_RE.sub("", raw_composition)

    ingredients: list[Ingredient] = []
    for match in _STRENGTH_RE.finditer(body):
        name = _clean_ingredient_name(match.group("name"))
        if not _is_valid_ingredient(name):
            continue
        ingredients.append(
            Ingredient(
                product_id=product_id,
                source_id=source_id,
                brand_name=brand,
                ingredient=name,
                strength=match.group("strength"),
                unit=clean_text(match.group("unit")),
                raw_composition=raw_composition,
            )
        )

    if not ingredients:
        # Could not parse reliably: preserve raw only, ingredient blank.
        return [
            Ingredient(
                product_id=product_id,
                source_id=source_id,
                brand_name=brand,
                ingredient="",
                strength="",
                unit="",
                raw_composition=raw_composition,
            )
        ]
    return ingredients


def make_product_id(source_id: str, brand_name: str) -> str:
    return f"{source_id}:{slugify(brand_name)}"


def build_product(
    source: Source,
    source_title: str,
    scraped_at: str,
    raw_product_name: str,
    raw_composition: str,
    raw_category: str,
) -> Product:
    brand = clean_text(raw_product_name)
    product_id = make_product_id(source.source_id, brand)

    composition_present = "" if _is_empty_composition(raw_composition) else clean_text(raw_composition)
    category = clean_text(raw_category)

    ingredients = parse_ingredients(product_id, source.source_id, brand, raw_composition)

    return Product(
        product_id=product_id,
        source_id=source.source_id,
        source_name=source.name,
        source_url=source.url,
        source_type=source.source_type,
        source_title=source_title,
        raw_product_name=raw_product_name,
        raw_category=raw_category,
        raw_composition=raw_composition,
        brand_name=brand,
        composition=composition_present,
        therapeutic_category=category,
        brand_name_normalized=normalize_key(brand),
        composition_normalized=normalize_key(composition_present),
        therapeutic_category_normalized=normalize_key(category),
        ingredients=ingredients,
        scraped_at=scraped_at,
    )


def build_products(source: Source, source_title: str, scraped_at: str, rows) -> tuple[list[Product], dict]:
    """Convert scraped rows into products and return a data-quality report."""
    products: list[Product] = []
    by_id: dict[str, Product] = {}
    duplicates = 0
    missing_composition = 0
    missing_category = 0

    for row in rows:
        product = build_product(
            source=source,
            source_title=source_title,
            scraped_at=scraped_at,
            raw_product_name=row.raw_product_name,
            raw_composition=row.raw_composition,
            raw_category=row.raw_category,
        )
        if product.product_id in by_id:
            duplicates += 1
            continue
        by_id[product.product_id] = product
        products.append(product)
        if not product.composition:
            missing_composition += 1
        if not product.therapeutic_category:
            missing_category += 1

    report = {
        "duplicates": duplicates,
        "missing_composition": missing_composition,
        "missing_category": missing_category,
        "product_count": len(products),
    }
    return products, report
