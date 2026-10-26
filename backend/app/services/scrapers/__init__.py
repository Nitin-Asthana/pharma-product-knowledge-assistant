"""Scraper abstractions."""
from .base import BaseScraper, ScrapedRow, ScrapeResult, get_scraper
from .product_catalogue import ProductCatalogueScraper

__all__ = [
    "BaseScraper",
    "ScrapedRow",
    "ScrapeResult",
    "ProductCatalogueScraper",
    "get_scraper",
]
