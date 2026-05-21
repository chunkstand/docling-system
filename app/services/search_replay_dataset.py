from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.public.retrieval import (
    SearchFeedback,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
)
from app.services import search_replay_common as replay_common
from app.services.session_utils import uses_in_memory_session

RANKING_DATASET_SCHEMA_VERSION = replay_common.RANKING_DATASET_SCHEMA_VERSION


def export_ranking_dataset(session: Session, *, limit: int = 200) -> list[dict]:
    feedback_rows = (
        session.execute(
            select(SearchFeedback).order_by(SearchFeedback.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    replay_rows = (
        session.execute(
            select(SearchReplayQuery).order_by(SearchReplayQuery.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )

    dataset: list[dict] = []

    def metadata_era(harness_config: dict | None) -> str:
        return "harness_v1" if harness_config else "legacy_pre_harness"

    if uses_in_memory_session(session):
        request_rows_by_id = {
            feedback.search_request_id: session.get(SearchRequestRecord, feedback.search_request_id)
            for feedback in feedback_rows
        }
        result_rows_by_id = {
            feedback.search_request_result_id: session.get(
                SearchRequestResult,
                feedback.search_request_result_id,
            )
            for feedback in feedback_rows
            if feedback.search_request_result_id is not None
        }
        replay_runs_by_id = {
            row.replay_run_id: session.get(SearchReplayRun, row.replay_run_id)
            for row in replay_rows
        }
    else:
        request_ids = {feedback.search_request_id for feedback in feedback_rows}
        result_ids = {
            feedback.search_request_result_id
            for feedback in feedback_rows
            if feedback.search_request_result_id is not None
        }
        replay_run_ids = {row.replay_run_id for row in replay_rows}
        request_rows_by_id = {
            row.id: row
            for row in session.execute(
                select(SearchRequestRecord).where(SearchRequestRecord.id.in_(request_ids))
            )
            .scalars()
            .all()
        }
        result_rows_by_id = {
            row.id: row
            for row in session.execute(
                select(SearchRequestResult).where(SearchRequestResult.id.in_(result_ids))
            )
            .scalars()
            .all()
        }
        replay_runs_by_id = {
            row.id: row
            for row in session.execute(
                select(SearchReplayRun).where(SearchReplayRun.id.in_(replay_run_ids))
            )
            .scalars()
            .all()
        }

    for feedback in feedback_rows:
        request_row = request_rows_by_id.get(feedback.search_request_id)
        result_row = result_rows_by_id.get(feedback.search_request_result_id)
        if request_row is None:
            continue
        harness_config = getattr(request_row, "harness_config_json", {}) or {}
        dataset.append(
            {
                "dataset_type": "feedback",
                "row_schema_version": RANKING_DATASET_SCHEMA_VERSION,
                "metadata_era": metadata_era(harness_config),
                "feedback_id": str(feedback.id),
                "feedback_type": feedback.feedback_type,
                "search_request_id": str(request_row.id),
                "harness_name": request_row.harness_name,
                "reranker_name": request_row.reranker_name,
                "reranker_version": request_row.reranker_version,
                "retrieval_profile_name": request_row.retrieval_profile_name,
                "harness_config": harness_config,
                "query_text": request_row.query_text,
                "mode": request_row.mode,
                "filters": request_row.filters_json or {},
                "note": feedback.note,
                "created_at": feedback.created_at.isoformat(),
                "result_rank": feedback.result_rank,
                "result_type": getattr(result_row, "result_type", None),
                "result_id": str(
                    getattr(result_row, "table_id", None) or getattr(result_row, "chunk_id", None)
                )
                if result_row is not None
                else None,
                "rerank_features": (
                    getattr(result_row, "rerank_features_json", {}) if result_row else {}
                ),
            }
        )

    for row in replay_rows:
        replay_run = replay_runs_by_id.get(row.replay_run_id)
        harness_config = getattr(replay_run, "harness_config_json", {}) or {}
        source_type = (
            replay_common._effective_replay_source_type(replay_run)
            if replay_run is not None
            else None
        )
        dataset.append(
            {
                "dataset_type": "replay",
                "row_schema_version": RANKING_DATASET_SCHEMA_VERSION,
                "metadata_era": metadata_era(harness_config),
                "replay_query_id": str(row.id),
                "replay_run_id": str(row.replay_run_id),
                "source_type": source_type,
                "harness_name": getattr(replay_run, "harness_name", None),
                "reranker_name": getattr(replay_run, "reranker_name", None),
                "reranker_version": getattr(replay_run, "reranker_version", None),
                "retrieval_profile_name": getattr(replay_run, "retrieval_profile_name", None),
                "harness_config": harness_config,
                "query_text": row.query_text,
                "mode": row.mode,
                "filters": row.filters_json or {},
                "expected_result_type": row.expected_result_type,
                "expected_top_n": row.expected_top_n,
                "passed": row.passed,
                "result_count": row.result_count,
                "table_hit_count": row.table_hit_count,
                "overlap_count": row.overlap_count,
                "added_count": row.added_count,
                "removed_count": row.removed_count,
                "top_result_changed": row.top_result_changed,
                "max_rank_shift": row.max_rank_shift,
                "details": row.details_json or {},
                "created_at": row.created_at.isoformat(),
            }
        )

    return dataset
