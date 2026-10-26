"""Scraper tests (offline: parse fixed HTML, no network)."""
from __future__ import annotations

from app.models.source import Source
from app.services.scrapers.base import ScraperError
from app.services.scrapers.product_catalogue import ProductCatalogueScraper

_SOURCE = Source(
    source_id="test-source",
    name="Test Source",
    url="https://example.com/products",
    source_type="product_catalogue",
    enabled=True,
)

_HTML = """
<html><head><title>Test Catalogue</title></head><body>
<table>
  <tr><th>Brand Name</th><th>Composition</th><th>Therapeutic Category</th></tr>
  <tr><td>DEMOCIN</td><td>Democillin 800 mg</td><td>ANTI INFECTIVES</td></tr>
  <tr><td>DEMOCIN O</td><td>Democillin 1000 mg</td><td>ANTI INFECTIVES</td></tr>
  <tr><td>DEMOCIN</td><td>Democillin 800 mg</td><td>ANTI INFECTIVES</td></tr>
  <tr><td></td><td>orphan composition</td><td>NONE</td></tr>
</table>
</body></html>
"""


def test_parses_rows_and_preserves_text():
    scraper = ProductCatalogueScraper()
    result = scraper.parse(_HTML, _SOURCE)
    brands = [r.raw_product_name for r in result.rows]
    assert "DEMOCIN" in brands
    assert "DEMOCIN O" in brands
    # Raw composition preserved verbatim.
    democin = next(r for r in result.rows if r.raw_product_name == "DEMOCIN")
    assert democin.raw_composition == "Democillin 800 mg"


def test_detects_duplicates_and_skips_empty_brand():
    scraper = ProductCatalogueScraper()
    result = scraper.parse(_HTML, _SOURCE)
    brands = [r.raw_product_name for r in result.rows]
    # Duplicate DEMOCIN collapsed to one; empty-brand row skipped.
    assert brands.count("DEMOCIN") == 1
    assert "" not in brands
    assert any("duplicate" in w.lower() for w in result.warnings)


def test_missing_table_raises():
    scraper = ProductCatalogueScraper()
    try:
        scraper.parse("<html><body><p>no table here</p></body></html>", _SOURCE)
    except ScraperError:
        return
    raise AssertionError("Expected ScraperError when no product table is present")


def test_td_based_header_row_is_not_a_product():
    # Some pages render the header row with <td> cells instead of <th>.
    html = """
    <html><body><table>
      <tr><td>Brand Name</td><td>Composition</td><td>Therapeutic Category</td></tr>
      <tr><td>DEMOCIN</td><td>Democillin 800 mg</td><td>ANTI INFECTIVES</td></tr>
    </table></body></html>
    """
    scraper = ProductCatalogueScraper()
    result = scraper.parse(html, _SOURCE)
    brands = [r.raw_product_name for r in result.rows]
    assert "Brand Name" not in brands
    assert brands == ["DEMOCIN"]

