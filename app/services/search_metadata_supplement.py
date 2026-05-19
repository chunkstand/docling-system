from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

import app.services.search_query_features as _query_features
import app.services.search_ranking as _search_ranking
import app.services.search_retrieval_primitives as _search_retrieval_primitives
from app.db.models import Document, DocumentChunk
from app.schemas.search import SearchRequest
from app.services.search_ranking import RankedResult

QUERY_INTENT_PROSE_LOOKUP = _query_features.QUERY_INTENT_PROSE_LOOKUP
QUERY_INTENT_PROSE_BROAD = _query_features.QUERY_INTENT_PROSE_BROAD
looks_like_identifier_lookup = _query_features.looks_like_identifier_lookup
metadata_query_tokens = _query_features.metadata_query_tokens
salient_tokens = _query_features.salient_tokens
token_coverage = _query_features.token_coverage
dedupe_ranked_results = _search_ranking.dedupe_ranked_results
strongest_ranked_score = _search_ranking.strongest_ranked_score
apply_chunk_filters = _search_retrieval_primitives.apply_chunk_filters
apply_document_filters = _search_retrieval_primitives.apply_document_filters
chunk_query = _search_retrieval_primitives.chunk_query
document_query = _search_retrieval_primitives.document_query

PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT = 12
PROSE_ADJACENT_EXPANSION_LIMIT = 12
PROSE_ADJACENT_SEED_LIMIT = 6
METADATA_SUPPLEMENT_DIRECT_CHUNK_MULTIPLIER = 4
METADATA_SUPPLEMENT_DOCUMENT_LIMIT = 8
METADATA_SUPPLEMENT_DOCUMENT_CHUNK_MULTIPLIER = 6
METADATA_SUPPLEMENT_SCORE_SCALE = 4.0


def ranked_metadata_overlap_score(
    query: str,
    *,
    document_title: str | None,
    heading: str | None,
    chunk_text: str | None,
    source_filename: str,
    include_document_context: bool = True,
) -> float:
    title_overlap = token_coverage(query, document_title) if include_document_context else 0.0
    heading_overlap = token_coverage(query, heading)
    chunk_overlap = token_coverage(query, chunk_text)
    filename_overlap = (
        token_coverage(query, Path(source_filename).stem) if include_document_context else 0.0
    )
    return max(title_overlap, heading_overlap, chunk_overlap, filename_overlap) + (
        0.2 * title_overlap
        + 0.15 * heading_overlap
        + 0.25 * chunk_overlap
        + 0.15 * filename_overlap
    )


def metadata_tsquery(config: str, tokens: list[str]):
    if not tokens:
        return None
    return func.to_tsquery(config, " | ".join(tokens))


def run_prose_metadata_chunk_search(
    session: Session,
    request: SearchRequest,
    *,
    run_id: UUID | None = None,
    candidate_limit: int = PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT,
) -> list[RankedResult]:
    document_tokens = metadata_query_tokens(request.query)
    content_tokens = sorted(salient_tokens(request.query))
    document_tsquery = metadata_tsquery("simple", document_tokens)
    content_tsquery = metadata_tsquery("english", content_tokens)
    if document_tsquery is None and content_tsquery is None:
        return []

    chunk_rows: list[tuple[DocumentChunk, Document]] = []
    if content_tsquery is not None:
        chunk_rank = func.ts_rank_cd(DocumentChunk.textsearch, content_tsquery)
        chunk_statement = (
            apply_chunk_filters(chunk_query(run_id), request.filters)
            .where(DocumentChunk.textsearch.op("@@")(content_tsquery))
            .order_by(chunk_rank.desc(), DocumentChunk.chunk_index.asc())
            .limit(
                max(
                    candidate_limit * METADATA_SUPPLEMENT_DIRECT_CHUNK_MULTIPLIER,
                    candidate_limit,
                )
            )
        )
        chunk_rows.extend(session.execute(chunk_statement).all())

    document_conditions = []
    document_rank_expressions = []
    if document_tsquery is not None:
        document_conditions.append(Document.metadata_textsearch.op("@@")(document_tsquery))
        document_rank_expressions.append(
            func.ts_rank_cd(Document.metadata_textsearch, document_tsquery)
        )
    if content_tsquery is not None:
        document_conditions.append(Document.metadata_textsearch.op("@@")(content_tsquery))
        document_rank_expressions.append(
            func.ts_rank_cd(Document.metadata_textsearch, content_tsquery)
        )

    document_rows: list[Document] = []
    if document_conditions:
        document_rank = (
            func.greatest(*document_rank_expressions)
            if len(document_rank_expressions) > 1
            else document_rank_expressions[0]
        )
        document_statement = (
            apply_document_filters(document_query(run_id), request.filters)
            .where(or_(*document_conditions))
            .order_by(document_rank.desc(), Document.id.asc())
            .limit(max(candidate_limit * 2, METADATA_SUPPLEMENT_DOCUMENT_LIMIT))
        )
        document_rows = session.execute(document_statement).scalars().all()

    if document_rows:
        document_ids = [document.id for document in document_rows]
        hydration_statement = apply_chunk_filters(chunk_query(run_id), request.filters).where(
            DocumentChunk.document_id.in_(document_ids)
        )
        if content_tsquery is not None:
            hydration_rank = func.ts_rank_cd(DocumentChunk.textsearch, content_tsquery)
            hydration_statement = hydration_statement.order_by(
                hydration_rank.desc(),
                DocumentChunk.chunk_index.asc(),
            )
        else:
            hydration_statement = hydration_statement.order_by(DocumentChunk.chunk_index.asc())
        hydration_statement = hydration_statement.limit(
            max(
                candidate_limit * max(len(document_ids), 2),
                candidate_limit * METADATA_SUPPLEMENT_DOCUMENT_CHUNK_MULTIPLIER,
            )
        )
        chunk_rows.extend(session.execute(hydration_statement).all())

    candidates: list[RankedResult] = []
    include_document_context = request.filters is None or request.filters.document_id is None
    for chunk, document in chunk_rows:
        score = ranked_metadata_overlap_score(
            request.query,
            document_title=document.title,
            heading=chunk.heading,
            chunk_text=chunk.text,
            source_filename=document.source_filename,
            include_document_context=include_document_context,
        )
        if score <= 0:
            continue
        candidates.append(
            RankedResult(
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
                keyword_score=score * METADATA_SUPPLEMENT_SCORE_SCALE,
                retrieval_sources=("metadata_supplement",),
            )
        )
    candidates.sort(
        key=lambda item: (
            -strongest_ranked_score(item),
            item.page_from if item.page_from is not None else 10**9,
            str(item.result_id),
        )
    )
    return dedupe_ranked_results(candidates)[:candidate_limit]


def should_run_metadata_supplement(
    *,
    query: str,
    query_intent: str,
    strict_keyword_count: int,
    harness_name: str,
) -> bool:
    prose_query = query_intent in {
        QUERY_INTENT_PROSE_LOOKUP,
        QUERY_INTENT_PROSE_BROAD,
    }
    if not prose_query:
        return False
    if harness_name == "prose_v3":
        return True
    return strict_keyword_count == 0 and looks_like_identifier_lookup(query)


def expand_adjacent_chunk_context(
    session: Session,
    request: SearchRequest,
    *,
    seed_candidates: list[RankedResult],
    run_id: UUID | None = None,
    expansion_limit: int = PROSE_ADJACENT_EXPANSION_LIMIT,
) -> list[RankedResult]:
    expanded: list[RankedResult] = []
    seen_keys: set[tuple[str, UUID]] = set()
    chunk_seeds = [candidate for candidate in seed_candidates if candidate.result_type == "chunk"]
    chunk_seeds.sort(
        key=lambda item: (
            -strongest_ranked_score(item),
            item.page_from if item.page_from is not None else 10**9,
            str(item.result_id),
        )
    )

    for seed in chunk_seeds[:PROSE_ADJACENT_SEED_LIMIT]:
        if seed.result_type != "chunk" or seed.chunk_index is None:
            continue
        chunk_statement = apply_chunk_filters(chunk_query(run_id), request.filters).where(
            DocumentChunk.document_id == seed.document_id,
            DocumentChunk.run_id == seed.run_id,
            DocumentChunk.chunk_index.in_((max(seed.chunk_index - 1, -1), seed.chunk_index + 1)),
        )
        for chunk, document in session.execute(chunk_statement).all():
            key = ("chunk", chunk.id)
            if key in seen_keys or chunk.id == seed.result_id:
                continue
            seen_keys.add(key)
            expanded.append(
                RankedResult(
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
                    keyword_score=strongest_ranked_score(seed) * 0.85,
                    retrieval_sources=("adjacent_context",),
                )
            )
            if len(expanded) >= expansion_limit:
                return expanded
    return expanded


_ranked_metadata_overlap_score = ranked_metadata_overlap_score
_metadata_tsquery = metadata_tsquery
_run_prose_metadata_chunk_search = run_prose_metadata_chunk_search
_should_run_metadata_supplement = should_run_metadata_supplement
_expand_adjacent_chunk_context = expand_adjacent_chunk_context
