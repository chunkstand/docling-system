from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskStatus,
    AgentTaskVerification,
    Document,
    SearchHarnessEvaluation,
    SearchHarnessRelease,
)
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import create_agent_task
from tests.integration.agent_task_triage_roundtrip_support import _create_processed_document

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_triage_replay_regression_roundtrip(postgres_integration_harness) -> None:
    document_id, run_id = _create_processed_document(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        active_run_before = document.active_run_id
        latest_run_before = document.latest_run_id
        task_detail = create_agent_task(
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
                workflow_version="milestone5_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        assert task is not None
        assert task.status == AgentTaskStatus.COMPLETED.value
        assert task.side_effect_level == "read_only"
        assert task.requires_approval is False
        assert task.failure_artifact_path is None

        result_payload = task.result_json["payload"]
        assert result_payload["shadow_mode"] is True
        assert result_payload["triage_kind"] == "replay_regression"
        assert result_payload["candidate_harness_name"] == "wide_v2"
        assert result_payload["baseline_harness_name"] == "default_v1"
        assert result_payload["evaluation"]["total_shared_query_count"] >= 1
        assert result_payload["verification"]["outcome"] in {"passed", "failed"}
        assert result_payload["recommendation"]["next_action"]
        assert result_payload["artifact_kind"] == "triage_summary"
        assert result_payload["repair_case"]["schema_name"] == "search_harness_repair_case"
        assert result_payload["repair_case_artifact_kind"] == "repair_case"
        context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(task_id)
        )
        assert context_path.exists()
        context_payload = json.loads(context_path.read_text())
        assert (
            context_payload["summary"]["next_action"]
            == result_payload["recommendation"]["next_action"]
        )
        assert (
            context_payload["summary"]["metrics"]["confidence"]
            == result_payload["recommendation"]["confidence"]
        )
        assert {row["ref_key"] for row in context_payload["refs"]} >= {
            "triage_summary_artifact",
            "verification_record",
            "repair_case_artifact",
        }

        verification_rows = (
            session.execute(
                select(AgentTaskVerification).where(AgentTaskVerification.target_task_id == task_id)
            )
            .scalars()
            .all()
        )
        assert len(verification_rows) == 1
        verification = verification_rows[0]
        assert verification.verification_task_id == task_id
        assert verification.verifier_type == "shadow_mode_triage_gate"
        assert verification.outcome in {"passed", "failed"}

        artifact_rows = (
            session.execute(select(AgentTaskArtifact).where(AgentTaskArtifact.task_id == task_id))
            .scalars()
            .all()
        )
        assert {row.artifact_kind for row in artifact_rows} == {
            "triage_summary",
            "repair_case",
            "context",
        }
        artifact = next(row for row in artifact_rows if row.artifact_kind == "triage_summary")
        assert artifact.storage_path is not None
        artifact_path = Path(artifact.storage_path)
        assert artifact_path.exists()
        assert artifact_path.parent == (
            postgres_integration_harness.storage_service.storage_root / "agent_tasks" / str(task_id)
        )

        artifact_payload = json.loads(artifact_path.read_text())
        assert artifact_payload["shadow_mode"] is True
        assert artifact_payload["triage_kind"] == "replay_regression"
        assert artifact_payload["recommendation"] == result_payload["recommendation"]
        assert artifact_payload["evaluation"]["total_shared_query_count"] >= 1

        document = session.get(Document, document_id)
        assert document is not None
        assert document.active_run_id == active_run_before == run_id
        assert document.latest_run_id == latest_run_before == run_id

    client = postgres_integration_harness.client
    artifact_list_response = client.get(f"/agent-tasks/{task_id}/artifacts")
    assert artifact_list_response.status_code == 200
    assert {row["artifact_kind"] for row in artifact_list_response.json()} == {
        "triage_summary",
        "repair_case",
        "context",
    }
    artifact_id = next(
        row["artifact_id"]
        for row in artifact_list_response.json()
        if row["artifact_kind"] == "triage_summary"
    )

    artifact_detail_response = client.get(f"/agent-tasks/{task_id}/artifacts/{artifact_id}")
    assert artifact_detail_response.status_code == 200
    assert artifact_detail_response.json()["triage_kind"] == "replay_regression"

    context_response = client.get(f"/agent-tasks/{task_id}/context")
    assert context_response.status_code == 200
    assert context_response.json()["summary"]["next_action"] in {
        "candidate_ready_for_review",
        "keep_baseline_and_investigate",
        "investigate_unresolved_gaps",
        "collect_more_evidence",
        "no_change",
    }
    assert context_response.json()["freshness_status"] == "fresh"

    detail_response = client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert (
        detail_response.json()["context_summary"]["next_action"]
        == context_response.json()["summary"]["next_action"]
    )
    assert detail_response.json()["context_freshness_status"] == "fresh"

    verification_response = client.get(f"/agent-tasks/{task_id}/verifications")
    assert verification_response.status_code == 200
    assert len(verification_response.json()) == 1
    assert verification_response.json()[0]["verifier_type"] == "shadow_mode_triage_gate"


def test_evaluate_search_harness_context_roundtrip(postgres_integration_harness) -> None:
    _document_id, _run_id = _create_processed_document(postgres_integration_harness)
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_search_harness",
                input={
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "limit": 10,
                },
                workflow_version="milestone9_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        assert task is not None
        assert task.status == AgentTaskStatus.COMPLETED.value
        result_payload = task.result_json["payload"]
        evaluation_id = result_payload["evaluation"]["evaluation_id"]
        assert result_payload["evaluation"]["total_shared_query_count"] >= 1
        evaluation_row = session.get(SearchHarnessEvaluation, UUID(evaluation_id))
        assert evaluation_row is not None
        assert evaluation_row.status == "completed"
        context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(task_id)
        )
        assert context_path.exists()
        context_payload = json.loads(context_path.read_text())
        assert context_payload["summary"]["verification_state"] == "pending"
        assert context_payload["summary"]["metrics"]["total_shared_query_count"] >= 1
        assert {row["ref_key"] for row in context_payload["refs"]} >= {
            "search_harness_evaluation",
            "evaluation_queries_baseline_replay_run",
            "evaluation_queries_candidate_replay_run",
        }
        assert {row["ref_kind"] for row in context_payload["refs"]} == {
            "search_harness_evaluation",
            "replay_run",
        }

    action_catalog_response = client.get("/agent-tasks/actions")
    assert action_catalog_response.status_code == 200
    evaluate_action = next(
        row
        for row in action_catalog_response.json()
        if row["task_type"] == "evaluate_search_harness"
    )
    assert evaluate_action["output_schema_name"] == "evaluate_search_harness_output"

    context_response = client.get(f"/agent-tasks/{task_id}/context")
    assert context_response.status_code == 200
    context_json = context_response.json()
    assert context_json["summary"]["headline"].startswith("Evaluated wide_v2 against default_v1")
    assert context_json["refs"][0]["freshness_status"] == "fresh"

    evaluations_response = client.get("/search/harness-evaluations")
    assert evaluations_response.status_code == 200
    assert evaluations_response.json()[0]["evaluation_id"] == evaluation_id

    evaluation_response = client.get(f"/search/harness-evaluations/{evaluation_id}")
    assert evaluation_response.status_code == 200
    evaluation_json = evaluation_response.json()
    assert evaluation_json["evaluation_id"] == evaluation_id
    assert evaluation_json["sources"][0]["source_type"] == "evaluation_queries"

    detail_response = client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["context_summary"]["verification_state"] == "pending"

    export_response = client.get(
        "/agent-tasks/traces/export",
        params={
            "limit": 10,
            "workflow_version": "milestone9_integration",
            "task_type": "evaluate_search_harness",
        },
    )
    assert export_response.status_code == 200
    assert (
        export_response.json()["traces"][0]["context_summary"]["metrics"][
            "total_shared_query_count"
        ]
        >= 1
    )


def test_verify_search_harness_evaluation_context_roundtrip(postgres_integration_harness) -> None:
    _document_id, _run_id = _create_processed_document(postgres_integration_harness)
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        evaluate_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_search_harness",
                input={
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "limit": 10,
                },
                workflow_version="milestone10_integration",
            ),
        )
        evaluate_task_id = evaluate_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == evaluate_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_search_harness_evaluation",
                input={
                    "target_task_id": str(evaluate_task_id),
                    "max_total_regressed_count": 0,
                    "max_mrr_drop": 0.0,
                    "max_zero_result_count_increase": 0,
                    "max_foreign_top_result_count_increase": 0,
                    "min_total_shared_query_count": 1,
                },
                workflow_version="milestone10_integration",
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
        verify_context_payload = json.loads(verify_context_path.read_text())
        assert verify_context_payload["summary"]["verification_state"] in {"passed", "failed"}
        assert verify_context_payload["summary"]["metrics"]["max_total_regressed_count"] == 0
        assert verify_context_payload["output"]["release"]["release_package_sha256"]
        assert {row["ref_key"] for row in verify_context_payload["refs"]} >= {
            "target_task_output",
            "verification_record",
        }
        release_rows = (
            session.execute(
                select(SearchHarnessRelease)
                .where(SearchHarnessRelease.requested_by == f"agent_task:{verify_task_id}")
                .order_by(SearchHarnessRelease.created_at.desc())
            )
            .scalars()
            .all()
        )
        assert len(release_rows) == 1
        assert release_rows[0].search_harness_evaluation_id == UUID(
            verify_context_payload["output"]["evaluation"]["evaluation_id"]
        )

    context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert context_response.status_code == 200
    context_json = context_response.json()
    assert (
        context_json["output"]["verification"]["details"]["thresholds"]["max_total_regressed_count"]
        == 0
    )
    assert context_json["output"]["release"]["release_id"]
    assert context_json["output"]["verification"]["details"]["search_harness_release_id"] == (
        context_json["output"]["release"]["release_id"]
    )
    assert context_json["refs"][0]["ref_key"] == "target_task_output"

    detail_response = client.get(f"/agent-tasks/{verify_task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["context_summary"]["verification_state"] in {"passed", "failed"}
    assert detail_response.json()["context_refs"][0]["freshness_status"] == "fresh"

    export_response = client.get(
        "/agent-tasks/traces/export",
        params={
            "limit": 10,
            "workflow_version": "milestone10_integration",
            "task_type": "verify_search_harness_evaluation",
        },
    )
    assert export_response.status_code == 200
    export_trace = export_response.json()["traces"][0]
    assert export_trace["context_summary"]["metrics"]["max_total_regressed_count"] == 0
    assert export_trace["context_refs"][0]["ref_key"] == "target_task_output"


def test_triage_replay_regression_failure_writes_failure_artifact(
    postgres_integration_harness,
) -> None:
    with postgres_integration_harness.session_factory() as session:
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_replay_regression",
                input={
                    "candidate_harness_name": "does_not_exist",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "replay_limit": 10,
                    "quality_candidate_limit": 10,
                    "min_total_shared_query_count": 0,
                },
                workflow_version="milestone5_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        assert task is not None
        assert task.status == AgentTaskStatus.FAILED.value
        assert "Unknown search harness 'does_not_exist'" in (task.error_message or "")
        assert task.failure_artifact_path is not None

        failure_path = Path(task.failure_artifact_path)
        assert failure_path.exists()
        assert failure_path.parent == (
            postgres_integration_harness.storage_service.storage_root / "agent_tasks" / str(task_id)
        )

        failure_payload = json.loads(failure_path.read_text())
        assert failure_payload["task_id"] == str(task_id)
        assert failure_payload["task_type"] == "triage_replay_regression"
        assert failure_payload["failure_type"] == "ValueError"
        assert failure_payload["failure_stage"] == "execute"
        assert "Unknown search harness 'does_not_exist'" in failure_payload["error_message"]

    failure_response = postgres_integration_harness.client.get(
        f"/agent-tasks/{task_id}/failure-artifact"
    )
    assert failure_response.status_code == 200
    assert failure_response.json()["failure_type"] == "ValueError"
