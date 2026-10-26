"""Azure AI Search index definition and management.

The index is source-aware: every document retains ``source_id``, ``source_name``,
``source_url`` and ``source_type``. Vector dimensions are taken from
``EMBEDDING_DIMENSIONS`` — never assumed.
"""
from __future__ import annotations

from ..config import settings


def build_index():
    """Construct the SearchIndex object for ``abc-pharma-products``."""
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchableField,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="product_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="source_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="brand_name", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="brand_name_normalized", type=SearchFieldDataType.String),
        SearchableField(name="composition", type=SearchFieldDataType.String),
        SearchableField(name="composition_normalized", type=SearchFieldDataType.String),
        SearchableField(
            name="therapeutic_category",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="therapeutic_category_normalized",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="source_url", type=SearchFieldDataType.String),
        SimpleField(name="source_title", type=SearchFieldDataType.String),
        SimpleField(name="document_type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="last_updated", type=SearchFieldDataType.String, filterable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=settings.embedding_dimensions,
            vector_search_profile_name="abc-pharma-hnsw-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="abc-pharma-hnsw")],
        profiles=[
            VectorSearchProfile(
                name="abc-pharma-hnsw-profile",
                algorithm_configuration_name="abc-pharma-hnsw",
            )
        ],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name=settings.azure_search_semantic_config,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="brand_name"),
                    content_fields=[
                        SemanticField(field_name="content"),
                        SemanticField(field_name="composition"),
                    ],
                    keywords_fields=[SemanticField(field_name="therapeutic_category")],
                ),
            )
        ]
    )

    return SearchIndex(
        name=settings.azure_search_index,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def get_index_client():
    from azure.search.documents.indexes import SearchIndexClient

    if not settings.azure_search_endpoint:
        raise RuntimeError("AZURE_SEARCH_ENDPOINT is not configured.")

    if settings.use_search_key:
        from azure.core.credentials import AzureKeyCredential

        credential = AzureKeyCredential(settings.azure_search_api_key)
    else:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()

    return SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=credential)


def create_or_update_index() -> str:
    client = get_index_client()
    index = build_index()
    result = client.create_or_update_index(index)
    return result.name
