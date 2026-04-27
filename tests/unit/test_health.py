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


def test_architecture_inspection_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.system.get_architecture_inspection_report",
        lambda: {
            "schema_name": "architecture_inspection",
            "valid": True,
            "violation_count": 0,
            "measurement": {"non_ignored_violation_count": 0},
        },
    )
    client = TestClient(app)

    response = client.get("/architecture/inspection")

    assert response.status_code == 200
    assert response.json()["schema_name"] == "architecture_inspection"
    assert response.json()["valid"] is True


def test_architecture_measurement_summary_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.system.summarize_architecture_measurements",
        lambda: {
            "schema_name": "architecture_measurement_summary",
            "record_count": 1,
            "latest_rule_violation_counts": {"architecture-contract-map-drift": 0},
            "latest_contract_violation_counts": {"architecture_contract_map": 0},
            "deltas": {"rule_violation_counts": {"architecture-contract-map-drift": 0}},
        },
    )
    client = TestClient(app)

    response = client.get("/architecture/measurements/summary")

    assert response.status_code == 200
    assert response.json()["schema_name"] == "architecture_measurement_summary"
    assert response.json()["record_count"] == 1


def test_architecture_measurement_summary_endpoint_uses_structured_errors(
    monkeypatch,
) -> None:
    def raise_invalid_history() -> dict:
        raise ValueError("invalid measurement history")

    monkeypatch.setattr(
        "app.api.routers.system.summarize_architecture_measurements",
        raise_invalid_history,
    )
    client = TestClient(app)

    response = client.get("/architecture/measurements/summary")

    assert response.status_code == 500
    assert response.json()["error_code"] == "architecture_measurement_history_invalid"


def test_architecture_endpoints_require_remote_system_read_capability(monkeypatch) -> None:
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
    monkeypatch.setattr(
        "app.api.routers.system.get_architecture_inspection_report",
        lambda: (_ for _ in ()).throw(
            AssertionError("capability gate should block architecture inspection")
        ),
    )
    client = TestClient(app)

    response = client.get("/architecture/inspection", headers={"X-API-Key": "secret"})

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


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
