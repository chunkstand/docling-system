from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.architecture_measurement_contracts import DEFAULT_ARCHITECTURE_GOVERNANCE_REPORT_PATH
from app.core.files import repo_root
from app.db.session import get_session_factory
from app.hygiene import (
    collect_ruff_violation_counts,
    find_ruff_regression_findings,
    load_ruff_baseline,
    run_improvement_case_contract_checks,
    run_python_hygiene_checks,
)
from app.services.improvement_cases import (
    ImprovementCaseObservation,
    collect_eval_failure_case_observations,
    collect_failed_agent_task_observations,
    collect_failed_agent_verification_observations,
    collect_hygiene_finding_observations,
    import_improvement_case_observations,
)

IMPROVEMENT_CASE_IMPORT_SCHEMA_NAME = "improvement_case_import"
IMPROVEMENT_CASE_IMPORT_SCHEMA_VERSION = "1.0"
IMPROVEMENT_CASE_IMPORT_SOURCES = frozenset(
    {
        "all",
        "hygiene",
        "architecture-governance-report",
        "eval-failure-cases",
        "failed-agent-tasks",
        "failed-agent-verifications",
    }
)
_DB_IMPORT_SOURCES = frozenset(
    {"all", "eval-failure-cases", "failed-agent-tasks", "failed-agent-verifications"}
)


def list_improvement_case_import_sources() -> tuple[str, ...]:
    return tuple(sorted(IMPROVEMENT_CASE_IMPORT_SOURCES))


def _validate_import_source(source: str) -> None:
    if source not in IMPROVEMENT_CASE_IMPORT_SOURCES:
        allowed = ", ".join(sorted(IMPROVEMENT_CASE_IMPORT_SOURCES))
        raise ValueError(
            f"Unknown improvement case import source '{source}'. Expected one of: {allowed}."
        )


class ImprovementCaseImportRequest(BaseModel):
    source: str = "hygiene"
    limit: int = Field(default=50, ge=0)
    workflow_version: str = "improvement_v1"
    path: str | Path | None = None
    source_path: str | Path | None = None
    dry_run: bool = False

    @field_validator("source")
    @staticmethod
    def validate_source(source: str) -> str:
        _validate_import_source(source)
        return source


class ImprovementCaseImportCaseSummary(BaseModel):
    case_id: str
    title: str
    status: str
    cause_class: str
    artifact_type: str
    artifact_target_path: str
    source_type: str
    workflow_version: str
    deployed_ref: str | None
    metric_name: str | None
    metric_value: float | None


class ImprovementCaseImportSkippedSource(BaseModel):
    source_type: str
    source_ref: str
    reason: str


class ImprovementCaseImportResult(BaseModel):
    schema_name: Literal["improvement_case_import"] = IMPROVEMENT_CASE_IMPORT_SCHEMA_NAME
    schema_version: Literal["1.0"] = IMPROVEMENT_CASE_IMPORT_SCHEMA_VERSION
    dry_run: bool = False
    candidate_count: int = Field(ge=0)
    imported_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    imported: list[ImprovementCaseImportCaseSummary] = Field(default_factory=list)
    skipped: list[ImprovementCaseImportSkippedSource] = Field(default_factory=list)


def collect_hygiene_import_observations(
    *,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
    project_root: Path | None = None,
) -> list[ImprovementCaseObservation]:
    root = project_root or repo_root()
    current_counts = collect_ruff_violation_counts(root)
    baseline_counts = load_ruff_baseline(project_root=root)
    findings = [
        *find_ruff_regression_findings(current_counts, baseline_counts),
        *run_python_hygiene_checks(root),
        *run_improvement_case_contract_checks(root),
    ]
    return collect_hygiene_finding_observations(
        findings,
        limit=limit,
        workflow_version=workflow_version,
    )


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

    inspection = report.get("inspection") if isinstance(report, dict) else None
    violations = (
        inspection.get("violations", [])
        if isinstance(inspection, dict) and isinstance(inspection.get("violations", []), list)
        else []
    )
    current_commit_sha = report.get("current_commit_sha") if isinstance(report, dict) else None
    latest_recorded_commit_sha = (
        report.get("latest_recorded_commit_sha") if isinstance(report, dict) else None
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

    if isinstance(report, dict) and report.get("valid") is False and not observations:
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

    if isinstance(report, dict) and report.get("recording_required") is True:
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


def collect_improvement_case_import_observations(
    *,
    source: str = "hygiene",
    limit: int = 50,
    workflow_version: str = "improvement_v1",
    source_path: str | Path | None = None,
    session_factory: Callable | None = None,
    project_root: Path | None = None,
) -> list[ImprovementCaseObservation]:
    _validate_import_source(source)
    observations: list[ImprovementCaseObservation] = []
    if source in {"all", "hygiene"}:
        observations.extend(
            collect_hygiene_import_observations(
                limit=limit,
                workflow_version=workflow_version,
                project_root=project_root,
            )
        )

    if source in {"all", "architecture-governance-report"}:
        observations.extend(
            collect_architecture_governance_report_observations(
                source_path=source_path,
                limit=limit,
                workflow_version=workflow_version,
                project_root=project_root,
                require_existing=source_path is not None,
            )
        )

    if source in _DB_IMPORT_SOURCES:
        factory = session_factory or get_session_factory()
        with factory() as session:
            if source in {"all", "eval-failure-cases"}:
                observations.extend(
                    collect_eval_failure_case_observations(
                        session,
                        limit=limit,
                        workflow_version=workflow_version,
                    )
                )
            if source in {"all", "failed-agent-tasks"}:
                observations.extend(
                    collect_failed_agent_task_observations(
                        session,
                        limit=limit,
                        workflow_version=workflow_version,
                    )
                )
            if source in {"all", "failed-agent-verifications"}:
                observations.extend(
                    collect_failed_agent_verification_observations(
                        session,
                        limit=limit,
                        workflow_version=workflow_version,
                    )
                )
    return observations


def run_improvement_case_import(
    request: ImprovementCaseImportRequest | None = None,
    *,
    source: str | None = None,
    limit: int | None = None,
    workflow_version: str | None = None,
    path: str | Path | None = None,
    source_path: str | Path | None = None,
    dry_run: bool | None = None,
    session_factory: Callable | None = None,
    project_root: Path | None = None,
) -> ImprovementCaseImportResult:
    request_payload = request.model_dump() if request is not None else {}
    if source is not None:
        request_payload["source"] = source
    if limit is not None:
        request_payload["limit"] = limit
    if workflow_version is not None:
        request_payload["workflow_version"] = workflow_version
    if path is not None:
        request_payload["path"] = path
    if source_path is not None:
        request_payload["source_path"] = source_path
    if dry_run is not None:
        request_payload["dry_run"] = dry_run
    import_request = ImprovementCaseImportRequest.model_validate(request_payload)

    observations = collect_improvement_case_import_observations(
        source=import_request.source,
        limit=import_request.limit,
        workflow_version=import_request.workflow_version,
        source_path=import_request.source_path,
        session_factory=session_factory,
        project_root=project_root,
    )
    payload = import_improvement_case_observations(
        observations,
        path=import_request.path,
        project_root=project_root,
        dry_run=import_request.dry_run,
    )
    return ImprovementCaseImportResult.model_validate(payload)
