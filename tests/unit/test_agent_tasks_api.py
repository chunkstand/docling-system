from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


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
                "input_example": {},
            }
        ],
    )

    client = TestClient(app)
    response = client.get("/agent-tasks/actions")

    assert response.status_code == 200
    assert response.json()[0]["task_type"] == "evaluate_search_harness"


def test_agent_task_routes_use_service_layer(monkeypatch) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    verification_id = uuid4()
    failure_path = "/tmp/agent-task-failure.json"

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
            "artifact_count": 0,
            "attempt_count": 0,
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
            "failure_artifact_path": failure_path,
            "attempts": 0,
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "next_attempt_at": None,
            "approved_at": None,
            "approved_by": None,
            "approval_note": None,
            "artifact_count": 0,
            "attempt_count": 0,
            "verification_count": 1,
            "artifacts": [],
            "verifications": [],
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
            "failure_artifact_path": failure_path,
            "attempts": 0,
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "next_attempt_at": None,
            "approved_at": "2026-04-12T00:00:01Z",
            "approved_by": payload.approved_by,
            "approval_note": payload.approval_note,
            "artifact_count": 0,
            "attempt_count": 0,
            "verification_count": 0,
            "artifacts": [],
            "verifications": [],
        },
    )
    monkeypatch.setattr("app.api.main.Path.exists", lambda self: str(self) == failure_path)
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
    assert create_response.json()["task_type"] == "list_quality_eval_candidates"

    detail_response = client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["task_id"] == str(task_id)

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
    assert failure_response.json()["path"] == failure_path

    approve_response = client.post(
        f"/agent-tasks/{task_id}/approve",
        json={"approved_by": "operator@example.com", "approval_note": "ok"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["approved_by"] == "operator@example.com"


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


def test_create_agent_task_route_returns_bad_request_on_unknown_task_type(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.create_agent_task",
        lambda session, payload: (_ for _ in ()).throw(ValueError("Unknown agent task type")),
    )

    client = TestClient(app)
    response = client.post("/agent-tasks", json={"task_type": "unknown_task", "input": {}})

    assert response.status_code == 400
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
