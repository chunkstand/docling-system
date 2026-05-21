from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_tasks import (
    DraftHarnessConfigFromOptimizationTaskInput,
    DraftHarnessConfigUpdateTaskInput,
    OptimizeSearchHarnessFromCaseTaskInput,
    VerifyDraftHarnessConfigTaskInput,
)
from app.services.agent_actions.search_harness import (
    _draft_harness_config_from_optimization_executor,
    _draft_harness_config_update_executor,
    _optimize_search_harness_from_case_executor,
    _verify_draft_harness_config_executor,
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
        "app.services.agent_actions.search_harness.create_agent_task_artifact",
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
        "app.services.agent_actions.search_harness.get_eval_failure_case",
        lambda session, requested_case_id: {"case_id": str(requested_case_id)},
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.run_search_harness_optimization_loop",
        lambda session, request: optimization,
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.create_agent_task_artifact",
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
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output={},
            task_type="optimize_search_harness_from_case",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.OptimizeSearchHarnessFromCaseTaskOutput.model_validate",
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
        "app.services.agent_actions.search_harness.get_search_harness",
        fake_get_search_harness,
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.create_agent_task_artifact",
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
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output={},
            task_type="optimize_search_harness_from_case",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.OptimizeSearchHarnessFromCaseTaskOutput.model_validate",
        lambda output: source_output,
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.get_search_harness",
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
        "app.services.agent_actions.search_harness.verify_draft_harness_config_task",
        lambda session, verification_task, payload: {
            "draft": {"draft_harness_name": "wide_v2_review"},
            "evaluation": {"candidate_harness_name": "wide_v2_review"},
            "verification": {"outcome": "passed"},
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.create_agent_task_artifact",
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
