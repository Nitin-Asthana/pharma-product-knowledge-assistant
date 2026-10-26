"""Product and ingredient data models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    """A single parsed ingredient from a product composition.

    ``ingredient`` may be empty when the composition could not be reliably
    parsed. In that case ``raw_composition`` preserves the exact source text.
    """

    product_id: str
    source_id: str
    brand_name: str
    ingredient: str = ""
    strength: str = ""
    unit: str = ""
    raw_composition: str = ""


class Product(BaseModel):
    """A normalized product record.

    Raw source fields are preserved verbatim; normalized fields are derived and
    never alter quantities, strengths, units, ingredient names or product names.
    """

    product_id: str = Field(description="{source_id}:{normalized_product_name}")

    # Source attribution (mandatory on every record)
    source_id: str
    source_name: str
    source_url: str
    source_type: str = "product_catalogue"
    source_title: str = ""

    # Raw (verbatim from source)
    raw_product_name: str = ""
    raw_category: str = ""
    raw_composition: str = ""

    # Presented fields
    brand_name: str
    composition: str = ""
    therapeutic_category: str = ""

    # Normalized (derived)
    brand_name_normalized: str = ""
    composition_normalized: str = ""
    therapeutic_category_normalized: str = ""

    # Structured ingredients
    ingredients: list[Ingredient] = Field(default_factory=list)

    # Provenance
    scraped_at: str = ""

    def content(self) -> str:
        """Build source-grounded embedding/index content from structured fields."""
        parts = [f"Brand:\n{self.brand_name}"]
        if self.therapeutic_category:
            parts.append(f"Therapeutic Category:\n{self.therapeutic_category}")
        if self.composition:
            parts.append(f"Composition:\n{self.composition}")
        parts.append(f"Source:\n{self.source_name}")
        return "\n\n".join(parts)


class ProductSummary(BaseModel):
    """Lightweight product representation for list/card views."""

    product_id: str
    brand_name: str
    therapeutic_category: str = ""
    composition: str = ""
    source_id: str
    source_name: str
    source_url: str = ""
