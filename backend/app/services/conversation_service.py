"""In-memory conversation store for limited multi-turn context.

Stores a bounded history per conversation_id so pronouns ("its composition")
can be resolved. This is intentionally ephemeral (no database) per the design.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque

from ..models.chat import ChatMessage

_MAX_TURNS = 10


class ConversationService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, deque[ChatMessage]] = {}

    def new_id(self) -> str:
        return uuid.uuid4().hex

    def get(self, conversation_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._store.get(conversation_id, deque()))

    def append(self, conversation_id: str, role: str, content: str) -> None:
        with self._lock:
            dq = self._store.setdefault(conversation_id, deque(maxlen=_MAX_TURNS))
            dq.append(ChatMessage(role=role, content=content))

    def reset(self, conversation_id: str) -> None:
        with self._lock:
            self._store.pop(conversation_id, None)


conversation_service = ConversationService()
