from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    SearchFeedback,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
)
from app.schemas.search import (
    SearchReplayComparisonResponse,
    SearchReplayComparisonRowResponse,
    SearchReplayQueryResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunRequest,
    SearchReplayRunSummaryResponse,
    SearchRequest,
)
from app.services.search import execute_search
from app.services.search_history import (
    build_search_replay_diff,
    get_search_request_detail,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class ReplayCase:
    query_text: str
    mode: str
    filters: dict
    limit: int
    expected_result_type: str | None = None
    expected_top_n: int | None = None
    source_search_request_id: UUID | None = None
    feedback_id: UUID | None = None
    evaluation_query_id: UUID | None = None
    feedback_type: str | None = None
    target_result_type: str | None = None
    target_result_id: UUID | None = None
    source_reason: str | None = None


def _replay_run_not_found(replay_run_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Search replay run not found: {replay_run_id}",
    )


def _filters_key(filters: dict) -> str:
    return json.dumps(filters or {}, sort_keys=True)


def _query_key(query_text: str, mode: str, filters: dict) -> tuple[str, str, str]:
    return query_text, mode, _filters_key(filters)


def _request_result_key(
    result_type: str | None,
    result_id: UUID | None,
) -> tuple[str | None, UUID | None]:
    return result_type, result_id


def _matching_rank(results, expected_result_type: str | None) -> int | None:
    if expected_result_type is None:
        return None
    for idx, result in enumerate(results, start=1):
        if result.result_type == expected_result_type:
            return idx
    return None


def _to_replay_run_summary(row: SearchReplayRun) -> SearchReplayRunSummaryResponse:
    return SearchReplayRunSummaryResponse(
        replay_run_id=row.id,
        source_type=row.source_type,
        status=row.status,
        query_count=row.query_count,
        passed_count=row.passed_count,
        failed_count=row.failed_count,
        zero_result_count=row.zero_result_count,
        table_hit_count=row.table_hit_count,
        top_result_changes=row.top_result_changes,
        max_rank_shift=row.max_rank_shift,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def _to_replay_query_response(row: SearchReplayQuery) -> SearchReplayQueryResponse:
    return SearchReplayQueryResponse(
        replay_query_id=row.id,
        source_search_request_id=row.source_search_request_id,
        replay_search_request_id=row.replay_search_request_id,
        feedback_id=row.feedback_id,
        evaluation_query_id=row.evaluation_query_id,
        query_text=row.query_text,
        mode=row.mode,
        filters=row.filters_json or {},
        expected_result_type=row.expected_result_type,
        expected_top_n=row.expected_top_n,
        passed=row.passed,
        result_count=row.result_count,
        table_hit_count=row.table_hit_count,
        overlap_count=row.overlap_count,
        added_count=row.added_count,
        removed_count=row.removed_count,
        top_result_changed=row.top_result_changed,
        max_rank_shift=row.max_rank_shift,
        details=row.details_json or {},
        created_at=row.created_at,
    )


def _load_replay_run(session: Session, replay_run_id: UUID) -> SearchReplayRun:
    replay_run = session.get(SearchReplayRun, replay_run_id)
    if replay_run is None:
        raise _replay_run_not_found(replay_run_id)
    return replay_run


def list_search_replay_runs(
    session: Session, *, limit: int = 10
) -> list[SearchReplayRunSummaryResponse]:
    rows = (
        session.execute(
            select(SearchReplayRun)
            .order_by(SearchReplayRun.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_to_replay_run_summary(row) for row in rows]


def get_search_replay_run_detail(
    session: Session, replay_run_id: UUID
) -> SearchReplayRunDetailResponse:
    replay_run = _load_replay_run(session, replay_run_id)
    query_rows = (
        session.execute(
            select(SearchReplayQuery)
            .where(SearchReplayQuery.replay_run_id == replay_run.id)
            .order_by(SearchReplayQuery.created_at.asc(), SearchReplayQuery.query_text.asc())
        )
        .scalars()
        .all()
    )
    summary = _to_replay_run_summary(replay_run)
    return SearchReplayRunDetailResponse(
        **summary.model_dump(),
        summary=replay_run.summary_json or {},
        query_results=[_to_replay_query_response(row) for row in query_rows],
    )


def _latest_evaluation_queries(session: Session, limit: int) -> list[ReplayCase]:
    documents = session.execute(select(Document)).scalars().all()
    cases: list[ReplayCase] = []

    for document in sorted(documents, key=lambda item: item.updated_at, reverse=True):
        if document.latest_run_id is None:
            continue
        evaluation = (
            session.execute(
                select(DocumentRunEvaluation)
                .where(DocumentRunEvaluation.run_id == document.latest_run_id)
                .order_by(DocumentRunEvaluation.created_at.desc())
            )
            .scalars()
            .first()
        )
        if evaluation is None:
            continue
        query_rows = (
            session.execute(
                select(DocumentRunEvaluationQuery)
                .where(DocumentRunEvaluationQuery.evaluation_id == evaluation.id)
                .order_by(DocumentRunEvaluationQuery.query_text.asc())
            )
            .scalars()
            .all()
        )
        for row in query_rows:
            cases.append(
                ReplayCase(
                    query_text=row.query_text,
                    mode=row.mode,
                    filters=row.filters_json or {},
                    limit=max(row.expected_top_n or 3, 10),
                    expected_result_type=row.expected_result_type,
                    expected_top_n=row.expected_top_n,
                    evaluation_query_id=row.id,
                    source_reason="evaluation_query",
                )
            )
            if len(cases) >= limit:
                return cases
    return cases


def _live_search_gap_cases(session: Session, limit: int) -> list[ReplayCase]:
    rows = (
        session.execute(
            select(SearchRequestRecord)
            .where(SearchRequestRecord.origin.in_(("api", "chat")))
            .order_by(SearchRequestRecord.created_at.desc())
        )
        .scalars()
        .all()
    )
    cases: list[ReplayCase] = []
    seen: set[tuple[str, str, str]] = set()

    for row in rows:
        filters = row.filters_json or {}
        request_key = _query_key(row.query_text, row.mode, filters)
        if request_key in seen:
            continue

        reason = None
        if row.result_count == 0:
            reason = "zero_result_gap"
        elif (
            row.tabular_query
            and filters.get("result_type") != "chunk"
            and row.table_hit_count == 0
        ):
            reason = "missing_table_gap"

        if reason is None:
            continue

        seen.add(request_key)
        cases.append(
            ReplayCase(
                query_text=row.query_text,
                mode=row.mode,
                filters=filters,
                limit=row.limit,
                source_search_request_id=row.id,
                source_reason=reason,
            )
        )
        if len(cases) >= limit:
            break
    return cases


def _feedback_cases(session: Session, limit: int) -> list[ReplayCase]:
    feedback_rows = (
        session.execute(select(SearchFeedback).order_by(SearchFeedback.created_at.desc()))
        .scalars()
        .all()
    )
    cases: list[ReplayCase] = []

    for feedback in feedback_rows[:limit]:
        request_row = session.get(SearchRequestRecord, feedback.search_request_id)
        if request_row is None:
            continue

        target_result_type = None
        target_result_id = None
        if feedback.search_request_result_id is not None:
            result_row = session.get(SearchRequestResult, feedback.search_request_result_id)
            if result_row is not None:
                target_result_type = result_row.result_type
                target_result_id = result_row.table_id or result_row.chunk_id

        cases.append(
            ReplayCase(
                query_text=request_row.query_text,
                mode=request_row.mode,
                filters=request_row.filters_json or {},
                limit=request_row.limit,
                source_search_request_id=request_row.id,
                feedback_id=feedback.id,
                feedback_type=feedback.feedback_type,
                target_result_type=target_result_type,
                target_result_id=target_result_id,
                source_reason="feedback_label",
            )
        )
    return cases


def _build_replay_cases(session: Session, request: SearchReplayRunRequest) -> list[ReplayCase]:
    if request.source_type == "evaluation_queries":
        return _latest_evaluation_queries(session, request.limit)
    if request.source_type == "live_search_gaps":
        return _live_search_gap_cases(session, request.limit)
    return _feedback_cases(session, request.limit)


def _evaluate_case_passed(case: ReplayCase, execution) -> tuple[bool, dict]:
    if case.evaluation_query_id is not None:
        matching_rank = _matching_rank(execution.results, case.expected_result_type)
        passed = matching_rank is not None and matching_rank <= (case.expected_top_n or 0)
        return passed, {"matching_rank": matching_rank}

    if case.feedback_type is not None:
        replay_keys = {
            _request_result_key(
                result.result_type,
                result.table_id if result.result_type == "table" else result.chunk_id,
            )
            for result in execution.results
        }
        target_key = _request_result_key(case.target_result_type, case.target_result_id)
        if case.feedback_type == "relevant":
            return target_key in replay_keys, {
                "target_key": [str(target_key[0]), str(target_key[1])]
            }
        if case.feedback_type == "irrelevant":
            return target_key not in replay_keys, {
                "target_key": [str(target_key[0]), str(target_key[1])]
            }
        if case.feedback_type == "missing_table":
            return execution.table_hit_count > 0, {"table_hit_count": execution.table_hit_count}
        if case.feedback_type == "missing_chunk":
            chunk_hit_count = sum(
                1 for result in execution.results if result.result_type == "chunk"
            )
            return any(result.result_type == "chunk" for result in execution.results), {
                "chunk_hit_count": chunk_hit_count
            }
        if case.feedback_type == "no_answer":
            return len(execution.results) == 0, {"result_count": len(execution.results)}

    if case.source_reason == "zero_result_gap":
        return len(execution.results) > 0, {"result_count": len(execution.results)}
    if case.source_reason == "missing_table_gap":
        return execution.table_hit_count > 0, {"table_hit_count": execution.table_hit_count}
    return False, {}


def run_search_replay_suite(
    session: Session,
    request: SearchReplayRunRequest,
) -> SearchReplayRunDetailResponse:
    replay_run = SearchReplayRun(
        id=uuid.uuid4(),
        source_type=request.source_type,
        status="failed",
        created_at=_utcnow(),
        summary_json={},
    )
    session.add(replay_run)
    session.flush()

    try:
        cases = _build_replay_cases(session, request)
        created_at = _utcnow()
        summary_counter: Counter[str] = Counter()

        for case in cases:
            filters = SearchRequest.model_validate(
                {
                    "query": case.query_text,
                    "mode": case.mode,
                    "filters": case.filters,
                    "limit": case.limit,
                }
            )
            execution = execute_search(
                session,
                filters,
                origin="replay_suite",
                parent_request_id=case.source_search_request_id,
            )
            replay_detail = (
                get_search_request_detail(session, execution.request_id)
                if execution.request_id is not None
                else None
            )
            diff = None
            if case.source_search_request_id is not None and replay_detail is not None:
                original_detail = get_search_request_detail(session, case.source_search_request_id)
                diff = build_search_replay_diff(original_detail, replay_detail)

            passed, pass_details = _evaluate_case_passed(case, execution)
            summary_counter["query_count"] += 1
            summary_counter["passed_count"] += int(passed)
            summary_counter["failed_count"] += int(not passed)
            summary_counter["zero_result_count"] += int(len(execution.results) == 0)
            summary_counter["table_hit_count"] += int(execution.table_hit_count > 0)
            summary_counter["top_result_changes"] += int(bool(diff and diff.top_result_changed))
            summary_counter["max_rank_shift"] = max(
                summary_counter["max_rank_shift"],
                diff.max_rank_shift if diff else 0,
            )

            session.add(
                SearchReplayQuery(
                    id=uuid.uuid4(),
                    replay_run_id=replay_run.id,
                    source_search_request_id=case.source_search_request_id,
                    replay_search_request_id=execution.request_id,
                    feedback_id=case.feedback_id,
                    evaluation_query_id=case.evaluation_query_id,
                    query_text=case.query_text,
                    mode=case.mode,
                    filters_json=case.filters,
                    expected_result_type=case.expected_result_type,
                    expected_top_n=case.expected_top_n,
                    passed=passed,
                    result_count=len(execution.results),
                    table_hit_count=execution.table_hit_count,
                    overlap_count=diff.overlap_count if diff else 0,
                    added_count=diff.added_count if diff else 0,
                    removed_count=diff.removed_count if diff else 0,
                    top_result_changed=diff.top_result_changed if diff else False,
                    max_rank_shift=diff.max_rank_shift if diff else 0,
                    details_json={
                        "source_reason": case.source_reason,
                        "feedback_type": case.feedback_type,
                        "embedding_status": execution.embedding_status,
                        "reranker_name": execution.reranker_name,
                        **pass_details,
                    },
                    created_at=created_at,
                )
            )

        replay_run.status = "completed"
        replay_run.query_count = summary_counter["query_count"]
        replay_run.passed_count = summary_counter["passed_count"]
        replay_run.failed_count = summary_counter["failed_count"]
        replay_run.zero_result_count = summary_counter["zero_result_count"]
        replay_run.table_hit_count = summary_counter["table_hit_count"]
        replay_run.top_result_changes = summary_counter["top_result_changes"]
        replay_run.max_rank_shift = summary_counter["max_rank_shift"]
        replay_run.summary_json = {
            "source_type": request.source_type,
            "source_limit": request.limit,
            "query_count": replay_run.query_count,
            "passed_count": replay_run.passed_count,
            "failed_count": replay_run.failed_count,
            "zero_result_count": replay_run.zero_result_count,
            "table_hit_count": replay_run.table_hit_count,
            "top_result_changes": replay_run.top_result_changes,
            "max_rank_shift": replay_run.max_rank_shift,
        }
        replay_run.completed_at = _utcnow()
        session.flush()
        return get_search_replay_run_detail(session, replay_run.id)
    except Exception as exc:
        replay_run.status = "failed"
        replay_run.error_message = str(exc)
        replay_run.summary_json = {
            "source_type": request.source_type,
            "source_limit": request.limit,
            "error": str(exc),
        }
        replay_run.completed_at = _utcnow()
        session.flush()
        return get_search_replay_run_detail(session, replay_run.id)


def compare_search_replay_runs(
    session: Session,
    baseline_replay_run_id: UUID,
    candidate_replay_run_id: UUID,
) -> SearchReplayComparisonResponse:
    baseline = get_search_replay_run_detail(session, baseline_replay_run_id)
    candidate = get_search_replay_run_detail(session, candidate_replay_run_id)

    baseline_rows = {
        _query_key(row.query_text, row.mode, row.filters): row for row in baseline.query_results
    }
    candidate_rows = {
        _query_key(row.query_text, row.mode, row.filters): row for row in candidate.query_results
    }
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


def export_ranking_dataset(session: Session, *, limit: int = 200) -> list[dict]:
    feedback_rows = (
        session.execute(select(SearchFeedback).order_by(SearchFeedback.created_at.desc()).limit(limit))
        .scalars()
        .all()
    )
    replay_rows = (
        session.execute(
            select(SearchReplayQuery)
            .order_by(SearchReplayQuery.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    dataset: list[dict] = []
    for feedback in feedback_rows:
        request_row = session.get(SearchRequestRecord, feedback.search_request_id)
        result_row = (
            session.get(SearchRequestResult, feedback.search_request_result_id)
            if feedback.search_request_result_id is not None
            else None
        )
        if request_row is None:
            continue
        dataset.append(
            {
                "dataset_type": "feedback",
                "feedback_id": str(feedback.id),
                "feedback_type": feedback.feedback_type,
                "search_request_id": str(request_row.id),
                "query_text": request_row.query_text,
                "mode": request_row.mode,
                "filters": request_row.filters_json or {},
                "note": feedback.note,
                "created_at": feedback.created_at.isoformat(),
                "result_rank": feedback.result_rank,
                "result_type": getattr(result_row, "result_type", None),
                "result_id": str(
                    getattr(result_row, "table_id", None)
                    or getattr(result_row, "chunk_id", None)
                )
                if result_row is not None
                else None,
                "rerank_features": (
                    getattr(result_row, "rerank_features_json", {}) if result_row else {}
                ),
            }
        )

    for row in replay_rows:
        dataset.append(
            {
                "dataset_type": "replay",
                "replay_query_id": str(row.id),
                "replay_run_id": str(row.replay_run_id),
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
