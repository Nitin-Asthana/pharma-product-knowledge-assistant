"""Source registry data models."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Source(BaseModel):
    """A configured ingestion source.

    Required fields mirror the source registry schema. Optional metadata fields
    may be added without breaking existing sources.
    """

    source_id: str
    name: str
    description: str = ""
    url: str
    source_type: str = "product_catalogue"
    enabled: bool = True

    # Optional metadata (future-proofing)
    scraper_type: str | None = None
    country: str | None = None
    business_unit: str | None = None
    language: str | None = None
    refresh_enabled: bool | None = None

    @field_validator("source_id", "name", "url")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("must not be empty")
        return str(v).strip()

    @field_validator("url")
    @classmethod
    def _valid_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"invalid URL: {v!r}")
        return v


class SourceStatus(BaseModel):
    source_id: str
    name: str
    enabled: bool
    status: str = Field(description="ready | disabled | error | not_ingested")
    product_count: int = 0
    category_count: int = 0
    last_ingested_at: str = ""
    url: str = ""
    source_type: str = "product_catalogue"
    message: str = ""
