from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import Float, Select, and_, cast, func, select
from sqlalchemy.orm import Session

import app.services.search_hydration as _search_hydration
from app.core.hashes import payload_sha256
from app.db.public.document_artifacts import DocumentChunk, DocumentTable
from app.db.public.ingest import Document
from app.db.public.retrieval import RetrievalEvidenceSpan, RetrievalEvidenceSpanMultiVector
from app.schemas.search import SearchFilters, SearchRequest
from app.services.search_ranking import RankedResult

span_chunk_query = _search_hydration._span_chunk_query
span_table_query = _search_hydration._span_table_query
hydrate_ranked_span_chunks = _search_hydration._hydrate_ranked_span_chunks
hydrate_ranked_span_tables = _search_hydration._hydrate_ranked_span_tables
supports_retrieval_span_search = _search_hydration._supports_retrieval_span_search
hydrate_late_interaction_results = _search_hydration._hydrate_late_interaction_results

LATE_INTERACTION_QUERY_WORD_WINDOW = 6
LATE_INTERACTION_QUERY_WORD_OVERLAP = 3
LATE_INTERACTION_FETCH_MULTIPLIER = 4


def apply_span_filters(statement: Select, filters: SearchFilters | None) -> Select:
    if filters is None:
        return statement

    if filters.result_type is not None:
        statement = statement.where(RetrievalEvidenceSpan.source_type == filters.result_type)

    if filters.document_id is not None:
        statement = statement.where(RetrievalEvidenceSpan.document_id == filters.document_id)

    if filters.page_range is not None:
        lower = filters.page_range.page_from
        upper = filters.page_range.page_to
        statement = statement.where(
            and_(
                func.coalesce(RetrievalEvidenceSpan.page_from, RetrievalEvidenceSpan.page_to)
                <= upper,
                func.coalesce(RetrievalEvidenceSpan.page_to, RetrievalEvidenceSpan.page_from)
                >= lower,
            )
        )

    return statement


def keyword_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9]+", query.lower()):
        if len(token) <= 1 or token in seen:
            continue
        seen.add(token)
        terms.append(token)
    return terms


def build_relaxed_tsquery(query: str):
    terms = keyword_terms(query)
    if len(terms) < 2:
        return None
    return func.to_tsquery("english", " | ".join(terms))


def run_keyword_span_chunk_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
    relaxed: bool = False,
) -> list[RankedResult]:
    if not supports_retrieval_span_search(session):
        return []
    tsquery = build_relaxed_tsquery(request.query) if relaxed else func.plainto_tsquery(
        "english", request.query
    )
    if tsquery is None:
        return []
    rank = cast(func.ts_rank_cd(RetrievalEvidenceSpan.textsearch, tsquery), Float)
    statement = (
        apply_span_filters(span_chunk_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(RetrievalEvidenceSpan.textsearch.op("@@")(tsquery))
        .order_by(
            rank.desc(), DocumentChunk.chunk_index.asc(), RetrievalEvidenceSpan.span_index.asc()
        )
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_span_chunks(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="span_keyword_relaxed" if relaxed else "span_keyword",
    )


def run_keyword_span_table_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
    relaxed: bool = False,
) -> list[RankedResult]:
    if not supports_retrieval_span_search(session):
        return []
    tsquery = build_relaxed_tsquery(request.query) if relaxed else func.plainto_tsquery(
        "english", request.query
    )
    if tsquery is None:
        return []
    rank = cast(func.ts_rank_cd(RetrievalEvidenceSpan.textsearch, tsquery), Float)
    statement = (
        apply_span_filters(span_table_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(RetrievalEvidenceSpan.textsearch.op("@@")(tsquery))
        .order_by(
            rank.desc(), DocumentTable.table_index.asc(), RetrievalEvidenceSpan.span_index.asc()
        )
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_span_tables(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="span_keyword_relaxed" if relaxed else "span_keyword",
    )


def run_semantic_span_chunk_search(
    session: Session,
    request: SearchRequest,
    query_embedding: list[float],
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    if not supports_retrieval_span_search(session):
        return []
    distance = RetrievalEvidenceSpan.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        apply_span_filters(span_chunk_query(run_id), request.filters)
        .add_columns(similarity.label("score"))
        .where(RetrievalEvidenceSpan.embedding.is_not(None))
        .order_by(
            distance.asc(), DocumentChunk.chunk_index.asc(), RetrievalEvidenceSpan.span_index.asc()
        )
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_span_chunks(
        session.execute(statement).all(),
        "semantic",
        retrieval_source="span_semantic",
    )


def run_semantic_span_table_search(
    session: Session,
    request: SearchRequest,
    query_embedding: list[float],
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    if not supports_retrieval_span_search(session):
        return []
    distance = RetrievalEvidenceSpan.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        apply_span_filters(span_table_query(run_id), request.filters)
        .add_columns(similarity.label("score"))
        .where(RetrievalEvidenceSpan.embedding.is_not(None))
        .order_by(
            distance.asc(), DocumentTable.table_index.asc(), RetrievalEvidenceSpan.span_index.asc()
        )
        .limit(candidate_limit or request.limit)
    )
    return hydrate_ranked_span_tables(
        session.execute(statement).all(),
        "semantic",
        retrieval_source="span_semantic",
    )


def query_multivector_windows(query: str) -> list[dict]:
    normalized = re.sub(r"\s+", " ", query or "").strip()
    if not normalized:
        return []
    words = normalized.split()
    if len(words) <= LATE_INTERACTION_QUERY_WORD_WINDOW:
        return [
            {
                "query_vector_index": 0,
                "token_start": 0,
                "token_end": len(words),
                "text": normalized,
                "text_sha256": payload_sha256({"query_vector_text": normalized}),
            }
        ]

    windows: list[dict] = []
    step = max(LATE_INTERACTION_QUERY_WORD_WINDOW - LATE_INTERACTION_QUERY_WORD_OVERLAP, 1)
    start = 0
    while start < len(words):
        end = min(start + LATE_INTERACTION_QUERY_WORD_WINDOW, len(words))
        text = " ".join(words[start:end])
        windows.append(
            {
                "query_vector_index": len(windows),
                "token_start": start,
                "token_end": end,
                "text": text,
                "text_sha256": payload_sha256(
                    {
                        "query_vector_index": len(windows),
                        "query_vector_text": text,
                    }
                ),
            }
        )
        if end == len(words):
            break
        start += step
    return windows


def multivector_span_query(
    run_id: UUID | None = None,
) -> Select[tuple[RetrievalEvidenceSpanMultiVector, RetrievalEvidenceSpan]]:
    statement = select(RetrievalEvidenceSpanMultiVector, RetrievalEvidenceSpan).join(
        RetrievalEvidenceSpan,
        RetrievalEvidenceSpanMultiVector.retrieval_evidence_span_id == RetrievalEvidenceSpan.id,
    )
    if run_id is None:
        return statement.join(
            Document,
            and_(
                Document.id == RetrievalEvidenceSpanMultiVector.document_id,
                Document.active_run_id == RetrievalEvidenceSpanMultiVector.run_id,
            ),
        )
    return statement.join(
        Document,
        Document.id == RetrievalEvidenceSpanMultiVector.document_id,
    ).where(RetrievalEvidenceSpanMultiVector.run_id == run_id)


def late_interaction_match_trace(
    *,
    query_windows: list[dict],
    query_matches: dict[int, dict],
    score: float,
) -> dict:
    ordered_matches = [query_matches[index] for index in sorted(query_matches)]
    return {
        "schema_name": "late_interaction_maxsim_trace",
        "schema_version": "1.0",
        "score_policy": "average_query_window_max_similarity",
        "score": score,
        "query_vector_count": len(query_windows),
        "matched_query_vector_count": len(ordered_matches),
        "query_vectors": [
            {
                "query_vector_index": item["query_vector_index"],
                "token_start": item["token_start"],
                "token_end": item["token_end"],
                "text": item["text"],
                "text_sha256": item["text_sha256"],
            }
            for item in query_windows
        ],
        "maxsim_matches": ordered_matches,
    }


def run_late_interaction_search(
    session: Session,
    request: SearchRequest,
    *,
    query_windows: list[dict],
    query_vectors: list[list[float]],
    candidate_limit: int,
    run_id: UUID | None,
) -> tuple[list[RankedResult], dict]:
    if not supports_retrieval_span_search(session) or not query_vectors:
        return [], {
            "status": "skipped",
            "query_vector_count": len(query_vectors),
            "match_count": 0,
            "candidate_count": 0,
        }

    span_states: dict[UUID, dict] = {}
    vector_fetch_limit = max(
        candidate_limit * LATE_INTERACTION_FETCH_MULTIPLIER,
        candidate_limit + len(query_vectors),
    )
    for query_vector_index, query_vector in enumerate(query_vectors):
        distance = RetrievalEvidenceSpanMultiVector.embedding.cosine_distance(query_vector)
        similarity = cast(1 - distance, Float)
        statement = (
            apply_span_filters(multivector_span_query(run_id), request.filters)
            .add_columns(similarity.label("score"))
            .where(RetrievalEvidenceSpanMultiVector.embedding.is_not(None))
            .order_by(
                distance.asc(),
                RetrievalEvidenceSpanMultiVector.vector_index.asc(),
                RetrievalEvidenceSpan.id.asc(),
            )
            .limit(vector_fetch_limit)
        )
        for vector_row, span, score in session.execute(statement).all():
            state = span_states.setdefault(
                span.id,
                {
                    "span": span,
                    "query_matches": {},
                },
            )
            current = state["query_matches"].get(query_vector_index)
            score_value = float(score)
            if current is not None and score_value <= float(current["score"]):
                continue
            state["query_matches"][query_vector_index] = {
                "query_vector_index": query_vector_index,
                "score": score_value,
                "span_vector_id": str(vector_row.id),
                "span_vector_index": vector_row.vector_index,
                "token_start": vector_row.token_start,
                "token_end": vector_row.token_end,
                "vector_text": vector_row.vector_text,
                "vector_content_sha256": vector_row.content_sha256,
                "embedding_model": vector_row.embedding_model,
                "embedding_sha256": vector_row.embedding_sha256,
            }

    scored_states: dict[UUID, dict] = {}
    for span_id, state in span_states.items():
        query_matches = state["query_matches"]
        score = sum(
            float(query_matches[index]["score"]) if index in query_matches else 0.0
            for index in range(len(query_vectors))
        ) / len(query_vectors)
        scored_states[span_id] = {
            **state,
            "score": score,
            "trace": late_interaction_match_trace(
                query_windows=query_windows,
                query_matches=query_matches,
                score=score,
            ),
        }

    results = hydrate_late_interaction_results(
        session,
        span_scores=scored_states,
        limit=candidate_limit,
        run_id=run_id,
    )
    return results, {
        "status": "completed" if results else "no_candidates",
        "query_vector_count": len(query_vectors),
        "match_count": sum(len(state["query_matches"]) for state in span_states.values()),
        "candidate_count": len(results),
        "candidate_limit": candidate_limit,
        "score_policy": "average_query_window_max_similarity",
    }
