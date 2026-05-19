from __future__ import annotations

import json
from pathlib import Path

from app.architecture_measurement_contracts import (
    ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME,
    DEFAULT_ARCHITECTURE_GOVERNANCE_REPORT_PATH,
)
from app.core.files import repo_root
from app.services.improvement_case_contracts import (
    AGENT_TRACE_REVIEW_REPORT_SCHEMA_NAME,
    DEFAULT_AGENT_TRACE_REVIEW_REPORT_PATH,
)
from app.services.improvement_case_models import ImprovementCaseObservation


def resolve_architecture_governance_report_path(
    source_path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    raw_path = (
        Path(source_path)
        if source_path is not None
        else DEFAULT_ARCHITECTURE_GOVERNANCE_REPORT_PATH
    )
    return raw_path if raw_path.is_absolute() else (project_root or repo_root()) / raw_path


def _architecture_governance_source_notes(
    *,
    report_path: Path,
    current_commit_sha: object,
    latest_recorded_commit_sha: object,
    extra: str | None = None,
) -> str:
    parts = [
        f"report_path={report_path.as_posix()}",
        f"current_commit_sha={current_commit_sha or 'unknown'}",
        f"latest_recorded_commit_sha={latest_recorded_commit_sha or 'none'}",
    ]
    if extra:
        parts.append(extra)
    return "; ".join(parts)


def _architecture_governance_report_value(
    report: dict,
    measurement_summary: dict | None,
    key: str,
) -> object:
    value = report.get(key)
    if value is None and measurement_summary is not None:
        return measurement_summary.get(key)
    return value


def _architecture_violation_source_ref(violation: dict) -> str:
    rule_id = str(violation.get("rule_id") or "unattributed")
    locator = (
        violation.get("relative_path")
        or violation.get("symbol")
        or violation.get("field")
        or "global"
    )
    lineno = violation.get("lineno")
    if lineno is not None:
        locator = f"{locator}:{lineno}"
    return f"architecture-governance:{rule_id}:{locator}"


def collect_architecture_governance_report_observations(
    *,
    source_path: str | Path | None = None,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
    project_root: Path | None = None,
    require_existing: bool = False,
) -> list[ImprovementCaseObservation]:
    report_path = resolve_architecture_governance_report_path(
        source_path,
        project_root=project_root,
    )
    if not report_path.exists():
        if require_existing:
            raise ValueError(f"Architecture governance report not found: {report_path}")
        return []

    try:
        report = json.loads(report_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid architecture governance report JSON: {exc}") from exc

    if not isinstance(report, dict):
        raise ValueError("Architecture governance report must be a JSON object.")
    if report.get("schema_name") != ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME:
        raise ValueError(
            "Architecture governance report has unexpected schema_name "
            f"{report.get('schema_name')!r}."
        )

    measurement_summary = report.get("measurement_summary")
    if not isinstance(measurement_summary, dict):
        measurement_summary = None
    inspection = report.get("inspection") if isinstance(report, dict) else None
    violations = (
        inspection.get("violations", [])
        if isinstance(inspection, dict) and isinstance(inspection.get("violations", []), list)
        else []
    )
    current_commit_sha = _architecture_governance_report_value(
        report,
        measurement_summary,
        "current_commit_sha",
    )
    latest_recorded_commit_sha = _architecture_governance_report_value(
        report,
        measurement_summary,
        "latest_recorded_commit_sha",
    )
    recording_required = _architecture_governance_report_value(
        report,
        measurement_summary,
        "recording_required",
    )
    observations: list[ImprovementCaseObservation] = []

    for violation in violations:
        if not isinstance(violation, dict):
            continue
        rule_id = str(violation.get("rule_id") or "unattributed")
        contract = str(violation.get("contract") or "architecture")
        field = str(violation.get("field") or "contract")
        severity = str(violation.get("severity") or "error")
        message = str(violation.get("message") or "Architecture governance violation.")
        observations.append(
            ImprovementCaseObservation(
                title=f"Architecture governance violation: {rule_id}",
                observed_failure=(
                    f"Architecture governance report failed rule '{rule_id}' for "
                    f"contract '{contract}' field '{field}': {message}"
                ),
                cause_class="missing_constraint",
                source_type="architecture_governance",
                source_ref=_architecture_violation_source_ref(violation),
                source_notes=_architecture_governance_source_notes(
                    report_path=report_path,
                    current_commit_sha=current_commit_sha,
                    latest_recorded_commit_sha=latest_recorded_commit_sha,
                    extra=f"severity={severity}; contract={contract}; field={field}",
                ),
                workflow_version=workflow_version,
            )
        )

    if report.get("valid") is False and not observations:
        observations.append(
            ImprovementCaseObservation(
                title="Architecture governance report is invalid",
                observed_failure=(
                    "Architecture governance report is invalid but did not expose "
                    "rule-level violations for import."
                ),
                cause_class="missing_context",
                source_type="architecture_governance",
                source_ref=(
                    "architecture-governance:invalid-report:"
                    f"{current_commit_sha or 'unknown'}"
                ),
                source_notes=_architecture_governance_source_notes(
                    report_path=report_path,
                    current_commit_sha=current_commit_sha,
                    latest_recorded_commit_sha=latest_recorded_commit_sha,
                ),
                workflow_version=workflow_version,
            )
        )

    if recording_required is True:
        observations.append(
            ImprovementCaseObservation(
                title="Architecture measurement history is stale",
                observed_failure=(
                    "Architecture governance report indicates the latest recorded "
                    f"measurement commit '{latest_recorded_commit_sha or 'none'}' does "
                    f"not match current commit '{current_commit_sha or 'unknown'}'."
                ),
                cause_class="missing_context",
                source_type="architecture_governance",
                source_ref=(
                    "architecture-governance:measurement-freshness:"
                    f"{current_commit_sha or 'unknown'}"
                ),
                source_notes=_architecture_governance_source_notes(
                    report_path=report_path,
                    current_commit_sha=current_commit_sha,
                    latest_recorded_commit_sha=latest_recorded_commit_sha,
                ),
                workflow_version=workflow_version,
            )
        )
    return observations[:limit]


def resolve_agent_trace_review_report_path(
    source_path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    raw_path = (
        Path(source_path)
        if source_path is not None
        else DEFAULT_AGENT_TRACE_REVIEW_REPORT_PATH
    )
    return raw_path if raw_path.is_absolute() else (project_root or repo_root()) / raw_path


def collect_agent_trace_review_report_observations(
    *,
    source_path: str | Path | None = None,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
    project_root: Path | None = None,
    require_existing: bool = False,
) -> list[ImprovementCaseObservation]:
    report_path = resolve_agent_trace_review_report_path(
        source_path,
        project_root=project_root,
    )
    if not report_path.exists():
        if require_existing:
            raise ValueError(f"Agent trace review report not found: {report_path}")
        return []

    try:
        report = json.loads(report_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid agent trace review report JSON: {exc}") from exc

    if not isinstance(report, dict):
        raise ValueError("Agent trace review report must be a JSON object.")
    if report.get("schema_name") != AGENT_TRACE_REVIEW_REPORT_SCHEMA_NAME:
        raise ValueError(
            "Agent trace review report has unexpected schema_name "
            f"{report.get('schema_name')!r}."
        )

    observations: list[ImprovementCaseObservation] = []
    report_observations = report.get("observations")
    if not isinstance(report_observations, list):
        report_observations = []
    for row in report_observations:
        if not isinstance(row, dict):
            continue
        source_ref = str(row.get("source_ref") or "")
        if not source_ref:
            continue
        observations.append(
            ImprovementCaseObservation(
                title=str(row.get("title") or "Agent trace review observation"),
                observed_failure=str(
                    row.get("observed_failure")
                    or "Agent trace review identified a failure."
                ),
                cause_class=str(row.get("cause_class") or "missing_context"),
                source_type=str(row.get("source_type") or "agent_task"),
                source_ref=source_ref,
                source_notes=(
                    f"report_path={report_path.as_posix()}; "
                    f"category={row.get('category') or 'unknown'}; "
                    f"{row.get('source_notes') or ''}"
                ),
                workflow_version=workflow_version,
            )
        )
    return observations[:limit]
