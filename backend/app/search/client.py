"""Azure AI Search client wrapper.

Provides document upload and the three retrieval modes used by the RAG layer:
exact/lexical keyword search, vector search and hybrid + semantic reranking.
All queries can be filtered by ``source_id`` for multi-source support.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..config import settings
from ..models.product import Product


class SearchUnavailable(Exception):
    """Raised when Azure AI Search is not configured or cannot be reached."""


def _credential():
    if settings.use_search_key:
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(settings.azure_search_api_key)
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


@lru_cache
def get_search_client():
    from azure.search.documents import SearchClient

    if not settings.azure_search_endpoint:
        raise SearchUnavailable("AZURE_SEARCH_ENDPOINT is not configured.")
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index,
        credential=_credential(),
    )


def product_to_document(product: Product, vector: list[float] | None, last_updated: str) -> dict[str, Any]:
    return {
        "id": product.product_id.replace(":", "__"),
        "product_id": product.product_id,
        "source_id": product.source_id,
        "source_name": product.source_name,
        "source_type": product.source_type,
        "brand_name": product.brand_name,
        "brand_name_normalized": product.brand_name_normalized,
        "composition": product.composition,
        "composition_normalized": product.composition_normalized,
        "therapeutic_category": product.therapeutic_category,
        "therapeutic_category_normalized": product.therapeutic_category_normalized,
        "content": product.content(),
        "source_url": product.source_url,
        "source_title": product.source_title,
        "document_type": "product",
        "last_updated": last_updated,
        **({"content_vector": vector} if vector is not None else {}),
    }


def upload_documents(documents: list[dict[str, Any]]) -> int:
    if not documents:
        return 0
    client = get_search_client()
    total = 0
    for i in range(0, len(documents), 100):
        batch = documents[i : i + 100]
        client.upload_documents(documents=batch)
        total += len(batch)
    return total


def delete_documents(ids: list[str]) -> int:
    if not ids:
        return 0
    client = get_search_client()
    docs = [{"id": _id} for _id in ids]
    client.delete_documents(documents=docs)
    return len(docs)


def _source_filter(source_ids: list[str] | None) -> str | None:
    if not source_ids:
        return None
    quoted = ",".join(source_ids)
    return f"search.in(source_id, '{quoted}', ',')"


_SELECT = [
    "product_id",
    "brand_name",
    "composition",
    "therapeutic_category",
    "source_id",
    "source_name",
    "source_url",
]


def keyword_search(
    query: str,
    source_ids: list[str] | None = None,
    top: int = 5,
    extra_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Lexical BM25 search."""
    client = get_search_client()
    filters = [f for f in (_source_filter(source_ids), extra_filter) if f]
    results = client.search(
        search_text=query,
        filter=" and ".join(filters) if filters else None,
        top=top,
        select=_SELECT,
    )
    return [_shape(r, "keyword") for r in results]


def hybrid_search(
    query: str,
    vector: list[float] | None,
    source_ids: list[str] | None = None,
    top: int = 5,
    semantic: bool = True,
) -> list[dict[str, Any]]:
    """Hybrid keyword + vector search with optional semantic reranking."""
    from azure.search.documents.models import VectorizedQuery

    client = get_search_client()
    filters = _source_filter(source_ids)

    vector_queries = None
    if vector:
        vector_queries = [
            VectorizedQuery(
                vector=vector,
                k_nearest_neighbors=settings.vector_top_k,
                fields="content_vector",
            )
        ]

    kwargs: dict[str, Any] = dict(
        search_text=query,
        filter=filters,
        top=top,
        select=_SELECT,
    )
    if vector_queries:
        kwargs["vector_queries"] = vector_queries

    mode = "hybrid" if vector else "keyword"
    if semantic:
        try:
            kwargs["query_type"] = "semantic"
            kwargs["semantic_configuration_name"] = settings.azure_search_semantic_config
            results = client.search(**kwargs)
            return [_shape(r, "semantic") for r in results]
        except Exception:  # noqa: BLE001 - fall back if semantic config unavailable
            kwargs.pop("query_type", None)
            kwargs.pop("semantic_configuration_name", None)
    results = client.search(**kwargs)
    return [_shape(r, mode) for r in results]


def _shape(result: dict[str, Any], mode: str) -> dict[str, Any]:
    score = result.get("@search.reranker_score")
    if score is None:
        score = result.get("@search.score", 0.0)
    return {
        "product_id": result.get("product_id", ""),
        "brand_name": result.get("brand_name", ""),
        "composition": result.get("composition", ""),
        "therapeutic_category": result.get("therapeutic_category", ""),
        "source_id": result.get("source_id", ""),
        "source_name": result.get("source_name", ""),
        "source_url": result.get("source_url", ""),
        "score": float(score) if score is not None else 0.0,
        "retrieval_mode": mode,
    }


def search_available() -> bool:
    try:
        client = get_search_client()
        # Cheap call to confirm connectivity + index existence.
        client.get_document_count()
        return True
    except Exception:  # noqa: BLE001
        return False


def document_count() -> int:
    client = get_search_client()
    return client.get_document_count()
