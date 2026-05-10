from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import app.services.search_query_features as _query_features
from app.schemas.search import (
    SearchEvidenceSpan,
    SearchFilters,
    SearchRequest,
    SearchResult,
    SearchScores,
)
from app.services.search_query_features import QueryFeatureSet


@dataclass
class RankedEvidenceSpan:
    retrieval_evidence_span_id: UUID
    source_type: str
    source_id: UUID
    span_index: int
    score_kind: str
    score: float | None
    page_from: int | None
    page_to: int | None
    text_excerpt: str
    content_sha256: str
    source_snapshot_sha256: str | None
    metadata: dict = field(default_factory=dict)


@dataclass
class RankedResult:
    result_type: str
    result_id: UUID
    document_id: UUID
    run_id: UUID
    source_filename: str
    page_from: int | None
    page_to: int | None
    chunk_index: int | None = None
    table_index: int | None = None
    document_title: str | None = None
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
    retrieval_sources: tuple[str, ...] = ()
    evidence_spans: tuple[RankedEvidenceSpan, ...] = ()


@dataclass
class RerankedResult:
    item: RankedResult
    rank: int
    base_rank: int | None
    score: float
    features: dict = field(default_factory=dict)


def reciprocal_rank(rank: int) -> float:
    return 1.0 / (60 + rank)


def document_query_overlap_features(
    item: RankedResult,
    query_or_features: QueryFeatureSet | str | None,
) -> dict[str, float]:
    return {
        "source_filename_exact_match": _query_features.strong_document_phrase_match(
            query_or_features,
            Path(item.source_filename).stem,
        ),
        "source_filename_token_coverage": _query_features.token_coverage(
            query_or_features,
            Path(item.source_filename).stem,
        ),
        "document_title_exact_match": _query_features.strong_document_phrase_match(
            query_or_features,
            item.document_title,
        ),
        "document_title_token_coverage": _query_features.token_coverage(
            query_or_features,
            item.document_title,
        ),
    }


def prose_result_text(item: RankedResult) -> str:
    return " ".join(
        part
        for part in (
            item.document_title,
            Path(item.source_filename).stem,
            item.heading,
            item.chunk_text,
            item.table_title,
            item.table_heading,
            item.table_preview,
        )
        if part
    )


def prose_query_match_features(
    item: RankedResult,
    query_or_features: QueryFeatureSet | str | None,
) -> dict[str, float]:
    query_features = _query_features.coerce_query_feature_set(query_or_features)
    result_text = _query_features.normalize_search_text(prose_result_text(item))
    result_tokens = set(result_text.split())
    heading_value = item.heading or item.table_heading
    return {
        "heading_token_coverage": _query_features.token_coverage(
            query_features,
            heading_value,
        ),
        "phrase_overlap": (
            sum(1 for phrase in query_features.phrases if phrase in result_text)
            / len(query_features.phrases)
            if query_features.phrases
            else 0.0
        ),
        "rare_token_overlap": (
            len(query_features.rare_tokens & result_tokens) / len(query_features.rare_tokens)
            if query_features.rare_tokens
            else 0.0
        ),
        "adjacent_chunk_context_signal": float("adjacent_context" in item.retrieval_sources),
    }


def merge_retrieval_sources(*source_groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in source_groups:
        for source in group:
            if source in seen:
                continue
            seen.add(source)
            merged.append(source)
    return tuple(merged)


def merge_evidence_spans(
    *span_groups: tuple[RankedEvidenceSpan, ...],
) -> tuple[RankedEvidenceSpan, ...]:
    merged: dict[UUID, RankedEvidenceSpan] = {}
    for group in span_groups:
        for span in group:
            current = merged.get(span.retrieval_evidence_span_id)
            if current is None or (span.score or 0.0) > (current.score or 0.0):
                merged[span.retrieval_evidence_span_id] = span
    return tuple(
        sorted(
            merged.values(),
            key=lambda span: (
                -(span.score or 0.0),
                span.source_type,
                str(span.source_id),
                span.span_index,
            ),
        )
    )


def table_title_match_features(
    item: RankedResult,
    query_or_features: QueryFeatureSet | str | None,
) -> dict[str, float]:
    if query_or_features is None or item.result_type != "table":
        return {"title_exact_match": 0.0, "title_token_coverage": 0.0}
    query_features = _query_features.coerce_query_feature_set(query_or_features)
    normalized_query = query_features.normalized_query
    title_value = " ".join(part for part in (item.table_title, item.table_heading) if part)
    normalized_title = _query_features.normalize_search_text(title_value)
    if not normalized_query or not normalized_title:
        return {"title_exact_match": 0.0, "title_token_coverage": 0.0}
    exact_match = float(len(normalized_query) >= 4 and normalized_query in normalized_title)
    if len(normalized_query) >= 4 and normalized_query in normalized_title:
        return {"title_exact_match": exact_match, "title_token_coverage": 1.0}
    query_tokens = query_features.normalized_tokens
    if len(query_tokens) < 2:
        return {"title_exact_match": exact_match, "title_token_coverage": 0.0}
    title_tokens = set(normalized_title.split())
    token_coverage = len(query_tokens & title_tokens) / len(query_tokens)
    return {
        "title_exact_match": exact_match,
        "title_token_coverage": token_coverage if token_coverage >= 0.5 else 0.0,
    }


def exact_filter_priority(item: RankedResult, filters: SearchFilters | None) -> int:
    if filters is None or filters.page_range is None:
        return 0
    if item.page_from is None or item.page_to is None:
        return 0
    if (
        item.page_from >= filters.page_range.page_from
        and item.page_to <= filters.page_range.page_to
    ):
        return 1
    return 0


def result_type_priority(item: RankedResult, tabular_query: bool) -> int:
    if tabular_query:
        return 1 if item.result_type == "table" else 0
    return 1 if item.result_type == "chunk" else 0


def document_cluster_strengths(
    items: list[RankedResult],
    *,
    score_getter: Callable[[RankedResult], float],
    query_intent: str,
) -> dict[UUID, float]:
    if query_intent == _query_features.QUERY_INTENT_TABULAR or len(items) < 2:
        return {}

    document_counts: dict[UUID, int] = {}
    document_score_sums: dict[UUID, float] = {}
    for item in items:
        document_counts[item.document_id] = document_counts.get(item.document_id, 0) + 1
        document_score_sums[item.document_id] = document_score_sums.get(
            item.document_id,
            0.0,
        ) + score_getter(item)

    max_count = max(document_counts.values(), default=0)
    max_score_sum = max(document_score_sums.values(), default=0.0)
    if max_count <= 1 or max_score_sum <= 0:
        return {}

    strengths: dict[UUID, float] = {}
    for document_id, count in document_counts.items():
        if count <= 1:
            strengths[document_id] = 0.0
            continue
        count_strength = (count - 1) / (max_count - 1)
        score_strength = document_score_sums[document_id] / max_score_sum
        strengths[document_id] = count_strength * score_strength
    return strengths


def to_search_result(item: RankedResult, score: float) -> SearchResult:
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
        evidence_spans=[
            SearchEvidenceSpan(
                retrieval_evidence_span_id=span.retrieval_evidence_span_id,
                source_type=span.source_type,
                source_id=span.source_id,
                span_index=span.span_index,
                score_kind=span.score_kind,
                score=span.score,
                page_from=span.page_from,
                page_to=span.page_to,
                text_excerpt=span.text_excerpt,
                content_sha256=span.content_sha256,
                source_snapshot_sha256=span.source_snapshot_sha256,
                metadata=span.metadata,
            )
            for span in item.evidence_spans
        ],
    )


def result_key(item: RankedResult) -> tuple[str, UUID]:
    return item.result_type, item.result_id


def keyword_score(item: RankedResult) -> float:
    return item.keyword_score or 0.0


def semantic_score(item: RankedResult) -> float:
    return item.semantic_score or 0.0


def hybrid_score(item: RankedResult) -> float:
    return item.hybrid_score or 0.0


def merge_hybrid_candidates(
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
) -> list[RankedResult]:
    merged: dict[tuple[str, UUID], RankedResult] = {}

    for idx, result in enumerate(keyword_results, start=1):
        current = merged.setdefault(result_key(result), result)
        current.keyword_score = result.keyword_score
        current.hybrid_score = (current.hybrid_score or 0.0) + reciprocal_rank(idx)
        current.retrieval_sources = merge_retrieval_sources(
            current.retrieval_sources,
            result.retrieval_sources,
        )
        current.evidence_spans = merge_evidence_spans(
            current.evidence_spans,
            result.evidence_spans,
        )

    for idx, result in enumerate(semantic_results, start=1):
        current = merged.get(result_key(result))
        if current is None:
            current = result
            merged[result_key(result)] = current
        current.semantic_score = result.semantic_score
        current.hybrid_score = (current.hybrid_score or 0.0) + reciprocal_rank(idx)
        current.retrieval_sources = merge_retrieval_sources(
            current.retrieval_sources,
            result.retrieval_sources,
        )
        current.evidence_spans = merge_evidence_spans(
            current.evidence_spans,
            result.evidence_spans,
        )
    return list(merged.values())


def dedupe_ranked_results(items: list[RankedResult]) -> list[RankedResult]:
    merged: dict[tuple[str, UUID], RankedResult] = {}
    for item in items:
        current = merged.get(result_key(item))
        if current is None:
            merged[result_key(item)] = item
            continue
        current.keyword_score = max(current.keyword_score or 0.0, item.keyword_score or 0.0) or None
        current.semantic_score = (
            max(current.semantic_score or 0.0, item.semantic_score or 0.0) or None
        )
        current.hybrid_score = max(current.hybrid_score or 0.0, item.hybrid_score or 0.0) or None
        current.retrieval_sources = merge_retrieval_sources(
            current.retrieval_sources,
            item.retrieval_sources,
        )
        current.evidence_spans = merge_evidence_spans(
            current.evidence_spans,
            item.evidence_spans,
        )
    return list(merged.values())


def strongest_ranked_score(item: RankedResult) -> float:
    return max(
        item.keyword_score or 0.0,
        item.semantic_score or 0.0,
        item.hybrid_score or 0.0,
    )


def sort_ranked_candidates_by_score(
    items: list[RankedResult],
    *,
    score_getter: Callable[[RankedResult], float],
) -> list[RankedResult]:
    return sorted(
        items,
        key=lambda item: (
            -score_getter(item),
            item.page_from if item.page_from is not None else 10**9,
            str(item.result_id),
        ),
    )


def candidate_source_breakdown(items: list[RankedResult]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        for source in item.retrieval_sources:
            counter[source] += 1
    return dict(sorted(counter.items()))


def rerank_results(
    items: list[RankedResult],
    *,
    request: SearchRequest,
    score_getter: Callable[[RankedResult], float],
    tabular_query: bool,
    query_intent: str,
    active_reranker: Any,
) -> list[RerankedResult]:
    query_features = _query_features.build_query_feature_set(request.query)
    return active_reranker.rerank(
        items,
        request=request,
        score_getter=score_getter,
        tabular_query=tabular_query,
        query_intent=query_intent,
        query_features=query_features,
    )


def merge_hybrid_results(
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
    limit: int,
    filters: SearchFilters | None,
    tabular_query: bool,
    *,
    active_reranker: Any,
    query_intent: str = _query_features.QUERY_INTENT_PROSE_LOOKUP,
    query: str | None = None,
) -> list[SearchResult]:
    merged = merge_hybrid_candidates(keyword_results, semantic_results)
    reranked = rerank_results(
        merged,
        request=SearchRequest(
            query=query or "hybrid results",
            mode="hybrid",
            filters=filters,
            limit=limit,
        ),
        score_getter=lambda item: item.hybrid_score or 0.0,
        tabular_query=tabular_query,
        query_intent=query_intent,
        active_reranker=active_reranker,
    )
    return [to_search_result(candidate.item, candidate.score) for candidate in reranked]


def result_label(item: RankedResult) -> str | None:
    if item.result_type == "table":
        return item.table_title or item.table_heading or item.table_preview
    return item.heading or item.chunk_text


def result_preview(item: RankedResult) -> str | None:
    return item.table_preview if item.result_type == "table" else item.chunk_text


def unique_uuid(values: Iterable[UUID]) -> UUID | None:
    unique_values = {value for value in values if value is not None}
    return next(iter(unique_values)) if len(unique_values) == 1 else None
