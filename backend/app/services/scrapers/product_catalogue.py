"""Product catalogue scraper.

Parses an HTML product-catalogue page structured as a table with the columns
``Brand Name``, ``Composition`` and ``Therapeutic Category``. Source text is
preserved verbatim; no LLM is used and no missing data is invented.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bs4 import BeautifulSoup

from ...models.source import Source
from .base import BaseScraper, ScrapedRow, ScrapeResult, ScraperError

# Header aliases -> canonical column key.
_HEADER_MAP = {
    "brand name": "brand",
    "brand": "brand",
    "product": "brand",
    "product name": "brand",
    "composition": "composition",
    "therapeutic category": "category",
    "category": "category",
}


def _cell_text(cell) -> str:
    # Preserve internal spacing but collapse newlines/tabs introduced by markup.
    return cell.get_text(separator=" ", strip=True)


class ProductCatalogueScraper(BaseScraper):
    source_type = "product_catalogue"

    def parse(self, html: str, source: Source) -> ScrapeResult:
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.get_text(strip=True) if soup.title else source.name) or source.name

        target_table = self._find_product_table(soup)
        if target_table is None:
            raise ScraperError(
                f"Could not locate a product table with Brand/Composition/Category "
                f"headers on {source.url}."
            )

        col_index = self._resolve_columns(target_table)
        if "brand" not in col_index:
            raise ScraperError("Product table is missing a Brand Name column.")

        rows: list[ScrapedRow] = []
        warnings: list[str] = []
        seen_signatures: set[str] = set()
        duplicates = 0

        for tr in target_table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells or tr.find("th") and not tr.find("td"):
                # header row
                continue
            values = [_cell_text(c) for c in cells]
            brand = values[col_index["brand"]] if col_index["brand"] < len(values) else ""
            composition = (
                values[col_index["composition"]]
                if "composition" in col_index and col_index["composition"] < len(values)
                else ""
            )
            category = (
                values[col_index["category"]]
                if "category" in col_index and col_index["category"] < len(values)
                else ""
            )
            brand = brand.strip()
            if not brand:
                warnings.append("Skipped a row with an empty brand name.")
                continue

            # Skip header rows even when they are built from <td> cells: a row
            # whose brand cell is itself a recognized header label ("Brand Name",
            # "Product", ...) is a header, not a product.
            if _HEADER_MAP.get(brand.lower()) == "brand":
                continue

            # Treat placeholder compositions as empty presented value but keep raw.
            raw_comp = composition.strip()
            signature = f"{brand.lower()}|{raw_comp.lower()}"
            if signature in seen_signatures:
                duplicates += 1
                continue
            seen_signatures.add(signature)

            rows.append(
                ScrapedRow(
                    raw_product_name=brand,
                    raw_composition=raw_comp,
                    raw_category=category.strip(),
                )
            )

        if duplicates:
            warnings.append(f"Detected and skipped {duplicates} duplicate row(s).")

        return ScrapeResult(
            source=source,
            rows=rows,
            source_title=title,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            warnings=warnings,
        )

    # ------------------------------------------------------------------ helpers
    def _find_product_table(self, soup: BeautifulSoup):
        best = None
        best_score = 0
        for table in soup.find_all("table"):
            header_text = " ".join(
                _cell_text(c).lower() for c in table.find_all(["th", "td"], limit=6)
            )
            score = sum(1 for key in ("brand", "composition", "category") if key in header_text)
            # Prefer tables with the most matching header keywords and many rows.
            row_count = len(table.find_all("tr"))
            total = score * 100 + row_count
            if score >= 2 and total > best_score:
                best = table
                best_score = total
        return best

    def _resolve_columns(self, table) -> dict[str, int]:
        # Find the header row: first row containing recognizable header labels.
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            labels = [_cell_text(c).lower() for c in cells]
            mapping: dict[str, int] = {}
            for idx, label in enumerate(labels):
                key = _HEADER_MAP.get(label)
                if key and key not in mapping:
                    mapping[key] = idx
            if "brand" in mapping and ("composition" in mapping or "category" in mapping):
                return mapping
        # Fallback: assume standard 3-column order.
        return {"brand": 0, "composition": 1, "category": 2}
