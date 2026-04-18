from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.services.storage import StorageService


def test_agent_task_actions_route_lists_supported_actions(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.list_agent_task_action_definitions",
        lambda: [
            {
                "task_type": "evaluate_search_harness",
                "description": "Compare harnesses.",
                "side_effect_level": "read_only",
                "requires_approval": False,
                "input_schema": {},
                "output_schema_name": "evaluate_search_harness_output",
                "output_schema_version": "1.0",
                "output_schema": {"title": "EvaluateSearchHarnessOutput"},
                "input_example": {},
            }
        ],
    )

    client = TestClient(app)
    response = client.get("/agent-tasks/actions")

    assert response.status_code == 200
    assert response.json()[0]["task_type"] == "evaluate_search_harness"
    assert response.json()[0]["output_schema_name"] == "evaluate_search_harness_output"


def test_agent_task_actions_route_exposes_output_schema_metadata_for_all_migrated_tasks() -> None:
    client = TestClient(app)
    response = client.get("/agent-tasks/actions")

    assert response.status_code == 200
    definitions = {row["task_type"]: row for row in response.json()}
    for task_type in [
        "get_latest_evaluation",
        "list_quality_eval_candidates",
        "replay_search_request",
        "run_search_replay_suite",
        "evaluate_search_harness",
        "verify_search_harness_evaluation",
        "draft_harness_config_update",
        "verify_draft_harness_config",
        "triage_replay_regression",
        "enqueue_document_reprocess",
        "apply_harness_config_update",
    ]:
        assert definitions[task_type]["output_schema_name"] is not None
        assert definitions[task_type]["output_schema_version"] == "1.0"
        assert definitions[task_type]["output_schema"]


def test_agent_task_routes_use_service_layer(monkeypatch, tmp_path: Path) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    verification_id = uuid4()
    outcome_id = uuid4()
    storage_service = StorageService(storage_root=tmp_path / "storage")
    failure_path = storage_service.get_agent_task_failure_artifact_path(task_id)
    failure_path.write_text('{"error":"failed"}')

    monkeypatch.setattr(
        "app.api.main.list_agent_tasks",
        lambda session, statuses=None, limit=50: [
            {
                "task_id": str(task_id),
                "task_type": "list_quality_eval_candidates",
                "status": "queued",
                "priority": 100,
                "side_effect_level": "read_only",
                "requires_approval": False,
                "parent_task_id": None,
                "workflow_version": "v1",
                "tool_version": None,
                "prompt_version": None,
                "model": None,
                "created_at": "2026-04-12T00:00:00Z",
                "updated_at": "2026-04-12T00:00:00Z",
                "started_at": None,
                "completed_at": None,
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.create_agent_task",
        lambda session, payload: {
            "task_id": str(task_id),
            "task_type": payload.task_type,
            "status": "queued",
            "priority": payload.priority,
            "side_effect_level": payload.side_effect_level or "read_only",
            "requires_approval": (
                payload.requires_approval if payload.requires_approval is not None else False
            ),
            "parent_task_id": None,
            "workflow_version": payload.workflow_version,
            "tool_version": payload.tool_version,
            "prompt_version": payload.prompt_version,
            "model": payload.model,
            "created_at": "2026-04-12T00:00:00Z",
            "updated_at": "2026-04-12T00:00:00Z",
            "started_at": None,
            "completed_at": None,
            "dependency_task_ids": [],
            "input": payload.input,
            "result": {},
            "model_settings": payload.model_settings,
            "error_message": None,
            "failure_artifact_path": None,
            "attempts": 0,
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "next_attempt_at": None,
            "approved_at": None,
            "approved_by": None,
            "approval_note": None,
            "rejected_at": None,
            "rejected_by": None,
            "rejection_note": None,
            "artifact_count": 0,
            "attempt_count": 0,
            "verification_count": 0,
            "outcome_count": 0,
            "artifacts": [],
            "verifications": [],
            "outcomes": [],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_analytics_summary",
        lambda session: {
            "task_count": 4,
            "completed_count": 2,
            "failed_count": 0,
            "rejected_count": 1,
            "awaiting_approval_count": 1,
            "processing_count": 0,
            "approval_required_count": 2,
            "approved_task_count": 1,
            "rejected_task_count": 1,
            "labeled_task_count": 1,
            "outcome_label_counts": {"useful": 1},
            "verification_outcome_counts": {"passed": 1},
            "avg_terminal_duration_seconds": 12.5,
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: {
            "bucket": bucket,
            "task_type": task_type,
            "workflow_version": workflow_version,
            "series": [
                {
                    "bucket_start": "2026-04-12T00:00:00Z",
                    "task_type": task_type,
                    "workflow_version": workflow_version,
                    "created_count": 1,
                    "completed_count": 1,
                    "failed_count": 0,
                    "rejected_count": 0,
                    "awaiting_approval_count": 0,
                    "median_queue_latency_ms": 5.0,
                    "p95_queue_latency_ms": 5.0,
                    "median_execution_latency_ms": 10.0,
                    "p95_execution_latency_ms": 10.0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_verification_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: {
            "bucket": bucket,
            "task_type": task_type,
            "workflow_version": workflow_version,
            "series": [
                {
                    "bucket_start": "2026-04-12T00:00:00Z",
                    "task_type": task_type,
                    "workflow_version": workflow_version,
                    "passed_count": 1,
                    "failed_count": 0,
                    "error_count": 0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_approval_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: {
            "bucket": bucket,
            "task_type": task_type,
            "workflow_version": workflow_version,
            "series": [
                {
                    "bucket_start": "2026-04-12T00:00:00Z",
                    "task_type": task_type,
                    "workflow_version": workflow_version,
                    "approval_count": 1,
                    "rejection_count": 0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_recommendation_summary",
        lambda session, task_type=None, workflow_version=None: {
            "task_type": task_type,
            "workflow_version": workflow_version,
            "recommendation_task_count": 1,
            "draft_count": 1,
            "verified_draft_count": 1,
            "passed_verification_count": 1,
            "approved_apply_count": 1,
            "rejected_apply_count": 0,
            "applied_count": 1,
            "useful_label_count": 1,
            "correct_label_count": 1,
            "downstream_improved_count": 1,
            "downstream_regressed_count": 0,
            "triage_to_draft_rate": 1.0,
            "verification_pass_rate": 1.0,
            "apply_rate": 1.0,
            "downstream_improvement_rate": 1.0,
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_recommendation_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: {
            "bucket": bucket,
            "task_type": task_type,
            "workflow_version": workflow_version,
            "series": [
                {
                    "bucket_start": "2026-04-12T00:00:00Z",
                    "task_type": task_type,
                    "workflow_version": workflow_version,
                    "recommendation_task_count": 1,
                    "draft_count": 1,
                    "applied_count": 1,
                    "downstream_improved_count": 1,
                    "downstream_regressed_count": 0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_cost_summary",
        lambda session, task_type=None, workflow_version=None: {
            "task_type": task_type,
            "workflow_version": workflow_version,
            "attempt_count": 1,
            "instrumented_attempt_count": 1,
            "estimated_usd_total": 0.0,
            "model_call_count": 1,
            "embedding_count": 0,
            "replay_query_count": 12,
            "evaluation_query_count": 0,
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_cost_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: {
            "bucket": bucket,
            "task_type": task_type,
            "workflow_version": workflow_version,
            "series": [
                {
                    "bucket_start": "2026-04-12T00:00:00Z",
                    "task_type": task_type,
                    "workflow_version": workflow_version,
                    "attempt_count": 1,
                    "estimated_usd_total": 0.0,
                    "replay_query_count": 12,
                    "evaluation_query_count": 0,
                    "embedding_count": 0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_performance_summary",
        lambda session, task_type=None, workflow_version=None: {
            "task_type": task_type,
            "workflow_version": workflow_version,
            "attempt_count": 1,
            "instrumented_attempt_count": 1,
            "median_queue_latency_ms": 5.0,
            "p95_queue_latency_ms": 5.0,
            "median_execution_latency_ms": 10.0,
            "p95_execution_latency_ms": 10.0,
            "median_end_to_end_latency_ms": 15.0,
            "p95_end_to_end_latency_ms": 15.0,
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_performance_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: {
            "bucket": bucket,
            "task_type": task_type,
            "workflow_version": workflow_version,
            "series": [
                {
                    "bucket_start": "2026-04-12T00:00:00Z",
                    "task_type": task_type,
                    "workflow_version": workflow_version,
                    "attempt_count": 1,
                    "median_queue_latency_ms": 5.0,
                    "p95_queue_latency_ms": 5.0,
                    "median_execution_latency_ms": 10.0,
                    "p95_execution_latency_ms": 10.0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_value_density",
        lambda session: [
            {
                "task_type": "triage_replay_regression",
                "workflow_version": "v1",
                "recommendation_task_count": 1,
                "downstream_improved_count": 1,
                "estimated_usd_total": 0.0,
                "median_end_to_end_latency_ms": 15.0,
                "useful_recommendation_rate": 1.0,
                "downstream_improvement_rate": 1.0,
                "improvements_per_dollar": None,
                "improvements_per_hour": 240.0,
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_decision_signals",
        lambda session: [
            {
                "task_type": "triage_replay_regression",
                "workflow_version": "v1",
                "status": "healthy",
                "reason": "Recommendation quality and latency are within current thresholds.",
                "threshold_crossed": "none",
                "recommended_action": "Continue collecting outcome labels and replay evidence.",
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.list_agent_task_workflow_summaries",
        lambda session: [
            {
                "workflow_version": "v1",
                "task_count": 4,
                "completed_count": 2,
                "failed_count": 0,
                "rejected_count": 1,
                "approved_task_count": 1,
                "rejected_task_count": 1,
                "labeled_task_count": 1,
                "outcome_label_counts": {"useful": 1},
                "verification_outcome_counts": {"passed": 1},
                "avg_terminal_duration_seconds": 12.5,
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.export_agent_task_traces",
        lambda session, limit=50, workflow_version=None, task_type=None: {
            "export_count": 1,
            "workflow_version": workflow_version,
            "task_type": task_type,
            "traces": [
                {
                    "task_id": str(task_id),
                    "task_type": "triage_replay_regression",
                    "status": "completed",
                    "priority": 100,
                    "side_effect_level": "read_only",
                    "requires_approval": False,
                    "parent_task_id": None,
                    "workflow_version": "v1",
                    "tool_version": None,
                    "prompt_version": None,
                    "model": None,
                    "created_at": "2026-04-12T00:00:00Z",
                    "updated_at": "2026-04-12T00:00:00Z",
                    "started_at": None,
                    "completed_at": None,
                    "dependency_task_ids": [],
                    "input": {},
                    "result": {},
                    "model_settings": {},
                    "error_message": None,
                    "failure_artifact_path": None,
                    "attempts": 1,
                    "locked_at": None,
                    "locked_by": None,
                    "last_heartbeat_at": None,
                    "next_attempt_at": None,
                    "approved_at": None,
                    "approved_by": None,
                    "approval_note": None,
                    "rejected_at": None,
                    "rejected_by": None,
                    "rejection_note": None,
                    "artifact_count": 0,
                    "attempt_count": 1,
                    "verification_count": 0,
                    "outcome_count": 1,
                    "artifacts": [],
                    "verifications": [],
                    "outcomes": [],
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_detail",
        lambda session, incoming_task_id: {
            "task_id": str(incoming_task_id),
            "task_type": "list_quality_eval_candidates",
            "status": "queued",
            "priority": 100,
            "side_effect_level": "read_only",
            "requires_approval": False,
            "parent_task_id": None,
            "workflow_version": "v1",
            "tool_version": None,
            "prompt_version": None,
            "model": None,
            "created_at": "2026-04-12T00:00:00Z",
            "updated_at": "2026-04-12T00:00:00Z",
            "started_at": None,
            "completed_at": None,
            "dependency_task_ids": [],
            "input": {"limit": 12},
            "result": {},
            "model_settings": {},
            "error_message": None,
            "failure_artifact_path": str(failure_path),
            "attempts": 0,
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "next_attempt_at": None,
            "approved_at": None,
            "approved_by": None,
            "approval_note": None,
            "rejected_at": None,
            "rejected_by": None,
            "rejection_note": None,
            "artifact_count": 0,
            "attempt_count": 0,
            "verification_count": 1,
            "outcome_count": 1,
            "artifacts": [],
            "verifications": [],
            "outcomes": [],
        },
    )
    monkeypatch.setattr(
        "app.api.main.list_agent_task_outcomes",
        lambda session, incoming_task_id, limit=20: [
            {
                "outcome_id": str(outcome_id),
                "task_id": str(incoming_task_id),
                "outcome_label": "useful",
                "created_by": "operator@example.com",
                "note": "accurate recommendation",
                "created_at": "2026-04-12T00:03:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.create_agent_task_outcome",
        lambda session, incoming_task_id, payload: {
            "outcome_id": str(outcome_id),
            "task_id": str(incoming_task_id),
            "outcome_label": payload.outcome_label,
            "created_by": payload.created_by,
            "note": payload.note,
            "created_at": "2026-04-12T00:03:00Z",
        },
    )
    monkeypatch.setattr(
        "app.api.main.list_agent_task_artifacts",
        lambda session, incoming_task_id, limit=20: [
            {
                "artifact_id": str(artifact_id),
                "task_id": str(incoming_task_id),
                "attempt_id": None,
                "artifact_kind": "triage_summary",
                "storage_path": "/tmp/triage_summary.json",
                "payload": {"shadow_mode": True},
                "created_at": "2026-04-12T00:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.get_agent_task_artifact",
        lambda session, incoming_task_id, incoming_artifact_id: type(
            "ArtifactRow",
            (),
            {
                "id": incoming_artifact_id,
                "task_id": incoming_task_id,
                "storage_path": None,
                "payload_json": {"shadow_mode": True, "triage_kind": "replay_regression"},
            },
        )(),
    )
    monkeypatch.setattr("app.api.main.get_storage_service", lambda: storage_service)
    monkeypatch.setattr(
        "app.api.main.get_agent_task_verifications",
        lambda session, incoming_task_id, limit=20: [
            {
                "verification_id": str(verification_id),
                "target_task_id": str(incoming_task_id),
                "verification_task_id": None,
                "verifier_type": "search_harness_evaluation_gate",
                "outcome": "passed",
                "metrics": {"total_regressed_count": 0},
                "reasons": [],
                "details": {},
                "created_at": "2026-04-12T00:00:00Z",
                "completed_at": "2026-04-12T00:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.main.approve_agent_task",
        lambda session, incoming_task_id, payload: {
            "task_id": str(incoming_task_id),
            "task_type": "evaluate_search_harness",
            "status": "queued",
            "priority": 100,
            "side_effect_level": "promotable",
            "requires_approval": True,
            "parent_task_id": None,
            "workflow_version": "v1",
            "tool_version": None,
            "prompt_version": None,
            "model": None,
            "created_at": "2026-04-12T00:00:00Z",
            "updated_at": "2026-04-12T00:00:01Z",
            "started_at": None,
            "completed_at": None,
            "dependency_task_ids": [],
            "input": {},
            "result": {},
            "model_settings": {},
            "error_message": None,
            "failure_artifact_path": str(failure_path),
            "attempts": 0,
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "next_attempt_at": None,
            "approved_at": "2026-04-12T00:00:01Z",
            "approved_by": payload.approved_by,
            "approval_note": payload.approval_note,
            "rejected_at": None,
            "rejected_by": None,
            "rejection_note": None,
            "artifact_count": 0,
            "attempt_count": 0,
            "verification_count": 0,
            "outcome_count": 0,
            "artifacts": [],
            "verifications": [],
            "outcomes": [],
        },
    )
    monkeypatch.setattr(
        "app.api.main.reject_agent_task",
        lambda session, incoming_task_id, payload: {
            "task_id": str(incoming_task_id),
            "task_type": "enqueue_document_reprocess",
            "status": "rejected",
            "priority": 100,
            "side_effect_level": "promotable",
            "requires_approval": True,
            "parent_task_id": None,
            "workflow_version": "v1",
            "tool_version": None,
            "prompt_version": None,
            "model": None,
            "created_at": "2026-04-12T00:00:00Z",
            "updated_at": "2026-04-12T00:00:02Z",
            "started_at": None,
            "completed_at": "2026-04-12T00:00:02Z",
            "dependency_task_ids": [],
            "input": {},
            "result": {},
            "model_settings": {},
            "error_message": None,
            "failure_artifact_path": None,
            "attempts": 0,
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "next_attempt_at": None,
            "approved_at": None,
            "approved_by": None,
            "approval_note": None,
            "rejected_at": "2026-04-12T00:00:02Z",
            "rejected_by": payload.rejected_by,
            "rejection_note": payload.rejection_note,
            "artifact_count": 0,
            "attempt_count": 0,
            "verification_count": 0,
            "artifacts": [],
            "verifications": [],
        },
    )
    monkeypatch.setattr(
        "app.api.main.FileResponse",
        lambda path, media_type=None: {"path": str(path), "media_type": media_type},
    )

    client = TestClient(app)

    list_response = client.get("/agent-tasks")
    assert list_response.status_code == 200
    assert list_response.json()[0]["task_id"] == str(task_id)

    create_response = client.post(
        "/agent-tasks",
        json={
            "task_type": "list_quality_eval_candidates",
            "input": {"limit": 12},
        },
    )
    assert create_response.status_code == 201
    assert create_response.headers["Location"] == f"/agent-tasks/{task_id}"
    assert create_response.json()["task_type"] == "list_quality_eval_candidates"

    analytics_response = client.get("/agent-tasks/analytics/summary")
    assert analytics_response.status_code == 200
    assert analytics_response.json()["task_count"] == 4

    trends_response = client.get(
        "/agent-tasks/analytics/trends?bucket=week&task_type=triage_replay_regression"
    )
    assert trends_response.status_code == 200
    assert trends_response.json()["bucket"] == "week"
    assert trends_response.json()["series"][0]["created_count"] == 1

    verification_trends_response = client.get("/agent-tasks/analytics/verifications")
    assert verification_trends_response.status_code == 200
    assert verification_trends_response.json()["series"][0]["passed_count"] == 1

    approval_trends_response = client.get("/agent-tasks/analytics/approvals")
    assert approval_trends_response.status_code == 200
    assert approval_trends_response.json()["series"][0]["approval_count"] == 1

    recommendation_summary_response = client.get("/agent-tasks/analytics/recommendations")
    assert recommendation_summary_response.status_code == 200
    assert recommendation_summary_response.json()["downstream_improved_count"] == 1

    recommendation_trends_response = client.get("/agent-tasks/analytics/recommendations/trends")
    assert recommendation_trends_response.status_code == 200
    assert recommendation_trends_response.json()["series"][0]["applied_count"] == 1

    cost_summary_response = client.get("/agent-tasks/analytics/costs")
    assert cost_summary_response.status_code == 200
    assert cost_summary_response.json()["replay_query_count"] == 12

    cost_trends_response = client.get("/agent-tasks/analytics/costs/trends")
    assert cost_trends_response.status_code == 200
    assert cost_trends_response.json()["series"][0]["attempt_count"] == 1

    performance_summary_response = client.get("/agent-tasks/analytics/performance")
    assert performance_summary_response.status_code == 200
    assert performance_summary_response.json()["median_execution_latency_ms"] == 10.0

    performance_trends_response = client.get("/agent-tasks/analytics/performance/trends")
    assert performance_trends_response.status_code == 200
    assert performance_trends_response.json()["series"][0]["p95_execution_latency_ms"] == 10.0

    value_density_response = client.get("/agent-tasks/analytics/value-density")
    assert value_density_response.status_code == 200
    assert value_density_response.json()[0]["task_type"] == "triage_replay_regression"

    decision_signals_response = client.get("/agent-tasks/analytics/decision-signals")
    assert decision_signals_response.status_code == 200
    assert decision_signals_response.json()[0]["status"] == "healthy"

    workflow_response = client.get("/agent-tasks/analytics/workflow-versions")
    assert workflow_response.status_code == 200
    assert workflow_response.json()[0]["workflow_version"] == "v1"

    export_response = client.get("/agent-tasks/traces/export?limit=10&workflow_version=v1")
    assert export_response.status_code == 200
    assert export_response.json()["export_count"] == 1

    detail_response = client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["task_id"] == str(task_id)
    assert "dependency_edges" in detail_response.json()
    assert "context_summary" in detail_response.json()
    assert "context_refs" in detail_response.json()

    outcomes_response = client.get(f"/agent-tasks/{task_id}/outcomes")
    assert outcomes_response.status_code == 200
    assert outcomes_response.json()[0]["outcome_id"] == str(outcome_id)

    create_outcome_response = client.post(
        f"/agent-tasks/{task_id}/outcomes",
        json={
            "outcome_label": "useful",
            "created_by": "operator@example.com",
            "note": "accurate recommendation",
        },
    )
    assert create_outcome_response.status_code == 200
    assert create_outcome_response.json()["outcome_label"] == "useful"

    artifact_response = client.get(f"/agent-tasks/{task_id}/artifacts")
    assert artifact_response.status_code == 200
    assert artifact_response.json()[0]["artifact_id"] == str(artifact_id)

    artifact_detail_response = client.get(f"/agent-tasks/{task_id}/artifacts/{artifact_id}")
    assert artifact_detail_response.status_code == 200
    assert artifact_detail_response.json()["triage_kind"] == "replay_regression"

    verification_response = client.get(f"/agent-tasks/{task_id}/verifications")
    assert verification_response.status_code == 200
    assert verification_response.json()[0]["verification_id"] == str(verification_id)

    failure_response = client.get(f"/agent-tasks/{task_id}/failure-artifact")
    assert failure_response.status_code == 200
    assert failure_response.json()["path"] == str(failure_path)

    approve_response = client.post(
        f"/agent-tasks/{task_id}/approve",
        json={"approved_by": "operator@example.com", "approval_note": "ok"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["approved_by"] == "operator@example.com"

    reject_response = client.post(
        f"/agent-tasks/{task_id}/reject",
        json={"rejected_by": "reviewer@example.com", "rejection_note": "not enough evidence"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"
    assert reject_response.json()["rejected_by"] == "reviewer@example.com"


def test_agent_task_context_route_supports_json_and_yaml(monkeypatch) -> None:
    task_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.get_agent_task_context",
        lambda session, incoming_task_id: {
            "task_id": str(incoming_task_id),
            "task_type": "draft_harness_config_update",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": "2026-04-15T00:00:00Z",
            "task_updated_at": "2026-04-15T00:00:00Z",
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "output_schema_name": "draft_harness_config_update_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Draft ready"},
            "refs": [
                {
                    "ref_key": "draft_task_output",
                    "ref_kind": "task_output",
                    "task_id": str(incoming_task_id),
                    "freshness_status": "fresh",
                }
            ],
            "output": {"artifact_kind": "harness_config_draft"},
        },
    )

    client = TestClient(app)

    json_response = client.get(f"/agent-tasks/{task_id}/context")
    assert json_response.status_code == 200
    assert json_response.json()["task_type"] == "draft_harness_config_update"
    assert json_response.json()["freshness_status"] == "fresh"
    assert json_response.json()["refs"][0]["freshness_status"] == "fresh"

    yaml_response = client.get(f"/agent-tasks/{task_id}/context?format=yaml")
    assert yaml_response.status_code == 200
    assert "agent_task_context" in yaml_response.text


def test_agent_task_failure_artifact_route_returns_404_when_missing(monkeypatch) -> None:
    task_id = uuid4()
    monkeypatch.setattr(
        "app.api.main.get_agent_task_detail",
        lambda session, incoming_task_id: {
            "task_id": str(incoming_task_id),
            "task_type": "triage_replay_regression",
            "status": "failed",
            "priority": 100,
            "side_effect_level": "read_only",
            "requires_approval": False,
            "parent_task_id": None,
            "workflow_version": "v1",
            "tool_version": None,
            "prompt_version": None,
            "model": None,
            "created_at": "2026-04-12T00:00:00Z",
            "updated_at": "2026-04-12T00:00:00Z",
            "started_at": None,
            "completed_at": None,
            "dependency_task_ids": [],
            "input": {},
            "result": {},
            "model_settings": {},
            "error_message": "failed",
            "failure_artifact_path": None,
            "attempts": 1,
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "next_attempt_at": None,
            "approved_at": None,
            "approved_by": None,
            "approval_note": None,
            "artifact_count": 0,
            "attempt_count": 1,
            "verification_count": 0,
            "artifacts": [],
            "verifications": [],
        },
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/failure-artifact")

    assert response.status_code == 404


def test_agent_task_artifact_route_does_not_serve_paths_outside_storage_root(
    monkeypatch, tmp_path: Path
) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    storage_service = StorageService(storage_root=tmp_path / "storage")
    outside_path = tmp_path / "outside.json"
    outside_path.write_text('{"should":"not-serve"}')

    monkeypatch.setattr("app.api.main.get_storage_service", lambda: storage_service)
    monkeypatch.setattr(
        "app.api.main.get_agent_task_artifact",
        lambda session, incoming_task_id, incoming_artifact_id: type(
            "ArtifactRow",
            (),
            {
                "id": incoming_artifact_id,
                "task_id": incoming_task_id,
                "storage_path": str(outside_path),
                "payload_json": {"fallback": True},
            },
        )(),
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/artifacts/{artifact_id}")

    assert response.status_code == 200
    assert response.json() == {"fallback": True}


def test_create_agent_task_route_returns_bad_request_on_unknown_task_type(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.create_agent_task",
        lambda session, payload: (_ for _ in ()).throw(ValueError("Unknown agent task type")),
    )

    client = TestClient(app)
    response = client.post("/agent-tasks", json={"task_type": "unknown_task", "input": {}})

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_agent_task_request"
    assert "Unknown agent task type" in response.json()["detail"]


def test_create_agent_task_route_returns_422_on_invalid_inner_payload() -> None:
    client = TestClient(app)
    response = client.post(
        "/agent-tasks",
        json={
            "task_type": "run_search_replay_suite",
            "input": {},
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["source_type"]


def test_create_agent_task_route_requires_remote_capability(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "api_mode": "remote",
                "api_host": "0.0.0.0",
                "api_port": 8000,
                "api_key": "operator-secret",
                "remote_api_capabilities": None,
            },
        )(),
    )
    monkeypatch.setattr(
        "app.api.main.create_agent_task",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("remote capability gate should block before agent task creation runs")
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/agent-tasks",
        json={"task_type": "list_quality_eval_candidates", "input": {"limit": 1}},
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_agent_task_context_route_returns_machine_readable_error_code_for_bad_format(
    monkeypatch,
) -> None:
    task_id = uuid4()
    monkeypatch.setattr(
        "app.api.main.get_agent_task_context",
        lambda session, requested_task_id: {"summary": {}, "refs": []},
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/context?format=xml")

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_context_format"


def test_agent_task_list_route_requires_api_key_in_remote_mode(monkeypatch) -> None:
    monkeypatch.setattr("app.api.main.list_agent_tasks", lambda session, statuses=None, limit=50: [])
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "api_mode": "remote",
                "api_host": "0.0.0.0",
                "api_port": 8000,
                "api_key": "operator-secret",
                "remote_api_capabilities": None,
            },
        )(),
    )

    client = TestClient(app)
    unauthorized = client.get("/agent-tasks")
    forbidden = client.get("/agent-tasks", headers={"X-API-Key": "operator-secret"})

    assert unauthorized.status_code == 401
    assert unauthorized.json()["error_code"] == "auth_required"
    assert forbidden.status_code == 403
    assert forbidden.json()["error_code"] == "capability_not_allowed"


def test_agent_task_list_route_allows_remote_read_capability(monkeypatch) -> None:
    monkeypatch.setattr("app.api.main.list_agent_tasks", lambda session, statuses=None, limit=50: [])
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "api_mode": "remote",
                "api_host": "0.0.0.0",
                "api_port": 8000,
                "api_key": "operator-secret",
                "remote_api_capabilities": "agent_tasks:read",
            },
        )(),
    )

    client = TestClient(app)
    response = client.get("/agent-tasks", headers={"X-API-Key": "operator-secret"})

    assert response.status_code == 200
    assert response.json() == []
