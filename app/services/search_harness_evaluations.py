from __future__ import annotations

from app.schemas.search import (
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSourceResponse,
    SearchHarnessResponse,
    SearchReplayRunRequest,
)
from app.services.search import DEFAULT_SEARCH_HARNESS_NAME, list_search_harnesses
from app.services.search_replays import compare_search_replay_runs, run_search_replay_suite

VALID_SOURCE_TYPES = {"evaluation_queries", "feedback", "live_search_gaps"}


def list_search_harness_definitions() -> list[SearchHarnessResponse]:
    return [
        SearchHarnessResponse(
            harness_name=harness.name,
            reranker_name=harness.reranker_name,
            reranker_version=harness.reranker_version,
            retrieval_profile_name=harness.retrieval_profile_name,
            harness_config=harness.config_snapshot,
            is_default=harness.name == DEFAULT_SEARCH_HARNESS_NAME,
        )
        for harness in list_search_harnesses()
    ]


def evaluate_search_harness(
    session,
    request: SearchHarnessEvaluationRequest,
) -> SearchHarnessEvaluationResponse:
    source_types = []
    for source_type in request.source_types:
        if source_type not in VALID_SOURCE_TYPES:
            msg = f"Unsupported replay source type: {source_type}"
            raise ValueError(msg)
        if source_type not in source_types:
            source_types.append(source_type)

    source_summaries: list[SearchHarnessEvaluationSourceResponse] = []
    total_shared_query_count = 0
    total_improved_count = 0
    total_regressed_count = 0
    total_unchanged_count = 0

    for source_type in source_types:
        baseline = run_search_replay_suite(
            session,
            SearchReplayRunRequest(
                source_type=source_type,
                limit=request.limit,
                harness_name=request.baseline_harness_name,
            ),
        )
        candidate = run_search_replay_suite(
            session,
            SearchReplayRunRequest(
                source_type=source_type,
                limit=request.limit,
                harness_name=request.candidate_harness_name,
            ),
        )
        comparison = compare_search_replay_runs(
            session,
            baseline.replay_run_id,
            candidate.replay_run_id,
        )
        source_summaries.append(
            SearchHarnessEvaluationSourceResponse(
                source_type=source_type,
                baseline_replay_run_id=baseline.replay_run_id,
                candidate_replay_run_id=candidate.replay_run_id,
                baseline_query_count=baseline.query_count,
                candidate_query_count=candidate.query_count,
                baseline_passed_count=baseline.passed_count,
                candidate_passed_count=candidate.passed_count,
                shared_query_count=comparison.shared_query_count,
                improved_count=comparison.improved_count,
                regressed_count=comparison.regressed_count,
                unchanged_count=comparison.unchanged_count,
            )
        )
        total_shared_query_count += comparison.shared_query_count
        total_improved_count += comparison.improved_count
        total_regressed_count += comparison.regressed_count
        total_unchanged_count += comparison.unchanged_count

    return SearchHarnessEvaluationResponse(
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        limit=request.limit,
        total_shared_query_count=total_shared_query_count,
        total_improved_count=total_improved_count,
        total_regressed_count=total_regressed_count,
        total_unchanged_count=total_unchanged_count,
        sources=source_summaries,
    )
