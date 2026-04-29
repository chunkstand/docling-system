from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import SearchReplayComparisonResponse, SearchReplayComparisonRowResponse
from app.services import search_replay_common as replay_common
from app.services.search_replay_resolver import resolve_search_replays_service


def compare_search_replay_runs(
    session: Session,
    baseline_replay_run_id: UUID,
    candidate_replay_run_id: UUID,
) -> SearchReplayComparisonResponse:
    get_replay_run_detail = resolve_search_replays_service(
        "get_search_replay_run_detail",
        replay_common.get_search_replay_run_detail,
    )
    baseline = get_replay_run_detail(session, baseline_replay_run_id)
    candidate = get_replay_run_detail(session, candidate_replay_run_id)

    comparison_key = replay_common._replay_query_comparison_key
    baseline_rows = {comparison_key(row): row for row in baseline.query_results}
    candidate_rows = {comparison_key(row): row for row in candidate.query_results}
    shared_keys = baseline_rows.keys() & candidate_rows.keys()

    improved_count = 0
    regressed_count = 0
    unchanged_count = 0
    changed_queries: list[SearchReplayComparisonRowResponse] = []

    for key in sorted(shared_keys):
        baseline_row = baseline_rows[key]
        candidate_row = candidate_rows[key]
        if not baseline_row.passed and candidate_row.passed:
            improved_count += 1
        elif baseline_row.passed and not candidate_row.passed:
            regressed_count += 1
        else:
            unchanged_count += 1

        if (
            baseline_row.passed != candidate_row.passed
            or baseline_row.result_count != candidate_row.result_count
            or baseline_row.top_result_changed != candidate_row.top_result_changed
        ):
            changed_queries.append(
                SearchReplayComparisonRowResponse(
                    query_text=baseline_row.query_text,
                    mode=baseline_row.mode,
                    filters=baseline_row.filters,
                    baseline_passed=baseline_row.passed,
                    candidate_passed=candidate_row.passed,
                    baseline_result_count=baseline_row.result_count,
                    candidate_result_count=candidate_row.result_count,
                    baseline_top_result_changed=baseline_row.top_result_changed,
                    candidate_top_result_changed=candidate_row.top_result_changed,
                )
            )

    return SearchReplayComparisonResponse(
        baseline_replay_run_id=baseline_replay_run_id,
        candidate_replay_run_id=candidate_replay_run_id,
        shared_query_count=len(shared_keys),
        improved_count=improved_count,
        regressed_count=regressed_count,
        unchanged_count=unchanged_count,
        baseline_zero_result_count=baseline.zero_result_count,
        candidate_zero_result_count=candidate.zero_result_count,
        changed_queries=changed_queries[:20],
    )
