# Retrieval & Grounded Generation (RAG)

## Principle

This is **not** a pure vector chatbot. It combines structured retrieval, exact search, hybrid
RAG, semantic reranking and grounded generation, selecting the method by question intent. The
LLM composes and presents; it never supplies product facts on its own.

## Query routing (`backend/app/rag/query_router.py`)

Deterministic, rule-based (no LLM). Intents:

| Intent | Example |
| --- | --- |
| `EXACT_PRODUCT` | "Tell me about DEMOCIN" |
| `COMPOSITION_LOOKUP` | "What is the composition of DEMOCIN?" |
| `INGREDIENT_SEARCH` | "Which products contain Nurobalin?" |
| `CATEGORY_SEARCH` | "Show anti-infective products" |
| `PRODUCT_COMPARISON` | "Compare DEMOCIN and DEMOCIN O" |
| `PORTFOLIO_OVERVIEW` | "Executive overview of the portfolio" |
| `SEMANTIC_PRODUCT_SEARCH` | "Products relevant to pain management" |
| `GENERAL_PRODUCT_QA` | free-form product Q&A |
| `OUT_OF_SCOPE` | "market share", "capital of France" |

The router also flags patient-specific medical-advice requests and can resolve a source hint
("from the Product Catalog catalogue...").

## Retrieval (`backend/app/rag/retriever.py`)

1. **Structured** — exact product-ID resolution, ingredient lookup (structured ingredients +
   normalized composition), category filter, or full portfolio.
2. **Hybrid** — Azure AI Search BM25 keyword + vector (`content_vector`) with optional
   semantic reranking, filterable by `source_id`.
3. **Local fallback** — deterministic brand/token matching when Azure Search is unavailable.

Exact/structured results short-circuit before semantic retrieval whenever they are sufficient.

## Evidence packet & gate (`backend/app/rag/evidence.py`)

Retrieved records become a delimited `<EVIDENCE>` block containing product, category,
composition, source name and source URL. The evidence gate checks that at least one grounded
product is present; otherwise the assistant abstains with:

> I couldn't find sufficient information in the current product knowledge base to answer that
> reliably.

## Generation (`backend/app/rag/generator.py`, `prompts.py`)

- System prompt enforces grounding rules (never invent composition, strengths, indications,
  dosage, pricing, market share, etc.), Markdown output, tables for comparisons, and a
  "Sources" section.
- Retrieved evidence is explicitly labelled as DATA; instructions inside retrieved content are
  ignored (prompt-injection defense).
- Response styles (`concise`, `standard`, `detailed`, `executive`) control depth/formatting.
- If Azure OpenAI is unavailable, a deterministic grounded summary of the retrieved evidence
  is returned instead of failing — it renders retrieved structured data and invents nothing.
- Streaming (`POST /api/chat/stream`, SSE) emits coarse progress stages ("Searching product
  knowledge...", "Reviewing relevant products...", "Preparing grounded response...") — never
  chain-of-thought.

## Citations (`backend/app/rag/citations.py`)

Built only from the source registry, one per distinct contributing source. Any citation whose
URL is not registered in `sources/sources.json` is dropped. The LLM never invents URLs.

## Azure AI Search index (`backend/app/search/index.py`)

Source-aware fields: `id`, `product_id`, `source_id`, `source_name`, `source_type`,
`brand_name(+_normalized)`, `composition(+_normalized)`,
`therapeutic_category(+_normalized)`, `content`, `source_url`, `source_title`,
`document_type`, `last_updated`, `content_vector`. Vector dimensions come from
`EMBEDDING_DIMENSIONS`. A semantic configuration prioritises brand/category/content.

## Medical safety

Patient-specific prescribing/diagnosis/treatment questions receive a safety notice and are not
answered with personalized advice; source-grounded product information may still be presented
with attribution.
