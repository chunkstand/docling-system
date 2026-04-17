from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCLING_SYSTEM_",
        env_file=".env",
        extra="ignore",
    )

    env: str = "development"
    database_url: str = "postgresql+psycopg://docling:docling@localhost:5432/docling_system"
    storage_root: Path = Field(default=Path("./storage"))
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4.1-mini"
    embedding_dim: int = 1536
    worker_poll_seconds: int = 2
    worker_lease_timeout_seconds: int = 300
    worker_max_attempts: int = 3
    worker_heartbeat_seconds: int = 30
    local_ingest_allowed_roots: str | None = None
    local_ingest_max_file_bytes: int = 268435456
    local_ingest_max_pages: int = 1000
    docling_document_timeout_seconds: float | None = 120.0
    docling_fallback_document_timeout_seconds: float | None = 30.0
    table_supplement_registry_path: Path = Field(default=Path("./config/table_supplements.yaml"))


def default_local_ingest_roots() -> list[Path]:
    return [
        Path.cwd().resolve(),
        (Path.home() / "Documents").resolve(),
        (Path.home() / "Downloads").resolve(),
    ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
