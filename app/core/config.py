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
    embedding_dim: int = 1536
    worker_poll_seconds: int = 2
    worker_lease_timeout_seconds: int = 300
    worker_max_attempts: int = 3
    worker_heartbeat_seconds: int = 30


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
