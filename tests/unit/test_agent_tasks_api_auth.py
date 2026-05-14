from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app


def test_create_agent_task_route_requires_remote_capability(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.deps.get_settings",
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
        "app.api.routers.agent_tasks.create_agent_task",
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


def test_agent_task_list_route_requires_api_key_in_remote_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.agent_tasks.list_agent_tasks", lambda session, statuses=None, limit=50: []
    )
    monkeypatch.setattr(
        "app.api.deps.get_settings",
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
    monkeypatch.setattr(
        "app.api.routers.agent_tasks.list_agent_tasks", lambda session, statuses=None, limit=50: []
    )
    monkeypatch.setattr(
        "app.api.deps.get_settings",
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
