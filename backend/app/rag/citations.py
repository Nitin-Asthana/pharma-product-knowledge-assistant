"""Dynamic citation construction and validation.

Citations are built exclusively from the source registry and the evidence that
was actually retrieved. The LLM never invents URLs. Only URLs registered in
``sources/sources.json`` may appear.
"""
from __future__ import annotations

from ..models.chat import Citation
from ..services.source_registry import source_registry
from .evidence import EvidencePacket


def build_citations(packet: EvidencePacket) -> list[Citation]:
    """One citation per distinct source that contributed retrieved evidence."""
    seen: set[str] = set()
    citations: list[Citation] = []
    for item in packet.items:
        if not item.source_id or item.source_id in seen:
            continue
        source = source_registry.get_source(item.source_id)
        if source is None:
            # Never cite a source that is not in the registry.
            continue
        seen.add(item.source_id)
        citations.append(
            Citation(
                source_id=source.source_id,
                source_name=source.name,
                title=source.name,
                url=source.url,
            )
        )
    return citations


def validate_citation_urls(citations: list[Citation]) -> list[Citation]:
    """Drop any citation whose URL is not registered in the source registry."""
    valid_urls = {s.url for s in source_registry.get_all_sources()}
    return [c for c in citations if c.url in valid_urls]
