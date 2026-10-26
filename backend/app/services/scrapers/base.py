"""Base scraper interface and shared HTTP utilities.

Scrapers fetch a configured source and return *raw* rows. They preserve source
text verbatim — normalization and ID generation happen in a separate step. No
source URL is hardcoded here; the source object comes from the registry.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

from ...models.source import Source


class ScraperError(Exception):
    """Raised when scraping fails in a way that must not be silently ignored."""


@dataclass
class ScrapedRow:
    """A single raw row extracted from a source, verbatim."""

    raw_product_name: str
    raw_composition: str
    raw_category: str


@dataclass
class ScrapeResult:
    source: Source
    rows: list[ScrapedRow] = field(default_factory=list)
    source_title: str = ""
    fetched_at: str = ""
    warnings: list[str] = field(default_factory=list)


DEFAULT_HEADERS = {
    "User-Agent": (
        "AbcPharmaProductAssistant/0.1 (+https://www.example.com) "
        "Python-requests"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


class BaseScraper:
    """Common scraper interface.

    Subclasses implement :meth:`parse` to turn HTML into :class:`ScrapedRow`
    objects. :meth:`scrape` handles fetching, retries and validation.
    """

    source_type: str = "base"

    def __init__(self, timeout: float = 30.0, retries: int = 3, backoff: float = 1.5) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    # --------------------------------------------------------------- fetching
    def fetch(self, url: str) -> str:
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout)
                resp.raise_for_status()
                if not resp.text or not resp.text.strip():
                    raise ScraperError(f"Empty response body from {url}")
                return resp.text
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                # Retry only transient server errors; fail fast on 4xx.
                if status is not None and 400 <= status < 500:
                    raise ScraperError(f"HTTP {status} fetching {url}") from exc
                last_exc = exc
            if attempt < self.retries:
                time.sleep(self.backoff * attempt)
        raise ScraperError(f"Failed to fetch {url} after {self.retries} attempts: {last_exc}")

    # ---------------------------------------------------------------- parsing
    def parse(self, html: str, source: Source) -> ScrapeResult:  # pragma: no cover - abstract
        raise NotImplementedError

    def scrape(self, source: Source) -> ScrapeResult:
        html = self.fetch(source.url)
        result = self.parse(html, source)
        if not result.rows:
            raise ScraperError(
                f"No products parsed from {source.url}. The page structure may have "
                "changed. Refusing to write an empty dataset."
            )
        return result


# Registry of scrapers by source_type. Populated at import time by subclasses'
# module to avoid circular imports we wire it lazily in get_scraper.
def get_scraper(source: Source) -> BaseScraper:
    from .product_catalogue import ProductCatalogueScraper

    stype = (source.scraper_type or source.source_type or "").strip().lower()
    if stype in ("product_catalogue", "product-catalogue", ""):
        return ProductCatalogueScraper()
    raise ScraperError(f"No scraper registered for source_type={source.source_type!r}")
