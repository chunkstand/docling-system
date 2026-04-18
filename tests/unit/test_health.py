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

    response = client.get("/runtime/status")

    assert response.status_code == 200
    assert response.json()["startup_code_fingerprint"] == "startup-1"
    assert response.json()["desired_code_fingerprint"] == "startup-1"
    assert response.json()["is_current"] is True
    assert response.json()["api_mode"] == "remote"
    assert response.json()["api_mode_explicit"] is True
