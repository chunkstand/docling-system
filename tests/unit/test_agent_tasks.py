from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.db.models import (
    AgentTask,
    AgentTaskAttempt,
    AgentTaskDependency,
    AgentTaskDependencyKind,
    AgentTaskOutcome,
    AgentTaskStatus,
)
from app.schemas.agent_tasks import (
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskOutcomeCreateRequest,
    AgentTaskRejectionRequest,
)
from app.services.agent_tasks import (
    _initial_task_status,
    approve_agent_task,
    create_agent_task,
    create_agent_task_outcome,
    get_agent_task_recommendation_summary,
    get_agent_task_trends,
    get_agent_task_value_density,
    reject_agent_task,
)


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
    ) -> None:
        self.task = task
        self.outcome_rows = outcome_rows or []
        self.task_rows = task_rows or ([] if task is None else [task])
        self.attempt_rows = attempt_rows or []
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
        if "FROM agent_tasks" in rendered:
            return FakeExecuteResult(self.task_rows)
        if "agent_task_outcomes" in rendered:
            return FakeExecuteResult(self.outcome_rows)
        raise AssertionError(f"Unexpected execute statement: {rendered}")


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
    assert {row.dependency_kind for row in dependency_rows} == {
        AgentTaskDependencyKind.EXPLICIT.value
    }
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
    assert dependency_rows[0].dependency_kind == AgentTaskDependencyKind.SOURCE_TASK.value


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
        assert "Only terminal tasks can receive outcome labels" in exc.detail
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
        assert "already been recorded" in exc.detail
    else:
        raise AssertionError("Expected duplicate outcome labeling to fail")


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


def test_create_apply_harness_task_auto_adds_draft_and_verification_dependencies(
    monkeypatch,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    session = FakeSession()

    monkeypatch.setattr("app.services.agent_tasks._validate_parent_task_id", lambda *args: None)
    monkeypatch.setattr("app.services.agent_tasks._validate_dependency_ids", lambda *args: None)
    monkeypatch.setattr("app.services.agent_tasks._incomplete_dependency_count", lambda *args: 0)
    monkeypatch.setattr("app.services.agent_tasks._build_detail", lambda session, task: task)

    task = create_agent_task(
        session,
        AgentTaskCreateRequest(
            task_type="apply_harness_config_update",
            input={
                "draft_task_id": str(draft_task_id),
                "verification_task_id": str(verification_task_id),
                "reason": "publish review harness",
            },
        ),
    )

    dependency_rows = [row for row in session.added if isinstance(row, AgentTaskDependency)]

    assert task.status == AgentTaskStatus.AWAITING_APPROVAL.value
    assert task.side_effect_level == "promotable"
    assert task.requires_approval is True
    assert {row.depends_on_task_id for row in dependency_rows} == {
        draft_task_id,
        verification_task_id,
    }


def test_agent_task_trends_bucket_attempt_metrics_with_attempt_task() -> None:
    first_created = datetime(2026, 4, 12, 10, 0, tzinfo=UTC)
    second_created = datetime(2026, 4, 13, 10, 0, tzinfo=UTC)
    first_task = AgentTask(
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
        created_at=first_created,
        updated_at=first_created,
    )
    second_task = AgentTask(
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
        created_at=second_created,
        updated_at=second_created,
    )
    first_attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=first_task.id,
        attempt_number=1,
        status="completed",
        input_json={},
        result_json={},
        cost_json={},
        performance_json={"queue_latency_ms": 5.0, "execution_latency_ms": 10.0},
        created_at=first_created,
    )
    second_attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=second_task.id,
        attempt_number=1,
        status="completed",
        input_json={},
        result_json={},
        cost_json={},
        performance_json={"queue_latency_ms": 7.0, "execution_latency_ms": 14.0},
        created_at=second_created,
    )
    session = FakeSession(
        task_rows=[first_task, second_task],
        attempt_rows=[first_attempt, second_attempt],
    )

    response = get_agent_task_trends(session)

    assert len(response.series) == 2
    assert response.series[0].median_execution_latency_ms == 10.0
    assert response.series[1].median_execution_latency_ms == 14.0


def test_recommendation_summary_task_type_filter_keeps_linked_tasks() -> None:
    now = datetime.now(UTC)
    triage_task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        result_json={"recommendation": {"next_action": "candidate_ready_for_review"}},
        input_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    draft_task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={"source_task_id": str(triage_task.id)},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    session = FakeSession(task_rows=[triage_task, draft_task])

    summary = get_agent_task_recommendation_summary(
        session,
        task_type="triage_replay_regression",
        workflow_version="v1",
    )

    assert summary.recommendation_task_count == 1
    assert summary.draft_count == 1


def test_value_density_includes_linked_workflow_attempt_costs() -> None:
    now = datetime.now(UTC)
    triage_task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        result_json={"recommendation": {"next_action": "candidate_ready_for_review"}},
        input_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    draft_task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={"source_task_id": str(triage_task.id)},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    triage_attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=triage_task.id,
        attempt_number=1,
        status="completed",
        input_json={},
        result_json={},
        cost_json={"estimated_usd": 1.0},
        performance_json={"end_to_end_latency_ms": 1000.0},
        created_at=now,
    )
    draft_attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=draft_task.id,
        attempt_number=1,
        status="completed",
        input_json={},
        result_json={},
        cost_json={"estimated_usd": 2.0},
        performance_json={"end_to_end_latency_ms": 2000.0},
        created_at=now,
    )
    useful_outcome = AgentTaskOutcome(
        id=uuid4(),
        task_id=triage_task.id,
        outcome_label="useful",
        created_by="operator@example.com",
        created_at=now,
    )
    session = FakeSession(
        task_rows=[triage_task, draft_task],
        attempt_rows=[triage_attempt, draft_attempt],
        outcome_rows=[useful_outcome],
    )

    rows = get_agent_task_value_density(session)

    assert len(rows) == 1
    assert rows[0].estimated_usd_total == 3.0
