"""Grounded generation orchestration.

Ties together routing -> retrieval -> evidence gate -> LLM generation ->
citation building. Produces a fully-formed answer plus citations, matched
products, intent and retrieval mode. Also supports token streaming.

The LLM composes and presents; it never supplies product facts on its own.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field

from ..config import settings
from ..models.chat import Citation, ResponseStyle
from ..services import azure_clients
from ..services.product_service import product_service
from . import prompts
from .citations import build_citations, validate_citation_urls
from .evidence import EvidencePacket
from .query_router import Intent, RouteResult, route
from .retriever import retriever

logger = logging.getLogger("abc-pharma.generator")

# Deterministic answer size guards per intent (keeps portfolio prompts bounded).
# Sized to comfortably hold the full single-source catalogue so portfolio and
# category answers remain complete and counts stay accurate.
_MAX_EVIDENCE_ITEMS = 250


@dataclass
class GenerationResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    intent: str = ""
    retrieval_mode: str = ""
    grounded: bool = True


def _history_note(history) -> str:
    if not history:
        return ""
    recent = history[-4:]
    lines = [f"{m.role}: {m.content}" for m in recent if getattr(m, "content", "")]
    return "\n".join(lines)


def _prepare(query: str, route_result: RouteResult, source_ids: list[str] | None) -> EvidencePacket:
    packet = retriever.retrieve(query, route_result, source_ids)
    if len(packet.items) > _MAX_EVIDENCE_ITEMS:
        packet.items = packet.items[:_MAX_EVIDENCE_ITEMS]
    return packet


class Generator:
    def _pre_generation_guard(self, route_result: RouteResult) -> str | None:
        """Return a fixed message when we must not call the LLM for facts."""
        if route_result.intent == Intent.OUT_OF_SCOPE:
            return prompts.OUT_OF_SCOPE_MESSAGE
        # A comparison needs at least two distinct products; if only one (or none)
        # was resolved, ask which second product to compare instead of abstaining.
        if route_result.intent == Intent.PRODUCT_COMPARISON and len(route_result.products) < 2:
            brand = None
            if route_result.products:
                p = product_service.get_product(route_result.products[0])
                brand = p.brand_name if p else None
            return prompts.comparison_needs_second_message(brand)
        return None

    def generate(
        self,
        message: str,
        response_style: ResponseStyle = ResponseStyle.standard,
        source_ids: list[str] | None = None,
        history=None,
    ) -> GenerationResult:
        product_service.load()
        route_result = route(message, source_ids)

        guard = self._pre_generation_guard(route_result)
        if guard is not None:
            return GenerationResult(
                answer=guard,
                intent=route_result.intent.value,
                retrieval_mode="none",
                grounded=True,
            )

        packet = _prepare(message, route_result, source_ids)

        # Evidence gate.
        if not packet.is_sufficient():
            return GenerationResult(
                answer=prompts.ABSTENTION_MESSAGE,
                intent=route_result.intent.value,
                retrieval_mode=packet.retrieval_mode or "none",
                grounded=True,
            )

        citations = validate_citation_urls(build_citations(packet))
        medical_prefix = (
            prompts.MEDICAL_SAFETY_MESSAGE + "\n\n" if route_result.is_medical_advice else ""
        )

        try:
            answer = self._call_llm(message, packet, response_style, history)
        except azure_clients.AzureOpenAIUnavailable as exc:
            logger.warning("Azure OpenAI unavailable, returning grounded evidence summary: %s", exc)
            answer = self._fallback_answer(packet)

        return GenerationResult(
            answer=medical_prefix + answer,
            citations=citations,
            products=packet.product_ids(),
            intent=route_result.intent.value,
            retrieval_mode=packet.retrieval_mode,
            grounded=True,
        )

    # ------------------------------------------------------------------ LLM call
    def _messages(self, message: str, packet: EvidencePacket, style: ResponseStyle, history):
        history_note = _history_note(history)
        user_prompt = prompts.build_user_prompt(
            question=message,
            evidence_block=packet.render(),
            style=style,
            history_note=history_note,
        )
        return [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _call_llm(self, message: str, packet: EvidencePacket, style: ResponseStyle, history) -> str:
        client = azure_clients.get_chat_client()
        messages = self._messages(message, packet, style, history)
        try:
            resp = client.chat.completions.create(
                model=settings.azure_openai_chat_deployment,
                messages=messages,
            )
        except Exception as exc:  # noqa: BLE001
            raise azure_clients.AzureOpenAIUnavailable(str(exc)) from exc
        return (resp.choices[0].message.content or "").strip()

    def stream(
        self,
        message: str,
        packet: EvidencePacket,
        response_style: ResponseStyle,
        history=None,
    ) -> Iterator[str]:
        client = azure_clients.get_chat_client()
        messages = self._messages(message, packet, response_style, history)
        stream = client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    # -------------------------------------------------------------- fallback
    def _fallback_answer(self, packet: EvidencePacket) -> str:
        """Deterministic grounded summary used when the LLM is unavailable.

        This does not invent anything — it renders the retrieved structured
        evidence directly.
        """
        lines = ["Based on the product knowledge base:", ""]
        if len(packet.items) == 1:
            item = packet.items[0]
            lines.append(f"### {item.brand_name}")
            if item.therapeutic_category:
                lines.append(f"- **Therapeutic Category:** {item.therapeutic_category}")
            if item.composition:
                lines.append(f"- **Composition:** {item.composition}")
            else:
                lines.append("- **Composition:** not provided in source")
            lines.append(f"- **Source:** {item.source_name}")
        else:
            lines.append("| Product | Therapeutic Category | Composition |")
            lines.append("| --- | --- | --- |")
            for item in packet.items[:40]:
                comp = (item.composition or "not provided").replace("|", "/")
                if len(comp) > 120:
                    comp = comp[:117] + "..."
                lines.append(f"| {item.brand_name} | {item.therapeutic_category or '-'} | {comp} |")
        return "\n".join(lines)


generator = Generator()
