from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException

from app.db.models import AgentTask, AgentTaskDependency, AgentTaskDependencyKind, AgentTaskStatus
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.services.agent_tasks import _initial_task_status, create_agent_task
from tests.unit.agent_task_service_support import FakeSession


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
        assert exc.detail["code"] == "invalid_agent_task_request"
        assert "depend on its parent task explicitly" in exc.detail["message"]
    else:
        raise AssertionError("Expected parent/dependency overlap to be rejected")


def test_create_agent_task_rejects_missing_dependency_ids() -> None:
    missing_dependency_id = uuid4()
    session = FakeSession(task_rows=[])

    try:
        create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_search_harness",
                side_effect_level="read_only",
                requires_approval=False,
                dependency_task_ids=[missing_dependency_id],
                input={"candidate_harness_name": "prose_v3"},
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail["code"] == "agent_task_dependency_not_found"
        assert exc.detail["context"]["dependency_task_ids"] == [str(missing_dependency_id)]
    else:
        raise AssertionError("Expected missing dependency IDs to be rejected")


def test_create_agent_task_rejects_missing_action_linked_dependency_ids() -> None:
    missing_target_task_id = uuid4()
    session = FakeSession(task_rows=[])

    try:
        create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_search_harness_evaluation",
                input={"target_task_id": str(missing_target_task_id)},
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail["code"] == "agent_task_dependency_not_found"
        assert exc.detail["context"]["dependency_task_ids"] == [str(missing_target_task_id)]
    else:
        raise AssertionError("Expected missing linked task IDs to be rejected")


def test_create_agent_task_rejects_existing_dependency_cycle() -> None:
    dependency_a = uuid4()
    dependency_b = uuid4()
    session = FakeSession(
        task_rows=[dependency_a],
        dependency_rows=[
            AgentTaskDependency(
                task_id=dependency_a,
                depends_on_task_id=dependency_b,
                dependency_kind=AgentTaskDependencyKind.EXPLICIT.value,
            ),
            AgentTaskDependency(
                task_id=dependency_b,
                depends_on_task_id=dependency_a,
                dependency_kind=AgentTaskDependencyKind.EXPLICIT.value,
            ),
        ],
    )

    try:
        create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_search_harness",
                side_effect_level="read_only",
                requires_approval=False,
                dependency_task_ids=[dependency_a],
                input={"candidate_harness_name": "wide_v2"},
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "agent_task_dependency_cycle"
        assert exc.detail["context"]["dependency_task_ids"] == [str(dependency_a)]
        assert exc.detail["context"]["cycle_task_ids"] == [
            str(dependency_a),
            str(dependency_b),
            str(dependency_a),
        ]
    else:
        raise AssertionError("Expected dependency cycles to be rejected")


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
        assert exc.detail["code"] == "invalid_agent_task_request"
        assert "requires side_effect_level 'read_only'" in exc.detail["message"]
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
