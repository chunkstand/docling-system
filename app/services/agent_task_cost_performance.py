from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import AgentTaskAttempt
from app.schemas.agent_task_core import (
    AgentTaskCostSummaryResponse,
    AgentTaskCostTrendPointResponse,
    AgentTaskCostTrendResponse,
    AgentTaskPerformanceSummaryResponse,
    AgentTaskPerformanceTrendPointResponse,
    AgentTaskPerformanceTrendResponse,
)
from app.services.agent_task_metric_utils import (
    bucket_start,
    float_value,
    int_value,
    list_task_attempt_rows,
    median,
    percentile,
    task_id_select_statement,
)


def cost_summary_from_attempts(
    attempts: list[AgentTaskAttempt],
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskCostSummaryResponse:
    instrumented_attempt_count = 0
    estimated_usd_total = 0.0
    model_call_count = 0
    embedding_count = 0
    replay_query_count = 0
    evaluation_query_count = 0
    for attempt in attempts:
        cost = attempt.cost_json or {}
        if cost:
            instrumented_attempt_count += 1
        estimated_usd_total += float_value(cost, "estimated_usd")
        model_call_count += int_value(cost, "call_count")
        embedding_count += int_value(cost, "embedding_count")
        replay_query_count += int_value(cost, "replay_query_count")
        evaluation_query_count += int_value(cost, "evaluation_query_count")
    return AgentTaskCostSummaryResponse(
        task_type=task_type,
        workflow_version=workflow_version,
        attempt_count=len(attempts),
        instrumented_attempt_count=instrumented_attempt_count,
        estimated_usd_total=estimated_usd_total,
        model_call_count=model_call_count,
        embedding_count=embedding_count,
        replay_query_count=replay_query_count,
        evaluation_query_count=evaluation_query_count,
    )


def performance_summary_from_attempts(
    attempts: list[AgentTaskAttempt],
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskPerformanceSummaryResponse:
    queue_latencies: list[float] = []
    execution_latencies: list[float] = []
    end_to_end_latencies: list[float] = []
    instrumented_attempt_count = 0
    for attempt in attempts:
        performance = attempt.performance_json or {}
        if performance:
            instrumented_attempt_count += 1
        queue_latency = float_value(performance, "queue_latency_ms")
        execution_latency = float_value(performance, "execution_latency_ms")
        end_to_end_latency = float_value(performance, "end_to_end_latency_ms")
        if queue_latency > 0:
            queue_latencies.append(queue_latency)
        if execution_latency > 0:
            execution_latencies.append(execution_latency)
        if end_to_end_latency > 0:
            end_to_end_latencies.append(end_to_end_latency)
    return AgentTaskPerformanceSummaryResponse(
        task_type=task_type,
        workflow_version=workflow_version,
        attempt_count=len(attempts),
        instrumented_attempt_count=instrumented_attempt_count,
        median_queue_latency_ms=median(queue_latencies),
        p95_queue_latency_ms=percentile(queue_latencies, 0.95),
        median_execution_latency_ms=median(execution_latencies),
        p95_execution_latency_ms=percentile(execution_latencies, 0.95),
        median_end_to_end_latency_ms=median(end_to_end_latencies),
        p95_end_to_end_latency_ms=percentile(end_to_end_latencies, 0.95),
    )


def get_agent_task_cost_summary(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskCostSummaryResponse:
    attempts = list_task_attempt_rows(
        session,
        task_id_select=task_id_select_statement(
            task_type=task_type,
            workflow_version=workflow_version,
        ),
    )
    return cost_summary_from_attempts(
        attempts,
        task_type=task_type,
        workflow_version=workflow_version,
    )


def get_agent_task_cost_trends(
    session: Session,
    *,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskCostTrendResponse:
    attempts = list_task_attempt_rows(
        session,
        task_id_select=task_id_select_statement(
            task_type=task_type,
            workflow_version=workflow_version,
        ),
    )
    bucket_rows: dict[datetime, dict] = defaultdict(
        lambda: {
            "attempt_count": 0,
            "estimated_usd_total": 0.0,
            "replay_query_count": 0,
            "evaluation_query_count": 0,
            "embedding_count": 0,
        }
    )
    for attempt in attempts:
        row = bucket_rows[bucket_start(attempt.created_at, bucket)]
        row["attempt_count"] += 1
        cost = attempt.cost_json or {}
        row["estimated_usd_total"] += float_value(cost, "estimated_usd")
        row["replay_query_count"] += int_value(cost, "replay_query_count")
        row["evaluation_query_count"] += int_value(cost, "evaluation_query_count")
        row["embedding_count"] += int_value(cost, "embedding_count")
    return AgentTaskCostTrendResponse(
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
        series=[
            AgentTaskCostTrendPointResponse(
                bucket_start=bucket_key,
                task_type=task_type,
                workflow_version=workflow_version,
                **values,
            )
            for bucket_key, values in sorted(bucket_rows.items())
        ],
    )


def get_agent_task_performance_summary(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskPerformanceSummaryResponse:
    attempts = list_task_attempt_rows(
        session,
        task_id_select=task_id_select_statement(
            task_type=task_type,
            workflow_version=workflow_version,
        ),
    )
    return performance_summary_from_attempts(
        attempts,
        task_type=task_type,
        workflow_version=workflow_version,
    )


def get_agent_task_performance_trends(
    session: Session,
    *,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskPerformanceTrendResponse:
    attempts = list_task_attempt_rows(
        session,
        task_id_select=task_id_select_statement(
            task_type=task_type,
            workflow_version=workflow_version,
        ),
    )
    bucket_rows: dict[datetime, dict] = defaultdict(
        lambda: {
            "attempt_count": 0,
            "queue_latencies": [],
            "execution_latencies": [],
        }
    )
    for attempt in attempts:
        row = bucket_rows[bucket_start(attempt.created_at, bucket)]
        row["attempt_count"] += 1
        performance = attempt.performance_json or {}
        queue_latency = float_value(performance, "queue_latency_ms")
        execution_latency = float_value(performance, "execution_latency_ms")
        if queue_latency > 0:
            row["queue_latencies"].append(queue_latency)
        if execution_latency > 0:
            row["execution_latencies"].append(execution_latency)
    return AgentTaskPerformanceTrendResponse(
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
        series=[
            AgentTaskPerformanceTrendPointResponse(
                bucket_start=bucket_key,
                task_type=task_type,
                workflow_version=workflow_version,
                attempt_count=values["attempt_count"],
                median_queue_latency_ms=median(values["queue_latencies"]),
                p95_queue_latency_ms=percentile(values["queue_latencies"], 0.95),
                median_execution_latency_ms=median(values["execution_latencies"]),
                p95_execution_latency_ms=percentile(values["execution_latencies"], 0.95),
            )
            for bucket_key, values in sorted(bucket_rows.items())
        ],
    )


__all__ = [
    "cost_summary_from_attempts",
    "get_agent_task_cost_summary",
    "get_agent_task_cost_trends",
    "get_agent_task_performance_summary",
    "get_agent_task_performance_trends",
    "performance_summary_from_attempts",
]
