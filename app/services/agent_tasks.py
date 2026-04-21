from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskAttempt,
    AgentTaskDependency,
    AgentTaskDependencyKind,
    AgentTaskOutcome,
    AgentTaskStatus,
    AgentTaskVerification,
    AgentTaskVerificationOutcome,
)
from app.schemas.agent_tasks import (
    AgentTaskActionDefinitionResponse,
    AgentTaskAnalyticsSummaryResponse,
    AgentTaskApprovalRequest,
    AgentTaskApprovalTrendPointResponse,
    AgentTaskApprovalTrendResponse,
    AgentTaskArtifactResponse,
    AgentTaskCostSummaryResponse,
    AgentTaskCostTrendPointResponse,
    AgentTaskCostTrendResponse,
    AgentTaskCreateRequest,
    AgentTaskDecisionSignalResponse,
    AgentTaskDependencyResponse,
    AgentTaskDetailResponse,
    AgentTaskOutcomeCreateRequest,
    AgentTaskOutcomeResponse,
    AgentTaskPerformanceSummaryResponse,
    AgentTaskPerformanceTrendPointResponse,
    AgentTaskPerformanceTrendResponse,
    AgentTaskRecommendationSummaryResponse,
    AgentTaskRecommendationTrendPointResponse,
    AgentTaskRecommendationTrendResponse,
    AgentTaskRejectionRequest,
    AgentTaskSummaryResponse,
    AgentTaskTraceExportResponse,
    AgentTaskTrendPointResponse,
    AgentTaskTrendResponse,
    AgentTaskValueDensityRowResponse,
    AgentTaskVerificationTrendPointResponse,
    AgentTaskVerificationTrendResponse,
    AgentTaskWorkflowVersionSummaryResponse,
    TaskContextEnvelope,
)
from app.services.agent_task_artifacts import list_agent_task_artifacts
from app.services.agent_task_context import get_agent_task_context, get_agent_task_context_artifact
from app.services.agent_task_verifications import (
    count_agent_task_verifications,
    list_agent_task_verifications,
)


def _agent_task_not_found(task_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "agent_task_not_found",
        "Agent task not found.",
        task_id=str(task_id),
    )


def _initial_task_status(*, requires_approval: bool, has_incomplete_dependencies: bool) -> str:
    if has_incomplete_dependencies:
        return AgentTaskStatus.BLOCKED.value
    if requires_approval:
        return AgentTaskStatus.AWAITING_APPROVAL.value
    return AgentTaskStatus.QUEUED.value


def _build_summary(task: AgentTask) -> AgentTaskSummaryResponse:
    return AgentTaskSummaryResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        side_effect_level=task.side_effect_level,
        requires_approval=task.requires_approval,
        parent_task_id=task.parent_task_id,
        workflow_version=task.workflow_version,
        tool_version=task.tool_version,
        prompt_version=task.prompt_version,
        model=task.model,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


def _list_dependency_ids(session: Session, task_id: UUID) -> list[UUID]:
    return list(
        session.execute(
            select(AgentTaskDependency.depends_on_task_id)
            .where(AgentTaskDependency.task_id == task_id)
            .order_by(AgentTaskDependency.created_at, AgentTaskDependency.depends_on_task_id)
        ).scalars()
    )


def _list_dependency_edges(session: Session, task_id: UUID) -> list[AgentTaskDependencyResponse]:
    rows = (
        session.execute(
            select(AgentTaskDependency)
            .where(AgentTaskDependency.task_id == task_id)
            .order_by(AgentTaskDependency.created_at, AgentTaskDependency.depends_on_task_id)
        )
        .scalars()
        .all()
    )
    return [
        AgentTaskDependencyResponse(
            task_id=row.depends_on_task_id,
            dependency_kind=row.dependency_kind,
        )
        for row in rows
    ]


def _count_task_attempts(session: Session, task_id: UUID) -> int:
    from app.db.models import AgentTaskAttempt

    return session.execute(
        select(func.count())
        .select_from(AgentTaskAttempt)
        .where(AgentTaskAttempt.task_id == task_id)
    ).scalar_one()


def _count_task_artifacts(session: Session, task_id: UUID) -> int:
    return session.execute(
        select(func.count())
        .select_from(AgentTaskArtifact)
        .where(AgentTaskArtifact.task_id == task_id)
    ).scalar_one()


def _list_task_artifacts(session: Session, task_id: UUID) -> list[AgentTaskArtifactResponse]:
    return list_agent_task_artifacts(session, task_id, limit=20)


def _to_outcome_response(row: AgentTaskOutcome) -> AgentTaskOutcomeResponse:
    return AgentTaskOutcomeResponse(
        outcome_id=row.id,
        task_id=row.task_id,
        outcome_label=row.outcome_label,
        created_by=row.created_by,
        note=row.note,
        created_at=row.created_at,
    )


def _count_task_outcomes(session: Session, task_id: UUID) -> int:
    return session.execute(
        select(func.count())
        .select_from(AgentTaskOutcome)
        .where(AgentTaskOutcome.task_id == task_id)
    ).scalar_one()


def _list_task_outcomes(session: Session, task_id: UUID) -> list[AgentTaskOutcomeResponse]:
    rows = (
        session.execute(
            select(AgentTaskOutcome)
            .where(AgentTaskOutcome.task_id == task_id)
            .order_by(AgentTaskOutcome.created_at.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )
    return [_to_outcome_response(row) for row in rows]


def _build_detail(session: Session, task: AgentTask) -> AgentTaskDetailResponse:
    summary = _build_summary(task)
    context_envelope: TaskContextEnvelope | None = None
    context_artifact_id: UUID | None = None
    try:
        context_artifact = get_agent_task_context_artifact(session, task.id)
        context_artifact_id = context_artifact.id
        context_envelope = get_agent_task_context(session, task.id)
    except HTTPException:
        context_envelope = None
    return AgentTaskDetailResponse(
        **summary.model_dump(),
        dependency_task_ids=_list_dependency_ids(session, task.id),
        dependency_edges=_list_dependency_edges(session, task.id),
        input=task.input_json,
        result=task.result_json,
        model_settings=task.model_settings_json,
        error_message=task.error_message,
        failure_artifact_path=task.failure_artifact_path,
        attempts=task.attempts,
        locked_at=task.locked_at,
        locked_by=task.locked_by,
        last_heartbeat_at=task.last_heartbeat_at,
        next_attempt_at=task.next_attempt_at,
        approved_at=task.approved_at,
        approved_by=task.approved_by,
        approval_note=task.approval_note,
        rejected_at=task.rejected_at,
        rejected_by=task.rejected_by,
        rejection_note=task.rejection_note,
        artifact_count=_count_task_artifacts(session, task.id),
        attempt_count=_count_task_attempts(session, task.id),
        verification_count=count_agent_task_verifications(session, task.id),
        outcome_count=_count_task_outcomes(session, task.id),
        context_summary=context_envelope.summary if context_envelope else None,
        context_refs=context_envelope.refs if context_envelope else [],
        context_artifact_id=context_artifact_id,
        context_freshness_status=context_envelope.freshness_status if context_envelope else None,
        artifacts=_list_task_artifacts(session, task.id),
        verifications=list_agent_task_verifications(session, task.id),
        outcomes=_list_task_outcomes(session, task.id),
    )


def _validate_dependency_ids(session: Session, dependency_task_ids: list[UUID]) -> None:
    if not dependency_task_ids:
        return
    existing_ids = set(
        session.execute(select(AgentTask.id).where(AgentTask.id.in_(dependency_task_ids)))
        .scalars()
        .all()
    )
    missing_ids = [task_id for task_id in dependency_task_ids if task_id not in existing_ids]
    if missing_ids:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_dependency_not_found",
            "Dependency task not found.",
            dependency_task_ids=[str(task_id) for task_id in missing_ids],
        )


def _dependency_row_task_id(row) -> UUID:
    if hasattr(row, "task_id"):
        return row.task_id
    return row[0]


def _dependency_row_depends_on_task_id(row) -> UUID:
    if hasattr(row, "depends_on_task_id"):
        return row.depends_on_task_id
    return row[1]


def _validate_dependency_graph_is_acyclic(
    session: Session,
    dependency_task_ids: list[UUID],
) -> None:
    if not dependency_task_ids:
        return

    adjacency: dict[UUID, list[UUID]] = defaultdict(list)
    visited_for_load: set[UUID] = set()
    pending = list(dict.fromkeys(dependency_task_ids))

    while pending:
        current_batch = [task_id for task_id in pending if task_id not in visited_for_load]
        pending = []
        if not current_batch:
            continue
        visited_for_load.update(current_batch)
        rows = session.execute(
            select(AgentTaskDependency.task_id, AgentTaskDependency.depends_on_task_id).where(
                AgentTaskDependency.task_id.in_(current_batch)
            )
        ).all()
        for row in rows:
            task_id = _dependency_row_task_id(row)
            depends_on_task_id = _dependency_row_depends_on_task_id(row)
            adjacency[task_id].append(depends_on_task_id)
            if depends_on_task_id not in visited_for_load:
                pending.append(depends_on_task_id)

    visiting: set[UUID] = set()
    visited: set[UUID] = set()

    def visit(task_id: UUID, path: list[UUID]) -> list[UUID] | None:
        if task_id in visiting:
            cycle_start = path.index(task_id)
            return path[cycle_start:] + [task_id]
        if task_id in visited:
            return None
        visiting.add(task_id)
        path.append(task_id)
        for child_id in adjacency.get(task_id, []):
            cycle = visit(child_id, path)
            if cycle is not None:
                return cycle
        path.pop()
        visiting.remove(task_id)
        visited.add(task_id)
        return None

    for dependency_task_id in dependency_task_ids:
        cycle = visit(dependency_task_id, [])
        if cycle is not None:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "agent_task_dependency_cycle",
                "Agent task dependency graph contains a cycle.",
                dependency_task_ids=[str(task_id) for task_id in dependency_task_ids],
                cycle_task_ids=[str(task_id) for task_id in cycle],
            )


def _validate_parent_task_id(session: Session, parent_task_id: UUID | None) -> None:
    if parent_task_id is None:
        return
    if session.get(AgentTask, parent_task_id) is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "parent_task_not_found",
            "Parent task not found.",
            parent_task_id=str(parent_task_id),
        )


def _incomplete_dependency_count(session: Session, dependency_task_ids: list[UUID]) -> int:
    if not dependency_task_ids:
        return 0
    return session.execute(
        select(func.count())
        .select_from(AgentTask)
        .where(
            AgentTask.id.in_(dependency_task_ids),
            AgentTask.status != AgentTaskStatus.COMPLETED.value,
        )
    ).scalar_one()


def _task_has_incomplete_dependencies(session: Session, task_id: UUID) -> bool:
    return (
        session.execute(
            select(func.count())
            .select_from(AgentTaskDependency)
            .join(AgentTask, AgentTask.id == AgentTaskDependency.depends_on_task_id)
            .where(
                AgentTaskDependency.task_id == task_id,
                AgentTask.status != AgentTaskStatus.COMPLETED.value,
            )
        ).scalar_one()
        > 0
    )


def _augment_dependency_kinds_for_action(
    *,
    validated_input,
    dependency_task_ids: list[UUID],
) -> list[tuple[UUID, str]]:
    dependency_kinds: dict[UUID, str] = {
        task_id: AgentTaskDependencyKind.EXPLICIT.value for task_id in dependency_task_ids
    }
    linked_task_specs = (
        ("target_task_id", AgentTaskDependencyKind.TARGET_TASK.value),
        ("source_task_id", AgentTaskDependencyKind.SOURCE_TASK.value),
        ("draft_task_id", AgentTaskDependencyKind.DRAFT_TASK.value),
        ("verification_task_id", AgentTaskDependencyKind.VERIFICATION_TASK.value),
    )
    for attr_name, dependency_kind in linked_task_specs:
        linked_task_id = getattr(validated_input, attr_name, None)
        if linked_task_id is None:
            continue
        dependency_kinds[linked_task_id] = dependency_kind
    return list(dependency_kinds.items())


def create_agent_task(session: Session, payload: AgentTaskCreateRequest) -> AgentTaskDetailResponse:
    from app.services.agent_task_actions import get_agent_task_action, validate_agent_task_input

    now = utcnow()
    dependency_task_ids = list(dict.fromkeys(payload.dependency_task_ids))
    if payload.parent_task_id is not None and payload.parent_task_id in dependency_task_ids:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_agent_task_request",
            "A task cannot depend on its parent task explicitly.",
        )
    action = get_agent_task_action(payload.task_type)
    try:
        validated_input = validate_agent_task_input(payload.task_type, payload.input)
    except ValidationError as exc:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_agent_task_input",
            "Agent task input did not match the task schema.",
            task_type=payload.task_type,
            validation_errors=jsonable_encoder(exc.errors()),
        ) from exc
    dependency_specs = _augment_dependency_kinds_for_action(
        validated_input=validated_input,
        dependency_task_ids=dependency_task_ids,
    )
    dependency_task_ids = [task_id for task_id, _kind in dependency_specs]
    if payload.parent_task_id is not None and payload.parent_task_id in dependency_task_ids:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_agent_task_request",
            "A task cannot depend on its parent task explicitly.",
        )
    effective_side_effect_level = payload.side_effect_level or action.side_effect_level
    if effective_side_effect_level != action.side_effect_level:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_agent_task_request",
            (
                f"Task type '{payload.task_type}' requires side_effect_level "
                f"'{action.side_effect_level}'."
            ),
            task_type=payload.task_type,
            required_side_effect_level=action.side_effect_level,
        )
    effective_requires_approval = (
        payload.requires_approval
        if payload.requires_approval is not None
        else action.requires_approval
    )
    if effective_requires_approval != action.requires_approval:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_agent_task_request",
            (
                f"Task type '{payload.task_type}' requires requires_approval="
                f"{str(action.requires_approval).lower()}."
            ),
            task_type=payload.task_type,
            requires_approval=action.requires_approval,
        )

    _validate_parent_task_id(session, payload.parent_task_id)
    _validate_dependency_ids(session, dependency_task_ids)
    _validate_dependency_graph_is_acyclic(session, dependency_task_ids)
    has_incomplete_dependencies = _incomplete_dependency_count(session, dependency_task_ids) > 0

    task = AgentTask(
        task_type=payload.task_type,
        status=_initial_task_status(
            requires_approval=effective_requires_approval,
            has_incomplete_dependencies=has_incomplete_dependencies,
        ),
        priority=payload.priority,
        side_effect_level=effective_side_effect_level,
        requires_approval=effective_requires_approval,
        parent_task_id=payload.parent_task_id,
        input_json=validated_input.model_dump(mode="json", exclude_none=True),
        result_json={},
        workflow_version=payload.workflow_version,
        tool_version=payload.tool_version,
        prompt_version=payload.prompt_version,
        model=payload.model,
        model_settings_json=payload.model_settings,
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    session.flush()

    for dependency_task_id, dependency_kind in dependency_specs:
        session.add(
            AgentTaskDependency(
                task_id=task.id,
                depends_on_task_id=dependency_task_id,
                dependency_kind=dependency_kind,
                created_at=now,
            )
        )

    session.commit()
    return _build_detail(session, task)


def list_agent_task_action_definitions() -> list[AgentTaskActionDefinitionResponse]:
    from app.services.agent_task_actions import list_agent_task_actions

    rows: list[AgentTaskActionDefinitionResponse] = []
    for action in list_agent_task_actions():
        rows.append(
            AgentTaskActionDefinitionResponse(
                task_type=action.task_type,
                definition_kind=action.definition_kind,
                description=action.description,
                side_effect_level=action.side_effect_level,
                requires_approval=action.requires_approval,
                input_schema=action.payload_model.model_json_schema(),
                output_schema_name=action.output_schema_name,
                output_schema_version=action.output_schema_version,
                output_schema=(
                    action.output_model.model_json_schema()
                    if action.output_model is not None
                    else None
                ),
                input_example=action.input_example or {},
            )
        )
    return rows


def list_agent_tasks(
    session: Session,
    *,
    statuses: list[str] | None = None,
    limit: int = 50,
) -> list[AgentTaskSummaryResponse]:
    statement = select(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit)
    if statuses:
        statement = statement.where(AgentTask.status.in_(statuses))
    return [_build_summary(task) for task in session.execute(statement).scalars().all()]


def get_agent_task_detail(session: Session, task_id: UUID) -> AgentTaskDetailResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise _agent_task_not_found(task_id)
    return _build_detail(session, task)


def list_agent_task_outcomes(
    session: Session,
    task_id: UUID,
    *,
    limit: int = 20,
) -> list[AgentTaskOutcomeResponse]:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise _agent_task_not_found(task_id)
    rows = (
        session.execute(
            select(AgentTaskOutcome)
            .where(AgentTaskOutcome.task_id == task_id)
            .order_by(AgentTaskOutcome.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_to_outcome_response(row) for row in rows]


def create_agent_task_outcome(
    session: Session,
    task_id: UUID,
    payload: AgentTaskOutcomeCreateRequest,
) -> AgentTaskOutcomeResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise _agent_task_not_found(task_id)
    if task.status not in {
        AgentTaskStatus.COMPLETED.value,
        AgentTaskStatus.FAILED.value,
        AgentTaskStatus.REJECTED.value,
    }:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Only terminal tasks can receive outcome labels.",
            task_id=str(task_id),
            task_status=task.status,
        )
    existing = session.execute(
        select(AgentTaskOutcome).where(
            AgentTaskOutcome.task_id == task_id,
            AgentTaskOutcome.outcome_label == payload.outcome_label,
            AgentTaskOutcome.created_by == payload.created_by,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "agent_task_outcome_already_recorded",
            "This outcome label has already been recorded by that actor for this task.",
            task_id=str(task_id),
            outcome_label=payload.outcome_label,
            created_by=payload.created_by,
        )

    row = AgentTaskOutcome(
        task_id=task_id,
        outcome_label=payload.outcome_label,
        created_by=payload.created_by,
        note=payload.note,
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    session.commit()
    return _to_outcome_response(row)


def _average_terminal_duration_seconds(tasks: list[AgentTask]) -> float | None:
    durations = [
        (task.completed_at - task.started_at).total_seconds()
        for task in tasks
        if task.status
        in {
            AgentTaskStatus.COMPLETED.value,
            AgentTaskStatus.FAILED.value,
            AgentTaskStatus.REJECTED.value,
        }
        and task.started_at is not None
        and task.completed_at is not None
    ]
    if not durations:
        return None
    return sum(durations) / len(durations)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = max(0, min(len(ordered) - 1, ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _median(values: list[float]) -> float | None:
    return _percentile(values, 0.5)


def _bucket_start(value: datetime, bucket: str) -> datetime:
    if bucket == "week":
        start_date: date = value.date() - timedelta(days=value.weekday())
    else:
        start_date = value.date()
    return datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)


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


def _task_select_statement(
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
    task_types: tuple[str, ...] | None = None,
):
    statement = select(AgentTask)
    if task_types is not None:
        statement = statement.where(AgentTask.task_type.in_(task_types))
    elif task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return statement


def _task_id_select_statement(
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
    task_types: tuple[str, ...] | None = None,
):
    statement = select(AgentTask.id)
    if task_types is not None:
        statement = statement.where(AgentTask.task_type.in_(task_types))
    elif task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return statement


def _list_filtered_tasks(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
    task_types: tuple[str, ...] | None = None,
) -> list[AgentTask]:
    return (
        session.execute(
            _task_select_statement(
                task_type=task_type,
                workflow_version=workflow_version,
                task_types=task_types,
            )
        )
        .scalars()
        .all()
    )


def _list_task_attempt_rows(
    session: Session,
    *,
    task_ids: set[UUID] | None = None,
    task_id_select=None,
) -> list[AgentTaskAttempt]:
    statement = select(AgentTaskAttempt)
    if task_ids is not None:
        if not task_ids:
            return []
        statement = statement.where(AgentTaskAttempt.task_id.in_(task_ids))
    elif task_id_select is not None:
        statement = statement.where(AgentTaskAttempt.task_id.in_(task_id_select))
    return session.execute(statement).scalars().all()


def _list_task_outcome_rows(
    session: Session,
    *,
    task_ids: set[UUID] | None = None,
) -> list[AgentTaskOutcome]:
    statement = select(AgentTaskOutcome)
    if task_ids is not None:
        if not task_ids:
            return []
        statement = statement.where(AgentTaskOutcome.task_id.in_(task_ids))
    return session.execute(statement).scalars().all()


def _list_task_trend_rows(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> list[tuple[UUID, datetime, str]]:
    statement = select(AgentTask.id, AgentTask.created_at, AgentTask.status)
    if task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return session.execute(statement).all()


def _list_verification_trend_rows(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> list[tuple[datetime, str]]:
    statement = select(AgentTaskVerification.created_at, AgentTaskVerification.outcome).join(
        AgentTask, AgentTask.id == AgentTaskVerification.target_task_id
    )
    if task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return session.execute(statement).all()


def _list_approval_trend_rows(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> list[tuple[datetime | None, datetime | None]]:
    statement = select(AgentTask.approved_at, AgentTask.rejected_at)
    if task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    return session.execute(statement).all()


def _filter_task_rows(
    tasks: list[AgentTask],
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> list[AgentTask]:
    rows = tasks
    if task_type is not None:
        rows = [task for task in rows if task.task_type == task_type]
    if workflow_version is not None:
        rows = [task for task in rows if task.workflow_version == workflow_version]
    return rows


def _task_ids(tasks: list[AgentTask]) -> set[UUID]:
    return {task.id for task in tasks}


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
    recommendation_ids = _task_ids(recommendation_tasks)
    if not recommendation_ids:
        return []

    draft_tasks = [
        task
        for task in all_tasks
        if task.task_type in {"draft_harness_config_update", "draft_semantic_registry_update"}
        and _task_input_task_id(task, "source_task_id") in recommendation_ids
    ]
    draft_ids = _task_ids(draft_tasks)
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
        recommendation_ids | draft_ids | _task_ids(verification_tasks) | _task_ids(apply_tasks)
    )
    return [task for task in all_tasks if task.id in family_ids]


def _float_value(payload: dict, key: str) -> float:
    try:
        return float(payload.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _int_value(payload: dict, key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0


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
                    if _int_value(metrics, "total_improved_count") > _int_value(
                        metrics, "total_regressed_count"
                    ):
                        saw_improvement = True
                    if _int_value(metrics, "total_regressed_count") > 0:
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


def _cost_summary_from_attempts(
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
        estimated_usd_total += _float_value(cost, "estimated_usd")
        model_call_count += _int_value(cost, "call_count")
        embedding_count += _int_value(cost, "embedding_count")
        replay_query_count += _int_value(cost, "replay_query_count")
        evaluation_query_count += _int_value(cost, "evaluation_query_count")
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


def _performance_summary_from_attempts(
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
        queue_latency = _float_value(performance, "queue_latency_ms")
        execution_latency = _float_value(performance, "execution_latency_ms")
        end_to_end_latency = _float_value(performance, "end_to_end_latency_ms")
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
        median_queue_latency_ms=_median(queue_latencies),
        p95_queue_latency_ms=_percentile(queue_latencies, 0.95),
        median_execution_latency_ms=_median(execution_latencies),
        p95_execution_latency_ms=_percentile(execution_latencies, 0.95),
        median_end_to_end_latency_ms=_median(end_to_end_latencies),
        p95_end_to_end_latency_ms=_percentile(end_to_end_latencies, 0.95),
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
    task_rows = _list_task_trend_rows(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )
    task_created_at_by_id = {task_id: created_at for task_id, created_at, _status in task_rows}
    attempts = _list_task_attempt_rows(session, task_ids=set(task_created_at_by_id))
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
        bucket_key = _bucket_start(created_at, bucket)
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
        bucket_key = _bucket_start(task_created_at, bucket)
        performance = attempt.performance_json or {}
        queue_latency_ms = _float_value(performance, "queue_latency_ms")
        execution_latency_ms = _float_value(performance, "execution_latency_ms")
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
            median_queue_latency_ms=_median(values["queue_latencies"]),
            p95_queue_latency_ms=_percentile(values["queue_latencies"], 0.95),
            median_execution_latency_ms=_median(values["execution_latencies"]),
            p95_execution_latency_ms=_percentile(values["execution_latencies"], 0.95),
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
    rows = _list_verification_trend_rows(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )
    bucket_rows: dict[datetime, dict] = defaultdict(
        lambda: {"passed_count": 0, "failed_count": 0, "error_count": 0}
    )
    for created_at, outcome in rows:
        bucket_key = _bucket_start(created_at, bucket)
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
    rows = _list_approval_trend_rows(
        session,
        task_type=task_type,
        workflow_version=workflow_version,
    )
    bucket_rows: dict[datetime, dict] = defaultdict(
        lambda: {"approval_count": 0, "rejection_count": 0}
    )
    for approved_at, rejected_at in rows:
        if approved_at is not None:
            bucket_rows[_bucket_start(approved_at, bucket)]["approval_count"] += 1
        if rejected_at is not None:
            bucket_rows[_bucket_start(rejected_at, bucket)]["rejection_count"] += 1
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


def get_agent_task_recommendation_summary(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskRecommendationSummaryResponse:
    all_tasks = _list_filtered_tasks(
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
    outcomes = _list_task_outcome_rows(session, task_ids=_task_ids(family_tasks))
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
    tasks = _list_filtered_tasks(
        session,
        workflow_version=workflow_version,
        task_types=RECOMMENDATION_FAMILY_TASK_TYPES,
    )
    outcomes = _list_task_outcome_rows(session, task_ids=_task_ids(tasks))
    bucket_rows: dict[datetime, list[AgentTask]] = defaultdict(list)
    for task in tasks:
        if _is_recommendation_task(task) and (task_type is None or task.task_type == task_type):
            bucket_rows[_bucket_start(task.created_at, bucket)].append(task)
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


def get_agent_task_cost_summary(
    session: Session,
    *,
    task_type: str | None = None,
    workflow_version: str | None = None,
) -> AgentTaskCostSummaryResponse:
    attempts = _list_task_attempt_rows(
        session,
        task_id_select=_task_id_select_statement(
            task_type=task_type,
            workflow_version=workflow_version,
        ),
    )
    return _cost_summary_from_attempts(
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
    attempts = _list_task_attempt_rows(
        session,
        task_id_select=_task_id_select_statement(
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
        row = bucket_rows[_bucket_start(attempt.created_at, bucket)]
        row["attempt_count"] += 1
        cost = attempt.cost_json or {}
        row["estimated_usd_total"] += _float_value(cost, "estimated_usd")
        row["replay_query_count"] += _int_value(cost, "replay_query_count")
        row["evaluation_query_count"] += _int_value(cost, "evaluation_query_count")
        row["embedding_count"] += _int_value(cost, "embedding_count")
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
    attempts = _list_task_attempt_rows(
        session,
        task_id_select=_task_id_select_statement(
            task_type=task_type,
            workflow_version=workflow_version,
        ),
    )
    return _performance_summary_from_attempts(
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
    attempts = _list_task_attempt_rows(
        session,
        task_id_select=_task_id_select_statement(
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
        row = bucket_rows[_bucket_start(attempt.created_at, bucket)]
        row["attempt_count"] += 1
        performance = attempt.performance_json or {}
        queue_latency = _float_value(performance, "queue_latency_ms")
        execution_latency = _float_value(performance, "execution_latency_ms")
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
                median_queue_latency_ms=_median(values["queue_latencies"]),
                p95_queue_latency_ms=_percentile(values["queue_latencies"], 0.95),
                median_execution_latency_ms=_median(values["execution_latencies"]),
                p95_execution_latency_ms=_percentile(values["execution_latencies"], 0.95),
            )
            for bucket_key, values in sorted(bucket_rows.items())
        ],
    )


def get_agent_task_value_density(
    session: Session,
) -> list[AgentTaskValueDensityRowResponse]:
    tasks = _list_filtered_tasks(session, task_types=RECOMMENDATION_FAMILY_TASK_TYPES)
    task_ids = _task_ids(tasks)
    outcomes = _list_task_outcome_rows(session, task_ids=task_ids)
    attempts = _list_task_attempt_rows(session, task_ids=task_ids)
    rows: list[AgentTaskValueDensityRowResponse] = []
    grouped_tasks: dict[tuple[str, str], list[AgentTask]] = defaultdict(list)
    for task in tasks:
        if _is_recommendation_task(task):
            grouped_tasks[(task.task_type, task.workflow_version)].append(task)
    for (task_type, workflow_version), grouped in sorted(grouped_tasks.items()):
        family_tasks = _recommendation_family_tasks(tasks, grouped)
        family_task_ids = _task_ids(family_tasks)
        family_attempts = [attempt for attempt in attempts if attempt.task_id in family_task_ids]
        recommendation_summary = _recommendation_summary_from_tasks(family_tasks, outcomes)
        performance_summary = _performance_summary_from_attempts(
            family_attempts,
            task_type=task_type,
            workflow_version=workflow_version,
        )
        cost_summary = _cost_summary_from_attempts(
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


def get_agent_task_decision_signals(
    session: Session,
) -> list[AgentTaskDecisionSignalResponse]:
    rows: list[AgentTaskDecisionSignalResponse] = []
    for value_row in get_agent_task_value_density(session):
        if value_row.recommendation_task_count == 0:
            continue
        if (value_row.downstream_improvement_rate or 0.0) < 0.4:
            rows.append(
                AgentTaskDecisionSignalResponse(
                    task_type=value_row.task_type,
                    workflow_version=value_row.workflow_version,
                    status="degraded",
                    reason="Downstream improvement rate is below 40%.",
                    threshold_crossed="downstream_improvement_rate<0.40",
                    recommended_action="Review recommendation thresholds and verifier gating.",
                )
            )
        elif (
            value_row.median_end_to_end_latency_ms is not None
            and value_row.median_end_to_end_latency_ms > 60_000
        ):
            rows.append(
                AgentTaskDecisionSignalResponse(
                    task_type=value_row.task_type,
                    workflow_version=value_row.workflow_version,
                    status="watch",
                    reason="Median end-to-end latency exceeds 60 seconds.",
                    threshold_crossed="median_end_to_end_latency_ms>60000",
                    recommended_action="Investigate queue, replay, or verification bottlenecks.",
                )
            )
        else:
            rows.append(
                AgentTaskDecisionSignalResponse(
                    task_type=value_row.task_type,
                    workflow_version=value_row.workflow_version,
                    status="healthy",
                    reason="Recommendation quality and latency are within current thresholds.",
                    threshold_crossed="none",
                    recommended_action="Continue collecting outcome labels and replay evidence.",
                )
            )
    return rows


def export_agent_task_traces(
    session: Session,
    *,
    limit: int = 50,
    workflow_version: str | None = None,
    task_type: str | None = None,
) -> AgentTaskTraceExportResponse:
    statement = select(AgentTask).order_by(AgentTask.created_at.desc())
    if workflow_version is not None:
        statement = statement.where(AgentTask.workflow_version == workflow_version)
    if task_type is not None:
        statement = statement.where(AgentTask.task_type == task_type)
    tasks = session.execute(statement.limit(limit)).scalars().all()
    traces = [_build_detail(session, task) for task in tasks]
    return AgentTaskTraceExportResponse(
        export_count=len(traces),
        workflow_version=workflow_version,
        task_type=task_type,
        traces=traces,
    )


def approve_agent_task(
    session: Session,
    task_id: UUID,
    payload: AgentTaskApprovalRequest,
) -> AgentTaskDetailResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise _agent_task_not_found(task_id)
    if not task.requires_approval:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "This task does not require approval.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.approved_at is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "This task has already been approved.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.rejected_at is not None or task.status == AgentTaskStatus.REJECTED.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Rejected tasks cannot be approved.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.status in {AgentTaskStatus.COMPLETED.value, AgentTaskStatus.FAILED.value}:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Completed or failed tasks cannot be approved.",
            task_id=str(task_id),
            task_status=task.status,
        )

    now = utcnow()
    task.approved_at = now
    task.approved_by = payload.approved_by
    task.approval_note = payload.approval_note
    task.updated_at = now
    task.status = (
        AgentTaskStatus.BLOCKED.value
        if _task_has_incomplete_dependencies(session, task.id)
        else AgentTaskStatus.QUEUED.value
    )
    session.commit()
    return _build_detail(session, task)


def reject_agent_task(
    session: Session,
    task_id: UUID,
    payload: AgentTaskRejectionRequest,
) -> AgentTaskDetailResponse:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise _agent_task_not_found(task_id)
    if not task.requires_approval:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "This task does not require approval.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.approved_at is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Approved tasks cannot be rejected.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.rejected_at is not None or task.status == AgentTaskStatus.REJECTED.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "This task has already been rejected.",
            task_id=str(task_id),
            task_status=task.status,
        )
    if task.status in {
        AgentTaskStatus.COMPLETED.value,
        AgentTaskStatus.FAILED.value,
        AgentTaskStatus.PROCESSING.value,
        AgentTaskStatus.RETRY_WAIT.value,
        AgentTaskStatus.QUEUED.value,
    }:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_agent_task_state",
            "Only pending approval tasks can be rejected.",
            task_id=str(task_id),
            task_status=task.status,
        )

    now = utcnow()
    task.status = AgentTaskStatus.REJECTED.value
    task.rejected_at = now
    task.rejected_by = payload.rejected_by
    task.rejection_note = payload.rejection_note
    task.updated_at = now
    task.completed_at = now
    task.next_attempt_at = None
    session.commit()
    return _build_detail(session, task)
