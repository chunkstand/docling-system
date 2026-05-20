from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import AgentTask, AgentTaskAttempt, AgentTaskStatus
from app.services.agent_task_worker import (
    PROMOTABLE_SIDE_EFFECT_APPLIED_KEY,
    PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY,
    process_agent_task,
    run_agent_task_worker_loop,
)
from app.services.storage import StorageService


def test_agent_task_worker_loop_exits_when_runtime_code_is_stale(monkeypatch) -> None:
    events: dict[str, object] = {"claimed": False, "slept": False}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "app.services.agent_task_worker.get_settings",
        lambda: SimpleNamespace(worker_poll_seconds=2),
    )
    monkeypatch.setattr(
        "app.db.session.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr("app.services.agent_task_worker.StorageService", lambda: object())
    monkeypatch.setattr(
        "app.services.agent_task_worker.get_process_identity",
        lambda: "agent-worker-1",
    )

    @contextmanager
    def fake_runtime_process_heartbeat(*_args, **_kwargs):
        yield SimpleNamespace(startup_code_fingerprint="old-fingerprint")

    monkeypatch.setattr(
        "app.services.agent_task_worker.runtime_process_heartbeat",
        fake_runtime_process_heartbeat,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.runtime_code_is_current",
        lambda startup_code_fingerprint=None: False,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.unblock_ready_agent_tasks",
        lambda *args: 0,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.requeue_stale_agent_tasks",
        lambda *args, **kwargs: 0,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.claim_next_agent_task",
        lambda *args, **kwargs: events.__setitem__("claimed", True),
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.time.sleep",
        lambda *_args, **_kwargs: events.__setitem__("slept", True),
    )

    run_agent_task_worker_loop()

    assert events["claimed"] is False
    assert events["slept"] is False


def test_agent_task_worker_loop_registers_runtime_before_claiming(monkeypatch) -> None:
    events: dict[str, object] = {"registered": False, "claimed": False}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "app.services.agent_task_worker.get_settings",
        lambda: SimpleNamespace(worker_poll_seconds=2),
    )
    monkeypatch.setattr(
        "app.db.session.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr("app.services.agent_task_worker.StorageService", lambda: object())
    monkeypatch.setattr(
        "app.services.agent_task_worker.get_process_identity",
        lambda: "agent-worker-1",
    )

    @contextmanager
    def fake_runtime_process_heartbeat(process_kind, process_identity, **_kwargs):
        events["registered"] = (process_kind, process_identity)
        yield SimpleNamespace(startup_code_fingerprint="current-fingerprint")

    def fake_claim_next_agent_task(*args, **kwargs):
        events["claimed"] = True
        raise SystemExit("stop after first claim attempt")

    monkeypatch.setattr(
        "app.services.agent_task_worker.runtime_process_heartbeat",
        fake_runtime_process_heartbeat,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.runtime_code_is_current",
        lambda startup_code_fingerprint=None: True,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.unblock_ready_agent_tasks",
        lambda *args: 0,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.requeue_stale_agent_tasks",
        lambda *args, **kwargs: 0,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.claim_next_agent_task",
        fake_claim_next_agent_task,
    )

    try:
        run_agent_task_worker_loop()
    except SystemExit as exc:
        assert str(exc) == "stop after first claim attempt"
    else:
        raise AssertionError("Expected worker loop to stop after first claim attempt")

    assert events["registered"] == ("agent_worker", "agent-worker-1")
    assert events["claimed"] is True


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
        locked_by="worker-1",
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
            self.added: list[object] = []

        def get(self, model, key):
            return task if key == task_id else None

        def add(self, row: object) -> None:
            if getattr(row, "id", None) is None:
                row.id = uuid4()
            self.added.append(row)

        def flush(self) -> None:
            return None

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    observed: dict[str, object | None] = {}

    @contextmanager
    def fake_agent_task_lease_heartbeat(task_id, *, worker_id):
        observed["heartbeat_task_id"] = task_id
        observed["heartbeat_worker_id"] = worker_id
        observed["heartbeat_entered"] = True
        try:
            yield
        finally:
            observed["heartbeat_exited"] = True

    monkeypatch.setattr(
        "app.services.agent_task_worker.agent_task_lease_heartbeat",
        fake_agent_task_lease_heartbeat,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.execute_agent_task_action",
        lambda session, task: {"task_type": task.task_type, "payload": {"candidate_count": 2}},
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker_finalization.current_attempt",
        lambda *args: None,
    )

    session = FakeSession()
    process_agent_task(session, task_id, storage_service)

    assert session.rollbacks == 0
    assert task.status == AgentTaskStatus.COMPLETED.value
    assert task.result_json["payload"]["candidate_count"] == 2
    assert observed["heartbeat_task_id"] == task_id
    assert observed["heartbeat_worker_id"] == "worker-1"
    assert observed["heartbeat_entered"] is True
    assert observed["heartbeat_exited"] is True


def test_process_agent_task_records_attempt_cost_and_performance(
    monkeypatch, tmp_path: Path
) -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    task = AgentTask(
        id=task_id,
        task_type="run_search_replay_suite",
        status=AgentTaskStatus.PROCESSING.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={"source_type": "evaluation_queries"},
        result_json={},
        attempts=1,
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        started_at=now,
        updated_at=now,
    )
    attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=task_id,
        attempt_number=1,
        status="processing",
        worker_id="worker-1",
        input_json=task.input_json,
        result_json={},
        cost_json={},
        performance_json={},
        created_at=now,
        started_at=now,
    )
    storage_service = StorageService(storage_root=tmp_path / "storage")

    class FakeSession:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0
            self.added: list[object] = []

        def get(self, model, key):
            return task if key == task_id else None

        def add(self, row: object) -> None:
            if getattr(row, "id", None) is None:
                row.id = uuid4()
            self.added.append(row)

        def flush(self) -> None:
            return None

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    monkeypatch.setattr(
        "app.services.agent_task_worker.execute_agent_task_action",
        lambda session, task: {
            "task_type": task.task_type,
            "payload": {"replay_run": {"query_count": 12}},
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker_finalization.current_attempt",
        lambda *args: attempt,
    )

    session = FakeSession()
    process_agent_task(session, task_id, storage_service)

    assert session.rollbacks == 0
    assert attempt.status == "completed"
    assert attempt.cost_json["replay_query_count"] == 12
    assert attempt.cost_json["estimated_usd"] == 0.0
    assert attempt.performance_json["execution_latency_ms"] is not None
    assert attempt.performance_json["queue_latency_ms"] is not None


def test_process_agent_task_checkpoints_promotable_result_before_context_write_failure(
    monkeypatch, tmp_path: Path
) -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    task = AgentTask(
        id=task_id,
        task_type="enqueue_document_reprocess",
        status=AgentTaskStatus.PROCESSING.value,
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={"document_id": str(uuid4())},
        result_json={},
        attempts=1,
        locked_by="worker-1",
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    storage_service = StorageService(storage_root=tmp_path / "storage")

    class FakeSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def get(self, model, key):
            return task if key == task_id else None

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    @contextmanager
    def fake_agent_task_lease_heartbeat(task_id, *, worker_id):
        yield

    monkeypatch.setattr(
        "app.services.agent_task_worker.agent_task_lease_heartbeat",
        fake_agent_task_lease_heartbeat,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.heartbeat_agent_task",
        lambda session, task: None,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.write_agent_task_context",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("context write failed")),
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker_finalization.current_attempt",
        lambda *args: None,
    )

    session = FakeSession()
    process_agent_task(
        session,
        task_id,
        storage_service,
        executor=lambda session, task: {
            "task_type": task.task_type,
            "payload": {"reprocess": {"run_id": str(uuid4())}},
        },
    )

    assert session.rollbacks == 1
    assert session.commits == 2
    assert task.status == AgentTaskStatus.RETRY_WAIT.value
    assert task.result_json[PROMOTABLE_SIDE_EFFECT_APPLIED_KEY] == "applied"
    assert task.result_json[PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY]["payload"]["reprocess"]["run_id"]


def test_process_agent_task_reuses_checkpointed_promotable_result_on_retry(
    monkeypatch, tmp_path: Path
) -> None:
    task_id = uuid4()
    run_id = uuid4()
    now = datetime.now(UTC)
    task = AgentTask(
        id=task_id,
        task_type="enqueue_document_reprocess",
        status=AgentTaskStatus.PROCESSING.value,
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={"document_id": str(uuid4())},
        result_json={
            PROMOTABLE_SIDE_EFFECT_APPLIED_KEY: "applied",
            PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY: {
                "task_type": "enqueue_document_reprocess",
                "payload": {"reprocess": {"run_id": str(run_id)}},
            },
            "failure_type": "RuntimeError",
            "failure_stage": "complete",
        },
        attempts=2,
        locked_by="worker-1",
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    storage_service = StorageService(storage_root=tmp_path / "storage")

    class FakeSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def get(self, model, key):
            return task if key == task_id else None

        def add(self, row: object) -> None:
            return None

        def flush(self) -> None:
            return None

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    @contextmanager
    def fake_agent_task_lease_heartbeat(task_id, *, worker_id):
        yield

    monkeypatch.setattr(
        "app.services.agent_task_worker.agent_task_lease_heartbeat",
        fake_agent_task_lease_heartbeat,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.heartbeat_agent_task",
        lambda session, task: None,
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker.execute_agent_task_action",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("executor should not rerun")),
    )
    monkeypatch.setattr(
        "app.services.agent_task_worker_finalization.current_attempt",
        lambda *args: None,
    )

    session = FakeSession()
    process_agent_task(session, task_id, storage_service)

    assert session.rollbacks == 0
    assert task.status == AgentTaskStatus.COMPLETED.value
    assert task.result_json["payload"]["reprocess"]["run_id"] == str(run_id)
    assert PROMOTABLE_SIDE_EFFECT_APPLIED_KEY not in task.result_json
    assert "failure_type" not in task.result_json
