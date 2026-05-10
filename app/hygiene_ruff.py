from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from app.core.files import repo_root
from app.hygiene_types import HygieneFinding

DEFAULT_RUFF_BASELINE_PATH = Path("config") / "ruff_baseline.yaml"


def _normalize_ruff_filename(project_root: Path, filename: str) -> str:
    path = Path(filename)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    try:
        return path.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_ruff_baseline(
    baseline_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, dict[str, int]]:
    root = project_root or repo_root()
    resolved_baseline_path = (root / (baseline_path or DEFAULT_RUFF_BASELINE_PATH)).resolve()
    if not resolved_baseline_path.exists():
        return {}

    payload = yaml.safe_load(resolved_baseline_path.read_text()) or {}
    baseline_payload = payload.get("ruff_baseline") or {}
    return {
        str(relative_path): {
            str(code): int(count) for code, count in sorted((counts or {}).items())
        }
        for relative_path, counts in sorted(baseline_payload.items())
    }


def write_ruff_baseline(
    violation_counts: dict[str, dict[str, int]],
    baseline_path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    resolved_baseline_path = (root / (baseline_path or DEFAULT_RUFF_BASELINE_PATH)).resolve()
    resolved_baseline_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ruff_baseline": {
            relative_path: {code: count for code, count in sorted(counts.items())}
            for relative_path, counts in sorted(violation_counts.items())
        }
    }
    resolved_baseline_path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return resolved_baseline_path


def collect_ruff_violation_counts(
    project_root: Path | None = None,
    *,
    targets: tuple[str, ...] = (".",),
    python_executable: str | None = None,
) -> dict[str, dict[str, int]]:
    root = project_root or repo_root()
    executable = python_executable or sys.executable
    command = [
        executable,
        "-m",
        "ruff",
        "check",
        *targets,
        "--output-format",
        "json",
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in (0, 1):
        stderr = completed.stderr.strip()
        raise RuntimeError(stderr or "ruff execution failed")

    try:
        rows = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError("ruff returned invalid JSON output") from exc

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        relative_path = _normalize_ruff_filename(root, row["filename"])
        counts[relative_path][row["code"]] += 1

    return {
        relative_path: dict(sorted(code_counts.items()))
        for relative_path, code_counts in sorted(counts.items())
    }


def find_ruff_regression_findings(
    current_counts: dict[str, dict[str, int]],
    baseline_counts: dict[str, dict[str, int]],
) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    for relative_path, code_counts in sorted(current_counts.items()):
        baseline_code_counts = baseline_counts.get(relative_path, {})
        for code, current_count in sorted(code_counts.items()):
            baseline_count = baseline_code_counts.get(code, 0)
            if current_count <= baseline_count:
                continue
            findings.append(
                HygieneFinding(
                    kind="ruff_regression",
                    relative_path=relative_path,
                    message=f"{code} count {current_count} exceeds baseline {baseline_count}",
                )
            )
    return findings
