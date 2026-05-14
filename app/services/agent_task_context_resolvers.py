from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import AgentTask, AgentTaskDependency
from app.schemas.agent_task_core import TaskContextEnvelope
from app.services.agent_task_context_store import (
    get_context_artifact_row,
    refresh_task_context_freshness,
)


def _target_task_not_found(task_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "agent_task_context_target_task_not_found",
        "Target task not found.",
        task_id=str(task_id),
    )


def _target_task_type_mismatch(
    task_id: UUID,
    *,
    expected_task_type: str,
    actual_task_type: str,
) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        "agent_task_context_target_task_type_mismatch",
        f"Target task must be a {expected_task_type} task.",
        task_id=str(task_id),
        expected_task_type=expected_task_type,
        actual_task_type=actual_task_type,
    )


def _target_task_not_completed(task_id: UUID, *, task_status: str | None) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        "agent_task_context_target_task_not_completed",
        "Target task must be completed before it can be consumed.",
        task_id=str(task_id),
        task_status=task_status,
    )


def _rerun_required(
    code: str,
    *,
    task_id: UUID,
    message: str,
    expected_schema_name: str,
    expected_schema_version: str,
    actual_schema_name: str | None = None,
    actual_schema_version: str | None = None,
) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        code,
        message,
        task_id=str(task_id),
        expected_schema_name=expected_schema_name,
        expected_schema_version=expected_schema_version,
        actual_schema_name=actual_schema_name,
        actual_schema_version=actual_schema_version,
    )


def _dependency_mismatch(
    *,
    task_id: UUID,
    depends_on_task_id: UUID,
    expected_dependency_kind: str,
    actual_dependency_kind: str | None,
    message: str,
) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        "agent_task_context_dependency_mismatch",
        message,
        task_id=str(task_id),
        depends_on_task_id=str(depends_on_task_id),
        expected_dependency_kind=expected_dependency_kind,
        actual_dependency_kind=actual_dependency_kind,
    )


def resolve_required_task_output_context(
    session: Session,
    *,
    task_id: UUID,
    expected_task_type: str | tuple[str, ...],
    expected_schema_name: str | tuple[str, ...],
    expected_schema_version: str,
    rerun_message: str,
) -> TaskContextEnvelope:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise _target_task_not_found(task_id)
    expected_task_types = (
        (expected_task_type,) if isinstance(expected_task_type, str) else expected_task_type
    )
    expected_schema_names = (
        (expected_schema_name,) if isinstance(expected_schema_name, str) else expected_schema_name
    )
    if task.task_type not in expected_task_types:
        raise _target_task_type_mismatch(
            task_id,
            expected_task_type=", ".join(expected_task_types),
            actual_task_type=task.task_type,
        )
    if task.status != "completed":
        raise _target_task_not_completed(task_id, task_status=task.status)
    context_row = get_context_artifact_row(session, task.id)
    if context_row is None:
        raise _rerun_required(
            "agent_task_context_output_missing",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=", ".join(expected_schema_names),
            expected_schema_version=expected_schema_version,
        )
    context = refresh_task_context_freshness(
        session,
        TaskContextEnvelope.model_validate(context_row.payload_json or {}),
    )
    if context.output_schema_name not in expected_schema_names:
        raise _rerun_required(
            "agent_task_context_output_schema_mismatch",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=", ".join(expected_schema_names),
            expected_schema_version=expected_schema_version,
            actual_schema_name=context.output_schema_name,
            actual_schema_version=context.output_schema_version,
        )
    if context.output_schema_version != expected_schema_version:
        raise _rerun_required(
            "agent_task_context_output_schema_version_mismatch",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=", ".join(expected_schema_names),
            expected_schema_version=expected_schema_version,
            actual_schema_name=context.output_schema_name,
            actual_schema_version=context.output_schema_version,
        )
    return context


def resolve_required_dependency_task_output_context(
    session: Session,
    *,
    task_id: UUID,
    depends_on_task_id: UUID,
    dependency_kind: str,
    expected_task_type: str | tuple[str, ...],
    expected_schema_name: str | tuple[str, ...],
    expected_schema_version: str,
    dependency_error_message: str,
    rerun_message: str,
) -> TaskContextEnvelope:
    dependency_row = (
        session.execute(
            select(AgentTaskDependency)
            .where(
                AgentTaskDependency.task_id == task_id,
                AgentTaskDependency.depends_on_task_id == depends_on_task_id,
            )
            .limit(1)
        )
        .scalars()
        .first()
    )
    if dependency_row is None or dependency_row.dependency_kind != dependency_kind:
        raise _dependency_mismatch(
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
            expected_dependency_kind=dependency_kind,
            actual_dependency_kind=(
                dependency_row.dependency_kind if dependency_row is not None else None
            ),
            message=dependency_error_message,
        )
    return resolve_required_task_output_context(
        session,
        task_id=depends_on_task_id,
        expected_task_type=expected_task_type,
        expected_schema_name=expected_schema_name,
        expected_schema_version=expected_schema_version,
        rerun_message=rerun_message,
    )


__all__ = [
    "resolve_required_dependency_task_output_context",
    "resolve_required_task_output_context",
]
