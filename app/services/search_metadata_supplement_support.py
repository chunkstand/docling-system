from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import func, or_, select

import app.services.search_query_features as _query_features
import app.services.search_retrieval_primitives as _search_retrieval_primitives
from app.db.public.document_artifacts import DocumentChunk
from app.db.public.ingest import Document
from app.schemas.search import SearchRequest

token_coverage = _query_features.token_coverage
apply_document_filters = _search_retrieval_primitives.apply_document_filters

METADATA_SUPPLEMENT_DOCUMENT_LIMIT = 8


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


def _document_run_scope_condition(*, run_id: UUID | None):
    if run_id is None:
        return Document.active_run_id.is_not(None)
    return (
        select(DocumentChunk.id)
        .where(
            DocumentChunk.document_id == Document.id,
            DocumentChunk.run_id == run_id,
        )
        .correlate(Document)
        .exists()
    )


def document_metadata_candidate_statement(
    request: SearchRequest,
    *,
    run_id: UUID | None,
    document_conditions: list,
    document_rank,
    candidate_limit: int,
):
    metadata_rank = document_rank.label("metadata_rank")
    return (
        apply_document_filters(
            select(Document, metadata_rank).where(_document_run_scope_condition(run_id=run_id)),
            request.filters,
        )
        .where(or_(*document_conditions))
        .order_by(metadata_rank.desc(), Document.id.asc())
        .limit(max(candidate_limit * 2, METADATA_SUPPLEMENT_DOCUMENT_LIMIT))
    )
