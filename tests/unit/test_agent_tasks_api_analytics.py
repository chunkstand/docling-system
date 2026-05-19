from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_agent_task_analytics_routes_use_service_layer(monkeypatch) -> None:
    task_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_analytics_summary",
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
        "app.api.routers.agent_tasks.get_agent_task_trends",
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
        "app.api.routers.agent_tasks.get_agent_verification_trends",
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
        "app.api.routers.agent_tasks.get_agent_approval_trends",
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
        "app.api.routers.agent_tasks.get_agent_task_recommendation_summary",
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
        "app.api.routers.agent_tasks.get_agent_task_recommendation_trends",
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
        "app.api.routers.agent_tasks.get_agent_task_cost_summary",
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
        "app.api.routers.agent_tasks.get_agent_task_cost_trends",
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
        "app.api.routers.agent_tasks.get_agent_task_performance_summary",
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
        "app.api.routers.agent_tasks.get_agent_task_performance_trends",
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
        "app.api.routers.agent_tasks.get_agent_task_value_density",
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
        "app.api.routers.agent_tasks.get_agent_task_decision_signals",
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
        "app.api.routers.agent_tasks.list_agent_task_workflow_summaries",
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
        "app.api.routers.agent_tasks.export_agent_task_traces",
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

    client = TestClient(app)

    summary_response = client.get("/agent-tasks/analytics/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["task_count"] == 4

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
