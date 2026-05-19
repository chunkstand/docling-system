from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_agent_task_routes_use_service_layer(monkeypatch) -> None:
    task_id = uuid4()
    verification_id = uuid4()
    outcome_id = uuid4()
    failure_path = "/tmp/agent_task_failure.json"

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.list_agent_tasks",
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
        "app.api.routers.agent_tasks.create_agent_task",
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
        "app.api.routers.agent_tasks.get_agent_task_detail",
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
            "failure_artifact_path": failure_path,
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
        "app.api.routers.agent_tasks.list_agent_task_outcomes",
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
        "app.api.routers.agent_tasks.create_agent_task_outcome",
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
        "app.api.routers.agent_tasks.get_agent_task_verifications",
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
        "app.api.routers.agent_tasks.approve_agent_task",
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
            "failure_artifact_path": failure_path,
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
        "app.api.routers.agent_tasks.reject_agent_task",
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

    verification_response = client.get(f"/agent-tasks/{task_id}/verifications")
    assert verification_response.status_code == 200
    assert verification_response.json()[0]["verification_id"] == str(verification_id)

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


def test_agent_task_list_route_accepts_repeated_status_query(monkeypatch) -> None:
    captured: dict = {}

    def fake_list_tasks(session, statuses=None, limit=50):
        captured["statuses"] = statuses
        captured["limit"] = limit
        return []

    monkeypatch.setattr("app.api.routers.agent_tasks.list_agent_tasks", fake_list_tasks)

    client = TestClient(app)
    response = client.get("/agent-tasks?status=queued&status=failed&limit=7")

    assert response.status_code == 200
    assert response.json() == []
    assert captured == {"statuses": ["queued", "failed"], "limit": 7}


def test_create_agent_task_route_returns_bad_request_on_unknown_task_type(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.agent_tasks.create_agent_task",
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
    body = response.json()
    assert body["error_code"] == "invalid_agent_task_input"
    assert body["error_context"]["validation_errors"][0]["loc"] == ["source_type"]
