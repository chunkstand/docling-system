from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskVerification,
    SearchReplayRun,
)
from app.schemas.agent_tasks import (
    VerifyDraftHarnessConfigTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifySearchHarnessEvaluationTaskInput,
    VerifySemanticGroundedDocumentTaskInput,
)
from app.services.agent_task_verifications import (
    verify_draft_harness_config_task,
    verify_draft_semantic_registry_update_task,
    verify_search_harness_evaluation_task,
    verify_semantic_grounded_document_task,
)


def _build_harness_evaluation_result(
    *,
    baseline_replay_run_id,
    candidate_replay_run_id,
    regressed_count: int,
    total_shared_query_count: int = 4,
) -> dict:
    return {
        "task_type": "evaluate_search_harness",
        "definition_kind": "action",
        "side_effect_level": "read_only",
        "requires_approval": False,
        "payload": {
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "evaluation": {
                "baseline_harness_name": "default_v1",
                "candidate_harness_name": "wide_v2",
                "limit": 12,
                "total_shared_query_count": total_shared_query_count,
                "total_improved_count": 1,
                "total_regressed_count": regressed_count,
                "total_unchanged_count": 0,
                "sources": [
                    {
                        "source_type": "feedback",
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
                        "acceptance_checks": {
                            "no_regressions": regressed_count == 0,
                            "mrr_not_lower": True,
                            "foreign_top_result_count_not_higher": True,
                            "zero_result_count_not_higher": True,
                        },
                        "shared_query_count": total_shared_query_count,
                        "improved_count": 1,
                        "regressed_count": regressed_count,
                        "unchanged_count": 0,
                    }
                ],
            },
        },
    }


class FakeExecuteResult:
    def __init__(self, rows) -> None:
        self.rows = list(rows)

    def scalars(self):
        class FakeScalarResult:
            def __init__(self, rows) -> None:
                self.rows = list(rows)

            def first(self):
                return self.rows[0] if self.rows else None

        return FakeScalarResult(self.rows)


class FakeSession:
    def __init__(
        self,
        *,
        tasks: dict,
        replay_runs: dict,
        artifacts: dict | None = None,
        dependencies: dict | None = None,
    ) -> None:
        self.tasks = tasks
        self.replay_runs = replay_runs
        self.artifacts = artifacts or {}
        self.dependencies = dependencies or {}
        self.added: list[object] = []
        self.flushed = False

    def get(self, model, key):
        if model.__name__ == "AgentTask":
            return self.tasks.get(key)
        if model.__name__ == "AgentTaskArtifact":
            return self.artifacts.get(key)
        if model.__name__ == "SearchReplayRun":
            return self.replay_runs.get(key)
        return None

    def add(self, row: object) -> None:
        if isinstance(row, AgentTaskVerification) and row.id is None:
            row.id = uuid4()
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True

    def execute(self, statement):
        rendered = str(statement)
        if "agent_task_artifacts" in rendered:
            return FakeExecuteResult(self.artifacts.values())
        if "agent_task_dependencies" in rendered:
            return FakeExecuteResult(self.dependencies.values())
        raise AssertionError(f"Unexpected statement: {rendered}")


def _build_evaluation_context_artifact(
    *,
    task_id,
    baseline_replay_run_id,
    candidate_replay_run_id,
    regressed_count: int,
    total_shared_query_count: int = 4,
) -> AgentTaskArtifact:
    now = datetime.now(UTC)
    return AgentTaskArtifact(
        id=uuid4(),
        task_id=task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(task_id),
            "task_type": "evaluate_search_harness",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "evaluate_search_harness_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Evaluation ready"},
            "refs": [],
            "output": {
                "candidate_harness_name": "wide_v2",
                "baseline_harness_name": "default_v1",
                "evaluation": {
                    "baseline_harness_name": "default_v1",
                    "candidate_harness_name": "wide_v2",
                    "limit": 12,
                    "total_shared_query_count": total_shared_query_count,
                    "total_improved_count": 1,
                    "total_regressed_count": regressed_count,
                    "total_unchanged_count": 0,
                    "sources": [
                        {
                            "source_type": "feedback",
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
                            "acceptance_checks": {
                                "no_regressions": regressed_count == 0,
                                "mrr_not_lower": True,
                                "foreign_top_result_count_not_higher": True,
                                "zero_result_count_not_higher": True,
                            },
                            "shared_query_count": total_shared_query_count,
                            "improved_count": 1,
                            "regressed_count": regressed_count,
                            "unchanged_count": 0,
                        }
                    ],
                },
            },
        },
        created_at=now,
    )


def test_verify_search_harness_evaluation_task_records_passed_verification() -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="evaluate_search_harness",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json=_build_harness_evaluation_result(
            baseline_replay_run_id=baseline_replay_run_id,
            candidate_replay_run_id=candidate_replay_run_id,
            regressed_count=0,
        ),
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_search_harness_evaluation",
        status="processing",
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
    baseline_replay_run = SearchReplayRun(
        id=baseline_replay_run_id,
        source_type="feedback",
        status="completed",
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config_json={},
        query_count=4,
        passed_count=4,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        created_at=now,
        completed_at=now,
    )
    candidate_replay_run = SearchReplayRun(
        id=candidate_replay_run_id,
        source_type="feedback",
        status="completed",
        harness_name="wide_v2",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="wide_v2",
        harness_config_json={},
        query_count=4,
        passed_count=4,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        created_at=now,
        completed_at=now,
    )
    context_artifact = _build_evaluation_context_artifact(
        task_id=target_task_id,
        baseline_replay_run_id=baseline_replay_run_id,
        candidate_replay_run_id=candidate_replay_run_id,
        regressed_count=0,
    )
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=target_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    session = FakeSession(
        tasks={
            target_task_id: target_task,
            verification_task_id: verification_task,
        },
        replay_runs={
            baseline_replay_run_id: baseline_replay_run,
            candidate_replay_run_id: candidate_replay_run,
        },
        artifacts={context_artifact.id: context_artifact},
        dependencies={(verification_task_id, target_task_id): dependency},
    )

    result = verify_search_harness_evaluation_task(
        session,
        verification_task,
        VerifySearchHarnessEvaluationTaskInput(target_task_id=target_task_id),
    )

    assert session.flushed is True
    assert len(session.added) == 1
    row = session.added[0]
    assert isinstance(row, AgentTaskVerification)
    assert row.outcome == "passed"
    assert row.verifier_type == "search_harness_evaluation_gate"
    assert result["verification"]["outcome"] == "passed"
    assert result["verification"]["target_task_id"] == str(target_task_id)
    assert result["evaluation"]["candidate_harness_name"] == "wide_v2"


def test_verify_search_harness_evaluation_task_records_failed_verification() -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="evaluate_search_harness",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json=_build_harness_evaluation_result(
            baseline_replay_run_id=baseline_replay_run_id,
            candidate_replay_run_id=candidate_replay_run_id,
            regressed_count=2,
        ),
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_search_harness_evaluation",
        status="processing",
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
    baseline_replay_run = SearchReplayRun(
        id=baseline_replay_run_id,
        source_type="feedback",
        status="completed",
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config_json={},
        query_count=4,
        passed_count=4,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 0.8, "foreign_top_result_count": 0}},
        created_at=now,
        completed_at=now,
    )
    candidate_replay_run = SearchReplayRun(
        id=candidate_replay_run_id,
        source_type="feedback",
        status="completed",
        harness_name="wide_v2",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="wide_v2",
        harness_config_json={},
        query_count=4,
        passed_count=2,
        failed_count=2,
        zero_result_count=1,
        table_hit_count=1,
        top_result_changes=1,
        max_rank_shift=2,
        summary_json={"rank_metrics": {"mrr": 0.4, "foreign_top_result_count": 2}},
        created_at=now,
        completed_at=now,
    )
    context_artifact = _build_evaluation_context_artifact(
        task_id=target_task_id,
        baseline_replay_run_id=baseline_replay_run_id,
        candidate_replay_run_id=candidate_replay_run_id,
        regressed_count=2,
    )
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=target_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    session = FakeSession(
        tasks={
            target_task_id: target_task,
            verification_task_id: verification_task,
        },
        replay_runs={
            baseline_replay_run_id: baseline_replay_run,
            candidate_replay_run_id: candidate_replay_run,
        },
        artifacts={context_artifact.id: context_artifact},
        dependencies={(verification_task_id, target_task_id): dependency},
    )

    result = verify_search_harness_evaluation_task(
        session,
        verification_task,
        VerifySearchHarnessEvaluationTaskInput(
            target_task_id=target_task_id,
            max_total_regressed_count=0,
            max_mrr_drop=0.0,
            max_zero_result_count_increase=0,
            max_foreign_top_result_count_increase=0,
        ),
    )

    assert result["verification"]["outcome"] == "failed"
    assert result["verification"]["reasons"]
    assert "regressed_count" in result["verification"]["reasons"][0]


def test_verify_search_harness_evaluation_task_rejects_pre_context_evaluations() -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="evaluate_search_harness",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json=_build_harness_evaluation_result(
            baseline_replay_run_id=uuid4(),
            candidate_replay_run_id=uuid4(),
            regressed_count=0,
        ),
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_search_harness_evaluation",
        status="processing",
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
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=target_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    session = FakeSession(
        tasks={target_task_id: target_task, verification_task_id: verification_task},
        replay_runs={},
        dependencies={(verification_task_id, target_task_id): dependency},
    )

    try:
        verify_search_harness_evaluation_task(
            session,
            verification_task,
            VerifySearchHarnessEvaluationTaskInput(target_task_id=target_task_id),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "must be rerun after the context migration" in exc.detail["message"]
    else:
        raise AssertionError("Expected pre-context evaluation task to be rejected")


def test_verify_draft_harness_config_task_uses_migrated_context_output(monkeypatch) -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="draft_harness_config_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_draft_harness_config",
        status="processing",
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
    artifact = AgentTaskArtifact(
        id=uuid4(),
        task_id=target_task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(target_task_id),
            "task_type": "draft_harness_config_update",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "draft_harness_config_update_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Draft ready"},
            "refs": [],
            "output": {
                "draft": {
                    "draft_harness_name": "wide_v2_review",
                    "base_harness_name": "wide_v2",
                    "source_task_id": None,
                    "source_task_type": None,
                    "rationale": "publish review harness",
                    "override_spec": {
                        "base_harness_name": "wide_v2",
                        "retrieval_profile_overrides": {},
                        "reranker_overrides": {"result_type_priority_bonus": 0.009},
                        "override_type": "draft_harness_config_update",
                        "override_source": "task_draft",
                        "draft_task_id": str(target_task_id),
                        "source_task_id": None,
                        "rationale": "publish review harness",
                    },
                    "effective_harness_config": {"base_harness_name": "wide_v2"},
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "harness_config_draft",
                "artifact_path": "/tmp/harness_config_draft.json",
            },
        },
        created_at=now,
    )
    session = FakeSession(
        tasks={target_task_id: target_task, verification_task_id: verification_task},
        replay_runs={},
        artifacts={artifact.id: artifact},
    )

    monkeypatch.setattr(
        "app.services.agent_task_verifications.evaluate_search_harness",
        lambda session, request, harness_overrides=None: {
            "candidate_harness_name": request.candidate_harness_name,
            "baseline_harness_name": request.baseline_harness_name,
            "total_shared_query_count": 4,
            "total_improved_count": 1,
            "total_regressed_count": 0,
            "sources": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_verifications.evaluate_search_harness_verification",
        lambda session, evaluation, payload: type(
            "Outcome",
            (),
            {
                "outcome": "passed",
                "metrics": {"total_shared_query_count": 4},
                "reasons": [],
                "details": {"thresholds": payload.model_dump(mode="json")},
            },
        )(),
    )

    result = verify_draft_harness_config_task(
        session,
        verification_task,
        VerifyDraftHarnessConfigTaskInput(target_task_id=target_task_id),
    )

    assert result["draft"]["draft_harness_name"] == "wide_v2_review"
    assert result["verification"]["outcome"] == "passed"


def test_verify_draft_harness_config_task_rejects_pre_context_drafts() -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="draft_harness_config_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={"payload": {"draft": {"draft_harness_name": "legacy"}}},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_draft_harness_config",
        status="processing",
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
    session = FakeSession(
        tasks={target_task_id: target_task, verification_task_id: verification_task},
        replay_runs={},
    )

    try:
        verify_draft_harness_config_task(
            session,
            verification_task,
            VerifyDraftHarnessConfigTaskInput(target_task_id=target_task_id),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "rerun after the context migration" in exc.detail["message"]
    else:
        raise AssertionError("Expected legacy draft task to be rejected")


def test_verify_draft_semantic_registry_update_task_uses_migrated_context_output(
    monkeypatch,
) -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    document_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="draft_semantic_registry_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_draft_semantic_registry_update",
        status="processing",
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
    artifact = AgentTaskArtifact(
        id=uuid4(),
        task_id=target_task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(target_task_id),
            "task_type": "draft_semantic_registry_update",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "draft_semantic_registry_update_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Semantic draft ready"},
            "refs": [],
            "output": {
                "draft": {
                    "base_registry_version": "semantics-layer-foundation-alpha.2",
                    "proposed_registry_version": "semantics-layer-foundation-alpha.3",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "triage_semantic_pass",
                    "rationale": "add the missing alias",
                    "document_ids": [str(document_id)],
                    "operations": [
                        {
                            "operation_id": "add_alias:integration_threshold:integration_guardrail",
                            "operation_type": "add_alias",
                            "concept_key": "integration_threshold",
                            "alias_text": "integration guardrail",
                            "category_key": None,
                            "source_issue_ids": ["missing_expected_concept:integration_threshold"],
                            "rationale": "missing alias",
                        }
                    ],
                    "effective_registry": {
                        "registry_version": "semantics-layer-foundation-alpha.3"
                    },
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_registry_draft",
                "artifact_path": "/tmp/semantic_registry_draft.json",
            },
        },
        created_at=now,
    )
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=target_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    session = FakeSession(
        tasks={target_task_id: target_task, verification_task_id: verification_task},
        replay_runs={},
        artifacts={artifact.id: artifact},
        dependencies={(verification_task_id, target_task_id): dependency},
    )

    monkeypatch.setattr(
        "app.services.agent_task_verifications.preview_semantic_registry_update_for_document",
        lambda session, requested_document_id, registry_payload: {
            "document_id": requested_document_id,
            "run_id": uuid4(),
            "evaluation_fixture_name": "semantic_fixture",
            "before_all_expectations_passed": False,
            "after_all_expectations_passed": True,
            "before_failed_expectations": 1,
            "after_failed_expectations": 0,
            "before_assertion_count": 0,
            "after_assertion_count": 1,
            "added_concept_keys": ["integration_threshold"],
            "removed_concept_keys": [],
            "introduced_expected_concepts": ["integration_threshold"],
            "regressed_expected_concepts": [],
        },
    )

    result = verify_draft_semantic_registry_update_task(
        session,
        verification_task,
        VerifyDraftSemanticRegistryUpdateTaskInput(target_task_id=target_task_id),
    )

    assert result["draft"]["proposed_registry_version"] == "semantics-layer-foundation-alpha.3"
    assert result["summary"]["improved_document_count"] == 1
    assert result["verification"]["outcome"] == "passed"


def test_verify_draft_semantic_registry_update_task_rejects_pre_context_drafts() -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="draft_semantic_registry_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={"payload": {"draft": {"proposed_registry_version": "legacy"}}},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_draft_semantic_registry_update",
        status="processing",
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
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=target_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    session = FakeSession(
        tasks={target_task_id: target_task, verification_task_id: verification_task},
        replay_runs={},
        dependencies={(verification_task_id, target_task_id): dependency},
    )

    try:
        verify_draft_semantic_registry_update_task(
            session,
            verification_task,
            VerifyDraftSemanticRegistryUpdateTaskInput(target_task_id=target_task_id),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "rerun after the context migration" in exc.detail["message"]
    else:
        raise AssertionError("Expected legacy semantic draft task to be rejected")


def test_verify_semantic_grounded_document_task_uses_migrated_context_output() -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    now = datetime.now(UTC)
    draft_task = AgentTask(
        id=draft_task_id,
        task_type="draft_semantic_grounded_document",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_semantic_grounded_document",
        status="processing",
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
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=draft_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    assertion_id = uuid4()
    draft_context_artifact = AgentTaskArtifact(
        id=uuid4(),
        task_id=draft_task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(draft_task_id),
            "task_type": "draft_semantic_grounded_document",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "draft_semantic_grounded_document_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Draft ready"},
            "refs": [],
            "output": {
                "draft": {
                    "document_kind": "knowledge_brief",
                    "title": "Integration Governance Brief",
                    "goal": "Summarize the knowledge base guidance on integration governance.",
                    "audience": "Operators",
                    "review_policy": "allow_candidate_with_disclosure",
                    "target_length": "medium",
                    "brief_task_id": str(uuid4()),
                    "generator_name": "structured_fallback",
                    "generator_model": None,
                    "used_fallback": True,
                    "required_concept_keys": ["integration_threshold"],
                    "document_refs": [],
                    "assertion_index": [
                        {
                            "document_id": str(uuid4()),
                            "run_id": str(uuid4()),
                            "semantic_pass_id": str(uuid4()),
                            "assertion_id": str(assertion_id),
                            "concept_key": "integration_threshold",
                            "preferred_label": "Integration Threshold",
                            "review_status": "candidate",
                            "support_level": "supported",
                            "source_types": ["chunk", "table"],
                            "evidence_count": 2,
                            "category_keys": ["integration_governance"],
                            "category_labels": ["Integration Governance"],
                        }
                    ],
                    "sections": [
                        {
                            "section_id": "section:integration_governance",
                            "title": "Integration Governance",
                            "body_markdown": "- Integration Threshold appears in Integration One.",
                            "claim_ids": ["claim:integration_threshold"],
                        }
                    ],
                    "claims": [
                        {
                            "claim_id": "claim:integration_threshold",
                            "section_id": "section:integration_governance",
                            "rendered_text": "Integration Threshold appears in Integration One.",
                            "concept_keys": ["integration_threshold"],
                            "assertion_ids": [str(assertion_id)],
                            "evidence_labels": ["E1"],
                            "source_document_ids": [str(uuid4())],
                            "support_level": "supported",
                            "review_policy_status": "candidate_disclosed",
                            "disclosure_note": "Candidate-backed support requires review.",
                        }
                    ],
                    "evidence_pack": [
                        {
                            "citation_label": "E1",
                            "document_id": str(uuid4()),
                            "run_id": str(uuid4()),
                            "semantic_pass_id": str(uuid4()),
                            "assertion_id": str(assertion_id),
                            "evidence_id": str(uuid4()),
                            "concept_key": "integration_threshold",
                            "preferred_label": "Integration Threshold",
                            "review_status": "candidate",
                            "source_filename": "integration-one.pdf",
                            "source_type": "chunk",
                            "page_from": 1,
                            "page_to": 1,
                            "excerpt": "Integration threshold guidance remains in force.",
                            "source_artifact_api_path": "/documents/example/chunks/1",
                            "matched_terms": ["integration threshold"],
                        }
                    ],
                    "markdown": "# Integration Governance Brief\n",
                    "markdown_path": "/tmp/semantic_grounded_document.md",
                    "warnings": [],
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_grounded_document_draft",
                "artifact_path": "/tmp/semantic_grounded_document_draft.json",
            },
        },
        created_at=now,
    )
    session = FakeSession(
        tasks={draft_task_id: draft_task, verification_task_id: verification_task},
        replay_runs={},
        artifacts={draft_context_artifact.id: draft_context_artifact},
        dependencies={(verification_task_id, draft_task_id): dependency},
    )

    result = verify_semantic_grounded_document_task(
        session,
        verification_task,
        VerifySemanticGroundedDocumentTaskInput(target_task_id=draft_task_id),
    )

    assert result["summary"]["claim_count"] == 1
    assert result["verification"]["outcome"] == "passed"
