# Ingestion

Ingestion is repeatable and source-driven. It loops over every **enabled** source in
`sources/sources.json`.

```
sources.json -> enabled sources -> for each source:
  scrape -> normalize/build -> structured dataset (xlsx/json)
         -> embeddings (reuse unchanged) -> Azure AI Search upsert + prune
         -> ingestion_report.json
```

## Commands

```powershell
# Full pipeline (scrape + embeddings + index + report)
python scripts/ingest.py

# Only a single source
python scripts/ingest.py --source abc-pharma-catalog

# Datasets only, no Azure calls (offline)
python scripts/ingest.py --skip-azure
```

Individual stages can also be run directly:

| Script | Does |
| --- | --- |
| `scripts/scrape_sources.py` | Scrape + build structured datasets + quality report |
| `scripts/normalize_products.py` | Re-derive normalized fields from existing raw data |
| `scripts/generate_embeddings.py` | Generate/refresh embeddings (incremental) |
| `scripts/create_search_index.py` | Create/update the `abc-pharma-products` index |
| `scripts/evaluate_rag.py` | Run RAG evaluation |

## Outputs (per source)

`data/sources/<source_id>/`:

- `products.json` — structured records (app source of truth)
- `products.xlsx` — Products / Ingredients / Categories / Metadata sheets
- `embeddings.json` — cached embeddings keyed by product_id + content hash
- `ingestion_report.json` — real counts and status

## Incremental behaviour

- **Unchanged product** (same embedding content hash) -> reuse existing embedding.
- **Changed / new product** -> regenerate embedding.
- **Removed product** -> its Azure Search document is deleted during the prune step.

## Data quality reporting

The scrape summary reports product count, duplicates skipped, missing composition and missing
category. Rows with an empty brand name are skipped with a warning; nothing is silently
discarded, and a structurally missing product table raises an error rather than producing an
empty dataset.

## Error handling

- Source unreachable / malformed -> that source is marked `failed` in its report; other
  sources still proceed. The run reports partial success (e.g. "1 of 2 sources succeeded") and
  never marks a failed source as ready.
- Azure OpenAI / Search unavailable -> embedding or indexing errors are surfaced in the report,
  not swallowed.

## Adding a new source

1. Append an entry to `sources/sources.json`:

   ```json
   {
     "source_id": "future-product-catalogue",
     "name": "Future Product Catalogue",
     "description": "Additional approved product catalogue",
     "url": "https://example.com/products",
     "source_type": "product_catalogue",
     "enabled": true
   }
   ```

2. Run `python scripts/ingest.py`.

No code changes are needed when the source follows the supported `product_catalogue` format.
The source selector, filters, status, citations and counts update automatically.
