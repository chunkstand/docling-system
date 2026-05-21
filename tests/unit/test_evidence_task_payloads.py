from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    AgentTaskVerification,
    KnowledgeOperatorRun,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_task_payloads import (
    artifact_payload,
    immutability_event_payload,
    operator_run_summary,
    task_payload,
    verification_payload,
)


def test_task_and_verification_payloads_preserve_legacy_shape() -> None:
    task_id = uuid4()
    verification_task_id = uuid4()
    verification_id = uuid4()
    timestamp = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)

    task = AgentTask(
        id=task_id,
        task_type="build_context_pack",
        status="completed",
        workflow_version="v1",
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=timestamp,
    )
    verification = AgentTaskVerification(
        id=verification_id,
        target_task_id=task_id,
        verification_task_id=verification_task_id,
        verifier_type="context_pack_gate",
        outcome="passed",
        metrics_json={"score": 1.0},
        reasons_json=["ok"],
        details_json={"checks": [{"passed": True}]},
        created_at=timestamp,
        completed_at=timestamp,
    )

    assert task_payload(None) is None
    assert task_payload(task) == {
        "task_id": task_id,
        "task_type": "build_context_pack",
        "status": "completed",
        "workflow_version": "v1",
        "created_at": timestamp,
        "updated_at": timestamp,
        "completed_at": timestamp,
    }
    assert verification_payload(None) is None
    assert verification_payload(verification) == {
        "verification_id": verification_id,
        "target_task_id": task_id,
        "verification_task_id": verification_task_id,
        "verifier_type": "context_pack_gate",
        "outcome": "passed",
        "metrics": {"score": 1.0},
        "reasons": ["ok"],
        "details": {"checks": [{"passed": True}]},
        "created_at": timestamp,
        "completed_at": timestamp,
    }


def test_artifact_and_immutability_payloads_preserve_hash_and_details() -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    timestamp = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    payload = {"b": 2, "a": 1}

    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        artifact_kind="context_pack",
        storage_path="storage/context_pack.json",
        payload_json=payload,
        created_at=timestamp,
    )
    event = AgentTaskArtifactImmutabilityEvent(
        id=7,
        artifact_id=artifact_id,
        task_id=task_id,
        event_kind="mutation_blocked",
        mutation_operation="UPDATE",
        frozen_artifact_kind="context_pack",
        attempted_artifact_kind="context_pack",
        frozen_storage_path="storage/context_pack.json",
        attempted_storage_path="storage/context_pack.json",
        frozen_payload_sha256="frozen",
        attempted_payload_sha256="attempted",
        details_json={"reason": "immutable"},
        created_at=timestamp,
    )

    assert artifact_payload(artifact) == {
        "artifact_id": artifact_id,
        "task_id": task_id,
        "artifact_kind": "context_pack",
        "storage_path": "storage/context_pack.json",
        "payload_sha256": payload_sha256(payload),
        "created_at": timestamp,
    }
    assert immutability_event_payload(event) == {
        "event_id": 7,
        "artifact_id": artifact_id,
        "task_id": task_id,
        "event_kind": "mutation_blocked",
        "mutation_operation": "UPDATE",
        "frozen_artifact_kind": "context_pack",
        "attempted_artifact_kind": "context_pack",
        "frozen_storage_path": "storage/context_pack.json",
        "attempted_storage_path": "storage/context_pack.json",
        "frozen_payload_sha256": "frozen",
        "attempted_payload_sha256": "attempted",
        "details": {"reason": "immutable"},
        "created_at": timestamp,
    }


def test_operator_run_summary_preserves_legacy_shape() -> None:
    task_id = uuid4()
    operator_run_id = uuid4()
    parent_operator_run_id = uuid4()
    search_request_id = uuid4()
    timestamp = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)

    row = KnowledgeOperatorRun(
        id=operator_run_id,
        parent_operator_run_id=parent_operator_run_id,
        operator_kind="retrieve",
        operator_name="hybrid_search",
        operator_version="v1",
        status="completed",
        agent_task_id=task_id,
        search_request_id=search_request_id,
        config_sha256="config",
        input_sha256="input",
        output_sha256="output",
        metrics_json={"latency_ms": 12},
        created_at=timestamp,
    )

    assert operator_run_summary(row) == {
        "operator_run_id": operator_run_id,
        "parent_operator_run_id": parent_operator_run_id,
        "operator_kind": "retrieve",
        "operator_name": "hybrid_search",
        "operator_version": "v1",
        "status": "completed",
        "agent_task_id": task_id,
        "search_request_id": search_request_id,
        "config_sha256": "config",
        "input_sha256": "input",
        "output_sha256": "output",
        "metrics": {"latency_ms": 12},
        "created_at": timestamp,
    }
