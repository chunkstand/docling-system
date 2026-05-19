from __future__ import annotations

from uuid import uuid4

from app.db.models import AgentTask


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def one_or_none(self):
        if len(self._rows) > 1:
            raise AssertionError("Expected zero or one row")
        return self._rows[0] if self._rows else None


class FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalars(self):
        return FakeScalarResult(self._rows)

    def scalar_one_or_none(self):
        if len(self._rows) > 1:
            raise AssertionError("Expected zero or one row")
        return self._rows[0] if self._rows else None


class FakeSession:
    def __init__(
        self,
        task: AgentTask | None = None,
        outcome_rows: list[object] | None = None,
        task_rows: list[object] | None = None,
        attempt_rows: list[object] | None = None,
        dependency_rows: list[object] | None = None,
        verification_rows: list[object] | None = None,
    ) -> None:
        self.task = task
        self.outcome_rows = outcome_rows or []
        self.task_rows = task_rows or ([] if task is None else [task])
        self.attempt_rows = attempt_rows or []
        self.dependency_rows = dependency_rows or []
        self.verification_rows = verification_rows or []
        self.added: list[object] = []
        self.flushed = False
        self.committed = False

    def add(self, row: object) -> None:
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True

    def commit(self) -> None:
        self.committed = True

    def get(self, model, task_id):
        return self.task

    def execute(self, statement):
        rendered = str(statement)
        if "agent_task_attempts" in rendered:
            return FakeExecuteResult(self.attempt_rows)
        if "agent_task_verifications" in rendered:
            if "agent_task_verifications.created_at, agent_task_verifications.outcome" in rendered:
                return FakeExecuteResult(
                    [(row.created_at, row.outcome) for row in self.verification_rows]
                )
            return FakeExecuteResult(self.verification_rows)
        if "agent_task_dependencies" in rendered:
            return FakeExecuteResult(self.dependency_rows)
        if "FROM agent_tasks" in rendered:
            if "agent_tasks.id, agent_tasks.created_at, agent_tasks.status" in rendered:
                return FakeExecuteResult(
                    [(row.id, row.created_at, row.status) for row in self.task_rows]
                )
            if "agent_tasks.approved_at, agent_tasks.rejected_at" in rendered:
                return FakeExecuteResult(
                    [(row.approved_at, row.rejected_at) for row in self.task_rows]
                )
            return FakeExecuteResult(self.task_rows)
        if "agent_task_outcomes" in rendered:
            return FakeExecuteResult(self.outcome_rows)
        raise AssertionError(f"Unexpected execute statement: {rendered}")
