from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

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


def collect_improvement_case_import_observations(
    *,
    source: str = "hygiene",
    limit: int = 50,
    workflow_version: str = "improvement_v1",
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
    if dry_run is not None:
        request_payload["dry_run"] = dry_run
    import_request = ImprovementCaseImportRequest.model_validate(request_payload)

    observations = collect_improvement_case_import_observations(
        source=import_request.source,
        limit=import_request.limit,
        workflow_version=import_request.workflow_version,
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
