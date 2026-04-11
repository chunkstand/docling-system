from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re
from uuid import UUID

from sqlalchemy import Float, Select, and_, cast, false, func, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk, DocumentTable
from app.schemas.search import SearchFilters, SearchRequest, SearchResult, SearchScores
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.telemetry import observe_search_results


TABULAR_QUERY_BOOST = 0.05
TABLE_TITLE_EXACT_MATCH_BOOST = 0.04
TABLE_TITLE_TOKEN_COVERAGE_BOOST = 0.02


@dataclass
class RankedResult:
    result_type: str
    result_id: UUID
    document_id: UUID
    run_id: UUID
    source_filename: str
    page_from: int | None
    page_to: int | None
    chunk_text: str | None = None
    heading: str | None = None
    table_title: str | None = None
    table_heading: str | None = None
    table_preview: str | None = None
    row_count: int | None = None
    col_count: int | None = None
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


def _active_table_query() -> Select[tuple[DocumentTable, Document]]:
    return select(DocumentTable, Document).join(
        Document,
        and_(
            Document.id == DocumentTable.document_id,
            Document.active_run_id == DocumentTable.run_id,
        ),
    )


def _apply_chunk_filters(statement: Select, filters: SearchFilters | None) -> Select:
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


def _apply_table_filters(statement: Select, filters: SearchFilters | None) -> Select:
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


def _hydrate_ranked_chunks(rows: Iterable[tuple[DocumentChunk, Document, float]], score_kind: str) -> list[RankedResult]:
    hydrated: list[RankedResult] = []
    for chunk, document, score in rows:
        ranked = RankedResult(
            result_type="chunk",
            result_id=chunk.id,
            document_id=chunk.document_id,
            run_id=chunk.run_id,
            source_filename=document.source_filename,
            page_from=chunk.page_from,
            page_to=chunk.page_to,
            chunk_text=chunk.text,
            heading=chunk.heading,
        )
        if score_kind == "keyword":
            ranked.keyword_score = float(score)
        else:
            ranked.semantic_score = float(score)
        hydrated.append(ranked)
    return hydrated


def _hydrate_ranked_tables(rows: Iterable[tuple[DocumentTable, Document, float]], score_kind: str) -> list[RankedResult]:
    hydrated: list[RankedResult] = []
    for table, document, score in rows:
        ranked = RankedResult(
            result_type="table",
            result_id=table.id,
            document_id=table.document_id,
            run_id=table.run_id,
            source_filename=document.source_filename,
            page_from=table.page_from,
            page_to=table.page_to,
            table_title=table.title,
            table_heading=table.heading,
            table_preview=table.preview_text,
            row_count=table.row_count,
            col_count=table.col_count,
        )
        if score_kind == "keyword":
            ranked.keyword_score = float(score)
        else:
            ranked.semantic_score = float(score)
        hydrated.append(ranked)
    return hydrated


def _run_keyword_chunk_search(session: Session, request: SearchRequest, candidate_limit: int | None = None) -> list[RankedResult]:
    tsquery = func.plainto_tsquery("english", request.query)
    rank = cast(func.ts_rank_cd(DocumentChunk.textsearch, tsquery), Float)
    statement = (
        _apply_chunk_filters(_active_chunk_query(), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentChunk.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_chunks(session.execute(statement).all(), "keyword")


def _run_keyword_table_search(session: Session, request: SearchRequest, candidate_limit: int | None = None) -> list[RankedResult]:
    tsquery = func.plainto_tsquery("english", request.query)
    rank = cast(func.ts_rank_cd(DocumentTable.textsearch, tsquery), Float)
    statement = (
        _apply_table_filters(_active_table_query(), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentTable.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentTable.table_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_tables(session.execute(statement).all(), "keyword")


def _run_semantic_chunk_search(
    session: Session,
    request: SearchRequest,
    query_embedding: list[float],
    candidate_limit: int | None = None,
) -> list[RankedResult]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        _apply_chunk_filters(_active_chunk_query(), request.filters)
        .add_columns(similarity.label("score"))
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance.asc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_chunks(session.execute(statement).all(), "semantic")


def _run_semantic_table_search(
    session: Session,
    request: SearchRequest,
    query_embedding: list[float],
    candidate_limit: int | None = None,
) -> list[RankedResult]:
    distance = DocumentTable.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        _apply_table_filters(_active_table_query(), request.filters)
        .add_columns(similarity.label("score"))
        .where(DocumentTable.embedding.is_not(None))
        .order_by(distance.asc(), DocumentTable.table_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_tables(session.execute(statement).all(), "semantic")


def _reciprocal_rank(rank: int) -> float:
    return 1.0 / (60 + rank)


def _is_tabular_query(query: str) -> bool:
    normalized = query.lower()
    if any(token in normalized for token in ("table", "row", "column")):
        return True
    if "table " in normalized and any(char.isdigit() for char in normalized):
        return True
    if any(op in normalized for op in (">", "<", ">=", "<=", "greater than", "less than")):
        return True
    if sum(char.isdigit() for char in normalized) >= 3:
        return True
    return False


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _table_title_match_boost(item: RankedResult, query: str | None) -> float:
    if query is None or item.result_type != "table" or not item.table_title:
        return 0.0
    normalized_query = _normalize_text(query)
    normalized_title = _normalize_text(item.table_title)
    if not normalized_query or not normalized_title:
        return 0.0
    if len(normalized_query) >= 4 and normalized_query in normalized_title:
        return TABLE_TITLE_EXACT_MATCH_BOOST
    query_tokens = set(normalized_query.split())
    if len(query_tokens) < 2:
        return 0.0
    title_tokens = set(normalized_title.split())
    token_coverage = len(query_tokens & title_tokens) / len(query_tokens)
    if token_coverage >= 0.8:
        return TABLE_TITLE_TOKEN_COVERAGE_BOOST
    return 0.0


def _exact_filter_priority(item: RankedResult, filters: SearchFilters | None) -> int:
    if filters is None or filters.page_range is None:
        return 0
    if item.page_from is None or item.page_to is None:
        return 0
    if item.page_from >= filters.page_range.page_from and item.page_to <= filters.page_range.page_to:
        return 1
    return 0


def _result_type_priority(item: RankedResult, tabular_query: bool) -> int:
    if tabular_query:
        return 1 if item.result_type == "table" else 0
    return 1 if item.result_type == "chunk" else 0


def _final_score(item: RankedResult, base_score: float, tabular_query: bool, query: str | None = None) -> float:
    boost = TABULAR_QUERY_BOOST if tabular_query and item.result_type == "table" else 0.0
    boost += _table_title_match_boost(item, query)
    return base_score + boost


def _sort_ranked_results(
    items: list[RankedResult],
    *,
    score_getter,
    filters: SearchFilters | None,
    tabular_query: bool,
    limit: int,
    query: str | None = None,
) -> list[SearchResult]:
    ranked = sorted(
        items,
        key=lambda item: (
            -_final_score(item, score_getter(item), tabular_query, query),
            -_exact_filter_priority(item, filters),
            -_result_type_priority(item, tabular_query),
            item.page_from if item.page_from is not None else 10**9,
            str(item.result_id),
        ),
    )[:limit]
    return [_to_search_result(item, score=_final_score(item, score_getter(item), tabular_query, query)) for item in ranked]


def _result_key(item: RankedResult) -> tuple[str, UUID]:
    return item.result_type, item.result_id


def _merge_hybrid_results(
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
    limit: int,
    filters: SearchFilters | None,
    tabular_query: bool,
    query: str | None = None,
) -> list[SearchResult]:
    merged: dict[tuple[str, UUID], RankedResult] = {}

    for idx, result in enumerate(keyword_results, start=1):
        current = merged.setdefault(_result_key(result), result)
        current.keyword_score = result.keyword_score
        current.hybrid_score = (current.hybrid_score or 0.0) + _reciprocal_rank(idx)

    for idx, result in enumerate(semantic_results, start=1):
        current = merged.get(_result_key(result))
        if current is None:
            current = result
            merged[_result_key(result)] = current
        current.semantic_score = result.semantic_score
        current.hybrid_score = (current.hybrid_score or 0.0) + _reciprocal_rank(idx)

    ranked = sorted(
        merged.values(),
        key=lambda item: (
            -_final_score(item, item.hybrid_score or 0.0, tabular_query, query),
            -_exact_filter_priority(item, filters),
            -_result_type_priority(item, tabular_query),
            item.page_from if item.page_from is not None else 10**9,
            str(item.result_id),
        ),
    )[:limit]
    return [_to_search_result(item, score=_final_score(item, item.hybrid_score or 0.0, tabular_query, query)) for item in ranked]


def _to_search_result(item: RankedResult, score: float) -> SearchResult:
    return SearchResult(
        result_type=item.result_type,
        document_id=item.document_id,
        run_id=item.run_id,
        score=score,
        chunk_id=item.result_id if item.result_type == "chunk" else None,
        chunk_text=item.chunk_text,
        heading=item.heading,
        table_id=item.result_id if item.result_type == "table" else None,
        table_title=item.table_title,
        table_heading=item.table_heading,
        table_preview=item.table_preview,
        row_count=item.row_count,
        col_count=item.col_count,
        page_from=item.page_from,
        page_to=item.page_to,
        source_filename=item.source_filename,
        scores=SearchScores(
            keyword_score=item.keyword_score,
            semantic_score=item.semantic_score,
            hybrid_score=item.hybrid_score,
        ),
    )


def search_documents(
    session: Session,
    request: SearchRequest,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[SearchResult]:
    tabular_query = _is_tabular_query(request.query)
    keyword_results = _run_keyword_chunk_search(session, request, candidate_limit=max(request.limit * 5, 20))
    keyword_results.extend(_run_keyword_table_search(session, request, candidate_limit=max(request.limit * 5, 20)))

    def keyword_fallback_results() -> list[SearchResult]:
        return _sort_ranked_results(
            keyword_results,
            score_getter=lambda item: item.keyword_score or 0.0,
            filters=request.filters,
            tabular_query=tabular_query,
            limit=request.limit,
            query=request.query,
        )

    if request.mode == "keyword":
        results = keyword_fallback_results()
        observe_search_results(sum(1 for item in results if item.result_type == "table"), mixed_request=False)
        return results

    provider = embedding_provider
    if provider is None:
        try:
            provider = get_embedding_provider()
        except Exception:
            results = keyword_fallback_results()
            observe_search_results(sum(1 for item in results if item.result_type == "table"), mixed_request=request.mode == "hybrid")
            return results

    try:
        query_embedding = provider.embed_texts([request.query])[0]
    except Exception:
        results = keyword_fallback_results()
        observe_search_results(sum(1 for item in results if item.result_type == "table"), mixed_request=request.mode == "hybrid")
        return results

    semantic_results = _run_semantic_chunk_search(
        session, request, query_embedding, candidate_limit=max(request.limit * 5, 20)
    )
    semantic_results.extend(
        _run_semantic_table_search(session, request, query_embedding, candidate_limit=max(request.limit * 5, 20))
    )

    if request.mode == "semantic":
        results = _sort_ranked_results(
            semantic_results,
            score_getter=lambda item: item.semantic_score or 0.0,
            filters=request.filters,
            tabular_query=tabular_query,
            limit=request.limit,
            query=request.query,
        )
        observe_search_results(sum(1 for item in results if item.result_type == "table"), mixed_request=False)
        return results

    results = _merge_hybrid_results(
        keyword_results,
        semantic_results,
        request.limit,
        request.filters,
        tabular_query,
        query=request.query,
    )
    observe_search_results(sum(1 for item in results if item.result_type == "table"), mixed_request=True)
    return results
