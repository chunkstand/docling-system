from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.db.models import AgentTask, AgentTaskStatus
from app.services.agent_task_worker import (
    claim_next_agent_task,
    finalize_agent_task_failure,
    is_retryable_agent_task_error,
    process_agent_task,
    unblock_ready_agent_tasks,
)
from app.services.storage import StorageService


def test_agent_task_value_errors_are_terminal() -> None:
    assert is_retryable_agent_task_error(ValueError("bad input")) is False


def test_agent_task_unknown_errors_are_retryable() -> None:
    assert is_retryable_agent_task_error(RuntimeError("transient")) is True


def test_agent_task_validation_errors_are_terminal() -> None:
    try:
        raise ValidationError.from_exception_data(
            "SearchReplayRunRequest",
            [{"type": "missing", "loc": ("source_type",), "input": {}, "msg": "Field required"}],
        )
    except ValidationError as exc:
        assert is_retryable_agent_task_error(exc) is False


def test_agent_task_http_errors_are_terminal() -> None:
    assert is_retryable_agent_task_error(HTTPException(status_code=404, detail="missing")) is False


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


def test_finalize_agent_task_failure_writes_replayable_failure_artifact(
    monkeypatch, tmp_path: Path
) -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    storage_service = StorageService(storage_root=tmp_path / "storage")
    task = AgentTask(
        id=task_id,
        task_type="evaluate_search_harness",
        status=AgentTaskStatus.PROCESSING.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={"candidate_harness_name": "prose_v3"},
        result_json={},
        attempts=3,
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )

    class FakeSession:
        def __init__(self) -> None:
            self.committed = False

        def commit(self) -> None:
            self.committed = True

    monkeypatch.setattr("app.services.agent_task_worker._current_attempt", lambda *args: None)

    session = FakeSession()
    finalize_agent_task_failure(
        session,
        task,
        RuntimeError("boom"),
        failure_stage="execute",
        storage_service=storage_service,
    )

    assert session.committed is True
    assert task.failure_artifact_path is not None
    artifact_path = Path(task.failure_artifact_path)
    assert artifact_path.exists() is True
    artifact = artifact_path.read_text()
    assert "boom" in artifact
    assert "execute" in artifact


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


def test_process_agent_task_uses_registered_executor(monkeypatch, tmp_path: Path) -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    task = AgentTask(
        id=task_id,
        task_type="list_quality_eval_candidates",
        status=AgentTaskStatus.PROCESSING.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={"limit": 3, "include_resolved": False},
        result_json={},
        attempts=1,
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    storage_service = StorageService(storage_root=tmp_path / "storage")

    class FakeSession:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        def get(self, model, key):
            return task if key == task_id else None

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    monkeypatch.setattr(
        "app.services.agent_task_worker.execute_agent_task_action",
        lambda session, task: {"task_type": task.task_type, "payload": {"candidate_count": 2}},
    )
    monkeypatch.setattr("app.services.agent_task_worker._current_attempt", lambda *args: None)

    session = FakeSession()
    process_agent_task(session, task_id, storage_service)

    assert session.rollbacks == 0
    assert task.status == AgentTaskStatus.COMPLETED.value
    assert task.result_json["payload"]["candidate_count"] == 2
