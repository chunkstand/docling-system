from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import Float, Select, and_, cast, func, select
from sqlalchemy.orm import Session

import app.services.search_ranking as _search_ranking
from app.db.public.document_artifacts import DocumentChunk, DocumentTable
from app.db.public.ingest import Document
from app.db.public.retrieval import RetrievalEvidenceSpan
from app.schemas.search import SearchRequest

SEARCH_RESULT_SPAN_LIMIT = 5

RankedEvidenceSpan = _search_ranking.RankedEvidenceSpan
RankedResult = _search_ranking.RankedResult
RerankedResult = _search_ranking.RerankedResult
_merge_evidence_spans = _search_ranking.merge_evidence_spans


def _span_chunk_query(
    run_id: UUID | None = None,
) -> Select[tuple[RetrievalEvidenceSpan, DocumentChunk, Document]]:
    if run_id is None:
        return (
            select(RetrievalEvidenceSpan, DocumentChunk, Document)
            .join(DocumentChunk, RetrievalEvidenceSpan.chunk_id == DocumentChunk.id)
            .join(
                Document,
                and_(
                    Document.id == RetrievalEvidenceSpan.document_id,
                    Document.active_run_id == RetrievalEvidenceSpan.run_id,
                ),
            )
            .where(RetrievalEvidenceSpan.source_type == "chunk")
        )
    return (
        select(RetrievalEvidenceSpan, DocumentChunk, Document)
        .join(DocumentChunk, RetrievalEvidenceSpan.chunk_id == DocumentChunk.id)
        .join(Document, Document.id == RetrievalEvidenceSpan.document_id)
        .where(
            RetrievalEvidenceSpan.run_id == run_id,
            RetrievalEvidenceSpan.source_type == "chunk",
        )
    )


def _span_table_query(
    run_id: UUID | None = None,
) -> Select[tuple[RetrievalEvidenceSpan, DocumentTable, Document]]:
    if run_id is None:
        return (
            select(RetrievalEvidenceSpan, DocumentTable, Document)
            .join(DocumentTable, RetrievalEvidenceSpan.table_id == DocumentTable.id)
            .join(
                Document,
                and_(
                    Document.id == RetrievalEvidenceSpan.document_id,
                    Document.active_run_id == RetrievalEvidenceSpan.run_id,
                ),
            )
            .where(RetrievalEvidenceSpan.source_type == "table")
        )
    return (
        select(RetrievalEvidenceSpan, DocumentTable, Document)
        .join(DocumentTable, RetrievalEvidenceSpan.table_id == DocumentTable.id)
        .join(Document, Document.id == RetrievalEvidenceSpan.document_id)
        .where(
            RetrievalEvidenceSpan.run_id == run_id,
            RetrievalEvidenceSpan.source_type == "table",
        )
    )


def _hydrate_ranked_chunks(
    rows: Iterable[tuple[DocumentChunk, Document, float]],
    score_kind: str,
    *,
    retrieval_source: str,
) -> list[RankedResult]:
    hydrated: list[RankedResult] = []
    for chunk, document, score in rows:
        ranked = RankedResult(
            result_type="chunk",
            result_id=chunk.id,
            document_id=chunk.document_id,
            run_id=chunk.run_id,
            source_filename=document.source_filename,
            document_title=document.title,
            page_from=chunk.page_from,
            page_to=chunk.page_to,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.text,
            heading=chunk.heading,
            retrieval_sources=(retrieval_source,),
        )
        if score_kind == "keyword":
            ranked.keyword_score = float(score)
        else:
            ranked.semantic_score = float(score)
        hydrated.append(ranked)
    return hydrated


def _span_evidence_payload(
    span: RetrievalEvidenceSpan,
    *,
    score_kind: str,
    score: float | None,
    metadata: dict | None = None,
) -> RankedEvidenceSpan:
    return RankedEvidenceSpan(
        retrieval_evidence_span_id=span.id,
        source_type=span.source_type,
        source_id=span.source_id,
        span_index=span.span_index,
        score_kind=score_kind,
        score=float(score) if score is not None else None,
        page_from=span.page_from,
        page_to=span.page_to,
        text_excerpt=span.span_text,
        content_sha256=span.content_sha256,
        source_snapshot_sha256=span.source_snapshot_sha256,
        metadata=metadata or {},
    )


def _hydrate_ranked_span_chunks(
    rows: Iterable[tuple[RetrievalEvidenceSpan, DocumentChunk, Document, float]],
    score_kind: str,
    *,
    retrieval_source: str,
) -> list[RankedResult]:
    hydrated: list[RankedResult] = []
    for span, chunk, document, score in rows:
        ranked = RankedResult(
            result_type="chunk",
            result_id=chunk.id,
            document_id=chunk.document_id,
            run_id=chunk.run_id,
            source_filename=document.source_filename,
            document_title=document.title,
            page_from=chunk.page_from,
            page_to=chunk.page_to,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.text,
            heading=chunk.heading,
            retrieval_sources=(retrieval_source,),
            evidence_spans=(
                _span_evidence_payload(span, score_kind=score_kind, score=float(score)),
            ),
        )
        if score_kind == "keyword":
            ranked.keyword_score = float(score)
        else:
            ranked.semantic_score = float(score)
        hydrated.append(ranked)
    return hydrated


def _hydrate_ranked_tables(
    rows: Iterable[tuple[DocumentTable, Document, float]],
    score_kind: str,
    *,
    retrieval_source: str,
) -> list[RankedResult]:
    hydrated: list[RankedResult] = []
    for table, document, score in rows:
        ranked = RankedResult(
            result_type="table",
            result_id=table.id,
            document_id=table.document_id,
            run_id=table.run_id,
            source_filename=document.source_filename,
            document_title=document.title,
            page_from=table.page_from,
            page_to=table.page_to,
            table_index=table.table_index,
            table_title=table.title,
            table_heading=table.heading,
            table_preview=table.preview_text,
            row_count=table.row_count,
            col_count=table.col_count,
            retrieval_sources=(retrieval_source,),
        )
        if score_kind == "keyword":
            ranked.keyword_score = float(score)
        else:
            ranked.semantic_score = float(score)
        hydrated.append(ranked)
    return hydrated


def _hydrate_ranked_span_tables(
    rows: Iterable[tuple[RetrievalEvidenceSpan, DocumentTable, Document, float]],
    score_kind: str,
    *,
    retrieval_source: str,
) -> list[RankedResult]:
    hydrated: list[RankedResult] = []
    for span, table, document, score in rows:
        ranked = RankedResult(
            result_type="table",
            result_id=table.id,
            document_id=table.document_id,
            run_id=table.run_id,
            source_filename=document.source_filename,
            document_title=document.title,
            page_from=table.page_from,
            page_to=table.page_to,
            table_index=table.table_index,
            table_title=table.title,
            table_heading=table.heading,
            table_preview=table.preview_text,
            row_count=table.row_count,
            col_count=table.col_count,
            retrieval_sources=(retrieval_source,),
            evidence_spans=(
                _span_evidence_payload(span, score_kind=score_kind, score=float(score)),
            ),
        )
        if score_kind == "keyword":
            ranked.keyword_score = float(score)
        else:
            ranked.semantic_score = float(score)
        hydrated.append(ranked)
    return hydrated


def _supports_retrieval_span_search(session: Session | None) -> bool:
    return isinstance(session, Session)


def _load_source_evidence_spans(
    session: Session,
    request: SearchRequest,
    item: RankedResult,
    *,
    limit: int = SEARCH_RESULT_SPAN_LIMIT,
) -> tuple[RankedEvidenceSpan, ...]:
    if not _supports_retrieval_span_search(session):
        return item.evidence_spans

    source_type = item.result_type
    tsquery = func.plainto_tsquery("english", request.query)
    rank = cast(func.ts_rank_cd(RetrievalEvidenceSpan.textsearch, tsquery), Float)
    scored_statement = (
        select(RetrievalEvidenceSpan, rank.label("score"))
        .where(
            RetrievalEvidenceSpan.source_type == source_type,
            RetrievalEvidenceSpan.source_id == item.result_id,
            RetrievalEvidenceSpan.textsearch.op("@@")(tsquery),
        )
        .order_by(rank.desc(), RetrievalEvidenceSpan.span_index.asc())
        .limit(limit)
    )
    scored_spans = tuple(
        _span_evidence_payload(span, score_kind="selected_result_keyword_span", score=score)
        for span, score in session.execute(scored_statement).all()
    )
    if scored_spans:
        return _merge_evidence_spans(item.evidence_spans, scored_spans)

    fallback_statement = (
        select(RetrievalEvidenceSpan)
        .where(
            RetrievalEvidenceSpan.source_type == source_type,
            RetrievalEvidenceSpan.source_id == item.result_id,
        )
        .order_by(RetrievalEvidenceSpan.span_index.asc())
        .limit(limit)
    )
    fallback_spans = tuple(
        _span_evidence_payload(span, score_kind="selected_result_source_span", score=None)
        for span in session.scalars(fallback_statement)
    )
    return _merge_evidence_spans(item.evidence_spans, fallback_spans)


def _ensure_reranked_result_evidence_spans(
    session: Session,
    request: SearchRequest,
    reranked_results: list[RerankedResult],
) -> None:
    if not _supports_retrieval_span_search(session):
        return
    for candidate in reranked_results:
        candidate.item.evidence_spans = _load_source_evidence_spans(
            session,
            request,
            candidate.item,
        )


def _hydrate_late_interaction_results(
    session: Session,
    *,
    span_scores: dict[UUID, dict],
    limit: int,
    run_id: UUID | None,
) -> list[RankedResult]:
    ordered_span_ids = [
        span_id
        for span_id, _state in sorted(
            span_scores.items(),
            key=lambda item: (
                -float(item[1]["score"]),
                str(item[0]),
            ),
        )
    ][:limit]
    if not ordered_span_ids:
        return []

    chunk_rows = (
        session.execute(
            _span_chunk_query(run_id).where(RetrievalEvidenceSpan.id.in_(ordered_span_ids))
        )
        .all()
    )
    table_rows = (
        session.execute(
            _span_table_query(run_id).where(RetrievalEvidenceSpan.id.in_(ordered_span_ids))
        )
        .all()
    )
    hydrated_by_span_id: dict[UUID, RankedResult] = {}
    for span, chunk, document in chunk_rows:
        state = span_scores[span.id]
        score = float(state["score"])
        hydrated_by_span_id[span.id] = RankedResult(
            result_type="chunk",
            result_id=chunk.id,
            document_id=chunk.document_id,
            run_id=chunk.run_id,
            source_filename=document.source_filename,
            document_title=document.title,
            page_from=chunk.page_from,
            page_to=chunk.page_to,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.text,
            heading=chunk.heading,
            semantic_score=score,
            retrieval_sources=("multivector_late_interaction",),
            evidence_spans=(
                _span_evidence_payload(
                    span,
                    score_kind="late_interaction_maxsim",
                    score=score,
                    metadata={"late_interaction": state["trace"]},
                ),
            ),
        )
    for span, table, document in table_rows:
        state = span_scores[span.id]
        score = float(state["score"])
        hydrated_by_span_id[span.id] = RankedResult(
            result_type="table",
            result_id=table.id,
            document_id=table.document_id,
            run_id=table.run_id,
            source_filename=document.source_filename,
            document_title=document.title,
            page_from=table.page_from,
            page_to=table.page_to,
            table_index=table.table_index,
            table_title=table.title,
            table_heading=table.heading,
            table_preview=table.preview_text,
            row_count=table.row_count,
            col_count=table.col_count,
            semantic_score=score,
            retrieval_sources=("multivector_late_interaction",),
            evidence_spans=(
                _span_evidence_payload(
                    span,
                    score_kind="late_interaction_maxsim",
                    score=score,
                    metadata={"late_interaction": state["trace"]},
                ),
            ),
        )
    return [
        hydrated_by_span_id[span_id]
        for span_id in ordered_span_ids
        if span_id in hydrated_by_span_id
    ]
