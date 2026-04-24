from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.core.files import repo_root
from app.core.time import utcnow
from app.services.improvement_cases import (
    IMPROVEMENT_CASE_STATUSES,
    ImprovementCase,
    ImprovementCaseDeployment,
    ImprovementCaseMeasurement,
    ImprovementCaseRegistry,
    build_improvement_case_manifest,
    load_improvement_case_registry,
    validate_improvement_case_registry,
    write_improvement_case_registry,
)

IMPROVEMENT_CASE_UPDATE_SCHEMA_NAME = "improvement_case_update"
IMPROVEMENT_CASE_UPDATE_SCHEMA_VERSION = "1.0"


class ImprovementCaseUpdateResult(BaseModel):
    schema_name: Literal["improvement_case_update"] = IMPROVEMENT_CASE_UPDATE_SCHEMA_NAME
    schema_version: Literal["1.0"] = IMPROVEMENT_CASE_UPDATE_SCHEMA_VERSION
    case: ImprovementCase
    manifest: list[dict] = Field(default_factory=list)


def _issue_lines(issues: list[object]) -> str:
    return "; ".join(
        f"{getattr(issue, 'case_id', None) or 'registry'} "
        f"{getattr(issue, 'field', 'unknown')}: {getattr(issue, 'message', issue)}"
        for issue in issues
    )


def _find_case_index(registry: ImprovementCaseRegistry, case_id: str) -> int:
    for index, case in enumerate(registry.cases):
        if case.case_id == case_id:
            return index
    raise ValueError(f"Unknown improvement case '{case_id}'.")


def _has_update_payload(**values: object) -> bool:
    return any(value is not None for value in values.values())


def update_improvement_case(
    *,
    case_id: str,
    path: str | Path | None = None,
    status: str | None = None,
    deployed_ref: str | None = None,
    deployment_notes: str | None = None,
    metric_name: str | None = None,
    metric_value: float | None = None,
    measurement_window: str | None = None,
    measurement_notes: str | None = None,
    project_root: Path | None = None,
) -> ImprovementCaseUpdateResult:
    if status is not None and status not in IMPROVEMENT_CASE_STATUSES:
        allowed = ", ".join(sorted(IMPROVEMENT_CASE_STATUSES))
        raise ValueError(f"Unknown improvement case status '{status}'. Expected one of: {allowed}.")
    if not _has_update_payload(
        status=status,
        deployed_ref=deployed_ref,
        deployment_notes=deployment_notes,
        metric_name=metric_name,
        metric_value=metric_value,
        measurement_window=measurement_window,
        measurement_notes=measurement_notes,
    ):
        raise ValueError("At least one improvement case update field is required.")

    root = project_root or repo_root()
    registry = load_improvement_case_registry(path, project_root=root)
    case_index = _find_case_index(registry, case_id)
    case = registry.cases[case_index].model_copy(deep=True)

    if status is not None:
        case.status = status
    if deployed_ref is not None or deployment_notes is not None:
        case.deployment = ImprovementCaseDeployment(
            deployed_ref=deployed_ref
            if deployed_ref is not None
            else case.deployment.deployed_ref,
            notes=deployment_notes if deployment_notes is not None else case.deployment.notes,
        )
    if (
        metric_name is not None
        or metric_value is not None
        or measurement_window is not None
        or measurement_notes is not None
    ):
        case.measurement = ImprovementCaseMeasurement(
            metric_name=metric_name if metric_name is not None else case.measurement.metric_name,
            current_value=metric_value
            if metric_value is not None
            else case.measurement.current_value,
            measurement_window=measurement_window
            if measurement_window is not None
            else case.measurement.measurement_window,
            notes=measurement_notes if measurement_notes is not None else case.measurement.notes,
        )
    case.updated_at = utcnow().isoformat()

    cases = [*registry.cases]
    cases[case_index] = case
    candidate_registry = ImprovementCaseRegistry(
        schema_name=registry.schema_name,
        schema_version=registry.schema_version,
        cases=cases,
    )
    issues = validate_improvement_case_registry(candidate_registry, project_root=root)
    if issues:
        raise ValueError(f"Invalid improvement case update: {_issue_lines(issues)}")

    write_improvement_case_registry(candidate_registry, path, project_root=root)
    return ImprovementCaseUpdateResult(
        case=case,
        manifest=build_improvement_case_manifest(ImprovementCaseRegistry(cases=[case])),
    )
