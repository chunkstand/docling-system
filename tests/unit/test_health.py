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
            "schema_version": "1.0",
            "valid": True,
            "violation_count": 0,
            "violations": [],
            "measurement": {"non_ignored_violation_count": 0},
            "architecture_map": {"schema_name": "architecture_contract_map"},
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
            "schema_version": "1.0",
            "history_schema_name": "architecture_measurement_history",
            "history_path": "/tmp/history.jsonl",
            "record_count": 1,
            "current_commit_sha": "current",
            "latest_recorded_commit_sha": "current",
            "latest_recorded_at": "2026-04-26T00:00:00+00:00",
            "is_current": True,
            "recording_required": False,
            "latest": {"commit_sha": "current"},
            "previous": None,
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
    assert response.json()["is_current"] is True
    assert response.json()["recording_required"] is False


def test_architecture_inspection_endpoint_uses_structured_errors(
    monkeypatch,
) -> None:
    def raise_failed_inspection() -> dict:
        raise ValueError("inspection failed")

    monkeypatch.setattr(
        "app.api.routers.system.get_architecture_inspection_report",
        raise_failed_inspection,
    )
    client = TestClient(app)

    response = client.get("/architecture/inspection")

    assert response.status_code == 500
    assert response.json()["error_code"] == "architecture_inspection_failed"


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


def test_architecture_summary_endpoint_requires_remote_system_read_capability(
    monkeypatch,
) -> None:
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
        "app.api.routers.system.summarize_architecture_measurements",
        lambda: (_ for _ in ()).throw(
            AssertionError("capability gate should block architecture summary")
        ),
    )
    client = TestClient(app)

    response = client.get(
        "/architecture/measurements/summary",
        headers={"X-API-Key": "secret"},
    )

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
