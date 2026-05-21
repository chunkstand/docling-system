from __future__ import annotations

import json
import os
from uuid import UUID

import pytest

from app.db.public.agent_tasks import AgentTask, AgentTaskStatus
from app.db.public.ingest import Document
from app.schemas.agent_task_core import (
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskRejectionRequest,
)
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task, reject_agent_task
from tests.integration.agent_task_triage_roundtrip_support import _create_processed_document

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_enqueue_document_reprocess_requires_approval_before_queuing_new_run(
    postgres_integration_harness,
) -> None:
    document_id, original_run_id = _create_processed_document(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "reason": "shadow-mode triage recommended a fresh parse",
                },
                workflow_version="milestone6_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        document = session.get(Document, document_id)
        assert task is not None
        assert document is not None
        assert task.status == AgentTaskStatus.AWAITING_APPROVAL.value
        assert task.side_effect_level == "promotable"
        assert task.requires_approval is True
        assert task.approved_at is None
        assert document.active_run_id == original_run_id
        assert document.latest_run_id == original_run_id
        assert claim_next_agent_task(session, "integration-agent-worker") is None

    with postgres_integration_harness.session_factory() as session:
        approved_task = approve_agent_task(
            session,
            task_id,
            AgentTaskApprovalRequest(
                approved_by="operator@example.com",
                approval_note="approved for milestone-6 integration coverage",
            ),
        )
        assert approved_task.status == AgentTaskStatus.QUEUED.value
        assert approved_task.approved_by == "operator@example.com"

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        document = session.get(Document, document_id)
        assert task is not None
        assert document is not None
        assert task.status == AgentTaskStatus.COMPLETED.value
        assert task.approved_by == "operator@example.com"
        assert task.approved_at is not None
        assert task.result_json["payload"]["document_id"] == str(document_id)
        assert (
            task.result_json["payload"]["reason"] == "shadow-mode triage recommended a fresh parse"
        )
        reprocess_payload = task.result_json["payload"]["reprocess"]
        assert reprocess_payload["document_id"] == str(document_id)
        assert reprocess_payload["status"] == "queued"
        assert reprocess_payload["run_id"] is not None

        new_run_id = UUID(reprocess_payload["run_id"])
        assert new_run_id != original_run_id
        assert document.active_run_id == original_run_id
        assert document.latest_run_id == new_run_id
        reprocess_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(task_id)
        )
        assert reprocess_context_path.exists()
        reprocess_context_payload = json.loads(reprocess_context_path.read_text())
        assert reprocess_context_payload["output"]["document_id"] == str(document_id)

    detail_response = postgres_integration_harness.client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["approved_by"] == "operator@example.com"
    assert detail_response.json()["context_summary"]["headline"] == (
        "enqueue_document_reprocess produced typed output."
    )
    context_response = postgres_integration_harness.client.get(f"/agent-tasks/{task_id}/context")
    assert context_response.status_code == 200
    assert context_response.json()["output"]["document_id"] == str(document_id)


def test_rejected_enqueue_document_reprocess_never_queues_new_run(
    postgres_integration_harness,
) -> None:
    document_id, original_run_id = _create_processed_document(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "reason": "operator rejected this promotion request",
                },
                workflow_version="milestone6_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        rejected_task = reject_agent_task(
            session,
            task_id,
            AgentTaskRejectionRequest(
                rejected_by="reviewer@example.com",
                rejection_note="not enough evidence for reprocess",
            ),
        )
        assert rejected_task.status == AgentTaskStatus.REJECTED.value

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        document = session.get(Document, document_id)
        assert task is not None
        assert document is not None
        assert task.status == AgentTaskStatus.REJECTED.value
        assert task.rejected_by == "reviewer@example.com"
        assert task.rejected_at is not None
        assert task.completed_at is not None
        assert task.approved_at is None
        assert claim_next_agent_task(session, "integration-agent-worker") is None
        assert document.active_run_id == original_run_id
        assert document.latest_run_id == original_run_id

    detail_response = postgres_integration_harness.client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "rejected"
    assert detail_response.json()["rejected_by"] == "reviewer@example.com"


def test_agent_task_learning_surfaces_roundtrip(postgres_integration_harness) -> None:
    document_id, _run_id = _create_processed_document(postgres_integration_harness)
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        triage_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_replay_regression",
                input={
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "replay_limit": 10,
                    "quality_candidate_limit": 10,
                    "min_total_shared_query_count": 1,
                },
                workflow_version="milestone7_integration",
            ),
        )
        triage_task_id = triage_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == triage_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        reprocess_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "source_task_id": str(triage_task_id),
                    "reason": "learning-surface integration coverage",
                },
                workflow_version="milestone7_integration",
            ),
        )
        reprocess_task_id = reprocess_task.task_id
        reject_agent_task(
            session,
            reprocess_task_id,
            AgentTaskRejectionRequest(
                rejected_by="reviewer@example.com",
                rejection_note="not enough evidence for promotion",
            ),
        )

    useful_outcome_response = client.post(
        f"/agent-tasks/{triage_task_id}/outcomes",
        json={
            "outcome_label": "useful",
            "created_by": "operator@example.com",
            "note": "shadow-mode recommendation was helpful",
        },
    )
    assert useful_outcome_response.status_code == 200
    assert useful_outcome_response.json()["outcome_label"] == "useful"

    correct_outcome_response = client.post(
        f"/agent-tasks/{reprocess_task_id}/outcomes",
        json={
            "outcome_label": "correct",
            "created_by": "reviewer@example.com",
            "note": "rejection was the right call",
        },
    )
    assert correct_outcome_response.status_code == 200
    assert correct_outcome_response.json()["outcome_label"] == "correct"

    duplicate_outcome_response = client.post(
        f"/agent-tasks/{triage_task_id}/outcomes",
        json={
            "outcome_label": "useful",
            "created_by": "operator@example.com",
            "note": "attempted duplicate label",
        },
    )
    assert duplicate_outcome_response.status_code == 409
    assert "already been recorded" in duplicate_outcome_response.json()["detail"]

    outcome_list_response = client.get(f"/agent-tasks/{triage_task_id}/outcomes")
    assert outcome_list_response.status_code == 200
    assert outcome_list_response.json()[0]["outcome_label"] == "useful"

    analytics_response = client.get("/agent-tasks/analytics/summary")
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["task_count"] == 2
    assert analytics["completed_count"] == 1
    assert analytics["rejected_count"] == 1
    assert analytics["labeled_task_count"] == 2
    assert analytics["outcome_label_counts"]["useful"] == 1
    assert analytics["outcome_label_counts"]["correct"] == 1
    assert analytics["verification_outcome_counts"]

    workflow_response = client.get("/agent-tasks/analytics/workflow-versions")
    assert workflow_response.status_code == 200
    workflow_row = next(
        row
        for row in workflow_response.json()
        if row["workflow_version"] == "milestone7_integration"
    )
    assert workflow_row["task_count"] == 2
    assert workflow_row["labeled_task_count"] == 2
    assert workflow_row["outcome_label_counts"]["useful"] == 1

    export_response = client.get(
        "/agent-tasks/traces/export?workflow_version=milestone7_integration&limit=10"
    )
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["export_count"] == 2
    assert export_payload["workflow_version"] == "milestone7_integration"
    traced_task_ids = {row["task_id"] for row in export_payload["traces"]}
    assert traced_task_ids == {str(triage_task_id), str(reprocess_task_id)}
    assert all("outcomes" in row for row in export_payload["traces"])
