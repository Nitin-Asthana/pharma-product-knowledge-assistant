"""Chat endpoints: POST /api/chat and POST /api/chat/stream (SSE)."""
from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..models.chat import ChatRequest, ChatResponse
from ..rag import prompts
from ..rag.citations import build_citations, validate_citation_urls
from ..rag.generator import _history_note, _prepare, generator
from ..rag.query_router import Intent, route
from ..services import azure_clients
from ..services.conversation_service import conversation_service
from ..services.product_service import product_service

logger = logging.getLogger("abc-pharma.chat")

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    conversation_id = req.conversation_id or conversation_service.new_id()
    history = conversation_service.get(conversation_id) or req.history

    started = time.perf_counter()
    result = generator.generate(
        message=req.message,
        response_style=req.response_style,
        source_ids=req.source_ids or None,
        history=history,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    conversation_service.append(conversation_id, "user", req.message)
    conversation_service.append(conversation_id, "assistant", result.answer)

    logger.info(
        "chat conversation_id=%s intent=%s retrieval_mode=%s products=%s latency_ms=%s",
        conversation_id,
        result.intent,
        result.retrieval_mode,
        result.products,
        latency_ms,
    )

    return ChatResponse(
        answer=result.answer,
        citations=result.citations,
        products=result.products,
        intent=result.intent,
        retrieval_mode=result.retrieval_mode,
        conversation_id=conversation_id,
    )


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    conversation_id = req.conversation_id or conversation_service.new_id()
    history = conversation_service.get(conversation_id) or req.history

    def sse(event: str, data: dict) -> dict:
        return {"event": event, "data": json.dumps(data)}

    def event_generator():
        product_service.load()
        yield sse("status", {"stage": "Searching product knowledge..."})
        route_result = route(req.message, req.source_ids or None)

        # Guard: fixed-response intents (out of scope, incomplete comparison) ->
        # deterministic message, no LLM, no fabricated facts.
        guard = generator._pre_generation_guard(route_result)
        if guard is not None:
            yield sse("token", {"text": guard})
            yield sse(
                "done",
                {
                    "citations": [],
                    "products": [],
                    "intent": route_result.intent.value,
                    "retrieval_mode": "none",
                    "conversation_id": conversation_id,
                },
            )
            return

        yield sse("status", {"stage": "Reviewing relevant products..."})
        packet = _prepare(req.message, route_result, req.source_ids or None)

        if not packet.is_sufficient():
            yield sse("token", {"text": prompts.ABSTENTION_MESSAGE})
            yield sse(
                "done",
                {
                    "citations": [],
                    "products": [],
                    "intent": route_result.intent.value,
                    "retrieval_mode": packet.retrieval_mode or "none",
                    "conversation_id": conversation_id,
                },
            )
            return

        citations = validate_citation_urls(build_citations(packet))
        yield sse("status", {"stage": "Preparing grounded response..."})

        if route_result.is_medical_advice:
            yield sse("token", {"text": prompts.MEDICAL_SAFETY_MESSAGE + "\n\n"})

        collected: list[str] = []
        try:
            for token in generator.stream(req.message, packet, req.response_style, history):
                collected.append(token)
                yield sse("token", {"text": token})
        except azure_clients.AzureOpenAIUnavailable:
            fallback = generator._fallback_answer(packet)
            collected.append(fallback)
            yield sse("token", {"text": fallback})
        except Exception as exc:  # noqa: BLE001
            logger.exception("streaming generation failed")
            fallback = generator._fallback_answer(packet)
            collected.append(fallback)
            yield sse("token", {"text": fallback})

        answer = "".join(collected)
        conversation_service.append(conversation_id, "user", req.message)
        conversation_service.append(conversation_id, "assistant", answer)

        yield sse(
            "done",
            {
                "citations": [c.model_dump() for c in citations],
                "products": packet.product_ids(),
                "intent": route_result.intent.value,
                "retrieval_mode": packet.retrieval_mode,
                "conversation_id": conversation_id,
            },
        )

    return EventSourceResponse(event_generator())
