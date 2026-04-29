from __future__ import annotations

from uuid import UUID

from app.core.files import source_filename_matches
from app.services.search_replay_common import (
    TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
    ReplayCase,
)


def execution_result_source_id(result) -> UUID | str | None:
    if getattr(result, "result_type", None) == "table":
        return getattr(result, "table_id", None)
    if getattr(result, "result_type", None) == "chunk":
        return getattr(result, "chunk_id", None)
    return getattr(result, "table_id", None) or getattr(result, "chunk_id", None)


def string_result_key(
    result_type: str | None,
    result_id: UUID | str | None,
) -> tuple[str | None, str | None]:
    return result_type, str(result_id) if result_id is not None else None


def target_rank(
    results,
    result_type: str | None,
    result_id: UUID | str | None,
) -> int | None:
    if result_type is None or result_id is None:
        return None
    target_key = string_result_key(result_type, result_id)
    for rank, result in enumerate(results, start=1):
        replay_key = string_result_key(
            getattr(result, "result_type", None),
            execution_result_source_id(result),
        )
        if replay_key == target_key:
            return rank
    return None


def matching_rank(
    results,
    expected_result_type: str | None,
    *,
    expected_source_filename: str | None = None,
) -> int | None:
    if expected_result_type is None:
        return None
    for idx, result in enumerate(results, start=1):
        if result.result_type == expected_result_type and source_filename_matches(
            result.source_filename,
            expected_source_filename,
        ):
            return idx
    return None


def top_n_source_hit_count(
    results,
    expected_source_filename: str | None,
    top_n: int | None,
) -> int | None:
    if expected_source_filename is None or top_n is None:
        return None
    return sum(
        1
        for result in results[:top_n]
        if source_filename_matches(result.source_filename, expected_source_filename)
    )


def foreign_results_before_first_expected_hit(
    results,
    expected_result_type: str | None,
    *,
    expected_source_filename: str | None = None,
) -> int | None:
    rank = matching_rank(
        results,
        expected_result_type,
        expected_source_filename=expected_source_filename,
    )
    if rank is None or expected_source_filename is None:
        return None
    return sum(
        1
        for result in results[: rank - 1]
        if not source_filename_matches(result.source_filename, expected_source_filename)
    )


def empty_replay_rank_metrics() -> dict:
    return {
        "query_count": 0,
        "mrr": 0.0,
        "foreign_top_result_count": 0,
        "source_constrained_query_count": 0,
    }


def finalize_replay_rank_metrics(metrics: dict) -> dict:
    query_count = int(metrics.get("query_count") or 0)
    reciprocal_rank_sum = float(metrics.pop("reciprocal_rank_sum", 0.0) or 0.0)
    metrics["mrr"] = reciprocal_rank_sum / query_count if query_count else 0.0
    return metrics


def is_rank_metric_case(case: ReplayCase) -> bool:
    if case.evaluation_query_id is not None:
        return True
    return (
        case.source_reason == TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE
        and (case.source_metadata or {}).get("learning_label") == "positive"
    )
