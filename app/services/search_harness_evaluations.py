from __future__ import annotations

from app.schemas.search import (
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSourceResponse,
    SearchHarnessResponse,
    SearchReplayRunRequest,
)
from app.services.search import DEFAULT_SEARCH_HARNESS_NAME, list_search_harnesses
from app.services.search_replays import (
    CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE,
    compare_search_replay_runs,
    run_search_replay_suite,
)

VALID_SOURCE_TYPES = {
    "evaluation_queries",
    "feedback",
    "live_search_gaps",
    CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE,
}


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
    *,
    harness_overrides: dict[str, dict] | None = None,
) -> SearchHarnessEvaluationResponse:
    def rank_metrics(detail) -> dict:
        return getattr(detail, "rank_metrics", None) or getattr(detail, "summary", {}).get(
            "rank_metrics",
            {},
        )

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
        baseline_request = SearchReplayRunRequest(
            source_type=source_type,
            limit=request.limit,
            harness_name=request.baseline_harness_name,
        )
        candidate_request = SearchReplayRunRequest(
            source_type=source_type,
            limit=request.limit,
            harness_name=request.candidate_harness_name,
        )
        if harness_overrides is None:
            baseline = run_search_replay_suite(session, baseline_request)
            candidate = run_search_replay_suite(session, candidate_request)
        else:
            baseline = run_search_replay_suite(
                session,
                baseline_request,
                harness_overrides=harness_overrides,
            )
            candidate = run_search_replay_suite(
                session,
                candidate_request,
                harness_overrides=harness_overrides,
            )
        comparison = compare_search_replay_runs(
            session,
            baseline.replay_run_id,
            candidate.replay_run_id,
        )
        baseline_rank_metrics = rank_metrics(baseline)
        candidate_rank_metrics = rank_metrics(candidate)
        acceptance_checks = {
            "no_regressions": comparison.regressed_count == 0,
            "mrr_not_lower": float(candidate_rank_metrics.get("mrr") or 0.0)
            >= float(baseline_rank_metrics.get("mrr") or 0.0),
            "foreign_top_result_count_not_higher": int(
                candidate_rank_metrics.get("foreign_top_result_count") or 0
            )
            <= int(baseline_rank_metrics.get("foreign_top_result_count") or 0),
            "zero_result_count_not_higher": candidate.zero_result_count
            <= baseline.zero_result_count,
        }
        source_summaries.append(
            SearchHarnessEvaluationSourceResponse(
                source_type=source_type,
                baseline_replay_run_id=baseline.replay_run_id,
                candidate_replay_run_id=candidate.replay_run_id,
                baseline_query_count=baseline.query_count,
                candidate_query_count=candidate.query_count,
                baseline_passed_count=baseline.passed_count,
                candidate_passed_count=candidate.passed_count,
                baseline_zero_result_count=baseline.zero_result_count,
                candidate_zero_result_count=candidate.zero_result_count,
                baseline_table_hit_count=baseline.table_hit_count,
                candidate_table_hit_count=candidate.table_hit_count,
                baseline_top_result_changes=baseline.top_result_changes,
                candidate_top_result_changes=candidate.top_result_changes,
                baseline_mrr=float(baseline_rank_metrics.get("mrr") or 0.0),
                candidate_mrr=float(candidate_rank_metrics.get("mrr") or 0.0),
                baseline_foreign_top_result_count=int(
                    baseline_rank_metrics.get("foreign_top_result_count") or 0
                ),
                candidate_foreign_top_result_count=int(
                    candidate_rank_metrics.get("foreign_top_result_count") or 0
                ),
                acceptance_checks=acceptance_checks,
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
