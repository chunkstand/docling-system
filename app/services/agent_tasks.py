from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskOutcome,
    AgentTaskStatus,
    AgentTaskVerification,
)
from app.schemas.agent_tasks import (
    AgentTaskActionDefinitionResponse,
    AgentTaskAnalyticsSummaryResponse,
    AgentTaskApprovalRequest,
    AgentTaskArtifactResponse,
    AgentTaskCreateRequest,
    AgentTaskDetailResponse,
    AgentTaskOutcomeCreateRequest,
    AgentTaskOutcomeResponse,
    AgentTaskRejectionRequest,
    AgentTaskSummaryResponse,
    AgentTaskTraceExportResponse,
    AgentTaskWorkflowVersionSummaryResponse,
)
from app.services.agent_task_artifacts import list_agent_task_artifacts
from app.services.agent_task_verifications import (
    count_agent_task_verifications,
    list_agent_task_verifications,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


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
    return AgentTaskDetailResponse(
        **summary.model_dump(),
        dependency_task_ids=_list_dependency_ids(session, task.id),
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
        artifacts=_list_task_artifacts(session, task.id),
        verifications=list_agent_task_verifications(session, task.id),
        outcomes=_list_task_outcomes(session, task.id),
    )


def _validate_dependency_ids(session: Session, dependency_task_ids: list[UUID]) -> None:
    if not dependency_task_ids:
        return
    existing_ids = set(
        session.execute(select(AgentTask.id).where(AgentTask.id.in_(dependency_task_ids))).scalars()
    )
    missing_ids = [task_id for task_id in dependency_task_ids if task_id not in existing_ids]
    if missing_ids:
        missing_str = ", ".join(str(task_id) for task_id in missing_ids)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dependency task(s) not found: {missing_str}",
        )


def _validate_parent_task_id(session: Session, parent_task_id: UUID | None) -> None:
    if parent_task_id is None:
        return
    if session.get(AgentTask, parent_task_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent task not found: {parent_task_id}",
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


def _augment_dependency_ids_for_action(
    *,
    action,
    validated_input,
    dependency_task_ids: list[UUID],
) -> list[UUID]:
    augmented_ids = list(dependency_task_ids)
    for linked_task_id in (
        getattr(validated_input, "target_task_id", None),
        getattr(validated_input, "source_task_id", None),
        getattr(validated_input, "draft_task_id", None),
        getattr(validated_input, "verification_task_id", None),
    ):
        if linked_task_id is None or linked_task_id in augmented_ids:
            continue
        augmented_ids.append(linked_task_id)
    return augmented_ids


def create_agent_task(session: Session, payload: AgentTaskCreateRequest) -> AgentTaskDetailResponse:
    from app.services.agent_task_actions import get_agent_task_action, validate_agent_task_input

    now = _utcnow()
    dependency_task_ids = list(dict.fromkeys(payload.dependency_task_ids))
    if payload.parent_task_id is not None and payload.parent_task_id in dependency_task_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task cannot depend on its parent task explicitly.",
        )
    action = get_agent_task_action(payload.task_type)
    try:
        validated_input = validate_agent_task_input(payload.task_type, payload.input)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc
    dependency_task_ids = _augment_dependency_ids_for_action(
        action=action,
        validated_input=validated_input,
        dependency_task_ids=dependency_task_ids,
    )
    if payload.parent_task_id is not None and payload.parent_task_id in dependency_task_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task cannot depend on its parent task explicitly.",
        )
    effective_side_effect_level = payload.side_effect_level or action.side_effect_level
    if effective_side_effect_level != action.side_effect_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Task type '{payload.task_type}' requires side_effect_level "
                f"'{action.side_effect_level}'."
            ),
        )
    effective_requires_approval = (
        payload.requires_approval
        if payload.requires_approval is not None
        else action.requires_approval
    )
    if effective_requires_approval != action.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Task type '{payload.task_type}' requires requires_approval="
                f"{str(action.requires_approval).lower()}."
            ),
        )

    _validate_parent_task_id(session, payload.parent_task_id)
    _validate_dependency_ids(session, dependency_task_ids)
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

    for dependency_task_id in dependency_task_ids:
        session.add(
            AgentTaskDependency(
                task_id=task.id,
                depends_on_task_id=dependency_task_id,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    return _build_detail(session, task)


def list_agent_task_outcomes(
    session: Session,
    task_id: UUID,
    *,
    limit: int = 20,
) -> list[AgentTaskOutcomeResponse]:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    if task.status not in {
        AgentTaskStatus.COMPLETED.value,
        AgentTaskStatus.FAILED.value,
        AgentTaskStatus.REJECTED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only terminal tasks can receive outcome labels.",
        )
    existing = session.execute(
        select(AgentTaskOutcome).where(
            AgentTaskOutcome.task_id == task_id,
            AgentTaskOutcome.outcome_label == payload.outcome_label,
            AgentTaskOutcome.created_by == payload.created_by,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This outcome label has already been recorded by that actor for this task.",
        )

    row = AgentTaskOutcome(
        task_id=task_id,
        outcome_label=payload.outcome_label,
        created_by=payload.created_by,
        note=payload.note,
        created_at=_utcnow(),
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


def get_agent_task_analytics_summary(session: Session) -> AgentTaskAnalyticsSummaryResponse:
    tasks = session.execute(select(AgentTask)).scalars().all()
    outcomes = session.execute(select(AgentTaskOutcome)).scalars().all()
    verifications = session.execute(select(AgentTaskVerification)).scalars().all()

    status_counts = Counter(task.status for task in tasks)
    outcome_counts = Counter(row.outcome_label for row in outcomes)
    verification_counts = Counter(row.outcome for row in verifications)

    return AgentTaskAnalyticsSummaryResponse(
        task_count=len(tasks),
        completed_count=status_counts.get(AgentTaskStatus.COMPLETED.value, 0),
        failed_count=status_counts.get(AgentTaskStatus.FAILED.value, 0),
        rejected_count=status_counts.get(AgentTaskStatus.REJECTED.value, 0),
        awaiting_approval_count=status_counts.get(AgentTaskStatus.AWAITING_APPROVAL.value, 0),
        processing_count=status_counts.get(AgentTaskStatus.PROCESSING.value, 0),
        approval_required_count=sum(1 for task in tasks if task.requires_approval),
        approved_task_count=sum(1 for task in tasks if task.approved_at is not None),
        rejected_task_count=sum(1 for task in tasks if task.rejected_at is not None),
        labeled_task_count=len({row.task_id for row in outcomes}),
        outcome_label_counts=dict(outcome_counts),
        verification_outcome_counts=dict(verification_counts),
        avg_terminal_duration_seconds=_average_terminal_duration_seconds(tasks),
    )


def list_agent_task_workflow_summaries(
    session: Session,
) -> list[AgentTaskWorkflowVersionSummaryResponse]:
    tasks = (
        session.execute(select(AgentTask).order_by(AgentTask.workflow_version.asc()))
        .scalars()
        .all()
    )
    outcomes = session.execute(select(AgentTaskOutcome)).scalars().all()
    verifications = session.execute(select(AgentTaskVerification)).scalars().all()

    tasks_by_version: dict[str, list[AgentTask]] = defaultdict(list)
    task_by_id = {}
    for task in tasks:
        tasks_by_version[task.workflow_version].append(task)
        task_by_id[task.id] = task

    outcomes_by_version: dict[str, list[AgentTaskOutcome]] = defaultdict(list)
    for row in outcomes:
        task = task_by_id.get(row.task_id)
        if task is not None:
            outcomes_by_version[task.workflow_version].append(row)

    verifications_by_version: dict[str, list[AgentTaskVerification]] = defaultdict(list)
    for row in verifications:
        task = task_by_id.get(row.target_task_id)
        if task is not None:
            verifications_by_version[task.workflow_version].append(row)

    summaries: list[AgentTaskWorkflowVersionSummaryResponse] = []
    for workflow_version, version_tasks in sorted(tasks_by_version.items()):
        status_counts = Counter(task.status for task in version_tasks)
        outcome_counts = Counter(row.outcome_label for row in outcomes_by_version[workflow_version])
        verification_counts = Counter(
            row.outcome for row in verifications_by_version[workflow_version]
        )
        summaries.append(
            AgentTaskWorkflowVersionSummaryResponse(
                workflow_version=workflow_version,
                task_count=len(version_tasks),
                completed_count=status_counts.get(AgentTaskStatus.COMPLETED.value, 0),
                failed_count=status_counts.get(AgentTaskStatus.FAILED.value, 0),
                rejected_count=status_counts.get(AgentTaskStatus.REJECTED.value, 0),
                approved_task_count=sum(
                    1 for task in version_tasks if task.approved_at is not None
                ),
                rejected_task_count=sum(
                    1 for task in version_tasks if task.rejected_at is not None
                ),
                labeled_task_count=len(
                    {row.task_id for row in outcomes_by_version[workflow_version]}
                ),
                outcome_label_counts=dict(outcome_counts),
                verification_outcome_counts=dict(verification_counts),
                avg_terminal_duration_seconds=_average_terminal_duration_seconds(version_tasks),
            )
        )
    summaries.sort(key=lambda row: (-row.task_count, row.workflow_version))
    return summaries


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    if not task.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task does not require approval.",
        )
    if task.approved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task has already been approved.",
        )
    if task.rejected_at is not None or task.status == AgentTaskStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rejected tasks cannot be approved.",
        )
    if task.status in {AgentTaskStatus.COMPLETED.value, AgentTaskStatus.FAILED.value}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed or failed tasks cannot be approved.",
        )

    now = _utcnow()
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    if not task.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task does not require approval.",
        )
    if task.approved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved tasks cannot be rejected.",
        )
    if task.rejected_at is not None or task.status == AgentTaskStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task has already been rejected.",
        )
    if task.status in {
        AgentTaskStatus.COMPLETED.value,
        AgentTaskStatus.FAILED.value,
        AgentTaskStatus.PROCESSING.value,
        AgentTaskStatus.RETRY_WAIT.value,
        AgentTaskStatus.QUEUED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending approval tasks can be rejected.",
        )

    now = _utcnow()
    task.status = AgentTaskStatus.REJECTED.value
    task.rejected_at = now
    task.rejected_by = payload.rejected_by
    task.rejection_note = payload.rejection_note
    task.updated_at = now
    task.completed_at = now
    task.next_attempt_at = None
    session.commit()
    return _build_detail(session, task)
