from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.services.storage import StorageService


def resolve_existing_bootstrap_path(
    path: Path,
    *,
    error_cls: type[Exception],
) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise error_cls(f"Required path does not exist: {resolved}")
    return resolved


def resolve_readiness_output_path(
    path: Path | None,
    *,
    storage_service: StorageService,
    default_filename: str,
) -> Path:
    if path is not None:
        return path.expanduser().resolve()
    return (storage_service.storage_root / default_filename).resolve()


def load_bootstrap_yaml_mapping(
    path: Path,
    *,
    error_cls: type[Exception],
) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise error_cls(f"Bootstrap seed must decode to a mapping: {path}")
    return data


def count_model_rows(
    session: Session,
    model: type[Any],
    *criteria: Any,
) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return int(session.scalar(statement) or 0)
