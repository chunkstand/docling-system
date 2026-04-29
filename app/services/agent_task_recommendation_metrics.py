from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
    AgentTaskAttempt,
    AgentTaskOutcome,
    AgentTaskStatus,
    AgentTaskVerificationOutcome,
)
from app.schemas.agent_tasks import (
    AgentTaskRecommendationSummaryResponse,
    AgentTaskRecommendationTrendPointResponse,
    AgentTaskRecommendationTrendResponse,
    AgentTaskValueDensityRowResponse,
)
from app.services.agent_task_cost_performance import (
    cost_summary_from_attempts,
    performance_summary_from_attempts,
)
from app.services.agent_task_metric_utils import (
    bucket_start,
    int_value,
    list_filtered_tasks,
    list_task_attempt_rows,
    list_task_outcome_rows,
    task_ids,
)

RECOMMENDATION_FAMILY_TASK_TYPES = (
    "triage_replay_regression",
    "triage_semantic_pass",
    "triage_semantic_candidate_disagreements",
    "draft_harness_config_update",
    "draft_semantic_registry_update",
    "verify_draft_harness_config",
    "verify_draft_semantic_registry_update",
    "apply_harness_config_update",
    "apply_semantic_registry_update",
)


def _is_recommendation_task(task: AgentTask) -> bool:
    return task.task_type in {
        "triage_replay_regression",
        "triage_semantic_pass",
        "triage_semantic_candidate_disagreements",
    } or bool((task.result_json or {}).get("recommendation"))


def _task_input_task_id(task: AgentTask, key: str) -> UUID | None:
    raw_value = (task.input_json or {}).get(key)
    if not raw_value:
        return None
    try:
        return UUID(str(raw_value))
    except ValueError:
        return None


def _recommendation_family_tasks(
    all_tasks: list[AgentTask],
    recommendation_tasks: list[AgentTask],
) -> list[AgentTask]:
    recommendation_ids = task_ids(recommendation_tasks)
    if not recommendation_ids:
        return []

    draft_tasks = [
        task
        for task in all_tasks
        if task.task_type in {"draft_harness_config_update", "draft_semantic_registry_update"}
        and _task_input_task_id(task, "source_task_id") in recommendation_ids
    ]
    draft_ids = task_ids(draft_tasks)
    verification_tasks = [
        task
        for task in all_tasks
        if task.task_type
        in {"verify_draft_harness_config", "verify_draft_semantic_registry_update"}
        and _task_input_task_id(task, "target_task_id") in draft_ids
    ]
    apply_tasks = [
        task
        for task in all_tasks
        if task.task_type in {"apply_harness_config_update", "apply_semantic_registry_update"}
        and _task_input_task_id(task, "draft_task_id") in draft_ids
    ]
    family_ids = (
        recommendation_ids | draft_ids | task_ids(verification_tasks) | task_ids(apply_tasks)
    )
    return [task for task in all_tasks if task.id in family_ids]


def _recommendation_summary_from_tasks(
    tasks: list[AgentTask],
    outcomes: list[AgentTaskOutcome],
) -> AgentTaskRecommendationSummaryResponse:
    recommendation_tasks = [task for task in tasks if _is_recommendation_task(task)]
    task_by_id = {task.id: task for task in tasks}
    drafts_by_source: dict[UUID, list[AgentTask]] = defaultdict(list)
    verifications_by_draft: dict[UUID, list[AgentTask]] = defaultdict(list)
    applies_by_draft: dict[UUID, list[AgentTask]] = defaultdict(list)

    for task in tasks:
        source_task_id = _task_input_task_id(task, "source_task_id")
        target_task_id = _task_input_task_id(task, "target_task_id")
        draft_task_id = _task_input_task_id(task, "draft_task_id")
        if source_task_id is not None and task.task_type in {
            "draft_harness_config_update",
            "draft_semantic_registry_update",
        }:
            drafts_by_source[source_task_id].append(task)
        if target_task_id is not None and task.task_type in {
            "verify_draft_harness_config",
            "verify_draft_semantic_registry_update",
        }:
            verifications_by_draft[target_task_id].append(task)
        if draft_task_id is not None and task.task_type in {
            "apply_harness_config_update",
            "apply_semantic_registry_update",
        }:
            applies_by_draft[draft_task_id].append(task)

    outcomes_by_task_id: dict[UUID, list[AgentTaskOutcome]] = defaultdict(list)
    for row in outcomes:
        if row.task_id in task_by_id:
            outcomes_by_task_id[row.task_id].append(row)

    draft_count = 0
    verified_draft_count = 0
    passed_verification_count = 0
    approved_apply_count = 0
    rejected_apply_count = 0
    applied_count = 0
    useful_label_count = 0
    correct_label_count = 0
    downstream_improved_count = 0
    downstream_regressed_count = 0

    for recommendation_task in recommendation_tasks:
        draft_tasks = drafts_by_source.get(recommendation_task.id, [])
        if draft_tasks:
            draft_count += 1

        positive_labels = outcomes_by_task_id.get(recommendation_task.id, [])
        useful_label_count += sum(1 for row in positive_labels if row.outcome_label == "useful")
        correct_label_count += sum(1 for row in positive_labels if row.outcome_label == "correct")

        saw_improvement = False
        saw_regression = False
        for draft_task in draft_tasks:
            verification_tasks = verifications_by_draft.get(draft_task.id, [])
            if verification_tasks:
                verified_draft_count += 1
            passed_tasks = []
            for verification_task in verification_tasks:
                verification = ((verification_task.result_json or {}).get("payload") or {}).get(
                    "verification"
                ) or {}
                if verification.get("outcome") == AgentTaskVerificationOutcome.PASSED.value:
                    passed_tasks.append(verification_task)
                    metrics = verification.get("metrics") or {}
                    if int_value(metrics, "total_improved_count") > int_value(
                        metrics, "total_regressed_count"
                    ):
                        saw_improvement = True
                    if int_value(metrics, "total_regressed_count") > 0:
                        saw_regression = True
                elif verification.get("outcome") == AgentTaskVerificationOutcome.FAILED.value:
                    saw_regression = True
            if passed_tasks:
                passed_verification_count += 1

            apply_tasks = applies_by_draft.get(draft_task.id, [])
            if any(task.approved_at is not None for task in apply_tasks):
                approved_apply_count += 1
            if any(task.rejected_at is not None for task in apply_tasks):
                rejected_apply_count += 1
            if any(task.status == AgentTaskStatus.COMPLETED.value for task in apply_tasks):
                applied_count += 1
            for apply_task in apply_tasks:
                apply_outcomes = outcomes_by_task_id.get(apply_task.id, [])
                if any(row.outcome_label in {"useful", "correct"} for row in apply_outcomes):
                    saw_improvement = True
                if any(row.outcome_label in {"not_useful", "incorrect"} for row in apply_outcomes):
                    saw_regression = True

        if saw_improvement:
            downstream_improved_count += 1
        if saw_regression:
            downstream_regressed_count += 1

    recommendation_task_count = len(recommendation_tasks)
    return AgentTaskRecommendationSummaryResponse(
        recommendation_task_count=recommendation_task_count,
        draft_count=draft_count,
        verified_draft_count=verified_draft_count,
        passed_verification_count=passed_verification_count,
        approved_apply_count=approved_apply_count,
        rejected_apply_count=rejected_apply_count,
        applied_count=applied_count,
        useful_label_count=useful_label_count,
        correct_label_count=correct_label_count,
        downstream_improved_count=downstream_improved_count,
        downstream_regressed_count=downstream_regressed_count,
        triage_to_draft_rate=(
            draft_count / recommendation_task_count if recommendation_task_count else None
        ),
        verification_pass_rate=(
            passed_verification_count / verified_draft_count if verified_draft_count else None
        ),
        apply_rate=(applied_count / draft_count if draft_count else None),
        downstream_improvement_rate=(
            downstream_improved_count / recommendation_task_count
            if recommendation_task_count
            else None
        ),
    )


def get_agent_task_recommendation_summary(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskRecommendationSummaryResponse:
    all_tasks = list_filtered_tasks(
        session,
        workflow_version=workflow_version,
        task_types=RECOMMENDATION_FAMILY_TASK_TYPES,
    )
    recommendation_tasks = [
        task
        for task in all_tasks
        if _is_recommendation_task(task) and (task_type is None or task.task_type == task_type)
    ]
    family_tasks = _recommendation_family_tasks(all_tasks, recommendation_tasks)
    outcomes = list_task_outcome_rows(session, task_ids=task_ids(family_tasks))
    summary = _recommendation_summary_from_tasks(family_tasks, outcomes)
    summary.task_type = task_type
    summary.workflow_version = workflow_version
    return summary


def get_agent_task_recommendation_trends(
    session: Session,
    *,
    bucket: str = "day",
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskRecommendationTrendResponse:
    tasks = list_filtered_tasks(
        session,
        workflow_version=workflow_version,
        task_types=RECOMMENDATION_FAMILY_TASK_TYPES,
    )
    outcomes = list_task_outcome_rows(session, task_ids=task_ids(tasks))
    bucket_rows: dict[datetime, list[AgentTask]] = defaultdict(list)
    for task in tasks:
        if _is_recommendation_task(task) and (task_type is None or task.task_type == task_type):
            bucket_rows[bucket_start(task.created_at, bucket)].append(task)
    series: list[AgentTaskRecommendationTrendPointResponse] = []
    for bucket_key, bucket_tasks in sorted(bucket_rows.items()):
        summary = _recommendation_summary_from_tasks(
            _recommendation_family_tasks(tasks, bucket_tasks),
            outcomes,
        )
        series.append(
            AgentTaskRecommendationTrendPointResponse(
                bucket_start=bucket_key,
                task_type=task_type,
                workflow_version=workflow_version,
                recommendation_task_count=summary.recommendation_task_count,
                draft_count=summary.draft_count,
                applied_count=summary.applied_count,
                downstream_improved_count=summary.downstream_improved_count,
                downstream_regressed_count=summary.downstream_regressed_count,
            )
        )
    return AgentTaskRecommendationTrendResponse(
        bucket=bucket,
        task_type=task_type,
        workflow_version=workflow_version,
        series=series,
    )


def get_agent_task_value_density(
    session: Session,
) -> list[AgentTaskValueDensityRowResponse]:
    tasks = list_filtered_tasks(session, task_types=RECOMMENDATION_FAMILY_TASK_TYPES)
    selected_task_ids = task_ids(tasks)
    outcomes = list_task_outcome_rows(session, task_ids=selected_task_ids)
    attempts = list_task_attempt_rows(session, task_ids=selected_task_ids)
    attempts_by_task_id: dict[UUID, list[AgentTaskAttempt]] = defaultdict(list)
    for attempt in attempts:
        attempts_by_task_id[attempt.task_id].append(attempt)
    rows: list[AgentTaskValueDensityRowResponse] = []
    grouped_tasks: dict[tuple[str, str], list[AgentTask]] = defaultdict(list)
    for task in tasks:
        if _is_recommendation_task(task):
            grouped_tasks[(task.task_type, task.workflow_version)].append(task)
    for (task_type, workflow_version), grouped in sorted(grouped_tasks.items()):
        family_tasks = _recommendation_family_tasks(tasks, grouped)
        family_attempts = [
            attempt for task in family_tasks for attempt in attempts_by_task_id.get(task.id, [])
        ]
        recommendation_summary = _recommendation_summary_from_tasks(family_tasks, outcomes)
        performance_summary = performance_summary_from_attempts(
            family_attempts,
            task_type=task_type,
            workflow_version=workflow_version,
        )
        cost_summary = cost_summary_from_attempts(
            family_attempts,
            task_type=task_type,
            workflow_version=workflow_version,
        )
        total_hours = (
            (performance_summary.median_end_to_end_latency_ms or 0.0) / 1000.0 / 3600.0
        ) * max(recommendation_summary.recommendation_task_count, 1)
        improvements = recommendation_summary.downstream_improved_count
        rows.append(
            AgentTaskValueDensityRowResponse(
                task_type=task_type,
                workflow_version=workflow_version,
                recommendation_task_count=recommendation_summary.recommendation_task_count,
                downstream_improved_count=improvements,
                estimated_usd_total=cost_summary.estimated_usd_total,
                median_end_to_end_latency_ms=performance_summary.median_end_to_end_latency_ms,
                useful_recommendation_rate=(
                    recommendation_summary.useful_label_count
                    / recommendation_summary.recommendation_task_count
                    if recommendation_summary.recommendation_task_count
                    else None
                ),
                downstream_improvement_rate=recommendation_summary.downstream_improvement_rate,
                improvements_per_dollar=(
                    improvements / cost_summary.estimated_usd_total
                    if cost_summary.estimated_usd_total > 0
                    else None
                ),
                improvements_per_hour=(improvements / total_hours if total_hours > 0 else None),
            )
        )
    return rows


__all__ = [
    "get_agent_task_recommendation_summary",
    "get_agent_task_recommendation_trends",
    "get_agent_task_value_density",
]
