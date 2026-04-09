from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, Float, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.schemas.search import SearchFilters, SearchRequest, SearchResult, SearchScores
from app.services.embeddings import EmbeddingProvider, get_embedding_provider


@dataclass
class RankedChunk:
    chunk_id: UUID
    document_id: UUID
    run_id: UUID
    chunk_text: str
    heading: str | None
    page_from: int | None
    page_to: int | None
    source_filename: str
    keyword_score: float | None = None
    semantic_score: float | None = None
    hybrid_score: float | None = None


def _active_chunk_query() -> Select[tuple[DocumentChunk, Document]]:
    return select(DocumentChunk, Document).join(
        Document,
        and_(
            Document.id == DocumentChunk.document_id,
            Document.active_run_id == DocumentChunk.run_id,
        ),
    )


def _apply_filters(statement: Select, filters: SearchFilters | None) -> Select:
    if filters is None:
        return statement

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


def _hydrate_ranked_chunks(rows: Iterable[tuple[DocumentChunk, Document, float]], score_kind: str) -> list[RankedChunk]:
    hydrated: list[RankedChunk] = []
    for chunk, document, score in rows:
        ranked = RankedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            run_id=chunk.run_id,
            chunk_text=chunk.text,
            heading=chunk.heading,
            page_from=chunk.page_from,
            page_to=chunk.page_to,
            source_filename=document.source_filename,
        )
        if score_kind == "keyword":
            ranked.keyword_score = float(score)
        else:
            ranked.semantic_score = float(score)
        hydrated.append(ranked)
    return hydrated


def _run_keyword_search(session: Session, request: SearchRequest, candidate_limit: int | None = None) -> list[RankedChunk]:
    tsquery = func.plainto_tsquery("english", request.query)
    rank = cast(func.ts_rank_cd(DocumentChunk.textsearch, tsquery), Float)
    statement = (
        _apply_filters(_active_chunk_query(), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentChunk.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    rows = session.execute(statement).all()
    return _hydrate_ranked_chunks(rows, "keyword")


def _run_semantic_search(
    session: Session,
    request: SearchRequest,
    embedding_provider: EmbeddingProvider,
    candidate_limit: int | None = None,
) -> list[RankedChunk]:
    query_embedding = embedding_provider.embed_texts([request.query])[0]
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        _apply_filters(_active_chunk_query(), request.filters)
        .add_columns(similarity.label("score"))
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance.asc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    rows = session.execute(statement).all()
    return _hydrate_ranked_chunks(rows, "semantic")


def _reciprocal_rank(rank: int) -> float:
    return 1.0 / (60 + rank)


def _merge_hybrid_results(keyword_results: list[RankedChunk], semantic_results: list[RankedChunk], limit: int) -> list[SearchResult]:
    merged: dict[UUID, RankedChunk] = {}

    for idx, result in enumerate(keyword_results, start=1):
        current = merged.setdefault(result.chunk_id, result)
        current.keyword_score = result.keyword_score
        current.hybrid_score = (current.hybrid_score or 0.0) + _reciprocal_rank(idx)

    for idx, result in enumerate(semantic_results, start=1):
        current = merged.get(result.chunk_id)
        if current is None:
            current = result
            merged[result.chunk_id] = current
        current.semantic_score = result.semantic_score
        current.hybrid_score = (current.hybrid_score or 0.0) + _reciprocal_rank(idx)

    ranked = sorted(merged.values(), key=lambda item: item.hybrid_score or 0.0, reverse=True)[:limit]
    return [_to_search_result(item, score=item.hybrid_score or 0.0) for item in ranked]


def _to_search_result(item: RankedChunk, score: float) -> SearchResult:
    return SearchResult(
        chunk_id=item.chunk_id,
        document_id=item.document_id,
        run_id=item.run_id,
        score=score,
        chunk_text=item.chunk_text,
        heading=item.heading,
        page_from=item.page_from,
        page_to=item.page_to,
        source_filename=item.source_filename,
        scores=SearchScores(
            keyword_score=item.keyword_score,
            semantic_score=item.semantic_score,
            hybrid_score=item.hybrid_score,
        ),
    )


def search_chunks(
    session: Session,
    request: SearchRequest,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[SearchResult]:
    provider = embedding_provider
    if request.mode in {"semantic", "hybrid"} and provider is None:
        provider = get_embedding_provider()

    if request.mode == "keyword":
        return [_to_search_result(item, score=item.keyword_score or 0.0) for item in _run_keyword_search(session, request)]

    if request.mode == "semantic":
        semantic_results = _run_semantic_search(session, request, provider)
        return [_to_search_result(item, score=item.semantic_score or 0.0) for item in semantic_results]

    candidate_limit = max(request.limit * 5, 20)
    keyword_results = _run_keyword_search(session, request, candidate_limit=candidate_limit)
    semantic_results = _run_semantic_search(session, request, provider, candidate_limit=candidate_limit)
    return _merge_hybrid_results(keyword_results, semantic_results, request.limit)
