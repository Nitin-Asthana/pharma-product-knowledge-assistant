"""Source registry service.

The registry is the single authoritative source of ingestion URLs and source
metadata. No source URL is hardcoded anywhere else in the application.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from ..config import settings
from ..models.source import Source


class SourceRegistryError(Exception):
    """Raised when the source registry is invalid or cannot be loaded."""


class SourceRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        self._path = registry_path or settings.source_registry_file
        self._lock = threading.Lock()
        self._sources: list[Source] = []
        self._by_id: dict[str, Source] = {}
        self._loaded = False

    # ------------------------------------------------------------------ loading
    def load(self, force: bool = False) -> list[Source]:
        with self._lock:
            if self._loaded and not force:
                return self._sources
            self._sources = self._read_and_validate()
            self._by_id = {s.source_id: s for s in self._sources}
            self._loaded = True
            return self._sources

    def _read_and_validate(self) -> list[Source]:
        path = Path(self._path)
        if not path.exists():
            raise SourceRegistryError(f"Source registry not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceRegistryError(f"Invalid JSON in {path}: {exc}") from exc

        if not isinstance(raw, dict) or "sources" not in raw:
            raise SourceRegistryError("Registry must be an object with a 'sources' array")

        entries = raw["sources"]
        if not isinstance(entries, list):
            raise SourceRegistryError("'sources' must be a list")

        sources: list[Source] = []
        seen_ids: set[str] = set()
        for i, entry in enumerate(entries):
            try:
                source = Source(**entry)
            except Exception as exc:  # pydantic ValidationError
                raise SourceRegistryError(f"Invalid source at index {i}: {exc}") from exc
            if source.source_id in seen_ids:
                raise SourceRegistryError(f"Duplicate source_id: {source.source_id!r}")
            seen_ids.add(source.source_id)
            sources.append(source)
        return sources

    # -------------------------------------------------------------- public API
    def validate_sources(self) -> list[Source]:
        """Re-read and validate; raises SourceRegistryError on any problem."""
        return self.load(force=True)

    def get_all_sources(self) -> list[Source]:
        return list(self.load())

    def get_enabled_sources(self) -> list[Source]:
        return [s for s in self.load() if s.enabled]

    def get_source(self, source_id: str) -> Source | None:
        self.load()
        return self._by_id.get(source_id)

    def resolve_source_id(self, source_id: str) -> str:
        source = self.get_source(source_id)
        if source is None:
            raise SourceRegistryError(f"Unknown source_id: {source_id!r}")
        return source.source_id

    def enabled_ids(self) -> list[str]:
        return [s.source_id for s in self.get_enabled_sources()]


# Module-level singleton used across the app.
source_registry = SourceRegistry()
