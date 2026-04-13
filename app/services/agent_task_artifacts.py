from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.models import AgentTaskArtifact
from app.services.storage import StorageService


def _utcnow() -> datetime:
    return datetime.now(UTC)


def create_agent_task_artifact(
    session: Session,
    *,
    task_id: UUID,
    artifact_kind: str,
    payload: dict,
    storage_service: StorageService | None = None,
    filename: str | None = None,
    attempt_id: UUID | None = None,
) -> AgentTaskArtifact:
    encoded_payload = jsonable_encoder(payload)
    storage_path: str | None = None

    if storage_service is not None and filename is not None:
        artifact_path = storage_service.get_agent_task_dir(task_id) / filename
        artifact_path.write_text(json.dumps(encoded_payload, indent=2, sort_keys=True))
        storage_path = str(artifact_path)

    row = AgentTaskArtifact(
        task_id=task_id,
        attempt_id=attempt_id,
        artifact_kind=artifact_kind,
        storage_path=storage_path,
        payload_json=encoded_payload,
        created_at=_utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def delete_agent_task_artifact_file(
    storage_service: StorageService,
    *,
    storage_path: str | None,
) -> None:
    if storage_path is None:
        return
    storage_service.delete_file_if_exists(Path(storage_path))
