"""Evidence packet construction and validation.

An evidence packet is the clean, structured, source-grounded context handed to
the LLM. Retrieved evidence is DATA, never instructions. The evidence gate
validates that we have enough grounded material before generating.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models.product import Product


@dataclass
class EvidenceItem:
    product_id: str
    brand_name: str
    therapeutic_category: str
    composition: str
    source_id: str
    source_name: str
    source_url: str
    score: float = 0.0
    retrieval_mode: str = ""

    @classmethod
    def from_product(cls, p: Product, score: float = 1.0, mode: str = "exact") -> "EvidenceItem":
        return cls(
            product_id=p.product_id,
            brand_name=p.brand_name,
            therapeutic_category=p.therapeutic_category,
            composition=p.composition,
            source_id=p.source_id,
            source_name=p.source_name,
            source_url=p.source_url,
            score=score,
            retrieval_mode=mode,
        )

    @classmethod
    def from_search(cls, r: dict) -> "EvidenceItem":
        return cls(
            product_id=r.get("product_id", ""),
            brand_name=r.get("brand_name", ""),
            therapeutic_category=r.get("therapeutic_category", ""),
            composition=r.get("composition", ""),
            source_id=r.get("source_id", ""),
            source_name=r.get("source_name", ""),
            source_url=r.get("source_url", ""),
            score=float(r.get("score", 0.0)),
            retrieval_mode=r.get("retrieval_mode", "hybrid"),
        )


@dataclass
class EvidencePacket:
    items: list[EvidenceItem] = field(default_factory=list)
    retrieval_mode: str = ""

    def is_sufficient(self) -> bool:
        return any(item.brand_name for item in self.items)

    def product_ids(self) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in self.items:
            if item.product_id and item.product_id not in seen:
                seen.add(item.product_id)
                ordered.append(item.product_id)
        return ordered

    def render(self) -> str:
        """Render a delimited evidence block for the prompt."""
        blocks: list[str] = []
        for i, item in enumerate(self.items, start=1):
            lines = [
                f"[{i}]",
                f"PRODUCT: {item.brand_name}",
            ]
            if item.therapeutic_category:
                lines.append(f"CATEGORY: {item.therapeutic_category}")
            if item.composition:
                lines.append(f"COMPOSITION: {item.composition}")
            else:
                lines.append("COMPOSITION: (not provided in source)")
            lines.append(f"SOURCE: {item.source_name}")
            lines.append(f"SOURCE URL: {item.source_url}")
            blocks.append("\n".join(lines))
        body = "\n\n".join(blocks) if blocks else "(no evidence retrieved)"
        return f"<EVIDENCE>\n{body}\n</EVIDENCE>"
