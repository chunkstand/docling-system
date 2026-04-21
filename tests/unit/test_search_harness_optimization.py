from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.schemas.search import (
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSourceResponse,
    SearchHarnessOptimizationRequest,
)
from app.services.search_harness_optimization import run_search_harness_optimization_loop


def _base_harness(keyword_multiplier: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        retrieval_profile=SimpleNamespace(keyword_candidate_multiplier=keyword_multiplier),
        reranker_config=SimpleNamespace(),
    )


def _evaluation_for_multiplier(multiplier: int) -> SearchHarnessEvaluationResponse:
    if multiplier == 6:
        return SearchHarnessEvaluationResponse(
            baseline_harness_name="default_v1",
            candidate_harness_name="wide_v2_loop",
            limit=5,
            total_shared_query_count=4,
            total_improved_count=3,
            total_regressed_count=0,
            total_unchanged_count=1,
            sources=[
                SearchHarnessEvaluationSourceResponse(
                    source_type="evaluation_queries",
                    baseline_replay_run_id="00000000-0000-0000-0000-000000000001",
                    candidate_replay_run_id="00000000-0000-0000-0000-000000000002",
                    baseline_query_count=4,
                    candidate_query_count=4,
                    baseline_passed_count=2,
                    candidate_passed_count=4,
                    baseline_mrr=0.4,
                    candidate_mrr=0.8,
                    shared_query_count=4,
                    improved_count=3,
                    regressed_count=0,
                    unchanged_count=1,
                )
            ],
        )
    if multiplier == 7:
        return SearchHarnessEvaluationResponse(
            baseline_harness_name="default_v1",
            candidate_harness_name="wide_v2_loop",
            limit=5,
            total_shared_query_count=4,
            total_improved_count=3,
            total_regressed_count=0,
            total_unchanged_count=1,
            sources=[
                SearchHarnessEvaluationSourceResponse(
                    source_type="evaluation_queries",
                    baseline_replay_run_id="00000000-0000-0000-0000-000000000001",
                    candidate_replay_run_id="00000000-0000-0000-0000-000000000003",
                    baseline_query_count=4,
                    candidate_query_count=4,
                    baseline_passed_count=2,
                    candidate_passed_count=4,
                    baseline_mrr=0.4,
                    candidate_mrr=0.7,
                    shared_query_count=4,
                    improved_count=3,
                    regressed_count=0,
                    unchanged_count=1,
                )
            ],
        )
    if multiplier == 4:
        return SearchHarnessEvaluationResponse(
            baseline_harness_name="default_v1",
            candidate_harness_name="wide_v2_loop",
            limit=5,
            total_shared_query_count=4,
            total_improved_count=0,
            total_regressed_count=1,
            total_unchanged_count=3,
            sources=[
                SearchHarnessEvaluationSourceResponse(
                    source_type="evaluation_queries",
                    baseline_replay_run_id="00000000-0000-0000-0000-000000000001",
                    candidate_replay_run_id="00000000-0000-0000-0000-000000000004",
                    baseline_query_count=4,
                    candidate_query_count=4,
                    baseline_passed_count=2,
                    candidate_passed_count=1,
                    baseline_zero_result_count=0,
                    candidate_zero_result_count=1,
                    baseline_mrr=0.4,
                    candidate_mrr=0.2,
                    baseline_foreign_top_result_count=0,
                    candidate_foreign_top_result_count=1,
                    shared_query_count=4,
                    improved_count=0,
                    regressed_count=1,
                    unchanged_count=3,
                )
            ],
        )
    return SearchHarnessEvaluationResponse(
        baseline_harness_name="default_v1",
        candidate_harness_name="wide_v2_loop",
        limit=5,
        total_shared_query_count=4,
        total_improved_count=0,
        total_regressed_count=0,
        total_unchanged_count=4,
        sources=[
            SearchHarnessEvaluationSourceResponse(
                source_type="evaluation_queries",
                baseline_replay_run_id="00000000-0000-0000-0000-000000000001",
                candidate_replay_run_id="00000000-0000-0000-0000-000000000005",
                baseline_query_count=4,
                candidate_query_count=4,
                baseline_passed_count=2,
                candidate_passed_count=2,
                baseline_mrr=0.4,
                candidate_mrr=0.4,
                shared_query_count=4,
                improved_count=0,
                regressed_count=0,
                unchanged_count=4,
            )
        ],
    )


def test_run_search_harness_optimization_loop_accepts_better_candidate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.services.search_harness_optimization.get_settings",
        lambda: SimpleNamespace(storage_root=tmp_path),
    )
    monkeypatch.setattr(
        "app.services.search_harness_optimization.get_search_harness",
        lambda name: _base_harness(),
    )

    def fake_evaluate_search_harness(session, payload, *, harness_overrides=None):
        override_spec = (harness_overrides or {}).get(payload.candidate_harness_name) or {}
        multiplier = (override_spec.get("retrieval_profile_overrides") or {}).get(
            "keyword_candidate_multiplier"
        ) or 5
        return _evaluation_for_multiplier(multiplier)

    def fake_release_gate(session, evaluation, payload):
        failed = evaluation.total_regressed_count > 0
        return SimpleNamespace(
            outcome="failed" if failed else "passed",
            metrics={"total_shared_query_count": evaluation.total_shared_query_count},
            reasons=["regressed queries"] if failed else [],
            details={"thresholds": payload.model_dump(mode="json")},
        )

    monkeypatch.setattr(
        "app.services.search_harness_optimization.evaluate_search_harness",
        fake_evaluate_search_harness,
    )
    monkeypatch.setattr(
        "app.services.search_harness_optimization.evaluate_search_harness_release_gate",
        fake_release_gate,
    )

    response = run_search_harness_optimization_loop(
        session=None,
        request=SearchHarnessOptimizationRequest(
            base_harness_name="wide_v2",
            baseline_harness_name="default_v1",
            candidate_harness_name="wide_v2_loop",
            source_types=["evaluation_queries"],
            limit=5,
            iterations=3,
            tune_fields=["keyword_candidate_multiplier"],
        ),
    )

    assert response.best_override_spec["retrieval_profile_overrides"] == {
        "keyword_candidate_multiplier": 6
    }
    assert response.best_score["passed"] is True
    assert response.stopped_reason == "no_improving_candidates"
    accepted_attempts = [attempt for attempt in response.attempts if attempt.accepted]
    assert len(accepted_attempts) == 2
    assert accepted_attempts[1].field_name == "keyword_candidate_multiplier"
    assert accepted_attempts[1].proposed_value == 6
    assert response.artifact_path is not None
    artifact_payload = json.loads(Path(response.artifact_path).read_text())
    assert artifact_payload["best_override_spec"]["retrieval_profile_overrides"] == {
        "keyword_candidate_multiplier": 6
    }


def test_run_search_harness_optimization_loop_rejects_candidate_matching_baseline() -> None:
    with pytest.raises(ValueError, match="candidate_harness_name must differ"):
        run_search_harness_optimization_loop(
            session=None,
            request=SearchHarnessOptimizationRequest(
                base_harness_name="default_v1",
                baseline_harness_name="default_v1",
                candidate_harness_name="default_v1",
                source_types=["evaluation_queries"],
                limit=5,
                iterations=1,
                tune_fields=["keyword_candidate_multiplier"],
            ),
        )
