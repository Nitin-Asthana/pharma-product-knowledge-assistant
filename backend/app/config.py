"""Application configuration.

All configuration is loaded from environment variables (optionally via a local
``.env`` file). Nothing sensitive is hardcoded. Source URLs never live here —
they are resolved exclusively through the source registry (``sources.json``).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file: backend/app/config.py -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from the project root if present (local development convenience).
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = Field(default="development")

    # Azure OpenAI
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_key: str = Field(default="")
    azure_openai_api_version: str = Field(default="2025-04-01-preview")
    azure_openai_chat_deployment: str = Field(default="gpt-5.4")
    azure_openai_embedding_deployment: str = Field(default="text-embedding-3-small")
    azure_openai_embedding_api_version: str = Field(default="2024-02-01")
    embedding_dimensions: int = Field(default=1536)

    # Azure AI Search
    azure_search_endpoint: str = Field(default="")
    azure_search_api_key: str = Field(default="")
    azure_search_index: str = Field(default="abc-pharma-products")
    azure_search_semantic_config: str = Field(default="abc-pharma-semantic")

    # Application
    source_registry_path: str = Field(default="sources/sources.json")
    data_dir: str = Field(default="data/sources")

    top_k: int = Field(default=5)
    vector_top_k: int = Field(default=10)
    semantic_top_k: int = Field(default=5)

    cors_allow_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    applicationinsights_connection_string: str = Field(default="")

    # ------------------------------------------------------------------ helpers
    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def source_registry_file(self) -> Path:
        p = Path(self.source_registry_path)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def data_root(self) -> Path:
        p = Path(self.data_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def use_openai_key(self) -> bool:
        return bool(self.azure_openai_api_key.strip())

    @property
    def use_search_key(self) -> bool:
        return bool(self.azure_search_api_key.strip())

    def source_data_dir(self, source_id: str) -> Path:
        return self.data_root / source_id


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
