"""Azure OpenAI client helpers.

Authentication uses ``DefaultAzureCredential`` (Managed Identity / az login) by
default. An API key is used only when explicitly configured for local fallback.
No credentials are ever logged or returned to the frontend.
"""
from __future__ import annotations

import os
import threading
from functools import lru_cache

from ..config import settings


class AzureOpenAIUnavailable(Exception):
    """Raised when Azure OpenAI is not configured or cannot be reached."""


_token_provider_lock = threading.Lock()
_token_provider = None


def _clear_empty_key_env() -> None:
    """Prevent the openai SDK from picking up an empty-string API key.

    ``.env`` files commonly contain ``AZURE_OPENAI_API_KEY=`` (empty) to signal
    "use Entra ID auth". ``load_dotenv`` puts that empty string into the process
    environment, and the openai SDK treats an empty string as an invalid key
    instead of falling through to the Entra ID token provider. When no key is
    configured we remove the empty variable so token-provider auth is used.
    """
    for var in ("AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"):
        if not (os.environ.get(var) or "").strip():
            os.environ.pop(var, None)



def _get_token_provider():
    global _token_provider
    with _token_provider_lock:
        if _token_provider is None:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            _token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
    return _token_provider


@lru_cache
def get_chat_client():
    from openai import AzureOpenAI

    if not settings.azure_openai_endpoint:
        raise AzureOpenAIUnavailable("AZURE_OPENAI_ENDPOINT is not configured.")

    kwargs = dict(
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
    )
    if settings.use_openai_key:
        kwargs["api_key"] = settings.azure_openai_api_key
    else:
        _clear_empty_key_env()
        kwargs["azure_ad_token_provider"] = _get_token_provider()
    return AzureOpenAI(**kwargs)


@lru_cache
def get_embedding_client():
    from openai import AzureOpenAI

    if not settings.azure_openai_endpoint:
        raise AzureOpenAIUnavailable("AZURE_OPENAI_ENDPOINT is not configured.")

    kwargs = dict(
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_embedding_api_version,
    )
    if settings.use_openai_key:
        kwargs["api_key"] = settings.azure_openai_api_key
    else:
        _clear_empty_key_env()
        kwargs["azure_ad_token_provider"] = _get_token_provider()
    return AzureOpenAI(**kwargs)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Validates dimensions against configuration."""
    if not texts:
        return []
    client = get_embedding_client()
    try:
        resp = client.embeddings.create(
            model=settings.azure_openai_embedding_deployment,
            input=texts,
        )
    except Exception as exc:  # noqa: BLE001
        raise AzureOpenAIUnavailable(f"Embedding request failed: {exc}") from exc

    vectors = [item.embedding for item in resp.data]
    expected = settings.embedding_dimensions
    for v in vectors:
        if len(v) != expected:
            raise AzureOpenAIUnavailable(
                f"Embedding dimension mismatch: got {len(v)}, expected {expected}. "
                "Check EMBEDDING_DIMENSIONS and the deployment."
            )
    return vectors


def embed_query(text: str) -> list[float]:
    result = embed_texts([text])
    return result[0] if result else []


def openai_available() -> bool:
    try:
        get_chat_client()
        return True
    except Exception:  # noqa: BLE001
        return False
