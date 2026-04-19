from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ApiMode = Literal["local", "remote"]
DEFAULT_REMOTE_API_CAPABILITIES = frozenset(
    {
        "documents:upload",
        "search:query",
        "search:feedback",
        "chat:query",
        "chat:feedback",
    }
)


@dataclass(frozen=True)
class ResolvedApiCredential:
    actor: str
    key: str
    capabilities: frozenset[str]


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
    api_credentials_json: str | None = None
    remote_api_capabilities: str | None = None
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


def resolve_remote_api_capabilities(settings: Settings | None = None) -> set[str]:
    current_settings = settings or get_settings()
    configured_capabilities = getattr(current_settings, "remote_api_capabilities", None)
    if configured_capabilities is None:
        return set(DEFAULT_REMOTE_API_CAPABILITIES)
    return {item.strip() for item in configured_capabilities.split(",") if item.strip()}


def resolve_api_credentials(
    settings: Settings | None = None,
) -> tuple[ResolvedApiCredential, ...]:
    current_settings = settings or get_settings()
    configured_credentials = getattr(current_settings, "api_credentials_json", None)
    if configured_credentials:
        try:
            payload = json.loads(configured_credentials)
        except json.JSONDecodeError as exc:
            raise ValueError("DOCLING_SYSTEM_API_CREDENTIALS_JSON must be valid JSON.") from exc
        if not isinstance(payload, list):
            raise ValueError("DOCLING_SYSTEM_API_CREDENTIALS_JSON must decode to a list.")

        resolved_credentials: list[ResolvedApiCredential] = []
        for index, raw_credential in enumerate(payload, start=1):
            if not isinstance(raw_credential, dict):
                raise ValueError("DOCLING_SYSTEM_API_CREDENTIALS_JSON entries must be objects.")
            key = str(raw_credential.get("key") or "").strip()
            if not key:
                raise ValueError("Each API credential must include a non-empty 'key'.")
            actor = str(raw_credential.get("actor") or f"credential_{index}").strip()
            raw_capabilities = raw_credential.get("capabilities")
            if raw_capabilities is None:
                capabilities = set(DEFAULT_REMOTE_API_CAPABILITIES)
            elif isinstance(raw_capabilities, str):
                capabilities = {
                    item.strip() for item in raw_capabilities.split(",") if item.strip()
                }
            elif isinstance(raw_capabilities, list):
                capabilities = {str(item).strip() for item in raw_capabilities if str(item).strip()}
            else:
                raise ValueError(
                    "API credential capabilities must be a comma-separated string or list."
                )
            resolved_credentials.append(
                ResolvedApiCredential(
                    actor=actor,
                    key=key,
                    capabilities=frozenset(capabilities),
                )
            )
        return tuple(resolved_credentials)

    legacy_api_key = getattr(current_settings, "api_key", None)
    if not legacy_api_key:
        return ()
    return (
        ResolvedApiCredential(
            actor="legacy_api_key",
            key=legacy_api_key,
            capabilities=frozenset(resolve_remote_api_capabilities(current_settings)),
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
