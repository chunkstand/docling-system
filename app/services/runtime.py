from __future__ import annotations

import fcntl
import hashlib
import json
import os
import socket
import tempfile
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.time import utcnow

_RUNTIME_SOURCE_SUFFIXES = {".py", ".toml", ".yaml", ".yml"}
_RUNTIME_SOURCE_DIRS = ("app", "config")
_RUNTIME_SOURCE_FILES = ("pyproject.toml",)


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

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


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
        payload["desired_code_fingerprint"] = startup_code_fingerprint
        payload["updated_at"] = registered_at
        processes = payload.setdefault("processes", {})
        processes[process_identity] = {
            "process_kind": process_kind,
            "pid": process_pid,
            "startup_code_fingerprint": startup_code_fingerprint,
            "registered_at": registered_at,
        }
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
    )


def get_runtime_status(process_identity: str | None = None) -> dict[str, Any]:
    registry_path = _runtime_registry_path()
    startup_code_fingerprint = get_startup_code_fingerprint()

    lock_handle = _with_runtime_registry_lock()
    try:
        payload = _read_runtime_registry_unlocked(registry_path)
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()

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
