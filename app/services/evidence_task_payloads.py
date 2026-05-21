from __future__ import annotations

from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    AgentTaskVerification,
    KnowledgeOperatorRun,
)
from app.services.evidence_common import payload_sha256


def task_payload(row: AgentTask | None) -> dict | None:
    if row is None:
        return None
    return {
        "task_id": row.id,
        "task_type": row.task_type,
        "status": row.status,
        "workflow_version": row.workflow_version,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "completed_at": row.completed_at,
    }


def artifact_payload(row: AgentTaskArtifact) -> dict:
    return {
        "artifact_id": row.id,
        "task_id": row.task_id,
        "artifact_kind": row.artifact_kind,
        "storage_path": row.storage_path,
        "payload_sha256": payload_sha256(row.payload_json or {}),
        "created_at": row.created_at,
    }


def immutability_event_payload(row: AgentTaskArtifactImmutabilityEvent) -> dict:
    return {
        "event_id": row.id,
        "artifact_id": row.artifact_id,
        "task_id": row.task_id,
        "event_kind": row.event_kind,
        "mutation_operation": row.mutation_operation,
        "frozen_artifact_kind": row.frozen_artifact_kind,
        "attempted_artifact_kind": row.attempted_artifact_kind,
        "frozen_storage_path": row.frozen_storage_path,
        "attempted_storage_path": row.attempted_storage_path,
        "frozen_payload_sha256": row.frozen_payload_sha256,
        "attempted_payload_sha256": row.attempted_payload_sha256,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def verification_payload(row: AgentTaskVerification | None) -> dict | None:
    if row is None:
        return None
    return {
        "verification_id": row.id,
        "target_task_id": row.target_task_id,
        "verification_task_id": row.verification_task_id,
        "verifier_type": row.verifier_type,
        "outcome": row.outcome,
        "metrics": row.metrics_json or {},
        "reasons": row.reasons_json or [],
        "details": row.details_json or {},
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


def operator_run_summary(row: KnowledgeOperatorRun) -> dict:
    return {
        "operator_run_id": row.id,
        "parent_operator_run_id": row.parent_operator_run_id,
        "operator_kind": row.operator_kind,
        "operator_name": row.operator_name,
        "operator_version": row.operator_version,
        "status": row.status,
        "agent_task_id": row.agent_task_id,
        "search_request_id": row.search_request_id,
        "config_sha256": row.config_sha256,
        "input_sha256": row.input_sha256,
        "output_sha256": row.output_sha256,
        "metrics": row.metrics_json or {},
        "created_at": row.created_at,
    }
