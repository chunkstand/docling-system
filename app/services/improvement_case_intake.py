from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

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


def _validate_import_source(source: str) -> None:
    if source not in IMPROVEMENT_CASE_IMPORT_SOURCES:
        allowed = ", ".join(sorted(IMPROVEMENT_CASE_IMPORT_SOURCES))
        raise ValueError(
            f"Unknown improvement case import source '{source}'. Expected one of: {allowed}."
        )


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
    *,
    source: str = "hygiene",
    limit: int = 50,
    workflow_version: str = "improvement_v1",
    path: str | Path | None = None,
    dry_run: bool = False,
    session_factory: Callable | None = None,
    project_root: Path | None = None,
) -> dict:
    observations = collect_improvement_case_import_observations(
        source=source,
        limit=limit,
        workflow_version=workflow_version,
        session_factory=session_factory,
        project_root=project_root,
    )
    return import_improvement_case_observations(
        observations,
        path=path,
        project_root=project_root,
        dry_run=dry_run,
    )
