from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.files import repo_root
from app.db.session import get_session_factory
from app.hygiene import (
    collect_ruff_violation_counts,
    find_ruff_regression_findings,
    load_ruff_baseline,
    run_improvement_case_contract_checks,
    run_python_hygiene_checks,
)
from app.services.improvement_case_architecture_quality import (
    collect_architecture_quality_report_observations,
)
from app.services.improvement_case_contracts import (
    IMPROVEMENT_CASE_IMPORT_ALL_SOURCE,
    IMPROVEMENT_CASE_IMPORT_SCHEMA_NAME,
    IMPROVEMENT_CASE_IMPORT_SCHEMA_VERSION,
    IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE,
    ImprovementCaseImportSourceContract,
)
from app.services.improvement_case_contracts import (
    list_improvement_case_import_source_specs as _list_improvement_case_import_source_specs,
)
from app.services.improvement_case_contracts import (
    list_improvement_case_import_sources as _list_improvement_case_import_sources,
)
from app.services.improvement_case_report_imports import (
    collect_agent_trace_review_report_observations,
    collect_architecture_governance_report_observations,
    resolve_agent_trace_review_report_path,
    resolve_architecture_governance_report_path,
)
from app.services.improvement_cases import (
    ImprovementCaseObservation,
    collect_eval_failure_case_observations,
    collect_failed_agent_task_observations,
    collect_failed_agent_verification_observations,
    collect_hygiene_finding_observations,
    import_improvement_case_observations,
    load_improvement_case_registry,
)

__all__ = [
    "ImprovementCaseImportCaseSummary",
    "ImprovementCaseImportRequest",
    "ImprovementCaseImportResult",
    "ImprovementCaseImportSkippedSource",
    "ImprovementCaseImportSourceContext",
    "ImprovementCaseImportSourceSpec",
    "collect_agent_trace_review_report_observations",
    "collect_architecture_governance_report_observations",
    "collect_hygiene_import_observations",
    "collect_improvement_case_import_observations",
    "list_improvement_case_import_source_specs",
    "list_improvement_case_import_sources",
    "resolve_agent_trace_review_report_path",
    "resolve_architecture_governance_report_path",
    "run_improvement_case_import",
]


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


list_improvement_case_import_sources = _list_improvement_case_import_sources
list_improvement_case_import_source_specs = _list_improvement_case_import_source_specs
ACTIVE_ARCHITECTURE_GOVERNANCE_CASE_STATUSES = frozenset({"open", "converted", "verified"})


def _validate_import_source(source: str) -> None:
    if source not in list_improvement_case_import_sources():
        allowed = ", ".join(list_improvement_case_import_sources())
        raise ValueError(
            f"Unknown improvement case import source '{source}'. Expected one of: {allowed}."
        )


def _active_architecture_governance_artifact_key(
    *,
    source_type: str,
    cause_class: str,
    artifact_target_path: str | None,
    status: str,
) -> tuple[str, str, str] | None:
    target_path = (artifact_target_path or "").strip()
    if (
        source_type != "architecture_governance"
        or status not in ACTIVE_ARCHITECTURE_GOVERNANCE_CASE_STATUSES
        or not cause_class
        or not target_path
    ):
        return None
    return source_type, cause_class, target_path


def _partition_active_architecture_governance_artifacts(
    observations: list[ImprovementCaseObservation],
    *,
    path: str | Path | None = None,
    project_root: Path | None = None,
) -> tuple[list[ImprovementCaseObservation], list[dict[str, str]]]:
    root = project_root or repo_root()
    registry = load_improvement_case_registry(path, project_root=root)
    existing_artifacts = {
        key
        for case in registry.cases
        if (
            key := _active_architecture_governance_artifact_key(
                source_type=case.source.source_type,
                cause_class=case.cause_class,
                artifact_target_path=case.artifact.target_path,
                status=case.status,
            )
        )
        is not None
    }
    retained: list[ImprovementCaseObservation] = []
    skipped: list[dict[str, str]] = []
    for observation in observations:
        artifact_key = _active_architecture_governance_artifact_key(
            source_type=observation.source_type,
            cause_class=observation.cause_class,
            artifact_target_path=observation.artifact_target_path,
            status="open",
        )
        if artifact_key in existing_artifacts:
            skipped.append(
                {
                    "source_type": observation.source_type,
                    "source_ref": observation.source_ref,
                    "reason": "artifact_already_governed",
                }
            )
            continue
        retained.append(observation)
        if artifact_key is not None:
            existing_artifacts.add(artifact_key)
    return retained, skipped


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
    verification_commands: list[str] = Field(default_factory=list)
    acceptance_conditions: list[str] = Field(default_factory=list)
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
        [finding for finding in findings if getattr(finding, "blocking", True)],
        limit=limit,
        workflow_version=workflow_version,
    )


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


def _collect_architecture_quality_report_source(
    context: ImprovementCaseImportSourceContext,
) -> list[ImprovementCaseObservation]:
    return collect_architecture_quality_report_observations(
        source_path=context.source_path,
        limit=context.limit,
        workflow_version=context.workflow_version,
        project_root=context.project_root,
        require_existing=context.source_path is not None,
    )


def _collect_agent_trace_review_report_source(
    context: ImprovementCaseImportSourceContext,
) -> list[ImprovementCaseObservation]:
    return collect_agent_trace_review_report_observations(
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


def _runtime_import_source_spec(
    contract: ImprovementCaseImportSourceContract,
    collector: Callable[
        [ImprovementCaseImportSourceContext],
        list[ImprovementCaseObservation],
    ],
) -> ImprovementCaseImportSourceSpec:
    return ImprovementCaseImportSourceSpec(
        source=contract.source,
        source_kind=contract.source_kind,
        requires_db_session=contract.requires_db_session,
        accepts_source_path=contract.accepts_source_path,
        collector=collector,
    )


_IMPORT_SOURCE_SPECS = (
    _runtime_import_source_spec(
        IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE["hygiene"],
        _collect_hygiene_source,
    ),
    _runtime_import_source_spec(
        IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE[
            "architecture-governance-report"
        ],
        _collect_architecture_governance_report_source,
    ),
    _runtime_import_source_spec(
        IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE["architecture-quality-report"],
        _collect_architecture_quality_report_source,
    ),
    _runtime_import_source_spec(
        IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE["agent-trace-review-report"],
        _collect_agent_trace_review_report_source,
    ),
    _runtime_import_source_spec(
        IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE["eval-failure-cases"],
        _collect_eval_failure_case_source,
    ),
    _runtime_import_source_spec(
        IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE["failed-agent-tasks"],
        _collect_failed_agent_task_source,
    ),
    _runtime_import_source_spec(
        IMPROVEMENT_CASE_IMPORT_SOURCE_CONTRACTS_BY_SOURCE["failed-agent-verifications"],
        _collect_failed_agent_verification_source,
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
    aggregate_import = source == IMPROVEMENT_CASE_IMPORT_ALL_SOURCE

    for spec in source_specs:
        if not spec.requires_db_session:
            resolved_source_path = resolved_source_paths.get(spec.source)
            if (
                aggregate_import
                and spec.source_kind == "file"
                and resolved_source_path is None
            ):
                continue
            context = replace(base_context, source_path=resolved_source_path)
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
    filtered_observations, pre_skipped = _partition_active_architecture_governance_artifacts(
        observations,
        path=import_request.path,
        project_root=project_root,
    )
    payload = import_improvement_case_observations(
        filtered_observations,
        path=import_request.path,
        project_root=project_root,
        dry_run=import_request.dry_run,
    )
    if pre_skipped:
        payload["candidate_count"] += len(pre_skipped)
        payload["skipped_count"] += len(pre_skipped)
        payload["skipped"] = [*payload["skipped"], *pre_skipped]
    return ImprovementCaseImportResult.model_validate(payload)
