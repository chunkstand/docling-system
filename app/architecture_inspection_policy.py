from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from app.architecture_inspection_types import (
    ARCHITECTURE_SEVERITIES,
    ArchitectureViolation,
)
from app.core.files import repo_root

DEFAULT_ARCHITECTURE_POLICY_PATH = Path("config") / "architecture_inspection.yaml"


@dataclass(frozen=True, slots=True)
class ArchitectureInspectionPolicy:
    default_severity: str = "error"
    severity_overrides: dict[str, str] | None = None


def load_architecture_inspection_policy(
    policy_path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> ArchitectureInspectionPolicy:
    root = project_root or repo_root()
    raw_path = Path(policy_path) if policy_path is not None else DEFAULT_ARCHITECTURE_POLICY_PATH
    resolved_path = raw_path if raw_path.is_absolute() else root / raw_path
    if not resolved_path.exists():
        return ArchitectureInspectionPolicy()

    payload = yaml.safe_load(resolved_path.read_text()) or {}
    default_severity = str(payload.get("default_severity", "error"))
    if default_severity not in ARCHITECTURE_SEVERITIES:
        raise ValueError(f"Unknown architecture severity '{default_severity}'.")

    overrides: dict[str, str] = {}
    for row in payload.get("severity_overrides") or []:
        key = str(row["match"]).strip()
        severity = str(row["severity"]).strip()
        if severity not in ARCHITECTURE_SEVERITIES:
            raise ValueError(f"Unknown architecture severity '{severity}'.")
        overrides[key] = severity

    return ArchitectureInspectionPolicy(
        default_severity=default_severity,
        severity_overrides=overrides,
    )


def _severity_for_violation(
    violation: ArchitectureViolation,
    policy: ArchitectureInspectionPolicy,
) -> str:
    overrides = policy.severity_overrides or {}
    return (
        overrides.get(f"{violation.contract}.{violation.field}.{violation.symbol}")
        or overrides.get(f"{violation.contract}.{violation.field}")
        or overrides.get(violation.contract)
        or policy.default_severity
    )


def apply_architecture_policy(
    violations: list[ArchitectureViolation],
    policy: ArchitectureInspectionPolicy,
) -> list[ArchitectureViolation]:
    return [
        replace(violation, severity=_severity_for_violation(violation, policy))
        for violation in violations
    ]
