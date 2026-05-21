from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.public.agent_tasks import (
    KnowledgeOperatorInput,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
)
from app.services.evidence_common import payload_sha256


def _record_inputs(
    session: Session,
    *,
    operator_run_id: UUID,
    rows: Iterable[dict[str, Any]],
    created_at,
) -> None:
    for index, row in enumerate(rows):
        session.add(
            KnowledgeOperatorInput(
                id=uuid.uuid4(),
                operator_run_id=operator_run_id,
                input_index=int(row.get("input_index", index)),
                input_kind=str(row.get("input_kind") or row.get("kind") or "input"),
                source_table=row.get("source_table"),
                source_id=_uuid_or_none(row.get("source_id")),
                artifact_path=row.get("artifact_path"),
                artifact_sha256=row.get("artifact_sha256"),
                payload_json=_json_payload(row.get("payload")),
                created_at=created_at,
            )
        )


def _record_outputs(
    session: Session,
    *,
    operator_run_id: UUID,
    rows: Iterable[dict[str, Any]],
    created_at,
) -> None:
    for index, row in enumerate(rows):
        session.add(
            KnowledgeOperatorOutput(
                id=uuid.uuid4(),
                operator_run_id=operator_run_id,
                output_index=int(row.get("output_index", index)),
                output_kind=str(row.get("output_kind") or row.get("kind") or "output"),
                target_table=row.get("target_table"),
                target_id=_uuid_or_none(row.get("target_id")),
                artifact_path=row.get("artifact_path"),
                artifact_sha256=row.get("artifact_sha256"),
                payload_json=_json_payload(row.get("payload")),
                created_at=created_at,
            )
        )


def record_knowledge_operator_run(
    session: Session | None,
    *,
    operator_kind: str,
    operator_name: str,
    operator_version: str | None = None,
    status: str = "completed",
    parent_operator_run_id: UUID | None = None,
    document_id: UUID | None = None,
    run_id: UUID | None = None,
    search_request_id: UUID | None = None,
    search_harness_evaluation_id: UUID | None = None,
    agent_task_id: UUID | None = None,
    agent_task_attempt_id: UUID | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    prompt_sha256: str | None = None,
    config: Any | None = None,
    input_payload: Any | None = None,
    output_payload: Any | None = None,
    metrics: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    inputs: Iterable[dict[str, Any]] = (),
    outputs: Iterable[dict[str, Any]] = (),
    started_at=None,
    completed_at=None,
    duration_ms: float | None = None,
) -> KnowledgeOperatorRun | None:
    if session is None or not hasattr(session, "add"):
        return None

    created_at = utcnow()
    completed_at = completed_at or created_at
    run = KnowledgeOperatorRun(
        id=uuid.uuid4(),
        parent_operator_run_id=parent_operator_run_id,
        operator_kind=operator_kind,
        operator_name=operator_name,
        operator_version=operator_version,
        status=status,
        document_id=document_id,
        run_id=run_id,
        search_request_id=search_request_id,
        search_harness_evaluation_id=search_harness_evaluation_id,
        agent_task_id=agent_task_id,
        agent_task_attempt_id=agent_task_attempt_id,
        model_name=model_name,
        model_version=model_version,
        prompt_sha256=prompt_sha256,
        config_sha256=payload_sha256(config),
        input_sha256=payload_sha256(input_payload),
        output_sha256=payload_sha256(output_payload),
        metrics_json=_json_payload(metrics),
        metadata_json=_json_payload(metadata),
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        created_at=created_at,
    )
    session.add(run)
    session.flush()
    _record_inputs(session, operator_run_id=run.id, rows=inputs, created_at=created_at)
    _record_outputs(session, operator_run_id=run.id, rows=outputs, created_at=created_at)
    session.flush()
    return run
