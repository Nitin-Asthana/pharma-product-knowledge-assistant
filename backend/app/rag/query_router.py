"""Deterministic query router.

Classifies a user question into an intent and extracts light structured signals
(candidate product names, ingredient/category hints). This runs BEFORE any
semantic retrieval so that deterministic lookups are preferred whenever they can
answer the question. No LLM is used here — routing is fast and rule-based.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from ..services.normalization import normalize_key
from ..services.product_service import product_service


class Intent(str, Enum):
    EXACT_PRODUCT = "EXACT_PRODUCT"
    COMPOSITION_LOOKUP = "COMPOSITION_LOOKUP"
    INGREDIENT_SEARCH = "INGREDIENT_SEARCH"
    CATEGORY_SEARCH = "CATEGORY_SEARCH"
    PRODUCT_COMPARISON = "PRODUCT_COMPARISON"
    PORTFOLIO_OVERVIEW = "PORTFOLIO_OVERVIEW"
    SEMANTIC_PRODUCT_SEARCH = "SEMANTIC_PRODUCT_SEARCH"
    GENERAL_PRODUCT_QA = "GENERAL_PRODUCT_QA"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass
class RouteResult:
    intent: Intent
    products: list[str] = field(default_factory=list)  # matched product_ids
    brand_candidates: list[str] = field(default_factory=list)
    ingredient: str | None = None
    category: str | None = None
    is_medical_advice: bool = False
    source_hint: str | None = None
    normalized_query: str = ""


# --- Signals -----------------------------------------------------------------
_COMPARE_RE = re.compile(r"\b(compare|comparison|versus|vs\.?|difference between)\b", re.I)
_COMPOSITION_RE = re.compile(r"\b(composition|what.*(in|made of)|contents?|formulation|ingredients? of)\b", re.I)
_INGREDIENT_RE = re.compile(r"\b(contain|containing|contains|with|include[s]?)\b", re.I)
_CATEGORY_RE = re.compile(
    r"\b(anti[- ]?infective|antibiotic|anti[- ]?diabetic|pain management|vitamin|"
    r"immunosupp|analgesic|category|therapeutic|nsaid|epileptic|neuropathic|"
    r"haematopoietic|hormone|steroid|multivitamin|nutraceutical)\b",
    re.I,
)
_PORTFOLIO_RE = re.compile(
    r"\b(portfolio|overview|all products|entire|list.*products|how many products|"
    r"executive (overview|summary)|what products)\b",
    re.I,
)
_MEDICAL_ADVICE_RE = re.compile(
    r"\b(should i (prescribe|give|take|use)|what (dose|dosage) (should|do)|"
    r"prescribe (for|to) (my|this|a) patient|best (medicine|drug|treatment) for|"
    r"treat my|my patient|diagnos)\b",
    re.I,
)
_OUT_OF_SCOPE_RE = re.compile(
    r"\b(market share|revenue|sales figures|stock price|profit|competitor|"
    r"weather|capital of|who is the ceo|joke|poem)\b",
    re.I,
)

# Words that are never product-name candidates even if capitalized.
_STOP_TOKENS = {
    "what", "which", "compare", "tell", "show", "give", "the", "and", "for", "with",
    "about", "everything", "all", "products", "product", "composition", "me", "is",
    "of", "in", "a", "an", "portfolio", "overview", "executive", "from", "india",
    "branded", "business", "catalogue", "source", "contain", "contains", "containing",
}


def _brand_lookup() -> dict[str, str]:
    """Map normalized brand name -> product_id (cached via product_service load)."""
    mapping: dict[str, str] = {}
    for p in product_service.all_products():
        mapping[normalize_key(p.brand_name)] = p.product_id
    return mapping


def _find_brand_mentions(query: str) -> list[str]:
    """Return product_ids whose brand names appear in the query (longest first)."""
    qkey = normalize_key(query)
    matches: list[tuple[int, str]] = []
    for p in product_service.all_products():
        bkey = normalize_key(p.brand_name)
        if not bkey:
            continue
        # Word-boundary-ish containment.
        if re.search(rf"(?<![a-z0-9]){re.escape(bkey)}(?![a-z0-9])", qkey):
            matches.append((len(bkey), p.product_id))
    # Sort by length desc so more specific brands (DEMOCIN O) win over DEMOCIN.
    matches.sort(key=lambda t: -t[0])
    seen: set[str] = set()
    ordered: list[str] = []
    for _, pid in matches:
        if pid not in seen:
            seen.add(pid)
            ordered.append(pid)
    return ordered


def _extract_ingredient(query: str) -> str | None:
    """Heuristic ingredient extraction: capitalized chemical-like token."""
    # Look for known ingredients from the catalogue first (deterministic).
    qkey = normalize_key(query)
    for ing in product_service.ingredients():
        if normalize_key(ing) and normalize_key(ing) in qkey:
            return ing
    # Fallback: 'contain <Word>' pattern.
    m = re.search(r"contain(?:s|ing)?\s+([A-Za-z][A-Za-z0-9\-]{3,})", query, re.I)
    if m and normalize_key(m.group(1)) not in _STOP_TOKENS:
        return m.group(1)
    return None


def route(query: str, source_ids: list[str] | None = None) -> RouteResult:
    product_service.load()
    q = query.strip()
    normalized = normalize_key(q)

    is_medical = bool(_MEDICAL_ADVICE_RE.search(q))
    brand_ids = _find_brand_mentions(q)

    # Out of scope (non-product topics) unless it clearly references a product.
    if _OUT_OF_SCOPE_RE.search(q) and not brand_ids:
        return RouteResult(
            intent=Intent.OUT_OF_SCOPE,
            is_medical_advice=is_medical,
            normalized_query=normalized,
        )

    # Comparison: two or more product mentions or an explicit compare verb.
    if _COMPARE_RE.search(q) and len(brand_ids) >= 1:
        return RouteResult(
            intent=Intent.PRODUCT_COMPARISON,
            products=brand_ids[:4],
            is_medical_advice=is_medical,
            normalized_query=normalized,
        )

    # Composition lookup for a specific product.
    if _COMPOSITION_RE.search(q) and brand_ids:
        return RouteResult(
            intent=Intent.COMPOSITION_LOOKUP,
            products=brand_ids[:2],
            is_medical_advice=is_medical,
            normalized_query=normalized,
        )

    # Portfolio / overview.
    if _PORTFOLIO_RE.search(q) and not brand_ids:
        return RouteResult(
            intent=Intent.PORTFOLIO_OVERVIEW,
            is_medical_advice=is_medical,
            normalized_query=normalized,
        )

    # Ingredient search.
    ingredient = _extract_ingredient(q)
    if ingredient and (_INGREDIENT_RE.search(q) or _COMPOSITION_RE.search(q)) and not brand_ids:
        return RouteResult(
            intent=Intent.INGREDIENT_SEARCH,
            ingredient=ingredient,
            is_medical_advice=is_medical,
            normalized_query=normalized,
        )

    # Category search.
    if _CATEGORY_RE.search(q) and not brand_ids:
        return RouteResult(
            intent=Intent.CATEGORY_SEARCH,
            category=_CATEGORY_RE.search(q).group(0),
            is_medical_advice=is_medical,
            normalized_query=normalized,
        )

    # Exact product (a brand is named, possibly "tell me about DEMOCIN").
    if brand_ids:
        return RouteResult(
            intent=Intent.EXACT_PRODUCT,
            products=brand_ids[:3],
            is_medical_advice=is_medical,
            normalized_query=normalized,
        )

    # Ingredient without explicit verb but matches known ingredient.
    if ingredient:
        return RouteResult(
            intent=Intent.INGREDIENT_SEARCH,
            ingredient=ingredient,
            is_medical_advice=is_medical,
            normalized_query=normalized,
        )

    # Fallback: semantic product search for natural-language product questions.
    return RouteResult(
        intent=Intent.SEMANTIC_PRODUCT_SEARCH,
        is_medical_advice=is_medical,
        normalized_query=normalized,
    )
