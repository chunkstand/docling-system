from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings
from app.services.semantic_registry_contracts import (
    SemanticRegistry,
    semantic_registry_from_marshaled_payload,
    semantic_registry_from_payload,
    validate_semantic_registry_payload,
)


def resolve_seed_registry_path() -> Path:
    settings = get_settings()
    if settings.semantic_registry_path is not None:
        return settings.semantic_registry_path.expanduser().resolve()
    return settings.upper_ontology_path.expanduser().resolve()


def load_semantic_registry_payload(registry_path: str | Path | None = None) -> dict[str, Any]:
    current_path = _resolved_registry_path(registry_path)
    if not current_path.is_file():
        raise ValueError(f"Semantic registry path does not exist: {current_path}")
    return validate_semantic_registry_payload(yaml.safe_load(current_path.read_bytes()) or {})


def clear_semantic_registry_cache() -> None:
    _load_semantic_registry_cached.cache_clear()


def write_semantic_registry_payload(
    payload: dict[str, Any],
    registry_path: str | Path | None = None,
) -> Path:
    semantic_registry_from_payload(payload)
    current_path = _resolved_registry_path(registry_path)
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text(
        yaml.safe_dump(
            validate_semantic_registry_payload(payload),
            sort_keys=False,
            allow_unicode=True,
        )
    )
    clear_semantic_registry_cache()
    return current_path


def load_semantic_registry(registry_path: str | Path | None = None) -> SemanticRegistry:
    current_path = _resolved_registry_path(registry_path)
    return _load_semantic_registry_cached(str(current_path))


def _resolved_registry_path(registry_path: str | Path | None) -> Path:
    if registry_path is not None:
        return Path(registry_path).expanduser().resolve()
    return resolve_seed_registry_path()


def _load_semantic_registry_uncached(registry_path: str) -> SemanticRegistry:
    path = Path(registry_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Semantic registry path does not exist: {path}")
    raw_bytes = path.read_bytes()
    payload = validate_semantic_registry_payload(yaml.safe_load(raw_bytes) or {})
    return semantic_registry_from_marshaled_payload(raw_bytes, payload)


@lru_cache(maxsize=4)
def _load_semantic_registry_cached(registry_path: str) -> SemanticRegistry:
    return _load_semantic_registry_uncached(registry_path)


__all__ = [
    "clear_semantic_registry_cache",
    "load_semantic_registry",
    "load_semantic_registry_payload",
    "resolve_seed_registry_path",
    "write_semantic_registry_payload",
]
