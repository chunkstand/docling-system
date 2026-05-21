from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskOutcome,
    AgentTaskStatus,
    AgentTaskVerification,
    AgentTaskVerificationOutcome,
)
from app.schemas.agent_task_core import (
    AgentTaskAnalyticsSummaryResponse,
    AgentTaskApprovalTrendPointResponse,
    AgentTaskApprovalTrendResponse,
    AgentTaskTrendPointResponse,
    AgentTaskTrendResponse,
    AgentTaskVerificationTrendPointResponse,
    AgentTaskVerificationTrendResponse,
    AgentTaskWorkflowVersionSummaryResponse,
)
from app.services.agent_task_metric_utils import (
    bucket_start,
    float_value,
    list_approval_trend_rows,
    list_task_attempt_rows,
    list_task_trend_rows,
    list_verification_trend_rows,
    median,
    percentile,
)


def get_agent_task_analytics_summary(session: Session) -> AgentTaskAnalyticsSummaryResponse:
    status_counts = {
        status: int(count)
        for status, count in session.execute(
            select(AgentTask.status, func.count().label("task_count")).group_by(AgentTask.status)
        ).all()
    }
    outcome_counts = {
        label: int(count)
        for label, count in session.execute(
            select(AgentTaskOutcome.outcome_label, func.count().label("outcome_count")).group_by(
                AgentTaskOutcome.outcome_label
            )
        ).all()
    }
    verification_counts = {
        outcome: int(count)
        for outcome, count in session.execute(
            select(
                AgentTaskVerification.outcome,
                func.count().label("verification_count"),
            ).group_by(AgentTaskVerification.outcome)
        ).all()
    }
    task_count = sum(status_counts.values())
    approval_required_count = session.execute(
        select(func.count()).select_from(AgentTask).where(AgentTask.requires_approval.is_(True))
    ).scalar_one()
    approved_task_count = session.execute(
        select(func.count()).select_from(AgentTask).where(AgentTask.approved_at.is_not(None))
    ).scalar_one()
    rejected_task_count = session.execute(
        select(func.count()).select_from(AgentTask).where(AgentTask.rejected_at.is_not(None))
    ).scalar_one()
    labeled_task_count = session.execute(
        select(func.count(func.distinct(AgentTaskOutcome.task_id))).select_from(AgentTaskOutcome)
    ).scalar_one()
    terminal_durations = session.execute(
        select(AgentTask.started_at, AgentTask.completed_at).where(
            AgentTask.status.in_(
                (
                    AgentTaskStatus.COMPLETED.value,
                    AgentTaskStatus.FAILED.value,
                    AgentTaskStatus.REJECTED.value,
                )
            ),
            AgentTask.started_at.is_not(None),
            AgentTask.completed_at.is_not(None),
        )
    ).all()
    avg_terminal_duration_seconds = None
    if terminal_durations:
        avg_terminal_duration_seconds = sum(
            max(0.0, (completed_at - started_at).total_seconds())
            for started_at, completed_at in terminal_durations
        ) / len(terminal_durations)

    return AgentTaskAnalyticsSummaryResponse(
        task_count=task_count,
        completed_count=status_counts.get(AgentTaskStatus.COMPLETED.value, 0),
        failed_count=status_counts.get(AgentTaskStatus.FAILED.value, 0),
        rejected_count=status_counts.get(AgentTaskStatus.REJECTED.value, 0),
        awaiting_approval_count=status_counts.get(AgentTaskStatus.AWAITING_APPROVAL.value, 0),
        processing_count=status_counts.get(AgentTaskStatus.PROCESSING.value, 0),
        approval_required_count=approval_required_count,
        approved_task_count=approved_task_count,
        rejected_task_count=rejected_task_count,
        labeled_task_count=labeled_task_count,
        outcome_label_counts=dict(outcome_counts),
        verification_outcome_counts=dict(verification_counts),
        avg_terminal_duration_seconds=avg_terminal_duration_seconds,
    )


def list_agent_task_workflow_summaries(
    session: Session,
) -> list[AgentTaskWorkflowVersionSummaryResponse]:
    status_rows = session.execute(
        select(
            AgentTask.workflow_version,
            AgentTask.status,
            func.count().label("task_count"),
        ).group_by(AgentTask.workflow_version, AgentTask.status)
    ).all()
    approved_rows = session.execute(
        select(AgentTask.workflow_version, func.count().label("task_count"))
        .where(AgentTask.approved_at.is_not(None))
        .group_by(AgentTask.workflow_version)
    ).all()
    rejected_rows = session.execute(
        select(AgentTask.workflow_version, func.count().label("task_count"))
        .where(AgentTask.rejected_at.is_not(None))
        .group_by(AgentTask.workflow_version)
    ).all()
    labeled_rows = session.execute(
        select(
            AgentTask.workflow_version,
            func.count(func.distinct(AgentTaskOutcome.task_id)).label("task_count"),
        )
        .join(AgentTask, AgentTask.id == AgentTaskOutcome.task_id)
        .group_by(AgentTask.workflow_version)
    ).all()
    outcome_rows = session.execute(
        select(
            AgentTask.workflow_version,
            AgentTaskOutcome.outcome_label,
            func.count().label("outcome_count"),
        )
        .join(AgentTask, AgentTask.id == AgentTaskOutcome.task_id)
        .group_by(AgentTask.workflow_version, AgentTaskOutcome.outcome_label)
    ).all()
    verification_rows = session.execute(
        select(
            AgentTask.workflow_version,
            AgentTaskVerification.outcome,
            func.count().label("verification_count"),
        )
        .join(AgentTask, AgentTask.id == AgentTaskVerification.target_task_id)
        .group_by(AgentTask.workflow_version, AgentTaskVerification.outcome)
    ).all()
    duration_rows = session.execute(
        select(
            AgentTask.workflow_version,
            AgentTask.started_at,
            AgentTask.completed_at,
        ).where(
            AgentTask.status.in_(
                (
                    AgentTaskStatus.COMPLETED.value,
                    AgentTaskStatus.FAILED.value,
                    AgentTaskStatus.REJECTED.value,
                )
            ),
            AgentTask.started_at.is_not(None),
            AgentTask.completed_at.is_not(None),
        )
    ).all()

    status_counts_by_version: dict[str, Counter[str]] = defaultdict(Counter)
    for workflow_version, task_status, count in status_rows:
        status_counts_by_version[workflow_version][task_status] = int(count)

    approved_by_version = {
        workflow_version: int(count) for workflow_version, count in approved_rows
    }
    rejected_by_version = {
        workflow_version: int(count) for workflow_version, count in rejected_rows
    }
    labeled_by_version = {workflow_version: int(count) for workflow_version, count in labeled_rows}
    outcome_counts_by_version: dict[str, Counter[str]] = defaultdict(Counter)
    for workflow_version, outcome_label, count in outcome_rows:
        outcome_counts_by_version[workflow_version][outcome_label] = int(count)
    verification_counts_by_version: dict[str, Counter[str]] = defaultdict(Counter)
    for workflow_version, outcome, count in verification_rows:
        verification_counts_by_version[workflow_version][outcome] = int(count)
    durations_by_version: dict[str, list[float]] = defaultdict(list)
    for workflow_version, started_at, completed_at in duration_rows:
        durations_by_version[workflow_version].append(
            max(0.0, (completed_at - started_at).total_seconds())
        )

    workflow_versions = {workflow_version for workflow_version, *_rest in status_rows}
    summaries: list[AgentTaskWorkflowVersionSummaryResponse] = []
    for workflow_version in sorted(workflow_versions):
        status_counts = status_counts_by_version[workflow_version]
        durations = durations_by_version.get(workflow_version, [])
        summaries.append(
            AgentTaskWorkflowVersionSummaryResponse(
                workflow_version=workflow_version,
                task_count=sum(status_counts.values()),
                completed_count=status_counts.get(AgentTaskStatus.COMPLETED.value, 0),
                failed_count=status_counts.get(AgentTaskStatus.FAILED.value, 0),
                rejected_count=status_counts.get(AgentTaskStatus.REJECTED.value, 0),
                approved_task_count=approved_by_version.get(workflow_version, 0),
                rejected_task_count=rejected_by_version.get(workflow_version, 0),
                labeled_task_count=labeled_by_version.get(workflow_version, 0),
                outcome_label_counts=dict(outcome_counts_by_version[workflow_version]),
                verification_outcome_counts=dict(verification_counts_by_version[workflow_version]),
                avg_terminal_duration_seconds=(
                    sum(durations) / len(durations) if durations else None
                ),
            )
        )
    summaries.sort(key=lambda row: (-row.task_count, row.workflow_version))
    return summaries


def get_agent_task_trends(
    session: Session,
    *,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskTrendResponse:
    task_rows = list_task_trend_rows(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )
    task_created_at_by_id = {task_id: created_at for task_id, created_at, _status in task_rows}
    attempts = list_task_attempt_rows(session, task_ids=set(task_created_at_by_id))
    bucket_rows: dict[datetime, dict] = defaultdict(
        lambda: {
            "created_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "rejected_count": 0,
            "awaiting_approval_count": 0,
            "queue_latencies": [],
            "execution_latencies": [],
        }
    )
    for _task_id, created_at, task_status in task_rows:
        bucket_key = bucket_start(created_at, bucket)
        row = bucket_rows[bucket_key]
        row["created_count"] += 1
        if task_status == AgentTaskStatus.COMPLETED.value:
            row["completed_count"] += 1
        elif task_status == AgentTaskStatus.FAILED.value:
            row["failed_count"] += 1
        elif task_status == AgentTaskStatus.REJECTED.value:
            row["rejected_count"] += 1
        elif task_status == AgentTaskStatus.AWAITING_APPROVAL.value:
            row["awaiting_approval_count"] += 1
    for attempt in attempts:
        task_created_at = task_created_at_by_id.get(attempt.task_id)
        if task_created_at is None:
            continue
        bucket_key = bucket_start(task_created_at, bucket)
        performance = attempt.performance_json or {}
        queue_latency_ms = float_value(performance, "queue_latency_ms")
        execution_latency_ms = float_value(performance, "execution_latency_ms")
        if queue_latency_ms > 0:
            bucket_rows[bucket_key]["queue_latencies"].append(queue_latency_ms)
        if execution_latency_ms > 0:
            bucket_rows[bucket_key]["execution_latencies"].append(execution_latency_ms)

    series = [
        AgentTaskTrendPointResponse(
            bucket_start=bucket_key,
            task_type=task_type,
            workflow_version=workflow_version,
            created_count=values["created_count"],
            completed_count=values["completed_count"],
            failed_count=values["failed_count"],
            rejected_count=values["rejected_count"],
            awaiting_approval_count=values["awaiting_approval_count"],
            median_queue_latency_ms=median(values["queue_latencies"]),
            p95_queue_latency_ms=percentile(values["queue_latencies"], 0.95),
            median_execution_latency_ms=median(values["execution_latencies"]),
            p95_execution_latency_ms=percentile(values["execution_latencies"], 0.95),
        )
        for bucket_key, values in sorted(bucket_rows.items())
    ]
    return AgentTaskTrendResponse(
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
        series=series,
    )


def get_agent_verification_trends(
    session: Session,
    *,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskVerificationTrendResponse:
    rows = list_verification_trend_rows(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )
    bucket_rows: dict[datetime, dict] = defaultdict(
        lambda: {"passed_count": 0, "failed_count": 0, "error_count": 0}
    )
    for created_at, outcome in rows:
        bucket_key = bucket_start(created_at, bucket)
        if outcome == AgentTaskVerificationOutcome.PASSED.value:
            bucket_rows[bucket_key]["passed_count"] += 1
        elif outcome == AgentTaskVerificationOutcome.FAILED.value:
            bucket_rows[bucket_key]["failed_count"] += 1
        else:
            bucket_rows[bucket_key]["error_count"] += 1
    return AgentTaskVerificationTrendResponse(
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
        series=[
            AgentTaskVerificationTrendPointResponse(
                bucket_start=bucket_key,
                task_type=task_type,
                workflow_version=workflow_version,
                **values,
            )
            for bucket_key, values in sorted(bucket_rows.items())
        ],
    )


def get_agent_approval_trends(
    session: Session,
    *,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskApprovalTrendResponse:
    rows = list_approval_trend_rows(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )
    bucket_rows: dict[datetime, dict] = defaultdict(
        lambda: {"approval_count": 0, "rejection_count": 0}
    )
    for approved_at, rejected_at in rows:
        if approved_at is not None:
            bucket_rows[bucket_start(approved_at, bucket)]["approval_count"] += 1
        if rejected_at is not None:
            bucket_rows[bucket_start(rejected_at, bucket)]["rejection_count"] += 1
    return AgentTaskApprovalTrendResponse(
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
        series=[
            AgentTaskApprovalTrendPointResponse(
                bucket_start=bucket_key,
                task_type=task_type,
                workflow_version=workflow_version,
                **values,
            )
            for bucket_key, values in sorted(bucket_rows.items())
        ],
    )


__all__ = [
    "get_agent_approval_trends",
    "get_agent_task_analytics_summary",
    "get_agent_task_trends",
    "get_agent_verification_trends",
    "list_agent_task_workflow_summaries",
]
