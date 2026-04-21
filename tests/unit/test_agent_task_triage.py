from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskVerification
from app.schemas.agent_tasks import TriageReplayRegressionTaskInput
from app.schemas.search import (
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSourceResponse,
)
from app.services.agent_task_actions import (
    _triage_replay_regression_executor,
    validate_agent_task_output,
)
from app.services.agent_task_verifications import VerificationOutcome
from app.services.storage import StorageService


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False

    def add(self, row: object) -> None:
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True


def test_triage_replay_regression_executor_persists_artifact_and_recommendation(
    monkeypatch,
    tmp_path,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
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
    session = FakeSession()
    evaluation = SearchHarnessEvaluationResponse(
        baseline_harness_name="default_v1",
        candidate_harness_name="wide_v2",
        limit=12,
        total_shared_query_count=4,
        total_improved_count=2,
        total_regressed_count=0,
        total_unchanged_count=2,
        sources=[
            SearchHarnessEvaluationSourceResponse(
                source_type="feedback",
                baseline_replay_run_id=uuid4(),
                candidate_replay_run_id=uuid4(),
                baseline_query_count=4,
                candidate_query_count=4,
                baseline_passed_count=4,
                candidate_passed_count=4,
                baseline_zero_result_count=0,
                candidate_zero_result_count=0,
                baseline_table_hit_count=1,
                candidate_table_hit_count=1,
                baseline_top_result_changes=0,
                candidate_top_result_changes=0,
                baseline_mrr=0.8,
                candidate_mrr=0.9,
                baseline_foreign_top_result_count=0,
                candidate_foreign_top_result_count=0,
                acceptance_checks={"no_regressions": True},
                shared_query_count=4,
                improved_count=2,
                regressed_count=0,
                unchanged_count=2,
            )
        ],
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.list_quality_eval_candidates",
        lambda session, limit, include_resolved: [
            {
                "candidate_type": "evaluation_gap",
                "reason": "failed_query",
                "query_text": "vent stack",
                "mode": "keyword",
                "filters": {},
                "occurrence_count": 2,
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.evaluate_search_harness",
        lambda session, request: evaluation,
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.evaluate_search_harness_verification",
        lambda session, evaluation, payload: VerificationOutcome(
            outcome="passed",
            metrics={"total_regressed_count": 0},
            reasons=[],
            details={},
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.StorageService",
        lambda: StorageService(storage_root=tmp_path / "storage"),
    )

    result = _triage_replay_regression_executor(
        session,
        task,
        TriageReplayRegressionTaskInput(
            candidate_harness_name="wide_v2",
            baseline_harness_name="default_v1",
            source_types=["feedback"],
            replay_limit=12,
            quality_candidate_limit=5,
        ),
    )

    assert session.flushed is True
    assert result["shadow_mode"] is True
    assert result["recommendation"]["next_action"] == "candidate_ready_for_review"
    assert result["verification"]["outcome"] == "passed"
    assert result["repair_case"]["schema_name"] == "search_harness_repair_case"
    assert result["repair_case"]["recommended_next_action"] == "candidate_ready_for_review"
    assert result["repair_case_artifact_kind"] == "repair_case"
    assert result["artifact_path"] is not None
    artifact_path = result["artifact_path"]
    assert artifact_path.endswith("triage_summary.json")
    assert (tmp_path / "storage" / "agent_tasks" / str(task.id) / "triage_summary.json").exists()
    assert (tmp_path / "storage" / "agent_tasks" / str(task.id) / "repair_case.json").exists()
    validated = validate_agent_task_output("triage_replay_regression", result)
    assert validated["recommendation"]["next_action"] == "candidate_ready_for_review"
    assert any(isinstance(row, AgentTaskArtifact) for row in session.added)
    assert any(isinstance(row, AgentTaskVerification) for row in session.added)
