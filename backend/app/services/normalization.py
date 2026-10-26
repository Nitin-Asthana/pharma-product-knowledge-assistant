"""Text normalization helpers.

Normalization is intentionally conservative. It may lowercase, trim, collapse
whitespace and normalize Unicode/punctuation variants — but it must NEVER alter
quantities, strengths, units, ingredient names or product names in the
*presented* fields. These helpers only produce derived ``*_normalized`` values
used for matching and lookup.
"""
from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFKC and standardize common punctuation variants."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def clean_text(text: str) -> str:
    """Trim + Unicode-normalize + collapse whitespace. Preserves case & content."""
    if not text:
        return ""
    return collapse_whitespace(normalize_unicode(text))


def normalize_key(text: str) -> str:
    """Lowercase normalized form used for matching (not for display)."""
    return clean_text(text).lower()


def slugify(text: str) -> str:
    """Stable slug for product IDs. Deterministic and collision-resistant."""
    text = normalize_unicode(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text
