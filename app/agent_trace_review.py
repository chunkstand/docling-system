from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.architecture_inspection import (
    ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
    inspect_architecture_contracts,
)
from app.core.files import repo_root
from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskStatus, SearchReplayRun
from app.db.session import get_session_factory
from app.hygiene import run_improvement_case_contract_checks, run_python_hygiene_checks
from app.services.improvement_cases import (
    ImprovementCaseObservation,
    collect_eval_failure_case_observations,
    collect_failed_agent_task_observations,
    collect_failed_agent_verification_observations,
)

AGENT_TRACE_REVIEW_REPORT_SCHEMA_NAME = "agent_trace_review_report"
DEFAULT_AGENT_TRACE_REVIEW_REPORT_PATH = (
    Path("build") / "architecture-governance" / "agent_trace_review_report.json"
)


def _observation_item(
    category: str,
    observation: ImprovementCaseObservation,
) -> dict[str, Any]:
    return {
        "category": category,
        "title": observation.title,
        "observed_failure": observation.observed_failure,
        "cause_class": observation.cause_class,
        "source_type": observation.source_type,
        "source_ref": observation.source_ref,
        "source_notes": observation.source_notes,
        "workflow_version": observation.workflow_version,
    }


def _collect_stale_approval_observations(
    session: Session,
    *,
    limit: int,
    workflow_version: str,
) -> list[ImprovementCaseObservation]:
    rows = (
        session.execute(
            select(AgentTask)
            .where(AgentTask.status == AgentTaskStatus.AWAITING_APPROVAL.value)
            .order_by(AgentTask.updated_at.asc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        ImprovementCaseObservation(
            title=f"Awaiting approval agent task: {row.task_type}",
            observed_failure=(
                f"Agent task {row.id} is awaiting approval for task_type={row.task_type}."
            ),
            cause_class="missing_context",
            source_type="agent_task",
            source_ref=f"agent_task_approval:{row.id}",
            source_notes=(
                f"task_type={row.task_type}; workflow_version={row.workflow_version}; "
                f"updated_at={row.updated_at.isoformat() if row.updated_at else 'unknown'}"
            ),
            workflow_version=workflow_version,
        )
        for row in rows
    ]


def _collect_search_replay_regression_observations(
    session: Session,
    *,
    limit: int,
    workflow_version: str,
) -> list[ImprovementCaseObservation]:
    rows = (
        session.execute(
            select(SearchReplayRun)
            .where(
                (SearchReplayRun.status == "failed")
                | (SearchReplayRun.failed_count > 0)
                | (
                    (SearchReplayRun.source_type != "feedback")
                    & (SearchReplayRun.zero_result_count > 0)
                )
            )
            .order_by(SearchReplayRun.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        ImprovementCaseObservation(
            title=f"Search replay regression: {row.source_type}",
            observed_failure=(
                f"Search replay run {row.id} has status={row.status}, "
                f"failed_count={row.failed_count}, zero_result_count={row.zero_result_count}, "
                f"top_result_changes={row.top_result_changes}, max_rank_shift={row.max_rank_shift}."
            ),
            cause_class="missing_test",
            source_type="search_replay",
            source_ref=f"search_replay_run:{row.id}",
            source_notes=(
                f"source_type={row.source_type}; harness_name={row.harness_name}; "
                f"reranker={row.reranker_name}:{row.reranker_version}; "
                f"retrieval_profile={row.retrieval_profile_name}; "
                f"created_at={row.created_at.isoformat() if row.created_at else 'unknown'}"
            ),
            workflow_version=workflow_version,
        )
        for row in rows
    ]


def _collect_workspace_observations(
    *,
    project_root: Path,
    limit: int,
    workflow_version: str,
    include_hygiene: bool,
    include_architecture: bool,
) -> list[ImprovementCaseObservation]:
    observations: list[ImprovementCaseObservation] = []
    if include_architecture:
        for violation in inspect_architecture_contracts(project_root)[:limit]:
            observations.append(
                ImprovementCaseObservation(
                    title=f"Architecture violation: {violation.rule_id or violation.contract}",
                    observed_failure=(
                        f"{violation.contract}.{violation.field}: {violation.message}"
                    ),
                    cause_class="missing_constraint",
                    source_type="architecture_governance",
                    source_ref=(
                        "agent-trace-review:architecture:"
                        f"{violation.rule_id or violation.contract}:"
                        f"{violation.relative_path or violation.symbol or 'global'}"
                    ),
                    source_notes=(
                        f"severity={violation.severity}; lineno={violation.lineno or 'none'}"
                    ),
                    workflow_version=workflow_version,
                )
            )
    if include_hygiene:
        findings = [
            *run_python_hygiene_checks(project_root),
            *run_improvement_case_contract_checks(project_root),
        ]
        for finding in findings[:limit]:
            observations.append(
                ImprovementCaseObservation(
                    title=f"Hygiene finding: {finding.kind}",
                    observed_failure=finding.message,
                    cause_class="bad_pattern",
                    source_type="hygiene_finding",
                    source_ref=(
                        "agent-trace-review:hygiene:"
                        f"{finding.kind}:{finding.relative_path or 'global'}"
                    ),
                    source_notes=(
                        f"relative_path={finding.relative_path or 'global'}; "
                        f"lineno={finding.lineno or 'none'}"
                    ),
                    workflow_version=workflow_version,
                )
            )
    return observations


def build_agent_trace_review_report(
    session: Session,
    *,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
    project_root: Path | None = None,
    include_workspace: bool = True,
    include_hygiene: bool = True,
    include_architecture: bool = True,
) -> dict[str, Any]:
    root = project_root or repo_root()
    categories: dict[str, list[dict[str, Any]]] = {}
    collector_payloads = {
        "failed_agent_tasks": collect_failed_agent_task_observations(
            session,
            limit=limit,
            workflow_version=workflow_version,
        ),
        "failed_agent_verifications": collect_failed_agent_verification_observations(
            session,
            limit=limit,
            workflow_version=workflow_version,
        ),
        "eval_failure_cases": collect_eval_failure_case_observations(
            session,
            limit=limit,
            workflow_version=workflow_version,
        ),
        "search_replay_regressions": _collect_search_replay_regression_observations(
            session,
            limit=limit,
            workflow_version=workflow_version,
        ),
        "stale_approval_gates": _collect_stale_approval_observations(
            session,
            limit=limit,
            workflow_version=workflow_version,
        ),
    }
    if include_workspace:
        collector_payloads["workspace_failures"] = _collect_workspace_observations(
            project_root=root,
            limit=limit,
            workflow_version=workflow_version,
            include_hygiene=include_hygiene,
            include_architecture=include_architecture,
        )

    observations: list[dict[str, Any]] = []
    for category, rows in collector_payloads.items():
        categories[category] = [_observation_item(category, row) for row in rows]
        observations.extend(categories[category])

    return {
        "schema_name": AGENT_TRACE_REVIEW_REPORT_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "generated_at": utcnow().isoformat(),
        "workflow_version": workflow_version,
        "limit": limit,
        "observation_count": len(observations),
        "categories": categories,
        "observations": observations[:limit],
        "improvement_case_intake": {
            "source": "agent-trace-review-report",
            "source_path_required": True,
            "command": (
                "uv run docling-system-improvement-case-import "
                "--source agent-trace-review-report "
                "--source-path build/architecture-governance/agent_trace_review_report.json"
            ),
        },
    }


def write_agent_trace_review_report(
    path: str | Path | None = None,
    *,
    report: dict[str, Any],
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    raw_path = Path(path) if path is not None else DEFAULT_AGENT_TRACE_REVIEW_REPORT_PATH
    resolved_path = raw_path if raw_path.is_absolute() else root / raw_path
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return resolved_path


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a trace-first agent review report for improvement intake."
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--workflow-version", default="improvement_v1")
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--skip-workspace", action="store_true")
    parser.add_argument("--skip-hygiene", action="store_true")
    parser.add_argument("--skip-architecture", action="store_true")
    args = parser.parse_args(argv)

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = build_agent_trace_review_report(
            session,
            limit=args.limit,
            workflow_version=args.workflow_version,
            include_workspace=not args.skip_workspace,
            include_hygiene=not args.skip_hygiene,
            include_architecture=not args.skip_architecture,
        )
    if args.output_path:
        write_agent_trace_review_report(args.output_path, report=payload)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
