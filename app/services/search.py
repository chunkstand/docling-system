from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Protocol
from uuid import UUID

from sqlalchemy import Float, Select, and_, cast, false, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentChunk,
    DocumentTable,
    SearchRequestRecord,
    SearchRequestResult,
)
from app.schemas.search import SearchFilters, SearchRequest, SearchResult, SearchScores
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.telemetry import observe_search_results

DEFAULT_SEARCH_HARNESS_NAME = "default_v1"


def _utcnow() -> datetime:
    return datetime.now(UTC)


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


@dataclass
class RerankedResult:
    item: RankedResult
    rank: int
    base_rank: int | None
    score: float
    features: dict = field(default_factory=dict)


@dataclass
class SearchExecution:
    results: list[SearchResult]
    request_id: UUID | None
    harness_name: str
    reranker_name: str
    reranker_version: str
    retrieval_profile_name: str
    harness_config: dict
    embedding_status: str
    embedding_error: str | None
    candidate_count: int
    table_hit_count: int
    duration_ms: float
    details: dict = field(default_factory=dict)


class SearchReranker(Protocol):
    name: str

    def rerank(
        self,
        items: list[RankedResult],
        *,
        request: SearchRequest,
        score_getter: Callable[[RankedResult], float],
        tabular_query: bool,
    ) -> list[RerankedResult]:
        ...


@dataclass(frozen=True)
class SearchRetrievalProfile:
    name: str
    keyword_candidate_multiplier: int
    semantic_candidate_multiplier: int
    min_candidate_limit: int

    def snapshot(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LinearRerankerConfig:
    harness_name: str
    reranker_name: str
    reranker_version: str
    retrieval_profile_name: str
    tabular_table_bonus: float
    title_exact_match_bonus: float
    title_token_coverage_bonus: float
    exact_filter_bonus: float
    result_type_priority_bonus: float

    def snapshot(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SearchHarness:
    name: str
    retrieval_profile: SearchRetrievalProfile
    reranker_config: LinearRerankerConfig

    @property
    def reranker_name(self) -> str:
        return self.reranker_config.reranker_name

    @property
    def reranker_version(self) -> str:
        return self.reranker_config.reranker_version

    @property
    def retrieval_profile_name(self) -> str:
        return self.retrieval_profile.name

    @property
    def config_snapshot(self) -> dict:
        return {
            "harness_name": self.name,
            "retrieval_profile": self.retrieval_profile.snapshot(),
            "reranker": self.reranker_config.snapshot(),
        }

    def build_reranker(self) -> LinearFeatureSearchReranker:
        return LinearFeatureSearchReranker(self.reranker_config)


DEFAULT_RETRIEVAL_PROFILE = SearchRetrievalProfile(
    name="default_v1",
    keyword_candidate_multiplier=5,
    semantic_candidate_multiplier=5,
    min_candidate_limit=20,
)
WIDE_RETRIEVAL_PROFILE = SearchRetrievalProfile(
    name="wide_v2",
    keyword_candidate_multiplier=7,
    semantic_candidate_multiplier=7,
    min_candidate_limit=28,
)

_HARNESS_REGISTRY: dict[str, SearchHarness] = {
    "default_v1": SearchHarness(
        name="default_v1",
        retrieval_profile=DEFAULT_RETRIEVAL_PROFILE,
        reranker_config=LinearRerankerConfig(
            harness_name="default_v1",
            reranker_name="linear_feature_reranker",
            reranker_version="v1",
            retrieval_profile_name=DEFAULT_RETRIEVAL_PROFILE.name,
            tabular_table_bonus=0.05,
            title_exact_match_bonus=0.04,
            title_token_coverage_bonus=0.02,
            exact_filter_bonus=0.01,
            result_type_priority_bonus=0.005,
        ),
    ),
    "wide_v2": SearchHarness(
        name="wide_v2",
        retrieval_profile=WIDE_RETRIEVAL_PROFILE,
        reranker_config=LinearRerankerConfig(
            harness_name="wide_v2",
            reranker_name="linear_feature_reranker",
            reranker_version="v2",
            retrieval_profile_name=WIDE_RETRIEVAL_PROFILE.name,
            tabular_table_bonus=0.08,
            title_exact_match_bonus=0.05,
            title_token_coverage_bonus=0.03,
            exact_filter_bonus=0.02,
            result_type_priority_bonus=0.008,
        ),
    ),
}


class LinearFeatureSearchReranker:
    def __init__(self, config: LinearRerankerConfig) -> None:
        self.config = config
        self.name = config.reranker_name

    def rerank(
        self,
        items: list[RankedResult],
        *,
        request: SearchRequest,
        score_getter: Callable[[RankedResult], float],
        tabular_query: bool,
    ) -> list[RerankedResult]:
        base_ranked = sorted(
            items,
            key=lambda item: (
                -score_getter(item),
                item.page_from if item.page_from is not None else 10**9,
                str(item.result_id),
            ),
        )

        annotated: list[RerankedResult] = []
        for base_rank, item in enumerate(base_ranked, start=1):
            base_score = score_getter(item)
            tabular_table_signal = int(tabular_query and item.result_type == "table")
            title_match_features = _table_title_match_features(item, request.query)
            exact_filter_priority = _exact_filter_priority(item, request.filters)
            result_type_priority = _result_type_priority(item, tabular_query)
            title_match_boost = (
                title_match_features["title_exact_match"] * self.config.title_exact_match_bonus
                + title_match_features["title_token_coverage"]
                * self.config.title_token_coverage_bonus
            )
            tabular_boost = tabular_table_signal * self.config.tabular_table_bonus
            exact_filter_boost = exact_filter_priority * self.config.exact_filter_bonus
            result_type_priority_boost = (
                result_type_priority * self.config.result_type_priority_bonus
            )
            final_score = (
                base_score
                + tabular_boost
                + title_match_boost
                + exact_filter_boost
                + result_type_priority_boost
            )
            annotated.append(
                RerankedResult(
                    item=item,
                    rank=0,
                    base_rank=base_rank,
                    score=final_score,
                    features={
                        "base_score": base_score,
                        "harness_name": self.config.harness_name,
                        "reranker_name": self.config.reranker_name,
                        "reranker_version": self.config.reranker_version,
                        "retrieval_profile_name": self.config.retrieval_profile_name,
                        "tabular_table_signal": tabular_table_signal,
                        "tabular_boost": tabular_boost,
                        "title_exact_match": title_match_features["title_exact_match"],
                        "title_token_coverage": title_match_features["title_token_coverage"],
                        "title_match_boost": title_match_boost,
                        "exact_filter_priority": exact_filter_priority,
                        "exact_filter_boost": exact_filter_boost,
                        "result_type_priority": result_type_priority,
                        "result_type_priority_boost": result_type_priority_boost,
                        "final_score": final_score,
                    },
                )
            )

        ranked = sorted(
            annotated,
            key=lambda candidate: (
                -candidate.score,
                -candidate.features["exact_filter_priority"],
                -candidate.features["result_type_priority"],
                candidate.item.page_from if candidate.item.page_from is not None else 10**9,
                str(candidate.item.result_id),
            ),
        )[: request.limit]

        for rank, candidate in enumerate(ranked, start=1):
            candidate.rank = rank
        return ranked


def list_search_harnesses() -> list[SearchHarness]:
    return list(_HARNESS_REGISTRY.values())


def get_search_harness(name: str | None = None) -> SearchHarness:
    harness_name = name or DEFAULT_SEARCH_HARNESS_NAME
    try:
        return _HARNESS_REGISTRY[harness_name]
    except KeyError as exc:
        available = ", ".join(sorted(_HARNESS_REGISTRY))
        msg = f"Unknown search harness '{harness_name}'. Available: {available}"
        raise ValueError(msg) from exc


def get_default_reranker() -> SearchReranker:
    return get_search_harness().build_reranker()


def _chunk_query(run_id: UUID | None = None) -> Select[tuple[DocumentChunk, Document]]:
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


def _table_query(run_id: UUID | None = None) -> Select[tuple[DocumentTable, Document]]:
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


def _hydrate_ranked_chunks(
    rows: Iterable[tuple[DocumentChunk, Document, float]], score_kind: str
) -> list[RankedResult]:
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


def _hydrate_ranked_tables(
    rows: Iterable[tuple[DocumentTable, Document, float]], score_kind: str
) -> list[RankedResult]:
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


def _keyword_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9]+", query.lower()):
        if len(token) <= 1 or token in seen:
            continue
        seen.add(token)
        terms.append(token)
    return terms


def _build_relaxed_tsquery(query: str):
    terms = _keyword_terms(query)
    if len(terms) < 2:
        return None
    return func.to_tsquery("english", " | ".join(terms))


def _run_keyword_chunk_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    tsquery = func.plainto_tsquery("english", request.query)
    rank = cast(func.ts_rank_cd(DocumentChunk.textsearch, tsquery), Float)
    statement = (
        _apply_chunk_filters(_chunk_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentChunk.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_chunks(session.execute(statement).all(), "keyword")


def _run_relaxed_keyword_chunk_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    tsquery = _build_relaxed_tsquery(request.query)
    if tsquery is None:
        return []

    rank = cast(func.ts_rank_cd(DocumentChunk.textsearch, tsquery), Float)
    statement = (
        _apply_chunk_filters(_chunk_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentChunk.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentChunk.chunk_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_chunks(session.execute(statement).all(), "keyword")


def _run_keyword_table_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    tsquery = func.plainto_tsquery("english", request.query)
    rank = cast(func.ts_rank_cd(DocumentTable.textsearch, tsquery), Float)
    statement = (
        _apply_table_filters(_table_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(DocumentTable.textsearch.op("@@")(tsquery))
        .order_by(rank.desc(), DocumentTable.table_index.asc())
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_tables(session.execute(statement).all(), "keyword")


def _run_relaxed_keyword_table_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    tsquery = _build_relaxed_tsquery(request.query)
    if tsquery is None:
        return []

    rank = cast(func.ts_rank_cd(DocumentTable.textsearch, tsquery), Float)
    statement = (
        _apply_table_filters(_table_query(run_id), request.filters)
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
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        _apply_chunk_filters(_chunk_query(run_id), request.filters)
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
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    distance = DocumentTable.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        _apply_table_filters(_table_query(run_id), request.filters)
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


def _table_title_match_features(item: RankedResult, query: str | None) -> dict[str, float]:
    if query is None or item.result_type != "table" or not item.table_title:
        return {"title_exact_match": 0.0, "title_token_coverage": 0.0}
    normalized_query = _normalize_text(query)
    normalized_title = _normalize_text(item.table_title)
    if not normalized_query or not normalized_title:
        return {"title_exact_match": 0.0, "title_token_coverage": 0.0}
    exact_match = float(len(normalized_query) >= 4 and normalized_query in normalized_title)
    if len(normalized_query) >= 4 and normalized_query in normalized_title:
        return {"title_exact_match": exact_match, "title_token_coverage": 1.0}
    query_tokens = set(normalized_query.split())
    if len(query_tokens) < 2:
        return {"title_exact_match": exact_match, "title_token_coverage": 0.0}
    title_tokens = set(normalized_title.split())
    token_coverage = len(query_tokens & title_tokens) / len(query_tokens)
    return {
        "title_exact_match": exact_match,
        "title_token_coverage": token_coverage if token_coverage >= 0.5 else 0.0,
    }


def _exact_filter_priority(item: RankedResult, filters: SearchFilters | None) -> int:
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


def _result_type_priority(item: RankedResult, tabular_query: bool) -> int:
    if tabular_query:
        return 1 if item.result_type == "table" else 0
    return 1 if item.result_type == "chunk" else 0


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


def _result_key(item: RankedResult) -> tuple[str, UUID]:
    return item.result_type, item.result_id


def _keyword_score(item: RankedResult) -> float:
    return item.keyword_score or 0.0


def _semantic_score(item: RankedResult) -> float:
    return item.semantic_score or 0.0


def _hybrid_score(item: RankedResult) -> float:
    return item.hybrid_score or 0.0


def _merge_hybrid_candidates(
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
) -> list[RankedResult]:
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

    return list(merged.values())


def _rerank_results(
    items: list[RankedResult],
    *,
    request: SearchRequest,
    score_getter: Callable[[RankedResult], float],
    tabular_query: bool,
    reranker: SearchReranker | None = None,
) -> list[RerankedResult]:
    active_reranker = reranker or get_default_reranker()
    return active_reranker.rerank(
        items,
        request=request,
        score_getter=score_getter,
        tabular_query=tabular_query,
    )


def _sort_ranked_results(
    items: list[RankedResult],
    *,
    score_getter,
    filters: SearchFilters | None,
    tabular_query: bool,
    limit: int,
    query: str | None = None,
    reranker: SearchReranker | None = None,
) -> list[SearchResult]:
    reranked = _rerank_results(
        items,
        request=SearchRequest(
            query=query or "ranked results",
            mode="keyword",
            filters=filters,
            limit=limit,
        ),
        score_getter=score_getter,
        tabular_query=tabular_query,
        reranker=reranker,
    )
    return [_to_search_result(candidate.item, candidate.score) for candidate in reranked]


def _merge_hybrid_results(
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
    limit: int,
    filters: SearchFilters | None,
    tabular_query: bool,
    query: str | None = None,
) -> list[SearchResult]:
    merged = _merge_hybrid_candidates(keyword_results, semantic_results)
    reranked = _rerank_results(
        merged,
        request=SearchRequest(
            query=query or "hybrid results",
            mode="hybrid",
            filters=filters,
            limit=limit,
        ),
        score_getter=lambda item: item.hybrid_score or 0.0,
        tabular_query=tabular_query,
    )
    return [_to_search_result(candidate.item, candidate.score) for candidate in reranked]


def _result_label(item: RankedResult) -> str | None:
    if item.result_type == "table":
        return item.table_title or item.table_heading or item.table_preview
    return item.heading or item.chunk_text


def _result_preview(item: RankedResult) -> str | None:
    return item.table_preview if item.result_type == "table" else item.chunk_text


def _persist_search_execution(
    session: Session | None,
    *,
    request: SearchRequest,
    origin: str,
    run_id: UUID | None,
    evaluation_id: UUID | None,
    parent_request_id: UUID | None,
    tabular_query: bool,
    harness_name: str,
    reranker_name: str,
    reranker_version: str,
    retrieval_profile_name: str,
    harness_config: dict,
    embedding_status: str,
    embedding_error: str | None,
    candidate_count: int,
    duration_ms: float,
    details: dict,
    reranked_results: list[RerankedResult],
) -> UUID | None:
    if session is None or not hasattr(session, "add"):
        return None

    created_at = _utcnow()
    filters_payload = (
        request.filters.model_dump(mode="json", exclude_none=True) if request.filters else {}
    )
    search_request = SearchRequestRecord(
        id=uuid.uuid4(),
        parent_request_id=parent_request_id,
        evaluation_id=evaluation_id,
        run_id=run_id,
        origin=origin,
        query_text=request.query,
        mode=request.mode,
        filters_json=filters_payload,
        details_json=details,
        limit=request.limit,
        tabular_query=tabular_query,
        harness_name=harness_name,
        reranker_name=reranker_name,
        reranker_version=reranker_version,
        retrieval_profile_name=retrieval_profile_name,
        harness_config_json=harness_config,
        embedding_status=embedding_status,
        embedding_error=embedding_error,
        candidate_count=candidate_count,
        result_count=len(reranked_results),
        table_hit_count=sum(1 for item in reranked_results if item.item.result_type == "table"),
        duration_ms=duration_ms,
        created_at=created_at,
    )
    session.add(search_request)
    session.flush()

    for candidate in reranked_results:
        item = candidate.item
        session.add(
            SearchRequestResult(
                id=uuid.uuid4(),
                search_request_id=search_request.id,
                rank=candidate.rank,
                base_rank=candidate.base_rank,
                result_type=item.result_type,
                document_id=item.document_id,
                run_id=item.run_id,
                chunk_id=item.result_id if item.result_type == "chunk" else None,
                table_id=item.result_id if item.result_type == "table" else None,
                score=candidate.score,
                keyword_score=item.keyword_score,
                semantic_score=item.semantic_score,
                hybrid_score=item.hybrid_score,
                rerank_features_json=candidate.features,
                page_from=item.page_from,
                page_to=item.page_to,
                source_filename=item.source_filename,
                label=_result_label(item),
                preview_text=_result_preview(item),
                created_at=created_at,
            )
        )

    session.flush()
    return search_request.id


def execute_search(
    session: Session,
    request: SearchRequest,
    embedding_provider: EmbeddingProvider | None = None,
    *,
    run_id: UUID | None = None,
    origin: str = "api",
    evaluation_id: UUID | None = None,
    parent_request_id: UUID | None = None,
    reranker: SearchReranker | None = None,
) -> SearchExecution:
    start = perf_counter()
    harness = get_search_harness(request.harness_name)
    active_reranker = reranker or harness.build_reranker()
    tabular_query = _is_tabular_query(request.query)
    keyword_candidate_limit = max(
        request.limit * harness.retrieval_profile.keyword_candidate_multiplier,
        harness.retrieval_profile.min_candidate_limit,
    )

    if run_id is None:
        keyword_results = _run_keyword_chunk_search(
            session, request, candidate_limit=keyword_candidate_limit
        )
        keyword_results.extend(
            _run_keyword_table_search(session, request, candidate_limit=keyword_candidate_limit)
        )
    else:
        keyword_results = _run_keyword_chunk_search(
            session,
            request,
            candidate_limit=keyword_candidate_limit,
            run_id=run_id,
        )
        keyword_results.extend(
            _run_keyword_table_search(
                session,
                request,
                candidate_limit=keyword_candidate_limit,
                run_id=run_id,
            )
        )

    keyword_strategy = "strict"
    strict_keyword_count = len(keyword_results)
    if strict_keyword_count == 0:
        if run_id is None:
            keyword_results = _run_relaxed_keyword_chunk_search(
                session, request, candidate_limit=keyword_candidate_limit
            )
            keyword_results.extend(
                _run_relaxed_keyword_table_search(
                    session, request, candidate_limit=keyword_candidate_limit
                )
            )
        else:
            keyword_results = _run_relaxed_keyword_chunk_search(
                session,
                request,
                candidate_limit=keyword_candidate_limit,
                run_id=run_id,
            )
            keyword_results.extend(
                _run_relaxed_keyword_table_search(
                    session,
                    request,
                    candidate_limit=keyword_candidate_limit,
                    run_id=run_id,
                )
            )
        if keyword_results:
            keyword_strategy = "relaxed_or"

    keyword_details = {
        "keyword_candidate_count": len(keyword_results),
        "keyword_strict_candidate_count": strict_keyword_count,
        "keyword_strategy": keyword_strategy,
    }
    embedding_status = "skipped"
    embedding_error: str | None = None
    served_mode = request.mode
    fallback_reason: str | None = None
    candidate_items: list[RankedResult] = keyword_results
    score_getter: Callable[[RankedResult], float] = _keyword_score
    semantic_results: list[RankedResult] = []

    if request.mode != "keyword":
        provider = embedding_provider
        if provider is None:
            try:
                provider = get_embedding_provider()
            except Exception as exc:
                served_mode = "keyword"
                embedding_status = "provider_unavailable"
                embedding_error = str(exc)
                fallback_reason = "embedding_provider_unavailable"
                provider = None

        if provider is not None:
            try:
                query_embedding = provider.embed_texts([request.query])[0]
                embedding_status = "completed"
                semantic_candidate_limit = max(
                    request.limit * harness.retrieval_profile.semantic_candidate_multiplier,
                    harness.retrieval_profile.min_candidate_limit,
                )
                if run_id is None:
                    semantic_results = _run_semantic_chunk_search(
                        session,
                        request,
                        query_embedding,
                        candidate_limit=semantic_candidate_limit,
                    )
                    semantic_results.extend(
                        _run_semantic_table_search(
                            session,
                            request,
                            query_embedding,
                            candidate_limit=semantic_candidate_limit,
                        )
                    )
                else:
                    semantic_results = _run_semantic_chunk_search(
                        session,
                        request,
                        query_embedding,
                        candidate_limit=semantic_candidate_limit,
                        run_id=run_id,
                    )
                    semantic_results.extend(
                        _run_semantic_table_search(
                            session,
                            request,
                            query_embedding,
                            candidate_limit=semantic_candidate_limit,
                            run_id=run_id,
                        )
                    )
            except Exception as exc:
                served_mode = "keyword"
                embedding_status = "embedding_failed"
                embedding_error = str(exc)
                fallback_reason = "embedding_failed"

    if request.mode == "semantic" and embedding_status == "completed":
        candidate_items = semantic_results
        score_getter = _semantic_score
        served_mode = "semantic"
    elif request.mode == "hybrid" and embedding_status == "completed":
        candidate_items = _merge_hybrid_candidates(keyword_results, semantic_results)
        score_getter = _hybrid_score
        served_mode = "hybrid"

    details = {
        **keyword_details,
        "semantic_candidate_count": len(semantic_results),
        "requested_mode": request.mode,
        "served_mode": served_mode,
        "harness_name": harness.name,
        "reranker_name": harness.reranker_name,
        "reranker_version": harness.reranker_version,
        "retrieval_profile_name": harness.retrieval_profile_name,
    }
    if fallback_reason is not None:
        details["fallback_reason"] = fallback_reason

    reranked_results = _rerank_results(
        candidate_items,
        request=request,
        score_getter=score_getter,
        tabular_query=tabular_query,
        reranker=active_reranker,
    )
    results = [_to_search_result(candidate.item, candidate.score) for candidate in reranked_results]

    table_hit_count = sum(1 for item in results if item.result_type == "table")
    observe_search_results(
        table_hit_count,
        mixed_request=request.mode == "hybrid",
    )
    duration_ms = round((perf_counter() - start) * 1000, 3)
    request_id = _persist_search_execution(
        session,
        request=request,
        origin=origin,
        run_id=run_id,
        evaluation_id=evaluation_id,
        parent_request_id=parent_request_id,
        tabular_query=tabular_query,
        harness_name=harness.name,
        reranker_name=active_reranker.name,
        reranker_version=harness.reranker_version,
        retrieval_profile_name=harness.retrieval_profile_name,
        harness_config=harness.config_snapshot,
        embedding_status=embedding_status,
        embedding_error=embedding_error,
        candidate_count=len(candidate_items),
        duration_ms=duration_ms,
        details=details,
        reranked_results=reranked_results,
    )

    return SearchExecution(
        results=results,
        request_id=request_id,
        harness_name=harness.name,
        reranker_name=active_reranker.name,
        reranker_version=harness.reranker_version,
        retrieval_profile_name=harness.retrieval_profile_name,
        harness_config=harness.config_snapshot,
        embedding_status=embedding_status,
        embedding_error=embedding_error,
        candidate_count=len(candidate_items),
        table_hit_count=table_hit_count,
        duration_ms=duration_ms,
        details=details,
    )


def search_documents(
    session: Session,
    request: SearchRequest,
    embedding_provider: EmbeddingProvider | None = None,
    *,
    run_id: UUID | None = None,
    origin: str = "api",
    evaluation_id: UUID | None = None,
    parent_request_id: UUID | None = None,
    reranker: SearchReranker | None = None,
) -> list[SearchResult]:
    return execute_search(
        session,
        request,
        embedding_provider,
        run_id=run_id,
        origin=origin,
        evaluation_id=evaluation_id,
        parent_request_id=parent_request_id,
        reranker=reranker,
    ).results
