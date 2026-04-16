from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskVerification, SearchReplayRun
from app.schemas.agent_tasks import (
    VerifyDraftHarnessConfigTaskInput,
    VerifySearchHarnessEvaluationTaskInput,
)
from app.services.agent_task_verifications import (
    verify_draft_harness_config_task,
    verify_search_harness_evaluation_task,
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
    def __init__(self, *, tasks: dict, replay_runs: dict, artifacts: dict | None = None) -> None:
        self.tasks = tasks
        self.replay_runs = replay_runs
        self.artifacts = artifacts or {}
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
        raise AssertionError(f"Unexpected statement: {rendered}")


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
    session = FakeSession(
        tasks={
            target_task_id: target_task,
            verification_task_id: verification_task,
        },
        replay_runs={
            baseline_replay_run_id: baseline_replay_run,
            candidate_replay_run_id: candidate_replay_run,
        },
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
    session = FakeSession(
        tasks={
            target_task_id: target_task,
            verification_task_id: verification_task,
        },
        replay_runs={
            baseline_replay_run_id: baseline_replay_run,
            candidate_replay_run_id: candidate_replay_run,
        },
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
        assert "rerun after the context migration" in exc.detail
    else:
        raise AssertionError("Expected legacy draft task to be rejected")
