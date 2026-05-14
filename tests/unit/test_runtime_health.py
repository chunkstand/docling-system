from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.runtime_health import (
    build_runtime_health_report,
    get_public_health,
    get_runtime_diagnostics,
)


def _runtime_status(*, is_current: bool = True) -> dict[str, object]:
    return {
        "process_identity": None,
        "startup_code_fingerprint": "startup-1",
        "desired_code_fingerprint": "startup-1" if is_current else "startup-2",
        "is_current": is_current,
        "registered_process": None,
        "updated_at": "2026-05-14T21:00:00+00:00",
    }


def _registry() -> dict[str, object]:
    return {
        "desired_code_fingerprint": "startup-1",
        "updated_at": "2026-05-14T21:00:00+00:00",
        "processes": {},
    }


def test_runtime_health_report_passes_when_critical_checks_are_healthy() -> None:
    report = build_runtime_health_report(
        runtime_status_reader=lambda _process_identity=None: _runtime_status(),
        runtime_registry_reader=_registry,
        database_probe=lambda: None,
        storage_probe=lambda: None,
    )

    assert report.status == "ok"
    assert report.critical_failures() == ()
    assert [check.name for check in report.checks] == [
        "runtime_currentness",
        "runtime_registry",
        "database_connectivity",
        "storage_root_availability",
    ]


def test_runtime_health_report_fails_when_runtime_code_is_stale() -> None:
    report = build_runtime_health_report(
        runtime_status_reader=lambda _process_identity=None: _runtime_status(is_current=False),
        runtime_registry_reader=_registry,
        database_probe=lambda: None,
        storage_probe=lambda: None,
    )

    assert report.status == "error"
    assert "runtime_currentness" in report.critical_failures()


def test_runtime_health_report_fails_when_database_probe_errors() -> None:
    report = build_runtime_health_report(
        runtime_status_reader=lambda _process_identity=None: _runtime_status(),
        runtime_registry_reader=_registry,
        database_probe=lambda: (_ for _ in ()).throw(RuntimeError("db down")),
        storage_probe=lambda: None,
    )

    assert report.status == "error"
    assert "database_connectivity" in report.critical_failures()


def test_runtime_health_report_can_enforce_process_heartbeat_freshness() -> None:
    now = datetime(2026, 5, 14, 21, 0, tzinfo=UTC)
    fresh = (now - timedelta(seconds=10)).isoformat()
    stale = (now - timedelta(seconds=90)).isoformat()
    registry = {
        "desired_code_fingerprint": "startup-1",
        "updated_at": now.isoformat(),
        "processes": {
            "api-1": {"process_kind": "api", "heartbeat_at": fresh},
            "worker-1": {"process_kind": "worker", "heartbeat_at": stale},
            "agent-worker-1": {"process_kind": "agent_worker", "heartbeat_at": fresh},
        },
    }

    report = build_runtime_health_report(
        runtime_status_reader=lambda _process_identity=None: _runtime_status(),
        runtime_registry_reader=lambda: registry,
        database_probe=lambda: None,
        storage_probe=lambda: None,
        now_reader=lambda: now,
        include_process_heartbeat_check=True,
        heartbeat_ttl_seconds=60,
    )

    assert report.status == "error"
    assert "process_heartbeat_freshness" in report.critical_failures()
    heartbeat_check = next(
        check for check in report.checks if check.name == "process_heartbeat_freshness"
    )
    assert heartbeat_check.detail == "worker:stale"


def test_runtime_health_report_fails_when_fresh_process_is_on_stale_code() -> None:
    now = datetime(2026, 5, 14, 21, 0, tzinfo=UTC)
    fresh = (now - timedelta(seconds=10)).isoformat()
    registry = {
        "desired_code_fingerprint": "startup-2",
        "updated_at": now.isoformat(),
        "processes": {
            "worker-1": {
                "process_kind": "worker",
                "startup_code_fingerprint": "startup-1",
                "heartbeat_at": fresh,
            }
        },
    }

    report = build_runtime_health_report(
        runtime_status_reader=lambda _process_identity=None: _runtime_status(),
        runtime_registry_reader=lambda: registry,
        database_probe=lambda: None,
        storage_probe=lambda: None,
        now_reader=lambda: now,
        include_process_heartbeat_check=True,
        required_process_kinds=("worker",),
        heartbeat_ttl_seconds=60,
    )

    assert report.status == "error"
    heartbeat_check = next(
        check for check in report.checks if check.name == "process_heartbeat_freshness"
    )
    assert heartbeat_check.detail == "worker:stale_code"


def test_runtime_diagnostics_include_nested_health_report() -> None:
    payload = get_runtime_diagnostics(
        process_identity="api-1",
        runtime_status_reader=lambda process_identity=None: {
            **_runtime_status(),
            "process_identity": process_identity,
        },
        runtime_registry_reader=_registry,
        database_probe=lambda: None,
        storage_probe=lambda: None,
        required_process_kinds=("api",),
    )

    assert payload["process_identity"] == "api-1"
    assert payload["health"]["status"] == "error"
    assert payload["health"]["critical_failures"] == ["process_heartbeat_freshness"]


def test_public_health_response_is_bounded_on_failure() -> None:
    response = get_public_health(
        runtime_status_reader=lambda _process_identity=None: _runtime_status(is_current=False),
        runtime_registry_reader=_registry,
        database_probe=lambda: None,
        storage_probe=lambda: None,
    )

    assert response.status_code == 503
    assert response.model_dump() == {"status": "error"}
