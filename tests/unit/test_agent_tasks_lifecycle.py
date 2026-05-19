from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.db.models import AgentTask, AgentTaskStatus
from app.schemas.agent_tasks import (
    AgentTaskApprovalRequest,
    AgentTaskOutcomeCreateRequest,
    AgentTaskRejectionRequest,
)
from app.services.agent_tasks import (
    approve_agent_task,
    create_agent_task_outcome,
    reject_agent_task,
)
from tests.unit.agent_task_service_support import FakeSession


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


def test_approve_agent_task_rejects_non_approval_task() -> None:
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
        assert exc.detail["code"] == "invalid_agent_task_state"
        assert "does not require approval" in exc.detail["message"]
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


def test_reject_agent_task_rejects_already_approved_task() -> None:
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
        assert exc.detail["code"] == "invalid_agent_task_state"
        assert "Approved tasks cannot be rejected" in exc.detail["message"]
    else:
        raise AssertionError("Expected approved task rejection to fail")


def test_create_agent_task_outcome_records_label_for_terminal_task() -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
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

    outcome = create_agent_task_outcome(
        session,
        task.id,
        AgentTaskOutcomeCreateRequest(
            outcome_label="useful",
            created_by="operator@example.com",
            note="recommendation matched operator judgment",
        ),
    )

    assert outcome.task_id == task.id
    assert outcome.outcome_label == "useful"
    assert outcome.created_by == "operator@example.com"
    assert session.flushed is True
    assert session.committed is True


def test_create_agent_task_outcome_rejects_non_terminal_task() -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.PROCESSING.value,
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
        create_agent_task_outcome(
            session,
            task.id,
            AgentTaskOutcomeCreateRequest(
                outcome_label="useful",
                created_by="operator@example.com",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "invalid_agent_task_state"
        assert "Only terminal tasks can receive outcome labels" in exc.detail["message"]
    else:
        raise AssertionError("Expected non-terminal task labeling to fail")


def test_create_agent_task_outcome_rejects_duplicate_label_from_same_actor() -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
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
    existing_outcome = type(
        "OutcomeRow",
        (),
        {
            "id": uuid4(),
            "task_id": task.id,
            "outcome_label": "useful",
            "created_by": "operator@example.com",
            "note": "already recorded",
            "created_at": now,
        },
    )()
    session = FakeSession(task=task, outcome_rows=[existing_outcome])

    try:
        create_agent_task_outcome(
            session,
            task.id,
            AgentTaskOutcomeCreateRequest(
                outcome_label="useful",
                created_by="operator@example.com",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "agent_task_outcome_already_recorded"
        assert "already been recorded" in exc.detail["message"]
    else:
        raise AssertionError("Expected duplicate outcome labeling to fail")
