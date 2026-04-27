from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.architecture_measurement_contracts import (
    ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME,
    DEFAULT_ARCHITECTURE_GOVERNANCE_REPORT_PATH,
)
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
IMPROVEMENT_CASE_IMPORT_ALL_SOURCE = "all"


@dataclass(frozen=True, slots=True)
class ImprovementCaseImportSourceContext:
    limit: int
    workflow_version: str
    project_root: Path | None = None
    source_path: str | Path | None = None
    session: object | None = None


@dataclass(frozen=True, slots=True)
class ImprovementCaseImportSourceSpec:
    source: str
    source_kind: Literal["workspace", "file", "database"]
    requires_db_session: bool
    accepts_source_path: bool
    collector: Callable[
        [ImprovementCaseImportSourceContext],
        list[ImprovementCaseObservation],
    ]

    def to_contract(self) -> dict[str, object]:
        return {
            "source": self.source,
            "source_kind": self.source_kind,
            "requires_db_session": self.requires_db_session,
            "accepts_source_path": self.accepts_source_path,
        }


def list_improvement_case_import_sources() -> tuple[str, ...]:
    return tuple(sorted({IMPROVEMENT_CASE_IMPORT_ALL_SOURCE, *_IMPORT_SOURCE_REGISTRY}))


def list_improvement_case_import_source_specs() -> tuple[dict[str, object], ...]:
    return tuple(spec.to_contract() for spec in _IMPORT_SOURCE_REGISTRY.values())


def _validate_import_source(source: str) -> None:
    if source not in list_improvement_case_import_sources():
        allowed = ", ".join(list_improvement_case_import_sources())
        raise ValueError(
            f"Unknown improvement case import source '{source}'. Expected one of: {allowed}."
        )


class ImprovementCaseImportRequest(BaseModel):
    source: str = "hygiene"
    limit: int = Field(default=50, ge=0)
    workflow_version: str = "improvement_v1"
    path: str | Path | None = None
    source_path: str | Path | None = None
    source_paths: dict[str, str | Path] = Field(default_factory=dict)
    dry_run: bool = False

    @field_validator("source")
    @staticmethod
    def validate_source(source: str) -> str:
        _validate_import_source(source)
        return source

    @model_validator(mode="after")
    def validate_source_path_contract(self) -> ImprovementCaseImportRequest:
        _resolve_source_paths(
            _select_import_source_specs(self.source),
            source_path=self.source_path,
            source_paths=self.source_paths,
        )
        return self


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


def _require_import_session(context: ImprovementCaseImportSourceContext) -> object:
    if context.session is None:
        raise RuntimeError("DB-backed improvement import source requires a session.")
    return context.session


def _collect_hygiene_source(
    context: ImprovementCaseImportSourceContext,
) -> list[ImprovementCaseObservation]:
    return collect_hygiene_import_observations(
        limit=context.limit,
        workflow_version=context.workflow_version,
        project_root=context.project_root,
    )


def _collect_architecture_governance_report_source(
    context: ImprovementCaseImportSourceContext,
) -> list[ImprovementCaseObservation]:
    return collect_architecture_governance_report_observations(
        source_path=context.source_path,
        limit=context.limit,
        workflow_version=context.workflow_version,
        project_root=context.project_root,
        require_existing=context.source_path is not None,
    )


def _collect_eval_failure_case_source(
    context: ImprovementCaseImportSourceContext,
) -> list[ImprovementCaseObservation]:
    return collect_eval_failure_case_observations(
        _require_import_session(context),
        limit=context.limit,
        workflow_version=context.workflow_version,
    )


def _collect_failed_agent_task_source(
    context: ImprovementCaseImportSourceContext,
) -> list[ImprovementCaseObservation]:
    return collect_failed_agent_task_observations(
        _require_import_session(context),
        limit=context.limit,
        workflow_version=context.workflow_version,
    )


def _collect_failed_agent_verification_source(
    context: ImprovementCaseImportSourceContext,
) -> list[ImprovementCaseObservation]:
    return collect_failed_agent_verification_observations(
        _require_import_session(context),
        limit=context.limit,
        workflow_version=context.workflow_version,
    )


_IMPORT_SOURCE_SPECS = (
    ImprovementCaseImportSourceSpec(
        source="hygiene",
        source_kind="workspace",
        requires_db_session=False,
        accepts_source_path=False,
        collector=_collect_hygiene_source,
    ),
    ImprovementCaseImportSourceSpec(
        source="architecture-governance-report",
        source_kind="file",
        requires_db_session=False,
        accepts_source_path=True,
        collector=_collect_architecture_governance_report_source,
    ),
    ImprovementCaseImportSourceSpec(
        source="eval-failure-cases",
        source_kind="database",
        requires_db_session=True,
        accepts_source_path=False,
        collector=_collect_eval_failure_case_source,
    ),
    ImprovementCaseImportSourceSpec(
        source="failed-agent-tasks",
        source_kind="database",
        requires_db_session=True,
        accepts_source_path=False,
        collector=_collect_failed_agent_task_source,
    ),
    ImprovementCaseImportSourceSpec(
        source="failed-agent-verifications",
        source_kind="database",
        requires_db_session=True,
        accepts_source_path=False,
        collector=_collect_failed_agent_verification_source,
    ),
)
_IMPORT_SOURCE_REGISTRY = {spec.source: spec for spec in _IMPORT_SOURCE_SPECS}


def _select_import_source_specs(source: str) -> tuple[ImprovementCaseImportSourceSpec, ...]:
    _validate_import_source(source)
    if source == IMPROVEMENT_CASE_IMPORT_ALL_SOURCE:
        return _IMPORT_SOURCE_SPECS
    return (_IMPORT_SOURCE_REGISTRY[source],)


def _validate_source_path_support(
    source_specs: tuple[ImprovementCaseImportSourceSpec, ...],
    source_path: str | Path | None,
) -> None:
    if source_path is None or any(spec.accepts_source_path for spec in source_specs):
        return
    supported_sources = ", ".join(
        spec.source for spec in _IMPORT_SOURCE_SPECS if spec.accepts_source_path
    )
    selected_sources = ", ".join(spec.source for spec in source_specs)
    raise ValueError(
        f"source_path is not supported for import source '{selected_sources}'. "
        f"Sources that accept source_path: {supported_sources}."
    )


def _validate_source_paths(
    source_specs: tuple[ImprovementCaseImportSourceSpec, ...],
    source_paths: Mapping[str, str | Path],
) -> None:
    selected_sources = {spec.source for spec in source_specs}
    for source in source_paths:
        if source == IMPROVEMENT_CASE_IMPORT_ALL_SOURCE:
            raise ValueError("source_paths cannot target aggregate import source 'all'.")
        if source not in _IMPORT_SOURCE_REGISTRY:
            raise ValueError(f"source_paths contains unknown import source '{source}'.")
        spec = _IMPORT_SOURCE_REGISTRY[source]
        if source not in selected_sources:
            raise ValueError(f"source_paths contains unselected import source '{source}'.")
        if not spec.accepts_source_path:
            raise ValueError(f"source_paths is not supported for import source '{source}'.")


def _resolve_source_paths(
    source_specs: tuple[ImprovementCaseImportSourceSpec, ...],
    *,
    source_path: str | Path | None,
    source_paths: Mapping[str, str | Path] | None,
) -> dict[str, str | Path]:
    keyed_paths = dict(source_paths or {})
    if source_path is not None and keyed_paths:
        raise ValueError("Use source_path or source_paths, not both.")
    _validate_source_paths(source_specs, keyed_paths)
    if source_path is None:
        return keyed_paths
    _validate_source_path_support(source_specs, source_path)
    path_specs = [spec for spec in source_specs if spec.accepts_source_path]
    if len(path_specs) != 1:
        raise ValueError("source_path is ambiguous; use source_paths instead.")
    return {path_specs[0].source: source_path}


def collect_improvement_case_import_observations(
    *,
    source: str = "hygiene",
    limit: int = 50,
    workflow_version: str = "improvement_v1",
    source_path: str | Path | None = None,
    source_paths: Mapping[str, str | Path] | None = None,
    session_factory: Callable | None = None,
    project_root: Path | None = None,
) -> list[ImprovementCaseObservation]:
    source_specs = _select_import_source_specs(source)
    resolved_source_paths = _resolve_source_paths(
        source_specs,
        source_path=source_path,
        source_paths=source_paths,
    )
    observations: list[ImprovementCaseObservation] = []
    base_context = ImprovementCaseImportSourceContext(
        limit=limit,
        workflow_version=workflow_version,
        project_root=project_root,
    )

    for spec in source_specs:
        if not spec.requires_db_session:
            context = replace(base_context, source_path=resolved_source_paths.get(spec.source))
            observations.extend(spec.collector(context))

    db_source_specs = [spec for spec in source_specs if spec.requires_db_session]
    if db_source_specs:
        factory = session_factory or get_session_factory()
        with factory() as session:
            db_context = ImprovementCaseImportSourceContext(
                limit=limit,
                workflow_version=workflow_version,
                project_root=project_root,
                session=session,
            )
            for spec in db_source_specs:
                context = replace(db_context, source_path=resolved_source_paths.get(spec.source))
                observations.extend(spec.collector(context))
    return observations


def run_improvement_case_import(
    request: ImprovementCaseImportRequest | None = None,
    *,
    source: str | None = None,
    limit: int | None = None,
    workflow_version: str | None = None,
    path: str | Path | None = None,
    source_path: str | Path | None = None,
    source_paths: Mapping[str, str | Path] | None = None,
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
    if source_paths is not None:
        request_payload["source_paths"] = dict(source_paths)
    if dry_run is not None:
        request_payload["dry_run"] = dry_run
    import_request = ImprovementCaseImportRequest.model_validate(request_payload)

    observations = collect_improvement_case_import_observations(
        source=import_request.source,
        limit=import_request.limit,
        workflow_version=import_request.workflow_version,
        source_path=import_request.source_path,
        source_paths=import_request.source_paths,
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
