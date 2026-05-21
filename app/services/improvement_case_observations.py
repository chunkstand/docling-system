from __future__ import annotations

from pathlib import Path

from app.core.files import repo_root
from app.core.time import utcnow
from app.services.improvement_case_models import (
    ImprovementCase,
    ImprovementCaseArtifact,
    ImprovementCaseObservation,
    ImprovementCaseRegistry,
    ImprovementCaseSource,
    ImprovementCaseVerification,
    classify_improvement_case_cause,
    clip_improvement_case_text,
    deterministic_improvement_case_id,
    improvement_payload_fingerprint,
)
from app.services.improvement_case_registry import (
    build_improvement_case_manifest,
    load_improvement_case_registry,
    validate_improvement_case_registry,
    write_improvement_case_registry,
)


def import_improvement_case_observations(
    observations: list[ImprovementCaseObservation],
    *,
    path: str | Path | None = None,
    project_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
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

        imported_case = ImprovementCase(
            case_id=deterministic_improvement_case_id(
                observation.source_type,
                observation.source_ref,
            ),
            title=observation.title,
            status="open",
            cause_class=observation.cause_class,
            observed_failure=observation.observed_failure,
            source=ImprovementCaseSource(
                source_type=observation.source_type,
                source_ref=observation.source_ref,
                notes=observation.source_notes,
            ),
            artifact=ImprovementCaseArtifact(
                artifact_type=observation.artifact_type or "",
                target_path=observation.artifact_target_path or "",
                description=observation.artifact_description or "",
            ),
            verification=ImprovementCaseVerification(
                commands=observation.verification_commands,
                acceptance_conditions=observation.acceptance_conditions,
            ),
            workflow_version=observation.workflow_version,
            created_at=now,
            updated_at=now,
        )
        existing_refs.add(source_key)
        imported_cases.append(imported_case)

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
        "imported": build_improvement_case_manifest(ImprovementCaseRegistry(cases=imported_cases)),
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
        source_ref = f"hygiene:{improvement_payload_fingerprint(rendered)[:16]}"
        observations.append(
            ImprovementCaseObservation(
                title=f"Hygiene finding: {clip_improvement_case_text(kind, max_length=80)}",
                observed_failure=rendered,
                cause_class=classify_improvement_case_cause(
                    kind,
                    message,
                    default="bad_pattern",
                ),
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

    from app.db.public.evaluation_feedback import EvalFailureCase

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
    observations: list[object] = []
    for row in rows:
        observed_failure = (
            f"{row.problem_statement} Observed: {row.observed_behavior} "
            f"Expected: {row.expected_behavior}"
        )
        observations.append(
            ImprovementCaseObservation(
                title=(
                    f"Eval failure: "
                    f"{clip_improvement_case_text(row.problem_statement, max_length=100)}"
                ),
                observed_failure=observed_failure,
                cause_class=classify_improvement_case_cause(
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

    from app.db.public.agent_tasks import AgentTask, AgentTaskStatus

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
            title=(
                f"Failed agent task: "
                f"{clip_improvement_case_text(row.task_type, max_length=100)}"
            ),
            observed_failure=row.error_message
            or f"Agent task {row.task_type} failed without an error message.",
            cause_class=classify_improvement_case_cause(
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

    from app.db.public.agent_tasks import AgentTaskVerification

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
                title=(
                    f"Failed agent verification: "
                    f"{clip_improvement_case_text(row.verifier_type, max_length=90)}"
                ),
                observed_failure=reasons
                or f"Agent verification {row.verifier_type} ended with outcome {row.outcome}.",
                cause_class=classify_improvement_case_cause(
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
