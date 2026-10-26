"""Chat, search and API request/response models."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ResponseStyle(str, Enum):
    concise = "concise"
    standard = "standard"
    detailed = "detailed"
    executive = "executive"


class Citation(BaseModel):
    source_id: str
    source_name: str
    title: str = ""
    url: str = ""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    response_style: ResponseStyle = ResponseStyle.standard
    source_ids: list[str] = Field(default_factory=list)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    intent: str = ""
    retrieval_mode: str = ""
    conversation_id: str = ""


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    source_ids: list[str] = Field(default_factory=list)
    category: str | None = None
    ingredient: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResultItem(BaseModel):
    product_id: str
    brand_name: str
    therapeutic_category: str = ""
    composition: str = ""
    source_id: str
    source_name: str
    source_url: str = ""
    score: float = 0.0
    retrieval_mode: str = ""


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchResultItem] = Field(default_factory=list)
    retrieval_mode: str = ""


class StatsResponse(BaseModel):
    sources: int
    products: int
    categories: int
    last_refreshed: str = ""
    status: str = "ready"
    search_available: bool = False
    openai_available: bool = False
