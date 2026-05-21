from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.db.public.agent_tasks import AgentTask, AgentTaskStatus
from app.services.agent_task_worker import claim_next_agent_task, unblock_ready_agent_tasks


def test_claim_next_agent_task_limits_worker_lease_query_to_one_row() -> None:
    captured = {}

    class FakeResult:
        def scalar_one_or_none(self):
            return None

    class FakeSession:
        def execute(self, query):
            captured["sql"] = str(
                query.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
            )
            return FakeResult()

        def rollback(self) -> None:
            captured["rolled_back"] = True

    task = claim_next_agent_task(FakeSession(), "worker-1")

    assert task is None
    assert captured["rolled_back"] is True
    assert " LIMIT 1" in captured["sql"]
    assert "FOR UPDATE SKIP LOCKED" in captured["sql"]
    assert "'queued'" in captured["sql"]
    assert "'retry_wait'" in captured["sql"]


def test_unblock_ready_agent_tasks_transitions_when_dependencies_clear() -> None:
    now = datetime.now(UTC)
    awaiting_approval_task = AgentTask(
        id=uuid4(),
        task_type="evaluate_search_harness",
        status=AgentTaskStatus.BLOCKED.value,
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=None,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    queued_task = AgentTask(
        id=uuid4(),
        task_type="run_search_replay_suite",
        status=AgentTaskStatus.BLOCKED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )

    class ScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self._rows

        def first(self):
            return None

    class FakeSession:
        def __init__(self):
            self.calls = 0
            self.committed = False

        def execute(self, _query):
            self.calls += 1
            if self.calls == 1:
                return ScalarResult([awaiting_approval_task, queued_task])
            return ScalarResult([])

        def commit(self) -> None:
            self.committed = True

    session = FakeSession()
    updated = unblock_ready_agent_tasks(session)

    assert updated == 2
    assert session.committed is True
    assert awaiting_approval_task.status == AgentTaskStatus.AWAITING_APPROVAL.value
    assert queued_task.status == AgentTaskStatus.QUEUED.value
