from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.core.time import coerce_utc_datetime, utcnow
from app.db.session import get_engine
from app.services import runtime

RuntimeStatusReader = Callable[[str | None], dict[str, Any]]
RuntimeRegistryReader = Callable[[], dict[str, Any]]
Probe = Callable[[], None]
NowReader = Callable[[], Any]

DEFAULT_HEARTBEAT_PROCESS_KINDS = ("api", "worker", "agent_worker")


@dataclass(frozen=True, slots=True)
class RuntimeHealthCheckResult:
    name: str
    healthy: bool
    critical: bool
    detail: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RuntimeHealthReport:
    status: str
    checked_at: str
    checks: tuple[RuntimeHealthCheckResult, ...]

    def critical_failures(self) -> tuple[str, ...]:
        return tuple(
            check.name for check in self.checks if check.critical and not check.healthy
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "critical_failures": list(self.critical_failures()),
            "checks": [check.model_dump() for check in self.checks],
        }


@dataclass(frozen=True, slots=True)
class RuntimePublicHealthResponse:
    status: str
    status_code: int

    def model_dump(self) -> dict[str, str]:
        return {"status": self.status}


def probe_database_connectivity() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


def probe_storage_root_availability() -> None:
    storage_root = get_settings().storage_root
    if not storage_root.exists():
        raise RuntimeError(f"storage root does not exist: {storage_root}")
    if not storage_root.is_dir():
        raise RuntimeError(f"storage root is not a directory: {storage_root}")
    if not os.access(storage_root, os.R_OK | os.W_OK):
        raise RuntimeError(f"storage root is not readable and writable: {storage_root}")


def _runtime_currentness_check(
    *,
    runtime_status_reader: RuntimeStatusReader,
) -> RuntimeHealthCheckResult:
    status = runtime_status_reader(None)
    if status.get("is_current") is True:
        return RuntimeHealthCheckResult(
            name="runtime_currentness",
            healthy=True,
            critical=True,
        )
    return RuntimeHealthCheckResult(
        name="runtime_currentness",
        healthy=False,
        critical=True,
        detail="startup code fingerprint is stale against the desired fingerprint",
    )


def _runtime_registry_check(
    *,
    runtime_registry_reader: RuntimeRegistryReader,
) -> RuntimeHealthCheckResult:
    payload = runtime_registry_reader()
    if not payload:
        return RuntimeHealthCheckResult(
            name="runtime_registry",
            healthy=True,
            critical=True,
            detail="runtime registry has not been initialized yet",
        )

    updated_at = coerce_utc_datetime(payload.get("updated_at"))
    if payload.get("updated_at") is not None and updated_at is None:
        return RuntimeHealthCheckResult(
            name="runtime_registry",
            healthy=False,
            critical=True,
            detail="runtime registry updated_at is invalid",
        )
    if payload.get("processes") and not payload.get("desired_code_fingerprint"):
        return RuntimeHealthCheckResult(
            name="runtime_registry",
            healthy=False,
            critical=True,
            detail="runtime registry is missing desired_code_fingerprint",
        )
    return RuntimeHealthCheckResult(
        name="runtime_registry",
        healthy=True,
        critical=True,
    )


def _probe_check(
    name: str,
    *,
    probe: Probe,
    critical: bool,
) -> RuntimeHealthCheckResult:
    try:
        probe()
    except Exception as exc:  # pragma: no cover - exercised through callers
        return RuntimeHealthCheckResult(
            name=name,
            healthy=False,
            critical=critical,
            detail=str(exc),
        )
    return RuntimeHealthCheckResult(name=name, healthy=True, critical=critical)


def _process_heartbeat_check(
    *,
    runtime_registry_reader: RuntimeRegistryReader,
    now_reader: NowReader,
    required_process_kinds: Sequence[str],
    heartbeat_ttl_seconds: int,
) -> RuntimeHealthCheckResult:
    payload = runtime_registry_reader()
    processes = payload.get("processes") if isinstance(payload.get("processes"), dict) else {}
    now = coerce_utc_datetime(now_reader())
    if now is None:
        return RuntimeHealthCheckResult(
            name="process_heartbeat_freshness",
            healthy=False,
            critical=True,
            detail="current time is invalid",
        )

    failures: list[str] = []
    desired_code_fingerprint = payload.get("desired_code_fingerprint")
    for process_kind in required_process_kinds:
        matches = [
            entry
            for entry in processes.values()
            if isinstance(entry, dict) and entry.get("process_kind") == process_kind
        ]
        if not matches:
            failures.append(f"{process_kind}:missing")
            continue

        fresh_matches: list[dict[str, Any]] = []
        for entry in matches:
            heartbeat_at = coerce_utc_datetime(entry.get("heartbeat_at"))
            if heartbeat_at is None:
                continue
            age_seconds = (now - heartbeat_at).total_seconds()
            if age_seconds <= heartbeat_ttl_seconds:
                fresh_matches.append(entry)
        if not fresh_matches:
            failures.append(f"{process_kind}:stale")
            continue
        fresh_fingerprints = [
            str(fingerprint)
            for fingerprint in (
                entry.get("startup_code_fingerprint") for entry in fresh_matches
            )
            if fingerprint
        ]
        if (
            desired_code_fingerprint
            and fresh_fingerprints
            and desired_code_fingerprint not in set(fresh_fingerprints)
        ):
            failures.append(f"{process_kind}:stale_code")

    if failures:
        return RuntimeHealthCheckResult(
            name="process_heartbeat_freshness",
            healthy=False,
            critical=True,
            detail=", ".join(failures),
        )
    return RuntimeHealthCheckResult(
        name="process_heartbeat_freshness",
        healthy=True,
        critical=True,
    )


def build_runtime_health_report(
    *,
    runtime_status_reader: RuntimeStatusReader = runtime.get_runtime_status,
    runtime_registry_reader: RuntimeRegistryReader = runtime.get_runtime_registry,
    database_probe: Probe = probe_database_connectivity,
    storage_probe: Probe = probe_storage_root_availability,
    now_reader: NowReader = utcnow,
    include_process_heartbeat_check: bool = False,
    required_process_kinds: Sequence[str] = DEFAULT_HEARTBEAT_PROCESS_KINDS,
    heartbeat_ttl_seconds: int | None = None,
) -> RuntimeHealthReport:
    ttl_seconds = heartbeat_ttl_seconds or max(get_settings().worker_heartbeat_seconds * 2, 1)
    checks = [
        _runtime_currentness_check(runtime_status_reader=runtime_status_reader),
        _runtime_registry_check(runtime_registry_reader=runtime_registry_reader),
        _probe_check("database_connectivity", probe=database_probe, critical=True),
        _probe_check("storage_root_availability", probe=storage_probe, critical=True),
    ]
    if include_process_heartbeat_check:
        checks.append(
            _process_heartbeat_check(
                runtime_registry_reader=runtime_registry_reader,
                now_reader=now_reader,
                required_process_kinds=required_process_kinds,
                heartbeat_ttl_seconds=ttl_seconds,
            )
        )
    status = "ok" if all(check.healthy or not check.critical for check in checks) else "error"
    return RuntimeHealthReport(
        status=status,
        checked_at=utcnow().isoformat(),
        checks=tuple(checks),
    )


def get_runtime_diagnostics(
    *,
    process_identity: str | None = None,
    runtime_status_reader: RuntimeStatusReader = runtime.get_runtime_status,
    runtime_registry_reader: RuntimeRegistryReader = runtime.get_runtime_registry,
    database_probe: Probe = probe_database_connectivity,
    storage_probe: Probe = probe_storage_root_availability,
    now_reader: NowReader = utcnow,
    required_process_kinds: Sequence[str] = DEFAULT_HEARTBEAT_PROCESS_KINDS,
    heartbeat_ttl_seconds: int | None = None,
) -> dict[str, Any]:
    payload = runtime_status_reader(process_identity)
    report = build_runtime_health_report(
        runtime_status_reader=runtime_status_reader,
        runtime_registry_reader=runtime_registry_reader,
        database_probe=database_probe,
        storage_probe=storage_probe,
        now_reader=now_reader,
        include_process_heartbeat_check=True,
        required_process_kinds=required_process_kinds,
        heartbeat_ttl_seconds=heartbeat_ttl_seconds,
    )
    return {
        **payload,
        "health": report.model_dump(),
    }


def get_public_health(
    *,
    runtime_status_reader: RuntimeStatusReader = runtime.get_runtime_status,
    runtime_registry_reader: RuntimeRegistryReader = runtime.get_runtime_registry,
    database_probe: Probe = probe_database_connectivity,
    storage_probe: Probe = probe_storage_root_availability,
) -> RuntimePublicHealthResponse:
    report = build_runtime_health_report(
        runtime_status_reader=runtime_status_reader,
        runtime_registry_reader=runtime_registry_reader,
        database_probe=database_probe,
        storage_probe=storage_probe,
        include_process_heartbeat_check=False,
    )
    if report.status == "ok":
        return RuntimePublicHealthResponse(status="ok", status_code=200)
    return RuntimePublicHealthResponse(status="error", status_code=503)
