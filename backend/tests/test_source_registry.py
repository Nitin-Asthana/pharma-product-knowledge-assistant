"""Source registry tests."""
from __future__ import annotations

import json

import pytest

from app.services.source_registry import SourceRegistry, SourceRegistryError, source_registry


def test_loads_abc-pharma_source():
    sources = source_registry.get_all_sources()
    ids = [s.source_id for s in sources]
    assert "abc-pharma-catalog" in ids


def test_enabled_sources_are_enabled():
    for s in source_registry.get_enabled_sources():
        assert s.enabled is True


def test_source_urls_are_present_and_valid():
    for s in source_registry.get_all_sources():
        assert s.url.startswith("http")


def test_resolve_and_get_source():
    s = source_registry.get_source("abc-pharma-catalog")
    assert s is not None
    assert s.name
    assert source_registry.resolve_source_id(s.source_id) == s.source_id


def test_unknown_source_raises():
    with pytest.raises(SourceRegistryError):
        source_registry.resolve_source_id("does-not-exist")


def test_duplicate_source_ids_rejected(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "dup",
                        "name": "A",
                        "url": "https://example.com/a",
                        "source_type": "product_catalogue",
                        "enabled": True,
                    },
                    {
                        "source_id": "dup",
                        "name": "B",
                        "url": "https://example.com/b",
                        "source_type": "product_catalogue",
                        "enabled": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    reg = SourceRegistry(registry_path=path)
    with pytest.raises(SourceRegistryError):
        reg.validate_sources()


def test_missing_file_raises(tmp_path):
    reg = SourceRegistry(registry_path=tmp_path / "nope.json")
    with pytest.raises(SourceRegistryError):
        reg.validate_sources()
