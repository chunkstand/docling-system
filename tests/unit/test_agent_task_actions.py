from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ApplyHarnessConfigUpdateTaskInput,
    DraftHarnessConfigUpdateTaskInput,
    EnqueueDocumentReprocessTaskInput,
    VerifyDraftHarnessConfigTaskInput,
)
from app.schemas.documents import DocumentUploadResponse
from app.services.agent_task_actions import (
    _apply_harness_config_update_executor,
    _draft_harness_config_update_executor,
    _enqueue_document_reprocess_executor,
    _verify_draft_harness_config_executor,
    get_agent_task_action,
    execute_agent_task_action,
    validate_agent_task_output,
)


def test_enqueue_document_reprocess_executor_queues_reprocess(monkeypatch) -> None:
    document_id = uuid4()
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="enqueue_document_reprocess",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.reprocess_document",
        lambda session, requested_document_id: DocumentUploadResponse(
            document_id=requested_document_id,
            run_id=uuid4(),
            status="queued",
            duplicate=False,
        ),
    )

    result = _enqueue_document_reprocess_executor(
        session=object(),
        _task=task,
        payload=EnqueueDocumentReprocessTaskInput(
            document_id=document_id,
            source_task_id=source_task_id,
            reason="triage requested reprocess",
        ),
    )

    assert result["document_id"] == str(document_id)
    assert result["source_task_id"] == str(source_task_id)
    assert result["reason"] == "triage requested reprocess"
    assert result["reprocess"]["document_id"] == str(document_id)
    assert result["reprocess"]["status"] == "queued"


def test_draft_harness_config_update_executor_writes_draft_artifact(
    monkeypatch,
    tmp_path,
) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/harness_config_draft.json",
            },
        )(),
    )
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )

    session = type(
        "FakeSession",
        (),
        {
            "get": lambda self, model, key: type(
                "SourceTask",
                (),
                {"id": key, "task_type": "triage_replay_regression"},
            )()
        },
    )()

    result = _draft_harness_config_update_executor(
        session=session,
        task=task,
        payload=DraftHarnessConfigUpdateTaskInput(
            draft_harness_name="wide_v2_review",
            base_harness_name="wide_v2",
            source_task_id=source_task_id,
            rationale="publish review harness",
            reranker_overrides={"result_type_priority_bonus": 0.009},
        ),
    )

    assert result["draft"]["draft_harness_name"] == "wide_v2_review"
    assert result["draft"]["base_harness_name"] == "wide_v2"
    assert result["draft"]["source_task_id"] == str(source_task_id)
    assert result["draft"]["effective_harness_config"]["base_harness_name"] == "wide_v2"
    assert result["artifact_kind"] == "harness_config_draft"


def test_validate_agent_task_output_accepts_migrated_draft_shape() -> None:
    artifact_id = uuid4()
    source_task_id = uuid4()

    validated = validate_agent_task_output(
        "draft_harness_config_update",
        {
            "draft": {
                "draft_harness_name": "wide_v2_review",
                "base_harness_name": "wide_v2",
                "source_task_id": str(source_task_id),
                "source_task_type": "triage_replay_regression",
                "rationale": "publish review harness",
                "override_spec": {
                    "base_harness_name": "wide_v2",
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {"result_type_priority_bonus": 0.009},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(uuid4()),
                    "source_task_id": str(source_task_id),
                    "rationale": "publish review harness",
                },
                "effective_harness_config": {"base_harness_name": "wide_v2"},
            },
            "artifact_id": str(artifact_id),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    )

    assert validated["artifact_id"] == str(artifact_id)
    assert validated["draft"]["source_task_id"] == str(source_task_id)


def test_validate_agent_task_output_rejects_invalid_migrated_draft_shape() -> None:
    try:
        validate_agent_task_output(
            "draft_harness_config_update",
            {
                "artifact_id": str(uuid4()),
                "artifact_kind": "harness_config_draft",
                "artifact_path": "/tmp/harness_config_draft.json",
            },
        )
    except ValidationError as exc:
        assert "draft" in str(exc)
    else:
        raise AssertionError("Expected draft output validation to fail")


def test_execute_agent_task_action_includes_output_schema_metadata(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={
            "draft_harness_name": "wide_v2_review",
            "base_harness_name": "wide_v2",
        },
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    action = replace(
        get_agent_task_action("draft_harness_config_update"),
        executor=lambda session, current_task, payload: {
            "draft": {
                "draft_harness_name": payload.draft_harness_name,
                "base_harness_name": payload.base_harness_name,
                "source_task_id": None,
                "source_task_type": None,
                "rationale": None,
                "override_spec": {
                    "base_harness_name": payload.base_harness_name,
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(current_task.id),
                    "source_task_id": None,
                    "rationale": None,
                },
                "effective_harness_config": {"base_harness_name": payload.base_harness_name},
            },
            "artifact_id": str(uuid4()),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    )
    monkeypatch.setattr("app.services.agent_task_actions.get_agent_task_action", lambda _task_type: action)

    result = execute_agent_task_action(object(), task)

    assert result["output_schema_name"] == "draft_harness_config_update_output"
    assert result["output_schema_version"] == "1.0"
    assert result["payload"]["draft"]["draft_harness_name"] == "wide_v2_review"


def test_verify_draft_harness_config_executor_writes_verification_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_harness_config",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    target_task_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_draft_harness_config_task",
        lambda session, verification_task, payload: {
            "draft": {"draft_harness_name": "wide_v2_review"},
            "evaluation": {"candidate_harness_name": "wide_v2_review"},
            "verification": {"outcome": "passed"},
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/harness_config_draft_verification.json",
            },
        )(),
    )

    result = _verify_draft_harness_config_executor(
        session=object(),
        task=task,
        payload=VerifyDraftHarnessConfigTaskInput(
            target_task_id=target_task_id,
            baseline_harness_name="wide_v2",
            source_types=["evaluation_queries"],
            limit=10,
        ),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "harness_config_draft_verification"


def test_apply_harness_config_update_executor_persists_review_harness(
    monkeypatch,
    tmp_path,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    draft_task = AgentTask(
        id=draft_task_id,
        task_type="draft_harness_config_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={
            "payload": {
                "draft": {
                    "draft_harness_name": "wide_v2_review",
                    "base_harness_name": "wide_v2",
                    "override_spec": {
                        "base_harness_name": "wide_v2",
                        "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                        "reranker_overrides": {"result_type_priority_bonus": 0.009},
                        "draft_task_id": str(draft_task_id),
                        "override_type": "draft_harness_config_update",
                    },
                }
            }
        },
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_draft_harness_config",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={
            "payload": {
                "verification": {
                    "outcome": "passed",
                    "details": {
                        "target_task_id": str(draft_task_id),
                        "draft_harness_name": "wide_v2_review",
                    },
                }
            }
        },
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    rows = {
        draft_task_id: draft_task,
        verification_task_id: verification_task,
    }

    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/applied_harness_config_update.json",
            },
        )(),
    )
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    session = type("FakeSession", (), {"get": lambda self, model, key: rows.get(key)})()

    result = _apply_harness_config_update_executor(
        session=session,
        task=apply_task,
        payload=ApplyHarnessConfigUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish review harness",
        ),
    )

    assert result["draft_harness_name"] == "wide_v2_review"
    assert result["applied_override"]["verification_task_id"] == str(verification_task_id)
    assert Path(result["config_path"]).exists()
    payload = json.loads(Path(result["config_path"]).read_text())
    assert payload["harnesses"]["wide_v2_review"]["base_harness_name"] == "wide_v2"


def test_apply_harness_config_update_executor_rejects_mismatched_verification_target(
    monkeypatch,
    tmp_path,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    other_draft_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    draft_task = AgentTask(
        id=draft_task_id,
        task_type="draft_harness_config_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={
            "payload": {
                "draft": {
                    "draft_harness_name": "wide_v2_review",
                    "base_harness_name": "wide_v2",
                    "override_spec": {
                        "base_harness_name": "wide_v2",
                        "retrieval_profile_overrides": {},
                        "reranker_overrides": {"result_type_priority_bonus": 0.009},
                        "draft_task_id": str(draft_task_id),
                        "override_type": "draft_harness_config_update",
                    },
                }
            }
        },
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_draft_harness_config",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={
            "payload": {
                "verification": {
                    "outcome": "passed",
                    "details": {
                        "target_task_id": str(other_draft_task_id),
                        "draft_harness_name": "wide_v2_review",
                    },
                }
            }
        },
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    rows = {
        draft_task_id: draft_task,
        verification_task_id: verification_task,
    }

    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    session = type("FakeSession", (), {"get": lambda self, model, key: rows.get(key)})()

    try:
        _apply_harness_config_update_executor(
            session=session,
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except ValueError as exc:
        assert "does not target the requested draft task" in str(exc)
    else:
        raise AssertionError("Expected mismatched verifier target to be rejected")
