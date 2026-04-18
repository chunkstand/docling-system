from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ApiMode = Literal["local", "remote"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCLING_SYSTEM_",
        env_file=".env",
        extra="ignore",
    )

    env: str = "development"
    database_url: str = "postgresql+psycopg://docling:docling@localhost:5432/docling_system"
    database_pool_size: int = 20
    database_max_overflow: int = 20
    database_pool_timeout_seconds: float = 30.0
    database_pool_pre_ping: bool = True
    storage_root: Path = Field(default=Path("./storage"))
    api_mode: ApiMode | None = None
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_key: str | None = None
    remote_ingest_max_inflight_runs: int | None = 8
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 2
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


def is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def resolve_api_mode(settings: Settings | None = None) -> ApiMode:
    current_settings = settings or get_settings()
    if current_settings.api_mode is not None:
        return current_settings.api_mode
    if not is_loopback_host(current_settings.api_host):
        return "remote"
    return "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
