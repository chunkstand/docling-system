import json

from fastapi.testclient import TestClient

from app.api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_status_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.system.get_runtime_status",
        lambda process_identity=None: {
            "process_identity": process_identity,
            "startup_code_fingerprint": "startup-1",
            "desired_code_fingerprint": "startup-1",
            "is_current": True,
            "registered_process": {"pid": 123},
            "updated_at": "2026-04-18T00:00:00Z",
        },
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
                "api_key": "secret",
                "remote_api_capabilities": "system:read",
            },
        )(),
    )
    client = TestClient(app)

    unauthorized = client.get("/runtime/status")
    response = client.get("/runtime/status", headers={"X-API-Key": "secret"})

    assert unauthorized.status_code == 401
    assert unauthorized.json()["error_code"] == "auth_required"
    assert response.status_code == 200
    assert response.json()["startup_code_fingerprint"] == "startup-1"
    assert response.json()["desired_code_fingerprint"] == "startup-1"
    assert response.json()["is_current"] is True
    assert response.json()["api_mode"] == "remote"
    assert response.json()["api_mode_explicit"] is True


def test_runtime_status_endpoint_requires_remote_read_capability(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "api_mode": "remote",
                "api_host": "0.0.0.0",
                "api_port": 8000,
                "api_key": "secret",
                "remote_api_capabilities": None,
            },
        )(),
    )
    client = TestClient(app)

    response = client.get("/runtime/status", headers={"X-API-Key": "secret"})

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_runtime_status_endpoint_exposes_actor_scoped_auth_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.system.get_runtime_status",
        lambda process_identity=None: {
            "process_identity": process_identity,
            "startup_code_fingerprint": "startup-1",
            "desired_code_fingerprint": "startup-1",
            "is_current": True,
            "registered_process": {"pid": 123},
            "updated_at": "2026-04-18T00:00:00Z",
        },
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
                "api_key": None,
                "api_credentials_json": json.dumps(
                    [
                        {
                            "actor": "observer",
                            "key": "observer-secret",
                            "capabilities": ["system:read", "documents:inspect"],
                        },
                        {
                            "actor": "operator",
                            "key": "operator-secret",
                            "capabilities": ["*"],
                        },
                    ]
                ),
                "remote_api_capabilities": None,
            },
        )(),
    )
    client = TestClient(app)

    response = client.get("/runtime/status", headers={"X-API-Key": "observer-secret"})

    assert response.status_code == 200
    assert response.json()["remote_api_auth_mode"] == "actor_scoped"
    assert response.json()["remote_api_principals"] == [
        {
            "actor": "observer",
            "capabilities": ["documents:inspect", "system:read"],
        },
        {
            "actor": "operator",
            "capabilities": ["*"],
        },
    ]
    assert "remote_api_capabilities" not in response.json()


def test_health_endpoint_remains_public_in_remote_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: type(
            "Settings",
            (),
            {"api_mode": "remote", "api_host": "0.0.0.0", "api_port": 8000, "api_key": "secret"},
        )(),
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
