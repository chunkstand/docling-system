from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

from app.core.time import utcnow

DEFAULT_IMPROVEMENT_CASES_PATH = Path("config") / "improvement_cases.yaml"
IMPROVEMENT_CASE_SCHEMA_NAME = "improvement_cases"
IMPROVEMENT_CASE_SCHEMA_VERSION = "1.0"

IMPROVEMENT_CAUSE_CLASSES = frozenset(
    {
        "bad_pattern",
        "bad_tool",
        "missing_constraint",
        "missing_context",
        "missing_test",
        "unclear_ownership",
        "unsafe_permission",
    }
)
IMPROVEMENT_ARTIFACT_TYPES = frozenset(
    {
        "contract",
        "eval",
        "generated_map",
        "lint",
        "permission_rule",
        "runbook",
        "script",
        "test",
    }
)
IMPROVEMENT_CASE_STATUSES = frozenset(
    {
        "open",
        "converted",
        "verified",
        "deployed",
        "measured",
        "closed",
        "suppressed",
    }
)
IMPROVEMENT_SOURCE_TYPES = frozenset(
    {
        "agent_task",
        "bad_diff",
        "eval_failure",
        "flaky_test",
        "incident",
        "operator_note",
        "review_comment",
        "runtime_failure",
        "tool_confusion",
        "other",
    }
)
DEPLOYED_IMPROVEMENT_STATUSES = frozenset({"deployed", "measured", "closed"})
MEASURED_IMPROVEMENT_STATUSES = frozenset({"measured", "closed"})


class ImprovementCaseSource(BaseModel):
    source_type: str = ""
    source_ref: str | None = None
    notes: str | None = None


class ImprovementCaseArtifact(BaseModel):
    artifact_type: str = ""
    target_path: str = ""
    description: str = ""


class ImprovementCaseVerification(BaseModel):
    commands: list[str] = Field(default_factory=list)
    acceptance_conditions: list[str] = Field(default_factory=list)
    catches_old_failure: bool = False
    allows_good_changes: bool = False


class ImprovementCaseDeployment(BaseModel):
    deployed_ref: str | None = None
    notes: str | None = None


class ImprovementCaseMeasurement(BaseModel):
    metric_name: str | None = None
    current_value: float | None = None
    measurement_window: str | None = None
    notes: str | None = None


class ImprovementCase(BaseModel):
    case_id: str = ""
    title: str = ""
    status: str = "open"
    cause_class: str = ""
    observed_failure: str = ""
    source: ImprovementCaseSource = Field(default_factory=ImprovementCaseSource)
    artifact: ImprovementCaseArtifact = Field(default_factory=ImprovementCaseArtifact)
    verification: ImprovementCaseVerification
    workflow_version: str = "improvement_v1"
    deployment: ImprovementCaseDeployment = Field(default_factory=ImprovementCaseDeployment)
    measurement: ImprovementCaseMeasurement = Field(default_factory=ImprovementCaseMeasurement)
    created_at: str | None = None
    updated_at: str | None = None


class ImprovementCaseRegistry(BaseModel):
    schema_name: str = IMPROVEMENT_CASE_SCHEMA_NAME
    schema_version: str = IMPROVEMENT_CASE_SCHEMA_VERSION
    cases: list[ImprovementCase] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ImprovementCaseContractIssue:
    case_id: str | None
    field: str
    message: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_improvement_cases_path(path: str | Path | None = None) -> Path:
    raw_path = Path(path) if path is not None else DEFAULT_IMPROVEMENT_CASES_PATH
    if raw_path.is_absolute():
        return raw_path
    return _project_root() / raw_path


def empty_improvement_case_registry() -> ImprovementCaseRegistry:
    return ImprovementCaseRegistry()


def load_improvement_case_registry(path: str | Path | None = None) -> ImprovementCaseRegistry:
    resolved_path = resolve_improvement_cases_path(path)
    if not resolved_path.exists():
        return empty_improvement_case_registry()
    payload = yaml.safe_load(resolved_path.read_text()) or {}
    return ImprovementCaseRegistry.model_validate(payload)


def write_improvement_case_registry(
    registry: ImprovementCaseRegistry,
    path: str | Path | None = None,
) -> Path:
    resolved_path = resolve_improvement_cases_path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        yaml.safe_dump(
            registry.model_dump(mode="json"),
            sort_keys=False,
            allow_unicode=True,
        )
    )
    return resolved_path


def _empty_text(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _case_issue(case: ImprovementCase, field: str, message: str) -> ImprovementCaseContractIssue:
    return ImprovementCaseContractIssue(case_id=case.case_id, field=field, message=message)


def validate_improvement_case_registry(
    registry: ImprovementCaseRegistry,
) -> list[ImprovementCaseContractIssue]:
    issues: list[ImprovementCaseContractIssue] = []
    if registry.schema_name != IMPROVEMENT_CASE_SCHEMA_NAME:
        issues.append(
            ImprovementCaseContractIssue(
                case_id=None,
                field="schema_name",
                message=(
                    f"Expected schema_name '{IMPROVEMENT_CASE_SCHEMA_NAME}', "
                    f"got '{registry.schema_name}'."
                ),
            )
        )
    if registry.schema_version != IMPROVEMENT_CASE_SCHEMA_VERSION:
        issues.append(
            ImprovementCaseContractIssue(
                case_id=None,
                field="schema_version",
                message=(
                    f"Expected schema_version '{IMPROVEMENT_CASE_SCHEMA_VERSION}', "
                    f"got '{registry.schema_version}'."
                ),
            )
        )

    case_ids = [case.case_id for case in registry.cases]
    duplicates = {case_id for case_id, count in Counter(case_ids).items() if count > 1}
    for case_id in sorted(duplicates):
        issues.append(
            ImprovementCaseContractIssue(
                case_id=case_id,
                field="case_id",
                message="Improvement case IDs must be unique.",
            )
        )

    for case in registry.cases:
        if _empty_text(case.case_id):
            issues.append(_case_issue(case, "case_id", "Case ID is required."))
        if _empty_text(case.title):
            issues.append(_case_issue(case, "title", "Title is required."))
        if _empty_text(case.observed_failure):
            issues.append(
                _case_issue(case, "observed_failure", "Observed failure is required.")
            )
        if _empty_text(case.workflow_version):
            issues.append(
                _case_issue(case, "workflow_version", "Workflow version is required.")
            )
        if case.status not in IMPROVEMENT_CASE_STATUSES:
            issues.append(
                _case_issue(case, "status", f"Unknown improvement case status '{case.status}'.")
            )
        if case.cause_class not in IMPROVEMENT_CAUSE_CLASSES:
            issues.append(
                _case_issue(case, "cause_class", f"Unknown cause class '{case.cause_class}'.")
            )
        if case.source.source_type not in IMPROVEMENT_SOURCE_TYPES:
            issues.append(
                _case_issue(
                    case,
                    "source.source_type",
                    f"Unknown source type '{case.source.source_type}'.",
                )
            )
        if case.artifact.artifact_type not in IMPROVEMENT_ARTIFACT_TYPES:
            issues.append(
                _case_issue(
                    case,
                    "artifact.artifact_type",
                    f"Unknown artifact type '{case.artifact.artifact_type}'.",
                )
            )
        if _empty_text(case.artifact.target_path):
            issues.append(
                _case_issue(
                    case,
                    "artifact.target_path",
                    "Executable artifact target path is required.",
                )
            )
        if _empty_text(case.artifact.description):
            issues.append(
                _case_issue(
                    case,
                    "artifact.description",
                    "Executable artifact description is required.",
                )
            )

        has_verification_command = any(command.strip() for command in case.verification.commands)
        has_acceptance_condition = any(
            condition.strip() for condition in case.verification.acceptance_conditions
        )
        if not has_verification_command and not has_acceptance_condition:
            issues.append(
                _case_issue(
                    case,
                    "verification",
                    "At least one verification command or acceptance condition is required.",
                )
            )
        if not case.verification.catches_old_failure:
            issues.append(
                _case_issue(
                    case,
                    "verification.catches_old_failure",
                    "Verification must explicitly catch the old failure.",
                )
            )
        if not case.verification.allows_good_changes:
            issues.append(
                _case_issue(
                    case,
                    "verification.allows_good_changes",
                    "Verification must explicitly allow good changes.",
                )
            )
        if case.status in DEPLOYED_IMPROVEMENT_STATUSES and _empty_text(
            case.deployment.deployed_ref
        ):
            issues.append(
                _case_issue(
                    case,
                    "deployment.deployed_ref",
                    "Deployed, measured, and closed cases must include a deployment ref.",
                )
            )
        if case.status in MEASURED_IMPROVEMENT_STATUSES and (
            _empty_text(case.measurement.metric_name) or case.measurement.current_value is None
        ):
            issues.append(
                _case_issue(
                    case,
                    "measurement",
                    "Measured and closed cases must include a metric name and value.",
                )
            )
    return issues


def build_improvement_case_manifest(
    registry: ImprovementCaseRegistry,
) -> list[dict]:
    return [
        {
            "case_id": case.case_id,
            "title": case.title,
            "status": case.status,
            "cause_class": case.cause_class,
            "artifact_type": case.artifact.artifact_type,
            "artifact_target_path": case.artifact.target_path,
            "source_type": case.source.source_type,
            "workflow_version": case.workflow_version,
            "deployed_ref": case.deployment.deployed_ref,
            "metric_name": case.measurement.metric_name,
            "metric_value": case.measurement.current_value,
        }
        for case in registry.cases
    ]


def summarize_improvement_cases(registry: ImprovementCaseRegistry) -> dict:
    cases = registry.cases
    measured_cases = [
        case
        for case in cases
        if case.measurement.metric_name is not None and case.measurement.current_value is not None
    ]
    return {
        "schema_name": "improvement_case_summary",
        "schema_version": "1.0",
        "case_count": len(cases),
        "status_counts": dict(Counter(case.status for case in cases)),
        "cause_class_counts": dict(Counter(case.cause_class for case in cases)),
        "artifact_type_counts": dict(Counter(case.artifact.artifact_type for case in cases)),
        "workflow_version_counts": dict(Counter(case.workflow_version for case in cases)),
        "source_type_counts": dict(Counter(case.source.source_type for case in cases)),
        "measured_case_count": len(measured_cases),
    }


def filter_improvement_cases(
    registry: ImprovementCaseRegistry,
    *,
    status: str | None = None,
    cause_class: str | None = None,
    artifact_type: str | None = None,
    workflow_version: str | None = None,
) -> ImprovementCaseRegistry:
    cases = registry.cases
    if status is not None:
        cases = [case for case in cases if case.status == status]
    if cause_class is not None:
        cases = [case for case in cases if case.cause_class == cause_class]
    if artifact_type is not None:
        cases = [case for case in cases if case.artifact.artifact_type == artifact_type]
    if workflow_version is not None:
        cases = [case for case in cases if case.workflow_version == workflow_version]
    return ImprovementCaseRegistry(
        schema_name=registry.schema_name,
        schema_version=registry.schema_version,
        cases=cases,
    )


def record_improvement_case(
    *,
    path: str | Path | None = None,
    title: str,
    observed_failure: str,
    cause_class: str,
    artifact_type: str,
    artifact_target_path: str,
    artifact_description: str,
    verification_commands: list[str] | None = None,
    acceptance_conditions: list[str] | None = None,
    source_type: str = "operator_note",
    source_ref: str | None = None,
    status: str = "converted",
    workflow_version: str = "improvement_v1",
    case_id: str | None = None,
    deployed_ref: str | None = None,
    metric_name: str | None = None,
    metric_value: float | None = None,
    measurement_window: str | None = None,
) -> ImprovementCase:
    registry = load_improvement_case_registry(path)
    now = utcnow().isoformat()
    case = ImprovementCase(
        case_id=case_id or f"IC-{utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8]}",
        title=title,
        status=status,
        cause_class=cause_class,
        observed_failure=observed_failure,
        source=ImprovementCaseSource(source_type=source_type, source_ref=source_ref),
        artifact=ImprovementCaseArtifact(
            artifact_type=artifact_type,
            target_path=artifact_target_path,
            description=artifact_description,
        ),
        verification=ImprovementCaseVerification(
            commands=verification_commands or [],
            acceptance_conditions=acceptance_conditions or [],
            catches_old_failure=True,
            allows_good_changes=True,
        ),
        workflow_version=workflow_version,
        deployment=ImprovementCaseDeployment(deployed_ref=deployed_ref),
        measurement=ImprovementCaseMeasurement(
            metric_name=metric_name,
            current_value=metric_value,
            measurement_window=measurement_window,
        ),
        created_at=now,
        updated_at=now,
    )
    candidate_registry = ImprovementCaseRegistry(
        schema_name=registry.schema_name,
        schema_version=registry.schema_version,
        cases=[*registry.cases, case],
    )
    issues = validate_improvement_case_registry(candidate_registry)
    if issues:
        issue_lines = "; ".join(
            f"{issue.case_id or 'registry'} {issue.field}: {issue.message}" for issue in issues
        )
        raise ValueError(f"Invalid improvement case registry: {issue_lines}")
    write_improvement_case_registry(candidate_registry, path)
    return case
