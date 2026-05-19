from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.models import AgentTaskArtifact, AgentTaskVerification


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
            params = getattr(statement.compile(), "params", {})
            task_id = next(
                (value for key, value in params.items() if "task_id" in key and value is not None),
                None,
            )
            artifacts = [
                artifact
                for artifact in self.artifacts.values()
                if task_id is None or artifact.task_id == task_id
            ]
            return FakeExecuteResult(artifacts)
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


def _build_triage_context_artifact(*, task_id) -> AgentTaskArtifact:
    now = datetime.now(UTC)
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()
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
            "task_type": "triage_replay_regression",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "triage_replay_regression_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Repair case ready"},
            "refs": [],
            "output": {
                "shadow_mode": True,
                "triage_kind": "replay_regression",
                "candidate_harness_name": "wide_v2",
                "baseline_harness_name": "default_v1",
                "quality_candidate_count": 0,
                "top_quality_candidates": [],
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
                            "acceptance_checks": {},
                            "shared_query_count": 4,
                            "improved_count": 1,
                            "regressed_count": 0,
                            "unchanged_count": 3,
                        }
                    ],
                },
                "verification": {
                    "verification_id": str(uuid4()),
                    "target_task_id": str(task_id),
                    "verification_task_id": str(task_id),
                    "verifier_type": "shadow_mode_triage_gate",
                    "outcome": "passed",
                    "metrics": {},
                    "reasons": [],
                    "details": {},
                    "created_at": now.isoformat(),
                    "completed_at": now.isoformat(),
                },
                "recommendation": {
                    "next_action": "candidate_ready_for_review",
                    "confidence": "medium",
                    "summary": "wide_v2 vs default_v1 across feedback.",
                },
                "repair_case": {
                    "schema_name": "search_harness_repair_case",
                    "schema_version": "1.0",
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "failure_classification": "candidate_improvement",
                    "problem_statement": "wide_v2 improves one replay query.",
                    "observed_metric_delta": {
                        "total_shared_query_count": 4,
                        "total_improved_count": 1,
                        "total_regressed_count": 0,
                    },
                    "affected_result_types": ["table"],
                    "likely_root_cause": "Candidate harness improves replay outcomes.",
                    "allowed_repair_surface": [
                        "retrieval_profile_overrides",
                        "reranker_overrides",
                    ],
                    "blocked_repair_surfaces": ["evaluation_corpus_weakening"],
                    "recommended_next_action": "candidate_ready_for_review",
                    "diagnostic_examples": [],
                    "evidence_refs": [{"ref_kind": "harness_evaluation"}],
                },
                "repair_case_artifact_id": str(uuid4()),
                "repair_case_artifact_kind": "repair_case",
                "repair_case_artifact_path": "/tmp/repair_case.json",
                "artifact_id": str(uuid4()),
                "artifact_kind": "triage_summary",
                "artifact_path": "/tmp/triage_summary.json",
            },
        },
        created_at=now,
    )
