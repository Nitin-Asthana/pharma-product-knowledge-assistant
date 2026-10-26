# ABC Pharma Product Knowledge Assistant

Dynamic, multi-source **Retrieval-Augmented Generation** over authoritative ABC Pharma
product data, built on **Azure AI Search** + **Azure OpenAI**. The assistant prioritises
factual accuracy and grounded, source-traceable answers — and abstains when the knowledge
base does not contain enough information rather than guessing.

> Correctly saying "I don't have enough information in the knowledge base" is better than
> generating an unsupported answer.

---

## 1. Product overview

A boardroom-ready assistant that answers questions about ABC Pharma product information
(brands, composition, ingredients, therapeutic categories, comparisons and portfolio
overviews) using only ingested source data. Every factual answer carries a dynamic
citation back to the registered source.

It is a **product knowledge assistant**, not a patient-specific medical advisor. It
declines to give diagnosis, treatment or prescribing recommendations.

## 2. Architecture

```
Source registry (sources/sources.json)
      -> Dynamic ingestion (scrape -> normalize -> structured dataset)
      -> Embeddings (Azure OpenAI text-embedding-3-small)
      -> Azure AI Search index (abc-pharma-products, source-aware)
      -> Query routing (deterministic intent classification)
      -> Retrieval (structured / exact / hybrid + semantic reranking)
      -> Evidence validation gate
      -> Grounded generation (Azure OpenAI gpt-5.4)
      -> Answer + citation validation
      -> React/TypeScript UI
```

The LLM understands questions and composes answers. It **never** acts as the product
database — all product facts come from retrieval.

See [docs/architecture.md](docs/architecture.md).

## 3. Dynamic multi-source architecture

Nothing about "ABC Pharma Catalog" is hardcoded in application logic or the
frontend. Adding a source is a data change in [sources/sources.json](sources/sources.json)
— the source selector, filtering, status, citations, counts and retrieval all adapt
automatically. See [docs/ingestion.md](docs/ingestion.md#adding-a-new-source).

## 4. Source registry

`sources/sources.json` is the single authoritative list of ingestion URLs and metadata.
`backend/app/services/source_registry.py` loads, validates (no duplicate IDs, valid URLs),
and exposes enabled sources to ingestion, retrieval, citations and the API. No source URL
appears anywhere else in the codebase.

## 5. Data model

Every product record and every Azure Search document retains
`source_id`, `source_name`, `source_url`, `source_type`. Product IDs are source-scoped:
`{source_id}:{normalized_product_name}` (e.g. `abc-pharma-catalog:democin`),
so the same brand from different sources never collides. Raw source text
(`raw_product_name`, `raw_composition`, `raw_category`) is preserved verbatim; normalized
fields are derived and never alter quantities, strengths, units or names.

## 6. Scraping

`ProductCatalogueScraper` fetches the configured page, validates the HTTP response, retries
transient failures, locates the product table by its Brand/Composition/Category headers,
preserves cell text verbatim, detects duplicates and fails loudly if the expected structure
is missing (never silently emitting an empty dataset). No LLM is used and no missing data is
invented.

## 7. Excel / JSON master data

Per source, ingestion writes to `data/sources/<source_id>/`:

| File | Purpose |
| --- | --- |
| `products.json` | Structured product dataset (source of truth for the app) |
| `products.xlsx` | Products / Ingredients / Categories / Metadata sheets |
| `embeddings.json` | Cached embeddings keyed by product_id + content hash |
| `ingestion_report.json` | Real ingestion counts and status |

## 8. Embeddings

`AZURE_OPENAI_EMBEDDING_DEPLOYMENT` and `EMBEDDING_DIMENSIONS` come from the environment —
the model and dimensions are never hardcoded. Embedding content is built only from
structured, source-grounded fields. Dimensions are validated during ingestion. Unchanged
products reuse their cached embedding (content-hash based); changed/new products are
re-embedded.

## 9. Azure AI Search

The `abc-pharma-products` index is source-aware with vector + semantic search. Vector
dimensions are configured from `EMBEDDING_DIMENSIONS`. Results are filterable by `source_id`.
See [docs/rag.md](docs/rag.md).

## 10. Hybrid retrieval & 11. Query routing

Deterministic intent routing runs first (`backend/app/rag/query_router.py`) and prefers
structured lookups whenever they can answer the question. Otherwise the retriever escalates:
exact/lexical -> hybrid keyword+vector -> semantic reranking. See [docs/rag.md](docs/rag.md).

## 12. Grounding & 13. Citations

An evidence packet is built and validated (the evidence gate) before any LLM call. If
evidence is insufficient the assistant abstains. Citations are constructed only from the
source registry and only for sources that actually contributed retrieved evidence; invalid
or unregistered URLs are dropped.

## 14. Multi-source

The application works unchanged whether `sources.json` has 1 or 10 sources.

## 15. Local setup

Prerequisites: Python 3.11+ and Node 18+, plus `az login` (Entra ID) or API keys.

> Tip: if your project lives inside a cloud-synced folder, create the Python virtual
> environment **outside** it. Sync tools can flag and re-add files such as
> `certifi/cacert.pem` inside `.venv`. A path like `C:\Users\<you>\venvs\abc-pharma`
> (Windows) works well.

```powershell
# 1. Create venv OUTSIDE the synced folder and install backend deps
python -m venv C:\Users\<you>\venvs\abc-pharma
& C:\Users\<you>\venvs\abc-pharma\Scripts\python.exe -m pip install -r requirements.txt

# 2. Configure environment
Copy-Item .env.example .env   # then fill in values

# 3. Run ingestion (scrape -> embeddings -> index)
& C:\Users\<you>\venvs\abc-pharma\Scripts\python.exe scripts/ingest.py

# 4. Start the backend (http://localhost:8000, docs at /docs)
& C:\Users\<you>\venvs\abc-pharma\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload

# 5. Start the frontend (http://localhost:5173)
cd frontend; npm install; npm run dev
```

To scrape/build datasets without Azure: `python scripts/ingest.py --skip-azure`.

## 16. Environment variables

See [.env.example](.env.example). Key/`DefaultAzureCredential` selection is automatic: when
a key variable is empty, Entra ID (`DefaultAzureCredential`) is used.

## 17. Azure deployment

The FastAPI backend runs on Azure App Service; prefer **Managed Identity** with Azure RBAC in
production (assign *Search Index Data Contributor* + *Search Service Contributor* on the
search service and *Cognitive Services OpenAI User* on the OpenAI resource). Azure AI Search
has Entra ID auth enabled, so both `az login` (local) and Managed Identity (production)
authenticate without keys. Never expose credentials to the browser. See
[docs/architecture.md](docs/architecture.md#azure-deployment).

## 18. Evaluation

`python scripts/evaluate_rag.py` measures retrieval recall/precision, groundedness, citation
validity, exact-fact accuracy, abstention and medical safety against `eval/questions.json`.
Metrics are measured, never fabricated; if Azure credentials are missing it reports that
instead of inventing numbers. See [docs/evaluation.md](docs/evaluation.md).

## 19. Responsible AI

- Retrieved content is treated as untrusted **data**, never as instructions (prompt-injection
  resistant).
- No patient-specific prescribing advice.
- Grounded abstention over speculation.
- No fabricated citations, counts, statuses or metrics.
- No secrets in the frontend or logs.

## 20. Limitations

- Ingredient parsing is best-effort; when composition can't be parsed reliably the structured
  ingredient is left blank and the raw composition is preserved as authoritative.
- Semantic answers describe relationships carefully and never imply clinical equivalence.
- Open meta-questions (e.g. "what isn't in the source?") may retrieve loosely-related products;
  the LLM is instructed to abstain when evidence doesn't support an answer.
- Data reflects the source page at ingestion time; re-run ingestion to refresh.

## 21. Demo script

Ten scripted questions in [docs/demo-script.md](docs/demo-script.md).

## Adding another source

Append an entry to `sources/sources.json` and re-run `python scripts/ingest.py`. No code
changes are required for a source that follows the supported catalogue format.
