from __future__ import annotations

import fcntl
import hashlib
import json
import os
import socket
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.time import utcnow

_RUNTIME_SOURCE_SUFFIXES = {".py", ".toml", ".yaml", ".yml"}
_RUNTIME_SOURCE_DIRS = ("app", "config")
_RUNTIME_SOURCE_FILES = ("pyproject.toml",)
logger = get_logger(__name__)
_ACTIVE_HEARTBEATS: dict[str, dict[str, Any]] = {}
_ACTIVE_HEARTBEATS_LOCK = threading.Lock()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _runtime_dir() -> Path:
    path = get_settings().storage_root / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _runtime_registry_path() -> Path:
    return _runtime_dir() / "process_registry.json"


def _runtime_lock_path() -> Path:
    return _runtime_dir() / "process_registry.lock"


def get_process_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _iter_runtime_source_paths() -> list[Path]:
    root = _repo_root()
    paths: list[Path] = []
    for directory_name in _RUNTIME_SOURCE_DIRS:
        directory_path = root / directory_name
        if not directory_path.exists():
            continue
        for candidate in directory_path.rglob("*"):
            if not candidate.is_file():
                continue
            if "__pycache__" in candidate.parts:
                continue
            if candidate.suffix.lower() not in _RUNTIME_SOURCE_SUFFIXES:
                continue
            paths.append(candidate)
    for filename in _RUNTIME_SOURCE_FILES:
        candidate = root / filename
        if candidate.is_file():
            paths.append(candidate)
    return sorted(set(paths), key=lambda path: str(path))


@lru_cache(maxsize=1)
def get_startup_code_fingerprint() -> str:
    root = _repo_root()
    digest = hashlib.sha256()
    for path in _iter_runtime_source_paths():
        relative = path.relative_to(root)
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as source_file:
            while chunk := source_file.read(1024 * 1024):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _read_runtime_registry_unlocked(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_runtime_registry_unlocked(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _with_runtime_registry_lock() -> Any:
    lock_path = _runtime_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = lock_path.open("a+")
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    return lock_handle


@dataclass(frozen=True)
class RuntimeProcessRegistration:
    process_kind: str
    process_identity: str
    pid: int
    startup_code_fingerprint: str
    desired_code_fingerprint: str
    registered_at: str
    heartbeat_at: str

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


def _write_runtime_process_entry(
    payload: dict[str, Any],
    *,
    process_kind: str,
    process_identity: str,
    pid: int,
    startup_code_fingerprint: str,
    desired_code_fingerprint: str,
    registered_at: str,
    heartbeat_at: str,
) -> dict[str, Any]:
    payload["desired_code_fingerprint"] = desired_code_fingerprint
    payload["updated_at"] = heartbeat_at
    processes = payload.setdefault("processes", {})
    existing = processes.get(process_identity, {})
    if not isinstance(existing, dict):
        existing = {}

    entry = {
        **existing,
        "process_kind": process_kind,
        "pid": pid,
        "startup_code_fingerprint": startup_code_fingerprint,
        "registered_at": existing.get("registered_at") or registered_at,
        "heartbeat_at": heartbeat_at,
    }
    processes[process_identity] = entry
    return entry


def register_runtime_process(
    process_kind: str,
    process_identity: str,
    *,
    pid: int | None = None,
) -> RuntimeProcessRegistration:
    registry_path = _runtime_registry_path()
    startup_code_fingerprint = get_startup_code_fingerprint()
    registered_at = utcnow().isoformat()
    process_pid = pid or os.getpid()

    lock_handle = _with_runtime_registry_lock()
    try:
        payload = _read_runtime_registry_unlocked(registry_path)
        _write_runtime_process_entry(
            payload,
            process_kind=process_kind,
            process_identity=process_identity,
            pid=process_pid,
            startup_code_fingerprint=startup_code_fingerprint,
            desired_code_fingerprint=startup_code_fingerprint,
            registered_at=registered_at,
            heartbeat_at=registered_at,
        )
        _write_runtime_registry_unlocked(registry_path, payload)
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()

    return RuntimeProcessRegistration(
        process_kind=process_kind,
        process_identity=process_identity,
        pid=process_pid,
        startup_code_fingerprint=startup_code_fingerprint,
        desired_code_fingerprint=startup_code_fingerprint,
        registered_at=registered_at,
        heartbeat_at=registered_at,
    )


def record_runtime_process_heartbeat(
    process_identity: str,
    *,
    process_kind: str | None = None,
    pid: int | None = None,
    startup_code_fingerprint: str | None = None,
) -> dict[str, Any]:
    registry_path = _runtime_registry_path()
    heartbeat_at = utcnow().isoformat()

    lock_handle = _with_runtime_registry_lock()
    try:
        payload = _read_runtime_registry_unlocked(registry_path)
        processes = payload.setdefault("processes", {})
        existing = processes.get(process_identity)
        if not isinstance(existing, dict):
            existing = {}

        resolved_process_kind = process_kind or existing.get("process_kind")
        if not resolved_process_kind:
            raise ValueError(f"Runtime process '{process_identity}' is not registered.")
        resolved_pid = pid or existing.get("pid") or os.getpid()
        resolved_startup_code_fingerprint = (
            startup_code_fingerprint
            or existing.get("startup_code_fingerprint")
            or get_startup_code_fingerprint()
        )
        desired_code_fingerprint = (
            payload.get("desired_code_fingerprint") or resolved_startup_code_fingerprint
        )
        entry = _write_runtime_process_entry(
            payload,
            process_kind=str(resolved_process_kind),
            process_identity=process_identity,
            pid=int(resolved_pid),
            startup_code_fingerprint=str(resolved_startup_code_fingerprint),
            desired_code_fingerprint=str(desired_code_fingerprint),
            registered_at=str(existing.get("registered_at") or heartbeat_at),
            heartbeat_at=heartbeat_at,
        )
        _write_runtime_registry_unlocked(registry_path, payload)
        return entry
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


def get_runtime_registry() -> dict[str, Any]:
    registry_path = _runtime_registry_path()

    lock_handle = _with_runtime_registry_lock()
    try:
        return _read_runtime_registry_unlocked(registry_path)
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


def get_runtime_status(process_identity: str | None = None) -> dict[str, Any]:
    startup_code_fingerprint = get_startup_code_fingerprint()
    payload = get_runtime_registry()

    desired_code_fingerprint = payload.get("desired_code_fingerprint")
    processes = payload.get("processes") if isinstance(payload.get("processes"), dict) else {}
    process_entry = processes.get(process_identity) if process_identity is not None else None
    return {
        "process_identity": process_identity,
        "startup_code_fingerprint": startup_code_fingerprint,
        "desired_code_fingerprint": desired_code_fingerprint,
        "is_current": desired_code_fingerprint in {None, startup_code_fingerprint},
        "registered_process": process_entry,
        "updated_at": payload.get("updated_at"),
    }


def runtime_code_is_current(startup_code_fingerprint: str | None = None) -> bool:
    status = get_runtime_status()
    if startup_code_fingerprint is None:
        startup_code_fingerprint = status["startup_code_fingerprint"]
    desired_code_fingerprint = status["desired_code_fingerprint"]
    return desired_code_fingerprint in {None, startup_code_fingerprint}


@contextmanager
def runtime_process_heartbeat(
    process_kind: str,
    process_identity: str,
    *,
    pid: int | None = None,
    heartbeat_interval_seconds: int | None = None,
) -> Iterator[RuntimeProcessRegistration]:
    registration = register_runtime_process(process_kind, process_identity, pid=pid)
    interval_seconds = heartbeat_interval_seconds or max(
        getattr(get_settings(), "worker_heartbeat_seconds", 30),
        1,
    )

    def _heartbeat_loop() -> None:
        with _ACTIVE_HEARTBEATS_LOCK:
            active = _ACTIVE_HEARTBEATS.get(process_identity)
            if active is None:
                return
            stop_event = active["stop_event"]
        while not stop_event.wait(interval_seconds):
            try:
                record_runtime_process_heartbeat(
                    process_identity,
                    process_kind=process_kind,
                    pid=registration.pid,
                    startup_code_fingerprint=registration.startup_code_fingerprint,
                )
            except Exception as exc:  # pragma: no cover - exercised via callers
                logger.warning(
                    "runtime_process_heartbeat_failed",
                    process_kind=process_kind,
                    process_identity=process_identity,
                    error=str(exc),
                )

    heartbeat_thread: threading.Thread | None = None
    with _ACTIVE_HEARTBEATS_LOCK:
        active = _ACTIVE_HEARTBEATS.get(process_identity)
        if active is None or not active["thread"].is_alive():
            stop_event = threading.Event()
            heartbeat_thread = threading.Thread(
                target=_heartbeat_loop,
                name=f"runtime-heartbeat-{process_kind}-{process_identity}",
                daemon=True,
            )
            _ACTIVE_HEARTBEATS[process_identity] = {
                "registration": registration,
                "stop_event": stop_event,
                "thread": heartbeat_thread,
                "ref_count": 1,
            }
        else:
            active["registration"] = registration
            active["ref_count"] += 1
            heartbeat_thread = None

    if heartbeat_thread is not None:
        heartbeat_thread.start()

    try:
        yield registration
    finally:
        stop_event: threading.Event | None = None
        thread_to_join: threading.Thread | None = None
        with _ACTIVE_HEARTBEATS_LOCK:
            active = _ACTIVE_HEARTBEATS.get(process_identity)
            if active is not None:
                active["ref_count"] -= 1
                if active["ref_count"] <= 0:
                    stop_event = active["stop_event"]
                    thread_to_join = active["thread"]
                    _ACTIVE_HEARTBEATS.pop(process_identity, None)
        if stop_event is not None and thread_to_join is not None:
            stop_event.set()
            thread_to_join.join(timeout=max(1, interval_seconds))
