from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SearchRequestRecord, SearchRequestResult
from app.schemas.search import (
    SearchFilters,
    SearchLoggedResultResponse,
    SearchReplayDiffResponse,
    SearchReplayResponse,
    SearchRequest,
    SearchRequestDetailResponse,
    SearchResult,
    SearchScores,
)
from app.services.search import execute_search


def _not_found(search_request_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Search request not found: {search_request_id}",
    )


def _search_result_key(
    result: SearchResult | SearchLoggedResultResponse,
) -> tuple[str, UUID | None]:
    if result.result_type == "table":
        return result.result_type, result.table_id
    return result.result_type, result.chunk_id


def _to_logged_result(row: SearchRequestResult) -> SearchLoggedResultResponse:
    return SearchLoggedResultResponse(
        rank=row.rank,
        base_rank=row.base_rank,
        rerank_features=row.rerank_features_json or {},
        result_type=row.result_type,
        document_id=row.document_id,
        run_id=row.run_id,
        score=row.score,
        chunk_id=row.chunk_id,
        chunk_text=row.preview_text if row.result_type == "chunk" else None,
        heading=row.label if row.result_type == "chunk" else None,
        table_id=row.table_id,
        table_title=row.label if row.result_type == "table" else None,
        table_heading=None,
        table_preview=row.preview_text if row.result_type == "table" else None,
        row_count=None,
        col_count=None,
        page_from=row.page_from,
        page_to=row.page_to,
        source_filename=row.source_filename,
        scores=SearchScores(
            keyword_score=row.keyword_score,
            semantic_score=row.semantic_score,
            hybrid_score=row.hybrid_score,
        ),
    )


def _load_request_row(session: Session, search_request_id: UUID) -> SearchRequestRecord:
    row = session.get(SearchRequestRecord, search_request_id)
    if row is None:
        raise _not_found(search_request_id)
    return row


def _build_request_detail(
    session: Session, request_row: SearchRequestRecord
) -> SearchRequestDetailResponse:
    result_rows = (
        session.execute(
            select(SearchRequestResult)
            .where(SearchRequestResult.search_request_id == request_row.id)
            .order_by(SearchRequestResult.rank.asc())
        )
        .scalars()
        .all()
    )
    return SearchRequestDetailResponse(
        search_request_id=request_row.id,
        parent_search_request_id=request_row.parent_request_id,
        evaluation_id=request_row.evaluation_id,
        run_id=request_row.run_id,
        origin=request_row.origin,
        query=request_row.query_text,
        mode=request_row.mode,
        filters=request_row.filters_json or {},
        details=request_row.details_json or {},
        limit=request_row.limit,
        tabular_query=request_row.tabular_query,
        reranker_name=request_row.reranker_name,
        embedding_status=request_row.embedding_status,
        embedding_error=request_row.embedding_error,
        candidate_count=request_row.candidate_count,
        result_count=request_row.result_count,
        table_hit_count=request_row.table_hit_count,
        duration_ms=request_row.duration_ms,
        created_at=request_row.created_at,
        results=[_to_logged_result(row) for row in result_rows],
    )


def get_search_request_detail(
    session: Session, search_request_id: UUID
) -> SearchRequestDetailResponse:
    request_row = _load_request_row(session, search_request_id)
    return _build_request_detail(session, request_row)


def replay_search_request(session: Session, search_request_id: UUID) -> SearchReplayResponse:
    request_row = _load_request_row(session, search_request_id)
    filters = (
        SearchFilters.model_validate(request_row.filters_json)
        if request_row.filters_json
        else None
    )
    execution = execute_search(
        session,
        SearchRequest(
            query=request_row.query_text,
            mode=request_row.mode,
            filters=filters,
            limit=request_row.limit,
        ),
        run_id=request_row.run_id,
        origin="replay",
        parent_request_id=request_row.id,
    )
    if execution.request_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Replay search request was not persisted.",
        )

    original = _build_request_detail(session, request_row)
    replay = get_search_request_detail(session, execution.request_id)

    original_ranks = {_search_result_key(result): result.rank for result in original.results}
    replay_ranks = {_search_result_key(result): result.rank for result in replay.results}
    overlap_keys = set(original_ranks) & set(replay_ranks)
    max_rank_shift = (
        max(abs(original_ranks[key] - replay_ranks[key]) for key in overlap_keys)
        if overlap_keys
        else 0
    )

    original_top = _search_result_key(original.results[0]) if original.results else None
    replay_top = _search_result_key(replay.results[0]) if replay.results else None

    return SearchReplayResponse(
        original_request=original,
        replay_request=replay,
        diff=SearchReplayDiffResponse(
            overlap_count=len(overlap_keys),
            added_count=len(set(replay_ranks) - set(original_ranks)),
            removed_count=len(set(original_ranks) - set(replay_ranks)),
            top_result_changed=original_top != replay_top,
            max_rank_shift=max_rank_shift,
        ),
    )
