from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
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


def _draft_output_payload(*, draft_task_id, draft_harness_name="wide_v2_review") -> dict:
    return {
        "draft": {
            "draft_harness_name": draft_harness_name,
            "base_harness_name": "wide_v2",
            "source_task_id": None,
            "source_task_type": None,
            "rationale": "publish review harness",
            "override_spec": {
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                "reranker_overrides": {"result_type_priority_bonus": 0.009},
                "override_type": "draft_harness_config_update",
                "override_source": "task_draft",
                "draft_task_id": str(draft_task_id),
                "source_task_id": None,
                "rationale": "publish review harness",
            },
            "effective_harness_config": {"base_harness_name": "wide_v2"},
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft",
        "artifact_path": "/tmp/harness_config_draft.json",
    }


def _verification_output_payload(
    *,
    verification_task_id,
    draft_task_id,
    draft_harness_name="wide_v2_review",
    outcome="passed",
) -> dict:
    return {
        "draft": _draft_output_payload(
            draft_task_id=draft_task_id,
            draft_harness_name=draft_harness_name,
        )["draft"],
        "evaluation": {
            "baseline_harness_name": "wide_v2",
            "total_regressed_count": 0,
            "total_improved_count": 1,
        },
        "verification": {
            "verification_id": str(uuid4()),
            "target_task_id": str(draft_task_id),
            "verification_task_id": str(verification_task_id),
            "verifier_type": "draft_harness_config_gate",
            "outcome": outcome,
            "metrics": {"total_shared_query_count": 10},
            "reasons": [],
            "details": {"draft_harness_name": draft_harness_name},
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft_verification",
        "artifact_path": "/tmp/harness_config_draft_verification.json",
    }


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


def test_validate_agent_task_output_accepts_migrated_evaluate_shape() -> None:
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    validated = validate_agent_task_output(
        "evaluate_search_harness",
        {
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "evaluation": {
                "baseline_harness_name": "default_v1",
                "candidate_harness_name": "wide_v2",
                "limit": 12,
                "total_shared_query_count": 4,
                "total_improved_count": 1,
                "total_regressed_count": 0,
                "total_unchanged_count": 3,
                "sources": [
                    {
                        "source_type": "evaluation_queries",
                        "baseline_replay_run_id": str(baseline_replay_run_id),
                        "candidate_replay_run_id": str(candidate_replay_run_id),
                        "baseline_query_count": 4,
                        "candidate_query_count": 4,
                        "baseline_passed_count": 4,
                        "candidate_passed_count": 4,
                        "baseline_zero_result_count": 0,
                        "candidate_zero_result_count": 0,
                        "baseline_table_hit_count": 1,
                        "candidate_table_hit_count": 1,
                        "baseline_top_result_changes": 0,
                        "candidate_top_result_changes": 0,
                        "baseline_mrr": 1.0,
                        "candidate_mrr": 1.0,
                        "baseline_foreign_top_result_count": 0,
                        "candidate_foreign_top_result_count": 0,
                        "acceptance_checks": {"no_regressions": True},
                        "shared_query_count": 4,
                        "improved_count": 1,
                        "regressed_count": 0,
                        "unchanged_count": 3,
                    }
                ],
            },
        },
    )

    assert validated["candidate_harness_name"] == "wide_v2"
    assert validated["evaluation"]["sources"][0]["source_type"] == "evaluation_queries"


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


def test_get_agent_task_action_exposes_evaluate_output_schema_metadata() -> None:
    action = get_agent_task_action("evaluate_search_harness")

    assert action.output_schema_name == "evaluate_search_harness_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None


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
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
            )
        ),
    }

    def fake_resolve(
        session,
        *,
        expected_task_type,
        **_kwargs,
    ):
        return resolver_payloads[expected_task_type]

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    result = _apply_harness_config_update_executor(
        session=object(),
        task=apply_task,
        payload=ApplyHarnessConfigUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish review harness",
        ),
    )

    assert result["draft_harness_name"] == "wide_v2_review"
    assert result["applied_override"]["verification_task_id"] == str(verification_task_id)
    assert result["applied_override"]["applied_by"] == "operator@example.com"
    assert Path(result["config_path"]).exists()
    payload = json.loads(Path(result["config_path"]).read_text())
    assert payload["harnesses"]["wide_v2_review"]["base_harness_name"] == "wide_v2"


def test_apply_harness_config_update_executor_rejects_mismatched_verification_target(
    monkeypatch,
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
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=other_draft_task_id,
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: resolver_payloads[expected_task_type],
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
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


def test_apply_harness_config_update_executor_rejects_failed_verification(monkeypatch) -> None:
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
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
                outcome="failed",
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: resolver_payloads[expected_task_type],
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except ValueError as exc:
        assert "Only passed draft harness verifications can be applied" in str(exc)
    else:
        raise AssertionError("Expected failed verification to be rejected")


def test_apply_harness_config_update_executor_bubbles_dependency_role_errors(monkeypatch) -> None:
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

    def fake_resolve(session, *, dependency_kind, **_kwargs):
        if dependency_kind == "draft_task":
            raise HTTPException(status_code=409, detail="wrong dependency kind")
        return SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
            )
        )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "wrong dependency kind"
    else:
        raise AssertionError("Expected dependency role validation to bubble")


def test_apply_harness_config_update_executor_bubbles_schema_errors(monkeypatch) -> None:
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

    def fake_resolve(session, *, dependency_kind, **_kwargs):
        if dependency_kind == "verification_task":
            raise HTTPException(status_code=409, detail="rerun required")
        return SimpleNamespace(output=_draft_output_payload(draft_task_id=draft_task_id))

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "rerun required"
    else:
        raise AssertionError("Expected schema/rerun validation to bubble")


def test_apply_harness_config_update_executor_bubbles_missing_verification(monkeypatch) -> None:
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

    def fake_resolve(session, *, dependency_kind, depends_on_task_id, **_kwargs):
        if dependency_kind == "verification_task":
            raise HTTPException(status_code=404, detail=f"Target task not found: {depends_on_task_id}")
        return SimpleNamespace(output=_draft_output_payload(draft_task_id=draft_task_id))

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert str(verification_task_id) in exc.detail
    else:
        raise AssertionError("Expected missing verification task to bubble")
