from fastapi.testclient import TestClient

from app.api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_status_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_runtime_status",
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
        "app.api.main.get_settings",
        lambda: type(
            "Settings",
            (),
            {"api_mode": "remote", "api_host": "0.0.0.0", "api_port": 8000, "api_key": "secret"},
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


def test_health_endpoint_remains_public_in_remote_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
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
