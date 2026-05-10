from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ApplyHarnessConfigUpdateTaskInput,
    DraftHarnessConfigFromOptimizationTaskInput,
    DraftHarnessConfigUpdateTaskInput,
    OptimizeSearchHarnessFromCaseTaskInput,
    VerifyDraftHarnessConfigTaskInput,
)
from app.services.agent_task_actions import (
    _apply_harness_config_update_executor,
    _draft_harness_config_from_optimization_executor,
    _draft_harness_config_update_executor,
    _optimize_search_harness_from_case_executor,
    _verify_draft_harness_config_executor,
)
from tests.unit.agent_task_actions_support import (
    _draft_output_payload,
    _resolve_payload_by_expected_type,
    _verification_output_payload,
)


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

def test_optimize_search_harness_from_case_does_not_recommend_noop_draft(
    monkeypatch,
) -> None:
    case_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="optimize_search_harness_from_case",
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
    optimization = SimpleNamespace(
        best_gate={"outcome": "passed"},
        best_override_spec={
            "base_harness_name": "wide_v2",
            "retrieval_profile_overrides": {},
            "reranker_overrides": {},
        },
        best_score={"sort_key": [1, 0, 0]},
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.get_eval_failure_case",
        lambda session, requested_case_id: {"case_id": str(requested_case_id)},
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.run_search_harness_optimization_loop",
        lambda session, request: optimization,
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/search_harness_optimization.json",
        ),
    )

    result = _optimize_search_harness_from_case_executor(
        session=object(),
        task=task,
        payload=OptimizeSearchHarnessFromCaseTaskInput(
            case_id=case_id,
            limit=1,
            iterations=1,
        ),
    )

    assert result["recommendation"]["next_action"] == "inspect_optimizer_attempts"
    assert "did not change the harness" in result["recommendation"]["summary"]

def test_draft_harness_from_optimization_uses_augmented_override_for_snapshot(
    monkeypatch,
) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update_from_optimization",
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
    source_output = SimpleNamespace(
        case={"case_id": str(uuid4())},
        optimization=SimpleNamespace(
            base_harness_name="wide_v2",
            best_override_spec={
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                "reranker_overrides": {},
            },
            stopped_reason="iteration_limit_reached",
            iterations_completed=1,
            best_score={"sort_key": [1, 0, 1]},
            best_gate={"outcome": "passed"},
        ),
    )
    captured: dict = {}

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output={},
            task_type="optimize_search_harness_from_case",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.OptimizeSearchHarnessFromCaseTaskOutput.model_validate",
        lambda output: source_output,
    )

    def fake_get_search_harness(name, harness_overrides=None):
        override_spec = dict((harness_overrides or {})[name])
        captured["override_spec"] = override_spec
        return SimpleNamespace(
            config_snapshot={
                "harness_name": name,
                "base_harness_name": override_spec["base_harness_name"],
                "metadata": {
                    "draft_task_id": override_spec.get("draft_task_id"),
                    "source_task_id": override_spec.get("source_task_id"),
                    "rationale": override_spec.get("rationale"),
                },
            }
        )

    monkeypatch.setattr(
        "app.services.agent_task_actions.get_search_harness",
        fake_get_search_harness,
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/harness_config_draft.json",
        ),
    )

    result = _draft_harness_config_from_optimization_executor(
        session=object(),
        task=task,
        payload=DraftHarnessConfigFromOptimizationTaskInput(
            source_task_id=source_task_id,
            draft_harness_name="case_review",
            rationale="Use wider candidate generation.",
        ),
    )

    assert captured["override_spec"]["draft_task_id"] == str(task.id)
    assert captured["override_spec"]["source_task_id"] == str(source_task_id)
    assert result["draft"]["effective_harness_config"]["metadata"] == {
        "draft_task_id": str(task.id),
        "source_task_id": str(source_task_id),
        "rationale": "Use wider candidate generation.",
    }

def test_draft_harness_from_optimization_rejects_noop_best_override(monkeypatch) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update_from_optimization",
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
    source_output = SimpleNamespace(
        case={"case_id": str(uuid4())},
        optimization=SimpleNamespace(
            base_harness_name="wide_v2",
            best_override_spec={
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {},
                "reranker_overrides": {},
            },
            stopped_reason="no_improving_candidates",
            iterations_completed=0,
            best_score={"sort_key": [1, 0, 0]},
            best_gate={"outcome": "passed"},
        ),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output={},
            task_type="optimize_search_harness_from_case",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.OptimizeSearchHarnessFromCaseTaskOutput.model_validate",
        lambda output: source_output,
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.get_search_harness",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("no-op optimization should not build an effective harness")
        ),
    )

    try:
        _draft_harness_config_from_optimization_executor(
            session=object(),
            task=task,
            payload=DraftHarnessConfigFromOptimizationTaskInput(
                source_task_id=source_task_id,
                draft_harness_name="case_review",
            ),
        )
    except ValueError as exc:
        assert "no-op config update" in str(exc)
    else:
        raise AssertionError("Expected no-op optimization draft to be rejected")

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
        return _resolve_payload_by_expected_type(
            resolver_payloads,
            expected_task_type,
        )

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

def test_apply_harness_config_update_executor_attaches_follow_up_evidence(
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
    created_artifacts = []

    def fake_create_artifact(session, **kwargs):
        artifact = type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": f"/tmp/{kwargs['filename']}",
            },
        )()
        created_artifacts.append((kwargs["artifact_kind"], kwargs["payload"]))
        return artifact

    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        fake_create_artifact,
    )
    verification_output = _verification_output_payload(
        verification_task_id=verification_task_id,
        draft_task_id=draft_task_id,
    )
    verification_output["comprehension_gate"] = {
        "comprehension_passed": True,
        "claim_evidence_alignment": "aligned",
        "change_justification": "publish review harness",
        "predicted_blast_radius": {"changed_scopes": ["reranker_overrides"]},
        "rollback_condition": "rollback on regression",
        "follow_up_plan": {
            "baseline_harness_name": "wide_v2",
            "candidate_harness_name": "wide_v2_review",
            "source_types": ["evaluation_queries"],
            "limit": 10,
        },
        "reasons": [],
    }
    verification_output["follow_up_plan"] = verification_output["comprehension_gate"][
        "follow_up_plan"
    ]
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(output=verification_output),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.evaluate_search_harness",
        lambda session, request: {
            "baseline_harness_name": request.baseline_harness_name,
            "candidate_harness_name": request.candidate_harness_name,
            "limit": request.limit,
            "total_shared_query_count": 10,
            "total_improved_count": 1,
            "total_regressed_count": 0,
            "total_unchanged_count": 9,
            "sources": [],
        },
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

    assert result["follow_up_summary"]["recommendation"] == "keep_override"
    assert result["follow_up_artifact_kind"] == "follow_up_evaluation_summary"
    assert [kind for kind, _payload in created_artifacts] == [
        "follow_up_evaluation_summary",
        "applied_harness_config_update",
    ]

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
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
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
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
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
            raise HTTPException(
                status_code=404, detail=f"Target task not found: {depends_on_task_id}"
            )
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
