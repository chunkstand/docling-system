from __future__ import annotations

from uuid import UUID

from sqlalchemy import Float, Select, and_, cast, false, func, select
from sqlalchemy.orm import Session

import app.services.search_hydration as _search_hydration
import app.services.search_span_retrieval as _search_span_retrieval
from app.db.public.document_artifacts import DocumentChunk, DocumentTable
from app.db.public.ingest import Document
from app.schemas.search import SearchFilters, SearchRequest
from app.services.search_ranking import RankedResult

hydrate_ranked_chunks = _search_hydration._hydrate_ranked_chunks
hydrate_ranked_tables = _search_hydration._hydrate_ranked_tables
apply_span_filters = _search_span_retrieval.apply_span_filters
keyword_terms = _search_span_retrieval.keyword_terms
build_relaxed_tsquery = _search_span_retrieval.build_relaxed_tsquery
run_keyword_span_chunk_search = _search_span_retrieval.run_keyword_span_chunk_search
run_keyword_span_table_search = _search_span_retrieval.run_keyword_span_table_search
run_semantic_span_chunk_search = _search_span_retrieval.run_semantic_span_chunk_search
run_semantic_span_table_search = _search_span_retrieval.run_semantic_span_table_search
LATE_INTERACTION_QUERY_WORD_WINDOW = (
    _search_span_retrieval.LATE_INTERACTION_QUERY_WORD_WINDOW
)
LATE_INTERACTION_QUERY_WORD_OVERLAP = (
    _search_span_retrieval.LATE_INTERACTION_QUERY_WORD_OVERLAP
)
LATE_INTERACTION_FETCH_MULTIPLIER = (
    _search_span_retrieval.LATE_INTERACTION_FETCH_MULTIPLIER
)
query_multivector_windows = _search_span_retrieval.query_multivector_windows
multivector_span_query = _search_span_retrieval.multivector_span_query
late_interaction_match_trace = _search_span_retrieval.late_interaction_match_trace
run_late_interaction_search = _search_span_retrieval.run_late_interaction_search


def chunk_query(run_id: UUID | None = None) -> Select[tuple[DocumentChunk, Document]]:
    if run_id is None:
        return select(DocumentChunk, Document).join(
            Document,
            and_(
                Document.id == DocumentChunk.document_id,
                Document.active_run_id == DocumentChunk.run_id,
            ),
        )
    return (
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.run_id == run_id)
    )


def table_query(run_id: UUID | None = None) -> Select[tuple[DocumentTable, Document]]:
    if run_id is None:
        return select(DocumentTable, Document).join(
            Document,
            and_(
                Document.id == DocumentTable.document_id,
                Document.active_run_id == DocumentTable.run_id,
            ),
        )
    return (
        select(DocumentTable, Document)
        .join(Document, Document.id == DocumentTable.document_id)
        .where(DocumentTable.run_id == run_id)
    )


def document_query(run_id: UUID | None = None) -> Select:
    if run_id is None:
        return select(Document).where(Document.active_run_id.is_not(None))
    return (
        select(Document)
        .join(
            DocumentChunk,
            and_(
                DocumentChunk.document_id == Document.id,
                DocumentChunk.run_id == run_id,
            ),
        )
        .distinct()
    )


def apply_chunk_filters(statement: Select, filters: SearchFilters | None) -> Select:
    if filters is None:
        return statement
    if filters.result_type == "table":
        return statement.where(false())

    if filters.document_id is not None:
        statement = statement.where(DocumentChunk.document_id == filters.document_id)

    if filters.page_range is not None:
        lower = filters.page_range.page_from
        upper = filters.page_range.page_to
        statement = statement.where(
            and_(
                func.coalesce(DocumentChunk.page_from, DocumentChunk.page_to) <= upper,
                func.coalesce(DocumentChunk.page_to, DocumentChunk.page_from) >= lower,
            )
        )

    return statement


def apply_table_filters(statement: Select, filters: SearchFilters | None) -> Select:
    if filters is None:
        return statement
    if filters.result_type == "chunk":
        return statement.where(false())

    if filters.document_id is not None:
        statement = statement.where(DocumentTable.document_id == filters.document_id)

    if filters.page_range is not None:
        lower = filters.page_range.page_from
        upper = filters.page_range.page_to
        statement = statement.where(
            and_(
                func.coalesce(DocumentTable.page_from, DocumentTable.page_to) <= upper,
                func.coalesce(DocumentTable.page_to, DocumentTable.page_from) >= lower,
            )
        )

    return statement


def apply_document_filters(statement: Select, filters: SearchFilters | None) -> Select:
    if filters is None:
        return statement
    if filters.result_type == "table":
        return statement.where(false())
    if filters.document_id is not None:
        statement = statement.where(Document.id == filters.document_id)
    return statement


def run_keyword_chunk_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    tsquery = func.plainto_tsquery("english", request.query)
    rank = cast(func.ts_rank_cd(DocumentChunk.textsearch, tsquery), Float)
    statement = (
        apply_chunk_filters(chunk_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentChunk.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_chunks(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="keyword_primary",
    )


def run_relaxed_keyword_chunk_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    tsquery = build_relaxed_tsquery(request.query)
    if tsquery is None:
        return []

    rank = cast(func.ts_rank_cd(DocumentChunk.textsearch, tsquery), Float)
    statement = (
        apply_chunk_filters(chunk_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentChunk.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_chunks(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="keyword_relaxed",
    )


def run_keyword_table_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    tsquery = func.plainto_tsquery("english", request.query)
    rank = cast(func.ts_rank_cd(DocumentTable.textsearch, tsquery), Float)
    statement = (
        apply_table_filters(table_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentTable.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentTable.table_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_tables(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="keyword_primary",
    )


def run_relaxed_keyword_table_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    tsquery = build_relaxed_tsquery(request.query)
    if tsquery is None:
        return []

    rank = cast(func.ts_rank_cd(DocumentTable.textsearch, tsquery), Float)
    statement = (
        apply_table_filters(table_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentTable.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentTable.table_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_tables(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="keyword_relaxed",
    )


def run_semantic_chunk_search(
    session: Session,
    request: SearchRequest,
    query_embedding: list[float],
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        apply_chunk_filters(chunk_query(run_id), request.filters)
        .add_columns(similarity.label("score"))
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance.asc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_chunks(
        session.execute(statement).all(),
        "semantic",
        retrieval_source="semantic_primary",
    )


def run_semantic_table_search(
    session: Session,
    request: SearchRequest,
    query_embedding: list[float],
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    distance = DocumentTable.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        apply_table_filters(table_query(run_id), request.filters)
        .add_columns(similarity.label("score"))
        .where(DocumentTable.embedding.is_not(None))
        .order_by(distance.asc(), DocumentTable.table_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_tables(
        session.execute(statement).all(),
        "semantic",
        retrieval_source="semantic_primary",
    )


_chunk_query = chunk_query
_table_query = table_query
_document_query = document_query
_apply_chunk_filters = apply_chunk_filters
_apply_table_filters = apply_table_filters
_apply_document_filters = apply_document_filters
_apply_span_filters = apply_span_filters
_keyword_terms = keyword_terms
_build_relaxed_tsquery = build_relaxed_tsquery
_run_keyword_chunk_search = run_keyword_chunk_search
_run_relaxed_keyword_chunk_search = run_relaxed_keyword_chunk_search
_run_keyword_table_search = run_keyword_table_search
_run_relaxed_keyword_table_search = run_relaxed_keyword_table_search
_run_keyword_span_chunk_search = run_keyword_span_chunk_search
_run_keyword_span_table_search = run_keyword_span_table_search
_run_semantic_chunk_search = run_semantic_chunk_search
_run_semantic_span_chunk_search = run_semantic_span_chunk_search
_run_semantic_table_search = run_semantic_table_search
_run_semantic_span_table_search = run_semantic_span_table_search
_query_multivector_windows = query_multivector_windows
_multivector_span_query = multivector_span_query
_late_interaction_match_trace = late_interaction_match_trace
_run_late_interaction_search = run_late_interaction_search
