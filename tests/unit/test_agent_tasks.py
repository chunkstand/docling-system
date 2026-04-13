from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.db.models import AgentTask, AgentTaskDependency, AgentTaskStatus
from app.schemas.agent_tasks import (
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskRejectionRequest,
)
from app.services.agent_tasks import (
    _initial_task_status,
    approve_agent_task,
    create_agent_task,
    reject_agent_task,
)


class FakeSession:
    def __init__(self, task: AgentTask | None = None) -> None:
        self.task = task
        self.added: list[object] = []
        self.flushed = False
        self.committed = False

    def add(self, row: object) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True

    def commit(self) -> None:
        self.committed = True

    def get(self, model, task_id):
        return self.task


def test_initial_task_status_prefers_blocked_over_approval() -> None:
    assert (
        _initial_task_status(requires_approval=True, has_incomplete_dependencies=True)
        == AgentTaskStatus.BLOCKED.value
    )


def test_initial_task_status_awaits_approval_when_ready() -> None:
    assert (
        _initial_task_status(requires_approval=True, has_incomplete_dependencies=False)
        == AgentTaskStatus.AWAITING_APPROVAL.value
    )


def test_create_agent_task_adds_dependency_rows_and_sets_status(monkeypatch) -> None:
    dependency_a = uuid4()
    dependency_b = uuid4()
    session = FakeSession()

    monkeypatch.setattr("app.services.agent_tasks._validate_parent_task_id", lambda *args: None)
    monkeypatch.setattr("app.services.agent_tasks._validate_dependency_ids", lambda *args: None)
    monkeypatch.setattr("app.services.agent_tasks._incomplete_dependency_count", lambda *args: 0)
    monkeypatch.setattr("app.services.agent_tasks._build_detail", lambda session, task: task)

    task = create_agent_task(
        session,
        AgentTaskCreateRequest(
            task_type="evaluate_search_harness",
            side_effect_level="read_only",
            requires_approval=False,
            dependency_task_ids=[dependency_a, dependency_b, dependency_a],
            input={"candidate_harness_name": "prose_v3"},
            model_settings={"temperature": 0},
        ),
    )

    dependency_rows = [row for row in session.added if isinstance(row, AgentTaskDependency)]

    assert isinstance(task, AgentTask)
    assert task.status == AgentTaskStatus.QUEUED.value
    assert task.requires_approval is False
    assert task.input_json["candidate_harness_name"] == "prose_v3"
    assert task.input_json["baseline_harness_name"] == "default_v1"
    assert task.model_settings_json == {"temperature": 0}
    assert len(dependency_rows) == 2
    assert {row.depends_on_task_id for row in dependency_rows} == {dependency_a, dependency_b}
    assert session.flushed is True
    assert session.committed is True


def test_create_promotable_task_uses_registry_defaults_and_awaits_approval(monkeypatch) -> None:
    source_task_id = uuid4()
    session = FakeSession()

    monkeypatch.setattr("app.services.agent_tasks._validate_parent_task_id", lambda *args: None)
    monkeypatch.setattr("app.services.agent_tasks._validate_dependency_ids", lambda *args: None)
    monkeypatch.setattr("app.services.agent_tasks._incomplete_dependency_count", lambda *args: 0)
    monkeypatch.setattr("app.services.agent_tasks._build_detail", lambda session, task: task)

    task = create_agent_task(
        session,
        AgentTaskCreateRequest(
            task_type="enqueue_document_reprocess",
            input={
                "document_id": str(uuid4()),
                "source_task_id": str(source_task_id),
                "reason": "triage requested a fresh run",
            },
        ),
    )

    dependency_rows = [row for row in session.added if isinstance(row, AgentTaskDependency)]

    assert task.status == AgentTaskStatus.AWAITING_APPROVAL.value
    assert task.side_effect_level == "promotable"
    assert task.requires_approval is True
    assert task.input_json["source_task_id"] == str(source_task_id)
    assert len(dependency_rows) == 1
    assert dependency_rows[0].depends_on_task_id == source_task_id


def test_create_agent_task_rejects_parent_as_explicit_dependency() -> None:
    parent_task_id = uuid4()
    session = FakeSession()

    try:
        create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="run_search_replay_suite",
                parent_task_id=parent_task_id,
                dependency_task_ids=[parent_task_id],
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "depend on its parent task explicitly" in exc.detail
    else:
        raise AssertionError("Expected parent/dependency overlap to be rejected")


def test_approve_agent_task_moves_ready_task_to_queue(monkeypatch) -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="evaluate_search_harness",
        status=AgentTaskStatus.AWAITING_APPROVAL.value,
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    session = FakeSession(task=task)

    monkeypatch.setattr(
        "app.services.agent_tasks._task_has_incomplete_dependencies",
        lambda *args: False,
    )
    monkeypatch.setattr("app.services.agent_tasks._build_detail", lambda session, task: task)

    approved = approve_agent_task(
        session,
        task.id,
        AgentTaskApprovalRequest(approved_by="operator@example.com", approval_note="ship it"),
    )

    assert approved.status == AgentTaskStatus.QUEUED.value
    assert approved.approved_by == "operator@example.com"
    assert approved.approval_note == "ship it"
    assert approved.approved_at is not None
    assert session.committed is True


def test_approve_agent_task_rejects_non_approval_task(monkeypatch) -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="get_latest_evaluation",
        status=AgentTaskStatus.QUEUED.value,
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
    session = FakeSession(task=task)

    try:
        approve_agent_task(
            session,
            task.id,
            AgentTaskApprovalRequest(approved_by="operator@example.com"),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "does not require approval" in exc.detail
    else:
        raise AssertionError("Expected non-approval task to reject approval")


def test_reject_agent_task_marks_pending_task_as_rejected(monkeypatch) -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="enqueue_document_reprocess",
        status=AgentTaskStatus.AWAITING_APPROVAL.value,
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    session = FakeSession(task=task)

    monkeypatch.setattr("app.services.agent_tasks._build_detail", lambda session, task: task)

    rejected = reject_agent_task(
        session,
        task.id,
        AgentTaskRejectionRequest(
            rejected_by="operator@example.com",
            rejection_note="not enough evidence",
        ),
    )

    assert rejected.status == AgentTaskStatus.REJECTED.value
    assert rejected.rejected_by == "operator@example.com"
    assert rejected.rejection_note == "not enough evidence"
    assert rejected.rejected_at is not None
    assert rejected.completed_at is not None
    assert session.committed is True


def test_reject_agent_task_rejects_already_approved_task(monkeypatch) -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="enqueue_document_reprocess",
        status=AgentTaskStatus.QUEUED.value,
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=now,
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    session = FakeSession(task=task)

    try:
        reject_agent_task(
            session,
            task.id,
            AgentTaskRejectionRequest(rejected_by="reviewer@example.com"),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "Approved tasks cannot be rejected" in exc.detail
    else:
        raise AssertionError("Expected approved task rejection to fail")


def test_create_agent_task_rejects_registry_side_effect_mismatch() -> None:
    session = FakeSession()

    try:
        create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_search_harness",
                side_effect_level="promotable",
                requires_approval=False,
                input={"candidate_harness_name": "wide_v2"},
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "requires side_effect_level 'read_only'" in exc.detail
    else:
        raise AssertionError("Expected side-effect mismatch to be rejected")


def test_create_verifier_task_auto_adds_target_dependency_and_blocks_until_ready(
    monkeypatch,
) -> None:
    target_task_id = uuid4()
    session = FakeSession()

    monkeypatch.setattr("app.services.agent_tasks._validate_parent_task_id", lambda *args: None)
    monkeypatch.setattr("app.services.agent_tasks._validate_dependency_ids", lambda *args: None)
    monkeypatch.setattr("app.services.agent_tasks._incomplete_dependency_count", lambda *args: 1)
    monkeypatch.setattr("app.services.agent_tasks._build_detail", lambda session, task: task)

    task = create_agent_task(
        session,
        AgentTaskCreateRequest(
            task_type="verify_search_harness_evaluation",
            side_effect_level="read_only",
            requires_approval=False,
            input={"target_task_id": str(target_task_id)},
        ),
    )

    dependency_rows = [row for row in session.added if isinstance(row, AgentTaskDependency)]

    assert task.status == AgentTaskStatus.BLOCKED.value
    assert len(dependency_rows) == 1
    assert dependency_rows[0].depends_on_task_id == target_task_id
