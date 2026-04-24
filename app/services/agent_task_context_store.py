from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskVerification,
    SearchHarnessEvaluation,
    SearchReplayRun,
)
from app.schemas.agent_tasks import ContextFreshnessStatus, ContextRef, TaskContextEnvelope
from app.services.storage import StorageService


def _payload_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact_context_ref(
    session: Session,
    *,
    task: AgentTask,
    artifact_id: UUID,
    action,
    ref_key: str,
    summary: str,
    now,
) -> ContextRef | None:
    artifact_row = session.get(AgentTaskArtifact, artifact_id)
    if artifact_row is None:
        return None
    return ContextRef(
        ref_key=ref_key,
        ref_kind="artifact",
        summary=summary,
        task_id=task.id,
        artifact_id=artifact_row.id,
        artifact_kind=artifact_row.artifact_kind,
        schema_name=action.output_schema_name,
        schema_version=action.output_schema_version,
        observed_sha256=_payload_sha256(artifact_row.payload_json or {}),
        source_updated_at=artifact_row.created_at,
        checked_at=now,
        freshness_status=ContextFreshnessStatus.FRESH,
    )


def _task_output_context_ref(
    *,
    ref_key: str,
    summary: str,
    context: TaskContextEnvelope,
    now,
) -> ContextRef:
    return ContextRef(
        ref_key=ref_key,
        ref_kind="task_output",
        summary=summary,
        task_id=context.task_id,
        schema_name=context.output_schema_name,
        schema_version=context.output_schema_version,
        observed_sha256=_payload_sha256(context.output),
        source_updated_at=context.task_updated_at,
        checked_at=now,
        freshness_status=context.freshness_status or ContextFreshnessStatus.FRESH,
    )


def _derive_freshness_status(refs: list[ContextRef]) -> ContextFreshnessStatus | None:
    statuses = [row.freshness_status for row in refs if row.freshness_status is not None]
    if not statuses:
        return None
    if ContextFreshnessStatus.SCHEMA_MISMATCH in statuses:
        return ContextFreshnessStatus.SCHEMA_MISMATCH
    if ContextFreshnessStatus.MISSING in statuses:
        return ContextFreshnessStatus.MISSING
    if ContextFreshnessStatus.STALE in statuses:
        return ContextFreshnessStatus.STALE
    return ContextFreshnessStatus.FRESH


def _get_context_artifact_row(session: Session, task_id: UUID) -> AgentTaskArtifact | None:
    return (
        session.execute(
            select(AgentTaskArtifact)
            .where(
                AgentTaskArtifact.task_id == task_id,
                AgentTaskArtifact.artifact_kind == "context",
            )
            .order_by(AgentTaskArtifact.created_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )


def get_agent_task_context_artifact(session: Session, task_id: UUID) -> AgentTaskArtifact:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_not_found",
            "Agent task not found.",
            task_id=str(task_id),
        )
    row = _get_context_artifact_row(session, task_id)
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_context_not_found",
            "Agent task context not found.",
            task_id=str(task_id),
        )
    return row


def get_agent_task_context(session: Session, task_id: UUID) -> TaskContextEnvelope:
    artifact = get_agent_task_context_artifact(session, task_id)
    envelope = TaskContextEnvelope.model_validate(artifact.payload_json or {})
    return refresh_task_context_freshness(session, envelope)


def get_agent_task_context_yaml_path(
    storage_service: StorageService,
    *,
    task_id: UUID,
) -> Path:
    return storage_service.get_agent_task_context_yaml_path(task_id)


def _verification_payload(row: AgentTaskVerification) -> dict:
    return {
        "verification_id": str(row.id),
        "target_task_id": str(row.target_task_id),
        "verification_task_id": (
            str(row.verification_task_id) if row.verification_task_id is not None else None
        ),
        "verifier_type": row.verifier_type,
        "outcome": row.outcome,
        "metrics": row.metrics_json or {},
        "reasons": row.reasons_json or [],
        "details": row.details_json or {},
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at is not None else None,
    }


def _search_replay_run_payload(row: SearchReplayRun) -> dict:
    return {
        "replay_run_id": str(row.id),
        "source_type": row.source_type,
        "status": row.status,
        "harness_name": row.harness_name,
        "reranker_name": row.reranker_name,
        "reranker_version": row.reranker_version,
        "retrieval_profile_name": row.retrieval_profile_name,
        "harness_config": row.harness_config_json or {},
        "query_count": row.query_count,
        "passed_count": row.passed_count,
        "failed_count": row.failed_count,
        "zero_result_count": row.zero_result_count,
        "table_hit_count": row.table_hit_count,
        "top_result_changes": row.top_result_changes,
        "max_rank_shift": row.max_rank_shift,
        "summary": row.summary_json or {},
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at is not None else None,
    }


def _search_harness_evaluation_payload(row: SearchHarnessEvaluation) -> dict:
    return {
        "evaluation_id": str(row.id),
        "status": row.status,
        "baseline_harness_name": row.baseline_harness_name,
        "candidate_harness_name": row.candidate_harness_name,
        "limit": row.limit,
        "source_types": row.source_types_json or [],
        "harness_overrides": row.harness_overrides_json or {},
        "total_shared_query_count": row.total_shared_query_count,
        "total_improved_count": row.total_improved_count,
        "total_regressed_count": row.total_regressed_count,
        "total_unchanged_count": row.total_unchanged_count,
        "summary": row.summary_json or {},
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at is not None else None,
    }


def _search_harness_evaluation_context_ref(
    session: Session,
    evaluation_id: UUID | str | None,
    *,
    now,
) -> ContextRef | None:
    if evaluation_id is None:
        return None
    evaluation_uuid = evaluation_id if isinstance(evaluation_id, UUID) else UUID(str(evaluation_id))
    evaluation_row = session.get(SearchHarnessEvaluation, evaluation_uuid)
    if evaluation_row is None:
        return None
    return ContextRef(
        ref_key="search_harness_evaluation",
        ref_kind="search_harness_evaluation",
        summary="Durable harness evaluation record consumed by verification gates.",
        search_harness_evaluation_id=evaluation_row.id,
        schema_name="search_harness_evaluation",
        schema_version="1.0",
        observed_sha256=_payload_sha256(_search_harness_evaluation_payload(evaluation_row)),
        source_updated_at=evaluation_row.completed_at or evaluation_row.created_at,
        checked_at=now,
        freshness_status=ContextFreshnessStatus.FRESH,
    )


def _refresh_context_ref(session: Session, ref: ContextRef) -> ContextRef:
    updated = ref.model_copy(deep=True)
    updated.checked_at = utcnow()

    if ref.ref_kind == "task_output":
        if ref.task_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        task = session.get(AgentTask, ref.task_id)
        if task is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        from app.services.agent_task_actions import get_agent_task_action

        action = get_agent_task_action(task.task_type)
        if (
            ref.schema_name
            and action.output_schema_name
            and ref.schema_name != action.output_schema_name
        ):
            updated.freshness_status = ContextFreshnessStatus.SCHEMA_MISMATCH
            return updated
        if (
            ref.schema_version
            and action.output_schema_version
            and ref.schema_version != action.output_schema_version
        ):
            updated.freshness_status = ContextFreshnessStatus.SCHEMA_MISMATCH
            return updated
        if action.output_model is not None:
            source_context_row = _get_context_artifact_row(session, task.id)
            if source_context_row is None:
                updated.freshness_status = ContextFreshnessStatus.MISSING
                return updated
            source_context = TaskContextEnvelope.model_validate(
                source_context_row.payload_json or {}
            )
            current_payload = source_context.output
        else:
            current_payload = task.result_json or {}
        current_hash = _payload_sha256(current_payload)
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = task.updated_at
        return updated

    if ref.ref_kind == "artifact":
        if ref.artifact_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        artifact = session.get(AgentTaskArtifact, ref.artifact_id)
        if artifact is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        if ref.artifact_kind and artifact.artifact_kind != ref.artifact_kind:
            updated.freshness_status = ContextFreshnessStatus.SCHEMA_MISMATCH
            return updated
        current_hash = _payload_sha256(artifact.payload_json or {})
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = artifact.created_at
        return updated

    if ref.ref_kind == "verification_record":
        if ref.verification_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        verification_row = session.get(AgentTaskVerification, ref.verification_id)
        if verification_row is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        current_hash = _payload_sha256(_verification_payload(verification_row))
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = verification_row.completed_at or verification_row.created_at
        return updated

    if ref.ref_kind == "replay_run":
        if ref.replay_run_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        replay_run = session.get(SearchReplayRun, ref.replay_run_id)
        if replay_run is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        current_hash = _payload_sha256(_search_replay_run_payload(replay_run))
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = replay_run.completed_at or replay_run.created_at
        return updated

    if ref.ref_kind == "search_harness_evaluation":
        if ref.search_harness_evaluation_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        evaluation = session.get(SearchHarnessEvaluation, ref.search_harness_evaluation_id)
        if evaluation is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        current_hash = _payload_sha256(_search_harness_evaluation_payload(evaluation))
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = evaluation.completed_at or evaluation.created_at
        return updated

    updated.freshness_status = ref.freshness_status or ContextFreshnessStatus.FRESH
    return updated


def refresh_task_context_freshness(
    session: Session,
    envelope: TaskContextEnvelope,
) -> TaskContextEnvelope:
    refreshed_refs = [_refresh_context_ref(session, ref) for ref in envelope.refs]
    refreshed = envelope.model_copy(deep=True)
    refreshed.refs = refreshed_refs
    refreshed.freshness_status = _derive_freshness_status(refreshed_refs)
    return refreshed
