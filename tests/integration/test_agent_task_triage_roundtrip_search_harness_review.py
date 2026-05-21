from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskAttempt,
    AgentTaskDependency,
    AgentTaskDependencyKind,
    AgentTaskStatus,
)
from app.schemas.agent_task_core import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task
from tests.integration.agent_task_triage_roundtrip_support import _create_processed_document

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_harness_draft_review_flow_roundtrip(postgres_integration_harness) -> None:
    _document_id, _run_id = _create_processed_document(postgres_integration_harness)
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
                workflow_version="milestone8_integration",
            ),
        )
        triage_task_id = triage_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == triage_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_harness_config_update",
                input={
                    "draft_harness_name": "wide_v2_review_integration",
                    "base_harness_name": "wide_v2",
                    "source_task_id": str(triage_task_id),
                    "rationale": "publish a review harness with a small reranker tweak",
                    "reranker_overrides": {"result_type_priority_bonus": 0.009},
                },
                workflow_version="milestone8_integration",
            ),
        )
        draft_task_id = draft_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == draft_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        assert draft_task_row.status == AgentTaskStatus.COMPLETED.value
        draft_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(
                draft_task_id
            )
        )
        draft_context_yaml_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_yaml_path(
                draft_task_id
            )
        )
        assert draft_context_path.exists()
        assert draft_context_yaml_path.exists()
        assert draft_task_row.result_json["payload"]["draft"]["draft_harness_name"] == (
            "wide_v2_review_integration"
        )
        draft_context_row = (
            session.execute(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == draft_task_id,
                    AgentTaskArtifact.artifact_kind == "context",
                )
            )
            .scalars()
            .one()
        )
        assert draft_context_row.storage_path == str(draft_context_path)
        draft_dependencies = (
            session.execute(
                select(AgentTaskDependency).where(AgentTaskDependency.task_id == draft_task_id)
            )
            .scalars()
            .all()
        )
        assert len(draft_dependencies) == 1
        assert draft_dependencies[0].depends_on_task_id == triage_task_id
        assert draft_dependencies[0].dependency_kind == AgentTaskDependencyKind.SOURCE_TASK.value
        draft_context_payload = json.loads(draft_context_path.read_text())
        assert draft_context_payload["summary"]["verification_state"] == "pending"
        assert draft_context_payload["refs"][0]["ref_key"] == "source_task"

        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_draft_harness_config",
                input={
                    "target_task_id": str(draft_task_id),
                    "baseline_harness_name": "wide_v2",
                    "source_types": ["evaluation_queries"],
                    "limit": 10,
                    "min_total_shared_query_count": 1,
                },
                workflow_version="milestone8_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == verify_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        assert verify_task_row.status == AgentTaskStatus.COMPLETED.value
        verify_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(
                verify_task_id
            )
        )
        assert verify_context_path.exists()
        verification = verify_task_row.result_json["payload"]["verification"]
        assert verification["outcome"] == "passed"
        verify_context_payload = json.loads(verify_context_path.read_text())
        assert verify_context_payload["summary"]["verification_state"] == "passed"
        assert {row["ref_key"] for row in verify_context_payload["refs"]} >= {
            "draft_task_output",
            "verification_record",
        }

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_harness_config_update",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "publish verified review harness",
                },
                workflow_version="milestone8_integration",
            ),
        )
        apply_task_id = apply_task.task_id

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        assert apply_task_row.status == AgentTaskStatus.AWAITING_APPROVAL.value
        assert claim_next_agent_task(session, "integration-agent-worker") is None

    with postgres_integration_harness.session_factory() as session:
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="operator@example.com",
                approval_note="publish the verified review harness",
            ),
        )

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == apply_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        assert apply_task_row.status == AgentTaskStatus.COMPLETED.value
        apply_payload = apply_task_row.result_json["payload"]
        assert apply_payload["draft_harness_name"] == "wide_v2_review_integration"
        assert Path(apply_payload["config_path"]).exists()
        assert apply_payload["follow_up_summary"]["schema_name"] == (
            "search_harness_follow_up_evidence"
        )
        assert apply_payload["follow_up_artifact_kind"] == "follow_up_evaluation_summary"
        apply_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(
                apply_task_id
            )
        )
        apply_context_yaml_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_yaml_path(
                apply_task_id
            )
        )
        assert apply_context_path.exists()
        assert apply_context_yaml_path.exists()
        apply_context_row = (
            session.execute(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == apply_task_id,
                    AgentTaskArtifact.artifact_kind == "context",
                )
            )
            .scalars()
            .one()
        )
        assert apply_context_row.storage_path == str(apply_context_path)
        apply_dependencies = (
            session.execute(
                select(AgentTaskDependency).where(AgentTaskDependency.task_id == apply_task_id)
            )
            .scalars()
            .all()
        )
        assert {row.dependency_kind for row in apply_dependencies} == {
            AgentTaskDependencyKind.DRAFT_TASK.value,
            AgentTaskDependencyKind.VERIFICATION_TASK.value,
        }
        apply_context_payload = json.loads(apply_context_path.read_text())
        assert apply_context_payload["summary"]["approval_state"] == "approved"
        assert apply_context_payload["summary"]["verification_state"] == "passed"
        assert {row["ref_key"] for row in apply_context_payload["refs"]} >= {
            "draft_task_output",
            "verification_task_output",
            "applied_artifact",
            "follow_up_evaluation_artifact",
        }
        apply_attempt = (
            session.execute(
                select(AgentTaskAttempt)
                .where(AgentTaskAttempt.task_id == apply_task_id)
                .order_by(AgentTaskAttempt.attempt_number.desc())
            )
            .scalars()
            .first()
        )
        assert apply_attempt is not None
        assert apply_attempt.cost_json["estimated_usd"] == 0.0
        assert apply_attempt.performance_json["execution_latency_ms"] is not None

    harnesses_response = client.get("/search/harnesses")
    assert harnesses_response.status_code == 200
    draft_context_response = client.get(f"/agent-tasks/{draft_task_id}/context")
    assert draft_context_response.status_code == 200
    assert draft_context_response.json()["task_type"] == "draft_harness_config_update"
    assert draft_context_response.json()["freshness_status"] == "fresh"
    draft_context_yaml_response = client.get(f"/agent-tasks/{draft_task_id}/context?format=yaml")
    assert draft_context_yaml_response.status_code == 200
    assert "agent_task_context" in draft_context_yaml_response.text
    draft_detail_response = client.get(f"/agent-tasks/{draft_task_id}")
    assert draft_detail_response.status_code == 200
    assert draft_detail_response.json()["dependency_edges"][0]["dependency_kind"] == "source_task"
    assert draft_detail_response.json()["context_freshness_status"] == "fresh"
    verify_context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert verify_context_response.status_code == 200
    verify_refs = {row["ref_key"]: row for row in verify_context_response.json()["refs"]}
    assert verify_refs["draft_task_output"]["freshness_status"] == "fresh"
    assert verify_refs["verification_record"]["freshness_status"] == "fresh"
    verify_detail_response = client.get(f"/agent-tasks/{verify_task_id}")
    assert verify_detail_response.status_code == 200
    assert verify_detail_response.json()["context_summary"]["verification_state"] == "passed"
    assert verify_detail_response.json()["context_refs"][0]["freshness_status"] == "fresh"
    apply_context_response = client.get(f"/agent-tasks/{apply_task_id}/context")
    assert apply_context_response.status_code == 200
    apply_context = apply_context_response.json()
    assert apply_context["summary"]["approval_state"] == "approved"
    assert apply_context["summary"]["verification_state"] == "passed"
    assert apply_context["summary"]["follow_up_status"] == "completed"
    apply_detail_response = client.get(f"/agent-tasks/{apply_task_id}")
    assert apply_detail_response.status_code == 200
    assert apply_detail_response.json()["context_summary"]["approval_state"] == "approved"
    assert apply_detail_response.json()["context_refs"][0]["freshness_status"] == "fresh"
    apply_artifact_id = apply_detail_response.json()["result"]["payload"]["artifact_id"]
    apply_artifact_response = client.get(
        f"/agent-tasks/{apply_task_id}/artifacts/{apply_artifact_id}"
    )
    assert apply_artifact_response.status_code == 200
    assert apply_artifact_response.json()["draft_harness_name"] == "wide_v2_review_integration"
    apply_export_response = client.get(
        "/agent-tasks/traces/export",
        params={
            "limit": 10,
            "workflow_version": "milestone8_integration",
            "task_type": "apply_harness_config_update",
        },
    )
    assert apply_export_response.status_code == 200
    assert apply_export_response.json()["traces"][0]["context_summary"]["approval_state"] == (
        "approved"
    )
    harness_row = next(
        row
        for row in harnesses_response.json()
        if row["harness_name"] == "wide_v2_review_integration"
    )
    assert harness_row["harness_config"]["base_harness_name"] == "wide_v2"
    assert harness_row["harness_config"]["metadata"]["override_type"] == (
        "applied_harness_config_update"
    )

    search_response = client.post(
        "/search",
        json={
            "query": "integration threshold",
            "mode": "keyword",
            "limit": 5,
            "harness_name": "wide_v2_review_integration",
        },
    )
    assert search_response.status_code == 200
    assert search_response.json()

    request_id = search_response.headers["X-Search-Request-Id"]
    detail_response = client.get(f"/search/requests/{request_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["harness_name"] == "wide_v2_review_integration"
    assert detail["harness_config"]["base_harness_name"] == "wide_v2"

    explanation_response = client.get(f"/search/requests/{request_id}/explain")
    assert explanation_response.status_code == 200
    explanation = explanation_response.json()
    assert explanation["schema_name"] == "search_request_explanation"
    assert explanation["harness_name"] == "wide_v2_review_integration"
    assert explanation["diagnosis"]["category"] in {
        "healthy",
        "low_recall",
        "bad_ranking",
        "fallback_only",
        "filter_overconstraint",
        "table_recall_gap",
        "metadata_bias",
        "unknown",
    }

    descriptor_response = client.get("/search/harnesses/wide_v2_review_integration/descriptor")
    assert descriptor_response.status_code == 200
    descriptor = descriptor_response.json()
    assert descriptor["schema_name"] == "search_harness_descriptor"
    assert descriptor["harness_name"] == "wide_v2_review_integration"
    assert descriptor["base_harness_name"] == "wide_v2"

    recommendation_summary_response = client.get(
        "/agent-tasks/analytics/recommendations?workflow_version=milestone8_integration"
    )
    assert recommendation_summary_response.status_code == 200
    recommendation_summary = recommendation_summary_response.json()
    assert recommendation_summary["recommendation_task_count"] >= 1
    assert recommendation_summary["draft_count"] >= 1
    assert recommendation_summary["passed_verification_count"] >= 1
    assert recommendation_summary["applied_count"] >= 1

    trends_response = client.get(
        "/agent-tasks/analytics/trends?workflow_version=milestone8_integration"
    )
    assert trends_response.status_code == 200
    assert trends_response.json()["series"]

    cost_summary_response = client.get(
        "/agent-tasks/analytics/costs?workflow_version=milestone8_integration"
    )
    assert cost_summary_response.status_code == 200
    assert cost_summary_response.json()["attempt_count"] >= 4

    performance_summary_response = client.get(
        "/agent-tasks/analytics/performance?workflow_version=milestone8_integration"
    )
    assert performance_summary_response.status_code == 200
    assert performance_summary_response.json()["median_execution_latency_ms"] is not None

    value_density_response = client.get("/agent-tasks/analytics/value-density")
    assert value_density_response.status_code == 200
    assert any(
        row["workflow_version"] == "milestone8_integration" for row in value_density_response.json()
    )

    decision_signals_response = client.get("/agent-tasks/analytics/decision-signals")
    assert decision_signals_response.status_code == 200
    assert any(
        row["workflow_version"] == "milestone8_integration"
        for row in decision_signals_response.json()
    )
