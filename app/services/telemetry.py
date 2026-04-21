from __future__ import annotations

import atexit
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from app.core.config import get_settings

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

_lock = Lock()
_pending_by_path: dict[Path, dict[str, float]] = {}
_defaults: dict[str, float] = {
    "tables_detected_total": 0,
    "logical_tables_persisted_total": 0,
    "table_segments_persisted_total": 0,
    "continuation_merges_total": 0,
    "ambiguous_continuations_total": 0,
    "repeated_header_rows_removed_total": 0,
    "table_artifact_write_failures_total": 0,
    "table_embedding_failures_total": 0,
    "table_search_hits_total": 0,
    "mixed_search_requests_total": 0,
    "mixed_search_requests_with_table_hits_total": 0,
    "mixed_search_table_results_total": 0,
}


def _metrics_path() -> Path:
    path = get_settings().storage_root.resolve() / "telemetry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _metrics_lock_path(path: Path) -> Path:
    path = path.with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _metrics_file_lock(path: Path):
    lock_path = _metrics_lock_path(path)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _read_metrics(path: Path) -> dict[str, float]:
    if not path.exists():
        return dict(_defaults)
    raw = path.read_text().strip()
    if not raw:
        return dict(_defaults)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return dict(_defaults)
    if not isinstance(payload, dict):
        return dict(_defaults)
    return {**_defaults, **payload}


def _write_metrics(path: Path, metrics: dict[str, float]) -> None:
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))
    os.replace(tmp_path, path)


def _add_pending(path: Path, metric: str, amount: float) -> None:
    pending = _pending_by_path.setdefault(path, {})
    pending[metric] = pending.get(metric, 0) + amount


def increment(metric: str, amount: float = 1) -> None:
    increment_many({metric: amount})


def increment_many(updates: dict[str, float]) -> None:
    if not updates:
        return
    path = _metrics_path()
    with _lock:
        for metric, amount in updates.items():
            if amount:
                _add_pending(path, metric, amount)


def observe_search_results(table_hits: int, mixed_request: bool) -> None:
    updates: dict[str, float] = {}
    if table_hits:
        updates["table_search_hits_total"] = table_hits
    if mixed_request:
        updates["mixed_search_requests_total"] = 1
        updates["mixed_search_table_results_total"] = table_hits
        if table_hits:
            updates["mixed_search_requests_with_table_hits_total"] = 1
    increment_many(updates)


def _flush_locked(path: Path) -> dict[str, float]:
    pending = _pending_by_path.pop(path, {})
    with _metrics_file_lock(path):
        metrics = _read_metrics(path)
        if pending:
            for metric, amount in pending.items():
                metrics[metric] = metrics.get(metric, 0) + amount
            _write_metrics(path, metrics)
    return metrics


def flush_metrics() -> None:
    with _lock:
        for path in list(_pending_by_path):
            _flush_locked(path)


def snapshot_metrics() -> dict[str, float]:
    path = _metrics_path()
    with _lock:
        metrics = _flush_locked(path)
    requests = metrics.get("mixed_search_requests_total", 0)
    requests_with_table_hits = metrics.get("mixed_search_requests_with_table_hits_total", 0)
    metrics["mixed_search_table_hit_rate"] = (
        (requests_with_table_hits / requests) if requests else 0.0
    )
    return metrics


atexit.register(flush_metrics)
