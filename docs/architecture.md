# Architecture

## Overview

```
                          sources/sources.json  (authoritative source registry)
                                     |
                        source_registry.py (load / validate / resolve)
                                     |
      +------------------------------+------------------------------+
      |                        INGESTION                            |
      |  scrape_sources.py -> product_builder -> dataset (xlsx/json)|
      |  generate_embeddings.py -> embeddings.json                  |
      |  create_search_index.py -> Azure AI Search index            |
      |  ingest.py orchestrates all of the above + report           |
      +------------------------------+------------------------------+
                                     |
                         Azure AI Search: abc-pharma-products
                                     |
      +------------------------------+------------------------------+
      |                        REQUEST PATH                         |
      |  query_router -> retriever -> evidence gate -> generator    |
      |  -> citations (validated) -> FastAPI response / SSE stream  |
      +------------------------------+------------------------------+
                                     |
                       React + TypeScript + Vite + Tailwind UI
```

## Backend modules

| Area | Module | Responsibility |
| --- | --- | --- |
| Config | `backend/app/config.py` | Env-driven settings; no source URLs, no secrets in code |
| Source registry | `backend/app/services/source_registry.py` | Load/validate/resolve sources |
| Scraping | `backend/app/services/scrapers/` | `BaseScraper` + `ProductCatalogueScraper` |
| Normalization | `backend/app/services/normalization.py` | Conservative text normalization, slugs |
| Product build | `backend/app/services/product_builder.py` | IDs, raw preservation, ingredient parsing |
| Dataset IO | `backend/app/services/dataset.py` | Excel/JSON/embeddings/report read+write |
| Product service | `backend/app/services/product_service.py` | Cached deterministic structured lookups |
| Search | `backend/app/search/` | Index definition + client (keyword/vector/hybrid/semantic) |
| Azure clients | `backend/app/services/azure_clients.py` | Azure OpenAI chat + embeddings (Entra ID / key) |
| RAG | `backend/app/rag/` | Router, retriever, evidence, generator, prompts, citations |
| API | `backend/app/api/` | health, sources, products, search, chat (+ SSE) |
| Models | `backend/app/models/` | Pydantic models (product, source, chat) |

## Retrieval hierarchy

1. Deterministic structured lookup (product / ingredient / category / portfolio)
2. Exact lexical search (Azure AI Search keyword)
3. Hybrid keyword + vector retrieval
4. Semantic reranking
5. Grounded generation (only after the evidence gate passes)

Deterministic lookups are preferred whenever they can answer the question and work even when
Azure Search is unavailable (local fallback).

## Authentication

`DefaultAzureCredential` is used whenever the corresponding key variable is empty. An empty
`AZURE_OPENAI_API_KEY` in `.env` is intentionally cleared from the process environment so the
Azure OpenAI SDK falls through to Entra ID instead of treating an empty string as an invalid
key. Azure AI Search likewise uses `DefaultAzureCredential` when `AZURE_SEARCH_API_KEY` is
empty (the `your-search-service` service has Entra ID / RBAC auth enabled), so the whole stack runs
keyless on `az login` locally and Managed Identity in production.

## Azure services used

| Service | Use |
| --- | --- |
| Azure OpenAI (`gpt-5.4`) | Question understanding + grounded answer composition |
| Azure OpenAI (`text-embedding-3-small`, 1536-d) | Vector embeddings |
| Azure AI Search (`your-search-service`) | Hybrid + semantic retrieval, source-aware index |
| Application Insights (optional) | Observability via connection string |

No Blob Storage, Cosmos DB, SQL, Redis or additional vector DB is used — the dataset lives in
Excel/JSON and Azure AI Search is the retrieval layer.

## Azure deployment

- Host the FastAPI app on Azure App Service (`uvicorn app.main:app --app-dir backend`).
- Build the frontend (`npm run build`) and serve `frontend/dist` from a static host or App Service.
- Prefer **Managed Identity** + RBAC:
  - *Cognitive Services OpenAI User* on the Azure OpenAI resource.
  - *Search Index Data Contributor* (data) and *Search Service Contributor* (index management)
    on the search service. The `your-search-service` service has Entra ID auth enabled
    (`authOptions: aadOrApiKey`), so both local development (`az login`) and production
    (Managed Identity) authenticate without keys.
- Keep any fallback secrets in App Settings / Key Vault, never in the frontend bundle.

## Observability

Chat requests log `conversation_id`, `intent`, `retrieval_mode`, retrieved product IDs and
latency. Secrets and hidden reasoning are never logged.
