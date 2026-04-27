from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from app.architecture_inspection import (
    ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
    build_architecture_inspection_report,
)
from app.architecture_measurement_contracts import (
    ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_RECORD_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME,
    DEFAULT_ARCHITECTURE_MEASUREMENT_HISTORY_PATH,
)
from app.core.files import repo_root
from app.core.time import utcnow


def resolve_architecture_measurement_history_path(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    raw_path = Path(path) if path is not None else DEFAULT_ARCHITECTURE_MEASUREMENT_HISTORY_PATH
    return raw_path if raw_path.is_absolute() else (project_root or repo_root()) / raw_path


def current_git_commit_sha(project_root: Path | None = None) -> str | None:
    root = project_root or repo_root()
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def record_architecture_measurement(
    report: dict[str, Any] | None = None,
    *,
    history_path: str | Path | None = None,
    project_root: Path | None = None,
    commit_sha: str | None = None,
) -> dict[str, Any]:
    root = project_root or repo_root()
    resolved_path = resolve_architecture_measurement_history_path(
        history_path,
        project_root=root,
    )
    report_payload = report or build_architecture_inspection_report(root)
    record = {
        "schema_name": ARCHITECTURE_MEASUREMENT_RECORD_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "recorded_at": utcnow().isoformat(),
        "commit_sha": commit_sha if commit_sha is not None else current_git_commit_sha(root),
        "valid": report_payload["valid"],
        "violation_count": report_payload["violation_count"],
        "measurement": report_payload["measurement"],
    }
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    with resolved_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def load_architecture_measurement_history(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> list[dict[str, Any]]:
    resolved_path = resolve_architecture_measurement_history_path(path, project_root=project_root)
    if not resolved_path.exists():
        return []

    records: list[dict[str, Any]] = []
    for lineno, line in enumerate(resolved_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid architecture measurement history JSON on line {lineno}: {exc}"
            ) from exc
    return records


def _metric(record: dict[str, Any] | None, name: str) -> int | float | None:
    if record is None:
        return None
    measurement = record.get("measurement") or {}
    if name == "error_count":
        return (measurement.get("severity_counts") or {}).get("error", 0)
    if name == "warning_count":
        return (measurement.get("severity_counts") or {}).get("warning", 0)
    if name == "info_count":
        return (measurement.get("severity_counts") or {}).get("info", 0)
    return measurement.get(name, record.get(name))


def _metric_mapping(
    record: dict[str, Any] | None,
    name: str,
) -> dict[str, int | float] | None:
    if record is None:
        return None
    measurement = record.get("measurement") or {}
    values = measurement.get(name)
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValueError(f"Architecture measurement field '{name}' must be an object.")
    metrics: dict[str, int | float] = {}
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"Architecture measurement field '{name}.{key}' must be numeric."
            )
        metrics[str(key)] = value
    return metrics


def _delta(
    latest: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    name: str,
) -> int | float | None:
    latest_value = _metric(latest, name)
    previous_value = _metric(previous, name)
    if latest_value is None or previous_value is None:
        return None
    return latest_value - previous_value


def _mapping_delta(
    latest: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    name: str,
) -> dict[str, int | float] | None:
    latest_values = _metric_mapping(latest, name)
    previous_values = _metric_mapping(previous, name)
    if latest_values is None or previous_values is None:
        return None
    return {
        key: latest_values.get(key, 0) - previous_values.get(key, 0)
        for key in sorted(set(latest_values) | set(previous_values))
    }


def summarize_architecture_measurements(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root or repo_root()
    resolved_path = resolve_architecture_measurement_history_path(path, project_root=root)
    records = load_architecture_measurement_history(resolved_path)
    latest = records[-1] if records else None
    previous = records[-2] if len(records) > 1 else None
    current_commit_sha = current_git_commit_sha(root)
    latest_recorded_commit_sha = (
        str(latest["commit_sha"])
        if latest is not None and latest.get("commit_sha") is not None
        else None
    )
    latest_recorded_at = (
        str(latest["recorded_at"])
        if latest is not None and latest.get("recorded_at") is not None
        else None
    )
    is_current = (
        current_commit_sha is not None
        and latest_recorded_commit_sha is not None
        and latest_recorded_commit_sha == current_commit_sha
    )
    return {
        "schema_name": ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "history_schema_name": ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME,
        "history_path": resolved_path.as_posix(),
        "record_count": len(records),
        "current_commit_sha": current_commit_sha,
        "latest_recorded_commit_sha": latest_recorded_commit_sha,
        "latest_recorded_at": latest_recorded_at,
        "is_current": is_current,
        "recording_required": not is_current,
        "latest": latest,
        "previous": previous,
        "latest_rule_violation_counts": _metric_mapping(
            latest,
            "rule_violation_counts",
        ),
        "latest_contract_violation_counts": _metric_mapping(
            latest,
            "contract_violation_counts",
        ),
        "deltas": {
            "non_ignored_violation_count": _delta(
                latest,
                previous,
                "non_ignored_violation_count",
            ),
            "error_count": _delta(latest, previous, "error_count"),
            "warning_count": _delta(latest, previous, "warning_count"),
            "info_count": _delta(latest, previous, "info_count"),
            "contract_count": _delta(latest, previous, "contract_count"),
            "rule_violation_counts": _mapping_delta(
                latest,
                previous,
                "rule_violation_counts",
            ),
            "contract_violation_counts": _mapping_delta(
                latest,
                previous,
                "contract_violation_counts",
            ),
        },
    }
