from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import (
    AgentTask,
    AgentTaskDependency,
    AgentTaskDependencyKind,
    AgentTaskStatus,
)


def initial_task_status(*, requires_approval: bool, has_incomplete_dependencies: bool) -> str:
    if has_incomplete_dependencies:
        return AgentTaskStatus.BLOCKED.value
    if requires_approval:
        return AgentTaskStatus.AWAITING_APPROVAL.value
    return AgentTaskStatus.QUEUED.value


def validate_dependency_ids(session: Session, dependency_task_ids: list[UUID]) -> None:
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
            404,
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


def validate_dependency_graph_is_acyclic(
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
                409,
                "agent_task_dependency_cycle",
                "Agent task dependency graph contains a cycle.",
                dependency_task_ids=[str(task_id) for task_id in dependency_task_ids],
                cycle_task_ids=[str(task_id) for task_id in cycle],
            )


def validate_parent_task_id(session: Session, parent_task_id: UUID | None) -> None:
    if parent_task_id is None:
        return
    if session.get(AgentTask, parent_task_id) is None:
        raise api_error(
            404,
            "parent_task_not_found",
            "Parent task not found.",
            parent_task_id=str(parent_task_id),
        )


def incomplete_dependency_count(session: Session, dependency_task_ids: list[UUID]) -> int:
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


def task_has_incomplete_dependencies(session: Session, task_id: UUID) -> bool:
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


def augment_dependency_kinds_for_action(
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
