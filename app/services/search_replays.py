from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import (
    SearchReplayComparisonResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunRequest,
    SearchReplayRunSummaryResponse,
)
from app.services import search_replay_cases as _replay_cases
from app.services import search_replay_claim_feedback_cases as _claim_feedback_cases
from app.services import search_replay_common as _replay_common
from app.services import search_replay_comparisons as _replay_comparisons
from app.services import search_replay_dataset as _replay_dataset
from app.services import search_replay_rank_metrics as _replay_rank_metrics
from app.services import search_replay_runner as _replay_runner
from app.services.search import execute_search as execute_search
from app.services.search import get_search_harness as get_search_harness
from app.services.search_history import build_search_replay_diff as build_search_replay_diff
from app.services.search_history import get_search_request_detail as get_search_request_detail

RANKING_DATASET_SCHEMA_VERSION = _replay_common.RANKING_DATASET_SCHEMA_VERSION
CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE = (
    _replay_common.CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE
)
EVALUATION_QUERY_SOURCE_TYPE = _replay_common.EVALUATION_QUERY_SOURCE_TYPE
TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE = (
    _replay_common.TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE
)
REPLAY_CASE_PAGE_MIN_LIMIT = _replay_common.REPLAY_CASE_PAGE_MIN_LIMIT
ReplayCase = _replay_common.ReplayCase


_PRIVATE_TEST_EXPORTS = {
    "_cross_document_prose_replay_case": _replay_cases._cross_document_prose_replay_case,
    "_evaluate_case_passed": _replay_runner._evaluate_case_passed,
    "_feedback_cases": _replay_cases._feedback_cases,
    "_finalize_replay_rank_metrics": _replay_rank_metrics.finalize_replay_rank_metrics,
    "_latest_evaluation_queries": _replay_cases._latest_evaluation_queries,
    "_live_search_gap_cases": _replay_cases._live_search_gap_cases,
    "_technical_report_claim_feedback_cases": (
        _claim_feedback_cases.technical_report_claim_feedback_cases
    ),
    "_to_replay_run_summary": _replay_common._to_replay_run_summary,
}


def __getattr__(name: str):
    if name in _PRIVATE_TEST_EXPORTS:
        return _PRIVATE_TEST_EXPORTS[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def list_search_replay_runs(
    session: Session,
    *,
    limit: int = 10,
) -> list[SearchReplayRunSummaryResponse]:
    return _replay_common.list_search_replay_runs(session, limit=limit)


def get_search_replay_run_detail(
    session: Session,
    replay_run_id: UUID,
) -> SearchReplayRunDetailResponse:
    return _replay_common.get_search_replay_run_detail(session, replay_run_id)


def run_search_replay_suite(
    session: Session,
    request: SearchReplayRunRequest,
    *,
    harness_overrides: dict[str, dict] | None = None,
) -> SearchReplayRunDetailResponse:
    return _replay_runner.run_search_replay_suite(
        session,
        request,
        harness_overrides=harness_overrides,
    )


def compare_search_replay_runs(
    session: Session,
    baseline_replay_run_id: UUID,
    candidate_replay_run_id: UUID,
) -> SearchReplayComparisonResponse:
    return _replay_comparisons.compare_search_replay_runs(
        session,
        baseline_replay_run_id,
        candidate_replay_run_id,
    )


def export_ranking_dataset(session: Session, *, limit: int = 200) -> list[dict]:
    return _replay_dataset.export_ranking_dataset(session, limit=limit)
