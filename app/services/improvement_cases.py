from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

from app.core.files import repo_root
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
        "agent_verification",
        "bad_diff",
        "eval_failure",
        "flaky_test",
        "hygiene_finding",
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
CONVERTED_IMPROVEMENT_STATUSES = frozenset(
    {"converted", "verified", "deployed", "measured", "closed"}
)
VERIFIED_IMPROVEMENT_STATUSES = frozenset({"verified", "deployed", "measured", "closed"})


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
    verification: ImprovementCaseVerification = Field(default_factory=ImprovementCaseVerification)
    workflow_version: str = "improvement_v1"
    deployment: ImprovementCaseDeployment = Field(default_factory=ImprovementCaseDeployment)
    measurement: ImprovementCaseMeasurement = Field(default_factory=ImprovementCaseMeasurement)
    created_at: str | None = None
    updated_at: str | None = None


class ImprovementCaseObservation(BaseModel):
    title: str
    observed_failure: str
    cause_class: str
    source_type: str
    source_ref: str
    source_notes: str | None = None
    workflow_version: str = "improvement_v1"


class ImprovementCaseRegistry(BaseModel):
    schema_name: str = IMPROVEMENT_CASE_SCHEMA_NAME
    schema_version: str = IMPROVEMENT_CASE_SCHEMA_VERSION
    cases: list[ImprovementCase] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ImprovementCaseContractIssue:
    case_id: str | None
    field: str
    message: str


def resolve_improvement_cases_path(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    raw_path = Path(path) if path is not None else DEFAULT_IMPROVEMENT_CASES_PATH
    if raw_path.is_absolute():
        return raw_path
    return (project_root or repo_root()) / raw_path


def empty_improvement_case_registry() -> ImprovementCaseRegistry:
    return ImprovementCaseRegistry()


def load_improvement_case_registry(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> ImprovementCaseRegistry:
    resolved_path = resolve_improvement_cases_path(path, project_root=project_root)
    if not resolved_path.exists():
        return empty_improvement_case_registry()
    payload = yaml.safe_load(resolved_path.read_text()) or {}
    return ImprovementCaseRegistry.model_validate(payload)


def load_improvement_case_registry_for_validation(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> tuple[ImprovementCaseRegistry, list[ImprovementCaseContractIssue]]:
    try:
        return (
            load_improvement_case_registry(path, project_root=project_root),
            [],
        )
    except Exception as exc:
        return (
            empty_improvement_case_registry(),
            [
                ImprovementCaseContractIssue(
                    case_id=None,
                    field="registry",
                    message=f"Unable to load improvement case registry: {exc}",
                )
            ],
        )


def write_improvement_case_registry(
    registry: ImprovementCaseRegistry,
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    resolved_path = resolve_improvement_cases_path(path, project_root=project_root)
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


def _improvement_payload_fingerprint(payload: object) -> str:
    encoded = yaml.safe_dump(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _deterministic_case_id(source_type: str, source_ref: str) -> str:
    digest = _improvement_payload_fingerprint(
        {"source_type": source_type, "source_ref": source_ref}
    )
    return f"IC-{digest[:12].upper()}"


def _clip_text(value: object, *, max_length: int = 140) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def _cause_class_from_text(*values: object, default: str = "missing_test") -> str:
    text = " ".join(str(value or "").lower() for value in values)
    if any(token in text for token in ("permission", "auth", "credential", "secret")):
        return "unsafe_permission"
    if "tool" in text:
        return "bad_tool"
    if any(token in text for token in ("owner", "ownership", "handoff")):
        return "unclear_ownership"
    if any(token in text for token in ("context", "provenance", "artifact", "source ref")):
        return "missing_context"
    if any(token in text for token in ("test", "eval", "coverage", "fixture")):
        return "missing_test"
    if any(token in text for token in ("contract", "constraint", "schema", "policy", "gate")):
        return "missing_constraint"
    if any(token in text for token in ("pattern", "duplicate", "budget", "lint", "ruff")):
        return "bad_pattern"
    return default


def _has_artifact_payload(case: ImprovementCase) -> bool:
    return any(
        isinstance(value, str) and value.strip()
        for value in (
            case.artifact.artifact_type,
            case.artifact.target_path,
            case.artifact.description,
        )
    )


def _artifact_path_issues(
    case: ImprovementCase,
    *,
    project_root: Path,
) -> list[ImprovementCaseContractIssue]:
    if _empty_text(case.artifact.target_path):
        return [
            _case_issue(
                case,
                "artifact.target_path",
                "Executable artifact target path is required.",
            )
        ]

    raw_target_path = Path(case.artifact.target_path)
    if raw_target_path.is_absolute():
        return [
            _case_issue(
                case,
                "artifact.target_path",
                "Executable artifact target path must be repo-relative.",
            )
        ]

    resolved_target_path = (project_root / raw_target_path).resolve()
    try:
        resolved_target_path.relative_to(project_root.resolve())
    except ValueError:
        return [
            _case_issue(
                case,
                "artifact.target_path",
                "Executable artifact target path must stay inside the repo.",
            )
        ]

    if not resolved_target_path.exists():
        return [
            _case_issue(
                case,
                "artifact.target_path",
                "Executable artifact target path does not exist.",
            )
        ]
    return []


def validate_improvement_case_registry(
    registry: ImprovementCaseRegistry,
    *,
    project_root: Path | None = None,
) -> list[ImprovementCaseContractIssue]:
    issues: list[ImprovementCaseContractIssue] = []
    root = (project_root or repo_root()).resolve()
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
        requires_artifact = case.status in CONVERTED_IMPROVEMENT_STATUSES
        has_artifact_payload = _has_artifact_payload(case)
        if (requires_artifact or has_artifact_payload) and (
            case.artifact.artifact_type not in IMPROVEMENT_ARTIFACT_TYPES
        ):
            issues.append(
                _case_issue(
                    case,
                    "artifact.artifact_type",
                    f"Unknown artifact type '{case.artifact.artifact_type}'.",
                )
            )
        if requires_artifact or has_artifact_payload:
            issues.extend(_artifact_path_issues(case, project_root=root))
        if (requires_artifact or has_artifact_payload) and _empty_text(
            case.artifact.description
        ):
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
        if requires_artifact and not has_verification_command and not has_acceptance_condition:
            issues.append(
                _case_issue(
                    case,
                    "verification",
                    "At least one verification command or acceptance condition is required.",
                )
            )
        if (
            case.status in VERIFIED_IMPROVEMENT_STATUSES
            and not case.verification.catches_old_failure
        ):
            issues.append(
                _case_issue(
                    case,
                    "verification.catches_old_failure",
                    "Verification must explicitly catch the old failure.",
                )
            )
        if (
            case.status in VERIFIED_IMPROVEMENT_STATUSES
            and not case.verification.allows_good_changes
        ):
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
    open_unconverted_cases = [case for case in cases if case.status == "open"]
    converted_unverified_cases = [case for case in cases if case.status == "converted"]
    verified_undeployed_cases = [case for case in cases if case.status == "verified"]
    repeated_cause_classes = {
        cause_class: count
        for cause_class, count in Counter(case.cause_class for case in cases).items()
        if cause_class and count > 1
    }
    oldest_open_case = min(
        open_unconverted_cases,
        key=lambda case: case.created_at or "",
        default=None,
    )
    return {
        "schema_name": "improvement_case_summary",
        "schema_version": "1.0",
        "case_count": len(cases),
        "status_counts": dict(Counter(case.status for case in cases)),
        "cause_class_counts": dict(Counter(case.cause_class for case in cases)),
        "artifact_type_counts": dict(
            Counter(case.artifact.artifact_type for case in cases if case.artifact.artifact_type)
        ),
        "workflow_version_counts": dict(Counter(case.workflow_version for case in cases)),
        "source_type_counts": dict(Counter(case.source.source_type for case in cases)),
        "measured_case_count": len(measured_cases),
        "actionable_buckets": {
            "open_unconverted_count": len(open_unconverted_cases),
            "converted_unverified_count": len(converted_unverified_cases),
            "verified_undeployed_count": len(verified_undeployed_cases),
            "oldest_open_case_id": oldest_open_case.case_id if oldest_open_case else None,
            "repeated_cause_classes": repeated_cause_classes,
        },
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
    artifact_type: str | None = None,
    artifact_target_path: str | None = None,
    artifact_description: str | None = None,
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
    project_root: Path | None = None,
) -> ImprovementCase:
    root = project_root or repo_root()
    registry = load_improvement_case_registry(path, project_root=root)
    now = utcnow().isoformat()
    commands = verification_commands or []
    acceptance_conditions = acceptance_conditions or []
    has_verification_evidence = bool(commands or acceptance_conditions)
    case = ImprovementCase(
        case_id=case_id or f"IC-{utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8]}",
        title=title,
        status=status,
        cause_class=cause_class,
        observed_failure=observed_failure,
        source=ImprovementCaseSource(source_type=source_type, source_ref=source_ref),
        artifact=ImprovementCaseArtifact(
            artifact_type=artifact_type or "",
            target_path=artifact_target_path or "",
            description=artifact_description or "",
        ),
        verification=ImprovementCaseVerification(
            commands=commands,
            acceptance_conditions=acceptance_conditions,
            catches_old_failure=has_verification_evidence,
            allows_good_changes=has_verification_evidence,
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
    issues = validate_improvement_case_registry(candidate_registry, project_root=root)
    if issues:
        issue_lines = "; ".join(
            f"{issue.case_id or 'registry'} {issue.field}: {issue.message}" for issue in issues
        )
        raise ValueError(f"Invalid improvement case registry: {issue_lines}")
    write_improvement_case_registry(candidate_registry, path, project_root=root)
    return case


def import_improvement_case_observations(
    observations: list[ImprovementCaseObservation],
    *,
    path: str | Path | None = None,
    project_root: Path | None = None,
    dry_run: bool = False,
) -> dict:
    root = project_root or repo_root()
    registry = load_improvement_case_registry(path, project_root=root)
    existing_refs = {
        (case.source.source_type, case.source.source_ref)
        for case in registry.cases
        if case.source.source_ref
    }
    imported_cases: list[ImprovementCase] = []
    skipped: list[dict] = []
    now = utcnow().isoformat()

    for observation in observations:
        source_key = (observation.source_type, observation.source_ref)
        if source_key in existing_refs:
            skipped.append(
                {
                    "source_type": observation.source_type,
                    "source_ref": observation.source_ref,
                    "reason": "already_imported",
                }
            )
            continue

        case = ImprovementCase(
            case_id=_deterministic_case_id(observation.source_type, observation.source_ref),
            title=observation.title,
            status="open",
            cause_class=observation.cause_class,
            observed_failure=observation.observed_failure,
            source=ImprovementCaseSource(
                source_type=observation.source_type,
                source_ref=observation.source_ref,
                notes=observation.source_notes,
            ),
            workflow_version=observation.workflow_version,
            created_at=now,
            updated_at=now,
        )
        existing_refs.add(source_key)
        imported_cases.append(case)

    candidate_registry = ImprovementCaseRegistry(
        schema_name=registry.schema_name,
        schema_version=registry.schema_version,
        cases=[*registry.cases, *imported_cases],
    )
    issues = validate_improvement_case_registry(candidate_registry, project_root=root)
    if issues:
        issue_lines = "; ".join(
            f"{issue.case_id or 'registry'} {issue.field}: {issue.message}" for issue in issues
        )
        raise ValueError(f"Invalid improvement case import: {issue_lines}")
    if imported_cases and not dry_run:
        write_improvement_case_registry(candidate_registry, path, project_root=root)

    return {
        "schema_name": "improvement_case_import",
        "schema_version": "1.0",
        "dry_run": dry_run,
        "candidate_count": len(observations),
        "imported_count": len(imported_cases),
        "skipped_count": len(skipped),
        "imported": build_improvement_case_manifest(
            ImprovementCaseRegistry(cases=imported_cases)
        ),
        "skipped": skipped,
    }


def collect_hygiene_finding_observations(
    findings: list[object],
    *,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
) -> list[ImprovementCaseObservation]:
    observations: list[ImprovementCaseObservation] = []
    for finding in findings[:limit]:
        kind = str(getattr(finding, "kind", "hygiene"))
        relative_path = getattr(finding, "relative_path", None)
        lineno = getattr(finding, "lineno", None)
        message = str(getattr(finding, "message", "Hygiene finding."))
        rendered = finding.render() if hasattr(finding, "render") else message
        source_ref = f"hygiene:{_improvement_payload_fingerprint(rendered)[:16]}"
        observations.append(
            ImprovementCaseObservation(
                title=f"Hygiene finding: {_clip_text(kind, max_length=80)}",
                observed_failure=rendered,
                cause_class=_cause_class_from_text(kind, message, default="bad_pattern"),
                source_type="hygiene_finding",
                source_ref=source_ref,
                source_notes=(
                    f"{relative_path}:{lineno}" if relative_path and lineno else relative_path
                ),
                workflow_version=workflow_version,
            )
        )
    return observations


def collect_eval_failure_case_observations(
    session,
    *,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
) -> list[ImprovementCaseObservation]:
    from sqlalchemy import select

    from app.db.models import EvalFailureCase

    rows = (
        session.execute(
            select(EvalFailureCase)
            .where(EvalFailureCase.status.notin_(("resolved", "suppressed")))
            .order_by(EvalFailureCase.updated_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    observations: list[ImprovementCaseObservation] = []
    for row in rows:
        observed_failure = (
            f"{row.problem_statement} Observed: {row.observed_behavior} "
            f"Expected: {row.expected_behavior}"
        )
        observations.append(
            ImprovementCaseObservation(
                title=f"Eval failure: {_clip_text(row.problem_statement, max_length=100)}",
                observed_failure=observed_failure,
                cause_class=_cause_class_from_text(
                    row.failure_classification,
                    row.problem_statement,
                    row.diagnosis,
                    default="missing_test",
                ),
                source_type="eval_failure",
                source_ref=f"eval_failure_case:{row.id}",
                source_notes=f"surface={row.surface}; severity={row.severity}; status={row.status}",
                workflow_version=workflow_version,
            )
        )
    return observations


def collect_failed_agent_task_observations(
    session,
    *,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
) -> list[ImprovementCaseObservation]:
    from sqlalchemy import select

    from app.db.models import AgentTask, AgentTaskStatus

    rows = (
        session.execute(
            select(AgentTask)
            .where(AgentTask.status == AgentTaskStatus.FAILED.value)
            .order_by(AgentTask.updated_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        ImprovementCaseObservation(
            title=f"Failed agent task: {_clip_text(row.task_type, max_length=100)}",
            observed_failure=row.error_message
            or f"Agent task {row.task_type} failed without an error message.",
            cause_class=_cause_class_from_text(
                row.task_type,
                row.error_message,
                default="missing_context",
            ),
            source_type="agent_task",
            source_ref=f"agent_task:{row.id}",
            source_notes=f"task_type={row.task_type}; workflow_version={row.workflow_version}",
            workflow_version=workflow_version,
        )
        for row in rows
    ]


def collect_failed_agent_verification_observations(
    session,
    *,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
) -> list[ImprovementCaseObservation]:
    from sqlalchemy import select

    from app.db.models import AgentTaskVerification

    rows = (
        session.execute(
            select(AgentTaskVerification)
            .where(AgentTaskVerification.outcome.in_(("failed", "error")))
            .order_by(AgentTaskVerification.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    observations: list[ImprovementCaseObservation] = []
    for row in rows:
        reasons = "; ".join(str(reason) for reason in (row.reasons_json or []))
        observations.append(
            ImprovementCaseObservation(
                title=f"Failed agent verification: {_clip_text(row.verifier_type, max_length=90)}",
                observed_failure=reasons
                or f"Agent verification {row.verifier_type} ended with outcome {row.outcome}.",
                cause_class=_cause_class_from_text(
                    row.verifier_type,
                    reasons,
                    default="missing_constraint",
                ),
                source_type="agent_verification",
                source_ref=f"agent_verification:{row.id}",
                source_notes=f"target_task_id={row.target_task_id}; outcome={row.outcome}",
                workflow_version=workflow_version,
            )
        )
    return observations
