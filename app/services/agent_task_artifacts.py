from __future__ import annotations

import json
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskArtifact
from app.schemas.agent_tasks import AgentTaskArtifactResponse
from app.services.storage import StorageService


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
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def _to_artifact_response(row: AgentTaskArtifact) -> AgentTaskArtifactResponse:
    return AgentTaskArtifactResponse(
        artifact_id=row.id,
        task_id=row.task_id,
        attempt_id=row.attempt_id,
        artifact_kind=row.artifact_kind,
        storage_path=row.storage_path,
        payload=row.payload_json or {},
        created_at=row.created_at,
    )


def list_agent_task_artifacts(
    session: Session,
    task_id: UUID,
    *,
    limit: int = 20,
) -> list[AgentTaskArtifactResponse]:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    rows = (
        session.execute(
            select(AgentTaskArtifact)
            .where(AgentTaskArtifact.task_id == task_id)
            .order_by(AgentTaskArtifact.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_to_artifact_response(row) for row in rows]


def get_agent_task_artifact(
    session: Session,
    task_id: UUID,
    artifact_id: UUID,
) -> AgentTaskArtifact:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    row = session.get(AgentTaskArtifact, artifact_id)
    if row is None or row.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent task artifact not found.",
        )
    return row
