from __future__ import annotations

import re
import uuid
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Protocol
from uuid import UUID

from sqlalchemy import Float, Select, and_, cast, false, func, or_, select
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
from app.services.search_harness_overrides import load_applied_search_harness_overrides
from app.services.telemetry import observe_search_results

DEFAULT_SEARCH_HARNESS_NAME = "default_v1"
QUERY_INTENT_TABULAR = "tabular"
QUERY_INTENT_PROSE_LOOKUP = "prose_lookup"
QUERY_INTENT_PROSE_BROAD = "prose_broad"
PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT = 12
PROSE_ADJACENT_EXPANSION_LIMIT = 12
PROSE_ADJACENT_SEED_LIMIT = 6
TABULAR_REFERENCE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)+(?:\s*\(\s*\d+\s*\))?\b"
)


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
        query_intent: str,
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
    source_filename_exact_match_bonus: float
    source_filename_token_coverage_bonus: float
    document_title_exact_match_bonus: float
    document_title_token_coverage_bonus: float
    prose_document_cluster_bonus: float
    heading_token_coverage_bonus: float
    phrase_overlap_bonus: float
    rare_token_overlap_bonus: float
    adjacent_chunk_context_bonus: float
    prose_table_penalty: float
    exact_filter_bonus: float
    result_type_priority_bonus: float

    def snapshot(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SearchHarness:
    name: str
    retrieval_profile: SearchRetrievalProfile
    reranker_config: LinearRerankerConfig
    base_harness_name: str | None = None
    metadata: dict = field(default_factory=dict)

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
        snapshot = {
            "harness_name": self.name,
            "retrieval_profile": self.retrieval_profile.snapshot(),
            "reranker": self.reranker_config.snapshot(),
        }
        if self.base_harness_name is not None:
            snapshot["base_harness_name"] = self.base_harness_name
        if self.metadata:
            snapshot["metadata"] = self.metadata
        return snapshot

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
PROSE_RETRIEVAL_PROFILE = SearchRetrievalProfile(
    name="prose_v3",
    keyword_candidate_multiplier=10,
    semantic_candidate_multiplier=10,
    min_candidate_limit=40,
)

METADATA_SUPPLEMENT_SCAN_LIMIT = 1000
METADATA_SUPPLEMENT_SCORE_SCALE = 4.0

SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS = {
    "keyword_candidate_multiplier",
    "semantic_candidate_multiplier",
    "min_candidate_limit",
}

SEARCH_HARNESS_RERANKER_OVERRIDE_FIELDS = {
    "tabular_table_bonus",
    "title_exact_match_bonus",
    "title_token_coverage_bonus",
    "source_filename_exact_match_bonus",
    "source_filename_token_coverage_bonus",
    "document_title_exact_match_bonus",
    "document_title_token_coverage_bonus",
    "prose_document_cluster_bonus",
    "heading_token_coverage_bonus",
    "phrase_overlap_bonus",
    "rare_token_overlap_bonus",
    "adjacent_chunk_context_bonus",
    "prose_table_penalty",
    "exact_filter_bonus",
    "result_type_priority_bonus",
}

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
            source_filename_exact_match_bonus=4.0,
            source_filename_token_coverage_bonus=0.035,
            document_title_exact_match_bonus=2.0,
            document_title_token_coverage_bonus=0.03,
            prose_document_cluster_bonus=0.025,
            heading_token_coverage_bonus=0.03,
            phrase_overlap_bonus=0.03,
            rare_token_overlap_bonus=0.04,
            adjacent_chunk_context_bonus=0.0,
            prose_table_penalty=0.0,
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
            source_filename_exact_match_bonus=4.0,
            source_filename_token_coverage_bonus=0.045,
            document_title_exact_match_bonus=2.25,
            document_title_token_coverage_bonus=0.04,
            prose_document_cluster_bonus=0.035,
            heading_token_coverage_bonus=0.03,
            phrase_overlap_bonus=0.03,
            rare_token_overlap_bonus=0.04,
            adjacent_chunk_context_bonus=0.0,
            prose_table_penalty=0.0,
            exact_filter_bonus=0.02,
            result_type_priority_bonus=0.008,
        ),
    ),
    "prose_v3": SearchHarness(
        name="prose_v3",
        retrieval_profile=PROSE_RETRIEVAL_PROFILE,
        reranker_config=LinearRerankerConfig(
            harness_name="prose_v3",
            reranker_name="linear_feature_reranker",
            reranker_version="v3",
            retrieval_profile_name=PROSE_RETRIEVAL_PROFILE.name,
            tabular_table_bonus=0.08,
            title_exact_match_bonus=0.05,
            title_token_coverage_bonus=0.03,
            source_filename_exact_match_bonus=3.5,
            source_filename_token_coverage_bonus=0.05,
            document_title_exact_match_bonus=2.25,
            document_title_token_coverage_bonus=0.045,
            prose_document_cluster_bonus=0.07,
            heading_token_coverage_bonus=0.03,
            phrase_overlap_bonus=0.04,
            rare_token_overlap_bonus=0.045,
            adjacent_chunk_context_bonus=0.025,
            prose_table_penalty=0.02,
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
        query_intent: str,
    ) -> list[RerankedResult]:
        base_ranked = sorted(
            items,
            key=lambda item: (
                -score_getter(item),
                item.page_from if item.page_from is not None else 10**9,
                str(item.result_id),
            ),
        )

        document_cluster_strengths = _document_cluster_strengths(
            base_ranked,
            score_getter=score_getter,
            query_intent=query_intent,
        )
        annotated: list[RerankedResult] = []
        for base_rank, item in enumerate(base_ranked, start=1):
            base_score = score_getter(item)
            tabular_table_signal = int(tabular_query and item.result_type == "table")
            title_match_features = _table_title_match_features(item, request.query)
            document_overlap_features = _document_query_overlap_features(item, request.query)
            prose_match_features = _prose_query_match_features(item, request.query)
            exact_filter_priority = _exact_filter_priority(item, request.filters)
            result_type_priority = _result_type_priority(item, tabular_query)
            document_cluster_strength = document_cluster_strengths.get(item.document_id, 0.0)
            title_match_boost = (
                title_match_features["title_exact_match"] * self.config.title_exact_match_bonus
                + title_match_features["title_token_coverage"]
                * self.config.title_token_coverage_bonus
            )
            source_filename_exact_match_boost = (
                document_overlap_features["source_filename_exact_match"]
                * self.config.source_filename_exact_match_bonus
            )
            source_filename_boost = (
                document_overlap_features["source_filename_token_coverage"]
                * self.config.source_filename_token_coverage_bonus
            )
            document_title_exact_match_boost = (
                document_overlap_features["document_title_exact_match"]
                * self.config.document_title_exact_match_bonus
            )
            document_title_boost = (
                document_overlap_features["document_title_token_coverage"]
                * self.config.document_title_token_coverage_bonus
            )
            prose_document_cluster_boost = (
                document_cluster_strength * self.config.prose_document_cluster_bonus
            )
            heading_boost = (
                prose_match_features["heading_token_coverage"]
                * self.config.heading_token_coverage_bonus
            )
            phrase_overlap_boost = (
                prose_match_features["phrase_overlap"] * self.config.phrase_overlap_bonus
            )
            rare_token_overlap_boost = (
                prose_match_features["rare_token_overlap"] * self.config.rare_token_overlap_bonus
            )
            adjacent_chunk_context_boost = (
                prose_match_features["adjacent_chunk_context_signal"]
                * self.config.adjacent_chunk_context_bonus
            )
            tabular_boost = tabular_table_signal * self.config.tabular_table_bonus
            prose_table_penalty = (
                self.config.prose_table_penalty
                if query_intent != QUERY_INTENT_TABULAR and item.result_type == "table"
                else 0.0
            )
            exact_filter_boost = exact_filter_priority * self.config.exact_filter_bonus
            result_type_priority_boost = (
                result_type_priority * self.config.result_type_priority_bonus
            )
            final_score = (
                base_score
                + tabular_boost
                + title_match_boost
                + source_filename_exact_match_boost
                + source_filename_boost
                + document_title_exact_match_boost
                + document_title_boost
                + prose_document_cluster_boost
                + heading_boost
                + phrase_overlap_boost
                + rare_token_overlap_boost
                + adjacent_chunk_context_boost
                - prose_table_penalty
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
                        "source_filename_exact_match": document_overlap_features[
                            "source_filename_exact_match"
                        ],
                        "source_filename_exact_match_boost": source_filename_exact_match_boost,
                        "source_filename_token_coverage": document_overlap_features[
                            "source_filename_token_coverage"
                        ],
                        "source_filename_boost": source_filename_boost,
                        "document_title_exact_match": document_overlap_features[
                            "document_title_exact_match"
                        ],
                        "document_title_exact_match_boost": document_title_exact_match_boost,
                        "document_title_token_coverage": document_overlap_features[
                            "document_title_token_coverage"
                        ],
                        "document_title_boost": document_title_boost,
                        "document_cluster_strength": document_cluster_strength,
                        "prose_document_cluster_boost": prose_document_cluster_boost,
                        "heading_token_coverage": prose_match_features[
                            "heading_token_coverage"
                        ],
                        "heading_boost": heading_boost,
                        "phrase_overlap": prose_match_features["phrase_overlap"],
                        "phrase_overlap_boost": phrase_overlap_boost,
                        "rare_token_overlap": prose_match_features["rare_token_overlap"],
                        "rare_token_overlap_boost": rare_token_overlap_boost,
                        "adjacent_chunk_context_signal": prose_match_features[
                            "adjacent_chunk_context_signal"
                        ],
                        "adjacent_chunk_context_boost": adjacent_chunk_context_boost,
                        "prose_table_penalty": prose_table_penalty,
                        "exact_filter_priority": exact_filter_priority,
                        "exact_filter_boost": exact_filter_boost,
                        "result_type_priority": result_type_priority,
                        "result_type_priority_boost": result_type_priority_boost,
                        "query_intent": query_intent,
                        "retrieval_sources": list(item.retrieval_sources),
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


def _build_derived_search_harness(
    *,
    harness_name: str,
    spec: dict,
    registry: dict[str, SearchHarness],
) -> SearchHarness:
    base_harness_name = str(spec.get("base_harness_name") or DEFAULT_SEARCH_HARNESS_NAME)
    try:
        base_harness = registry[base_harness_name]
    except KeyError as exc:
        msg = f"Unknown base search harness '{base_harness_name}' for override '{harness_name}'."
        raise ValueError(msg) from exc

    retrieval_overrides = dict(spec.get("retrieval_profile_overrides") or {})
    reranker_overrides = dict(spec.get("reranker_overrides") or {})
    invalid_retrieval_keys = sorted(
        set(retrieval_overrides) - SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS
    )
    if invalid_retrieval_keys:
        msg = (
            f"Invalid retrieval override field(s) for '{harness_name}': "
            f"{', '.join(invalid_retrieval_keys)}"
        )
        raise ValueError(msg)
    invalid_reranker_keys = sorted(
        set(reranker_overrides) - SEARCH_HARNESS_RERANKER_OVERRIDE_FIELDS
    )
    if invalid_reranker_keys:
        msg = (
            f"Invalid reranker override field(s) for '{harness_name}': "
            f"{', '.join(invalid_reranker_keys)}"
        )
        raise ValueError(msg)

    retrieval_profile = replace(
        base_harness.retrieval_profile,
        name=harness_name,
        **retrieval_overrides,
    )
    reranker_config = replace(
        base_harness.reranker_config,
        harness_name=harness_name,
        retrieval_profile_name=harness_name,
        reranker_version=f"{base_harness.reranker_version}+override",
        **reranker_overrides,
    )
    metadata = {
        "override_type": spec.get("override_type") or "derived_harness",
        "override_source": spec.get("override_source") or "unknown",
    }
    for key in (
        "draft_task_id",
        "source_task_id",
        "verification_task_id",
        "applied_by",
        "applied_at",
        "rationale",
    ):
        value = spec.get(key)
        if value is not None:
            metadata[key] = value

    return SearchHarness(
        name=harness_name,
        retrieval_profile=retrieval_profile,
        reranker_config=reranker_config,
        base_harness_name=base_harness.name,
        metadata=metadata,
    )


def _build_search_harness_registry(
    harness_overrides: dict[str, dict] | None = None,
) -> dict[str, SearchHarness]:
    registry = dict(_HARNESS_REGISTRY)
    applied_overrides = load_applied_search_harness_overrides()
    for source_name, overrides in (
        ("applied", applied_overrides),
        ("transient", harness_overrides or {}),
    ):
        for harness_name, spec in overrides.items():
            override_spec = dict(spec)
            override_spec.setdefault("override_source", source_name)
            registry[harness_name] = _build_derived_search_harness(
                harness_name=harness_name,
                spec=override_spec,
                registry=registry,
            )
    return registry


def list_search_harnesses(
    harness_overrides: dict[str, dict] | None = None,
) -> list[SearchHarness]:
    return sorted(
        _build_search_harness_registry(harness_overrides).values(),
        key=lambda harness: harness.name,
    )


def get_search_harness(
    name: str | None = None,
    harness_overrides: dict[str, dict] | None = None,
) -> SearchHarness:
    harness_name = name or DEFAULT_SEARCH_HARNESS_NAME
    registry = _build_search_harness_registry(harness_overrides)
    try:
        return registry[harness_name]
    except KeyError as exc:
        available = ", ".join(sorted(registry))
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
    return _hydrate_ranked_chunks(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="keyword_primary",
    )


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
    return _hydrate_ranked_chunks(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="keyword_relaxed",
    )


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
    return _hydrate_ranked_tables(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="keyword_primary",
    )


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
    return _hydrate_ranked_tables(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="keyword_relaxed",
    )


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
    return _hydrate_ranked_chunks(
        session.execute(statement).all(),
        "semantic",
        retrieval_source="semantic_primary",
    )


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
    return _hydrate_ranked_tables(
        session.execute(statement).all(),
        "semantic",
        retrieval_source="semantic_primary",
    )


def _reciprocal_rank(rank: int) -> float:
    return 1.0 / (60 + rank)


def _is_tabular_query(query: str) -> bool:
    normalized = query.lower()
    if any(token in normalized for token in ("table", "row", "column")):
        return True
    if any(op in normalized for op in (">", "<", ">=", "<=", "greater than", "less than")):
        return True
    if TABULAR_REFERENCE_PATTERN.search(normalized):
        return True
    return False


def _classify_query_intent(query: str) -> str:
    if _is_tabular_query(query):
        return QUERY_INTENT_TABULAR
    normalized = _normalize_text(query)
    if not normalized:
        return QUERY_INTENT_PROSE_LOOKUP
    salient_count = len(_salient_tokens(query))
    if (
        "?" in query
        or normalized.startswith(
            (
                "what ",
                "what is ",
                "what does ",
                "which ",
                "who ",
                "when ",
                "where ",
                "how many ",
                "how much ",
                "does ",
                "is ",
                "are ",
            )
        )
        or any(
            phrase in normalized
            for phrase in (
                "main claim",
                "due date",
                "what habitat",
                "what does table",
            )
        )
        or salient_count <= 6
    ):
        return QUERY_INTENT_PROSE_LOOKUP
    return QUERY_INTENT_PROSE_BROAD


def _looks_like_identifier_lookup(query: str) -> bool:
    normalized = _normalize_text(query)
    if not normalized:
        return False
    stripped = query.strip().lower()
    if stripped.endswith(".pdf"):
        return True
    compact = re.sub(r"\s+", "", stripped)
    has_alpha = any(char.isalpha() for char in compact)
    has_digit = any(char.isdigit() for char in compact)
    if " " not in stripped and has_alpha and has_digit and len(compact) >= 6:
        return True
    return (
        len(compact) >= 8
        and any(separator in stripped for separator in ("_", "-"))
        and len(stripped.split()) <= 3
    )


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    expanded = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", expanded)
    expanded = re.sub(r"(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])", " ", expanded)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", expanded.lower())).strip()


_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    }
)


def _salient_tokens(value: str | None) -> set[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return set()
    return {
        token
        for token in normalized.split()
        if len(token) >= 3 and token not in _QUERY_STOPWORDS
    }


def _rare_query_tokens(value: str | None) -> set[str]:
    return {token for token in _salient_tokens(value) if len(token) >= 7}


def _query_phrases(value: str | None, phrase_size: int = 2) -> set[str]:
    tokens = [token for token in _normalize_text(value).split() if token not in _QUERY_STOPWORDS]
    if len(tokens) < phrase_size:
        return set()
    return {
        " ".join(tokens[idx : idx + phrase_size])
        for idx in range(len(tokens) - phrase_size + 1)
    }


def _token_coverage(query: str | None, value: str | None) -> float:
    query_tokens = _salient_tokens(query)
    value_tokens = _salient_tokens(value)
    if not query_tokens or not value_tokens:
        return 0.0
    return len(query_tokens & value_tokens) / len(query_tokens)


def _strong_document_phrase_match(query: str | None, value: str | None) -> float:
    normalized_query = _normalize_text(query)
    normalized_value = _normalize_text(value)
    if not normalized_query or not normalized_value:
        return 0.0

    value_tokens = normalized_value.split()
    if len(value_tokens) < 2 and len(normalized_value) < 8:
        return 0.0

    if normalized_query in normalized_value:
        return 1.0
    if normalized_value in normalized_query:
        return 1.0
    return 0.0


def _document_query_overlap_features(item: RankedResult, query: str | None) -> dict[str, float]:
    return {
        "source_filename_exact_match": _strong_document_phrase_match(
            query,
            Path(item.source_filename).stem,
        ),
        "source_filename_token_coverage": _token_coverage(
            query,
            Path(item.source_filename).stem,
        ),
        "document_title_exact_match": _strong_document_phrase_match(query, item.document_title),
        "document_title_token_coverage": _token_coverage(query, item.document_title),
    }


def _prose_result_text(item: RankedResult) -> str:
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


def _prose_query_match_features(item: RankedResult, query: str | None) -> dict[str, float]:
    result_text = _normalize_text(_prose_result_text(item))
    query_phrases = _query_phrases(query)
    rare_tokens = _rare_query_tokens(query)
    heading_value = item.heading or item.table_heading
    return {
        "heading_token_coverage": _token_coverage(query, heading_value),
        "phrase_overlap": (
            sum(1 for phrase in query_phrases if phrase in result_text) / len(query_phrases)
            if query_phrases
            else 0.0
        ),
        "rare_token_overlap": (
            len(rare_tokens & set(result_text.split())) / len(rare_tokens) if rare_tokens else 0.0
        ),
        "adjacent_chunk_context_signal": float("adjacent_context" in item.retrieval_sources),
    }


def _merge_retrieval_sources(*source_groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in source_groups:
        for source in group:
            if source in seen:
                continue
            seen.add(source)
            merged.append(source)
    return tuple(merged)


def _table_title_match_features(item: RankedResult, query: str | None) -> dict[str, float]:
    if query is None or item.result_type != "table":
        return {"title_exact_match": 0.0, "title_token_coverage": 0.0}
    normalized_query = _normalize_text(query)
    title_value = " ".join(
        part for part in (item.table_title, item.table_heading) if part
    )
    normalized_title = _normalize_text(title_value)
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


def _document_cluster_strengths(
    items: list[RankedResult],
    *,
    score_getter: Callable[[RankedResult], float],
    query_intent: str,
) -> dict[UUID, float]:
    if query_intent == QUERY_INTENT_TABULAR or len(items) < 2:
        return {}

    document_counts: dict[UUID, int] = {}
    document_score_sums: dict[UUID, float] = {}
    for item in items:
        document_counts[item.document_id] = document_counts.get(item.document_id, 0) + 1
        document_score_sums[item.document_id] = (
            document_score_sums.get(item.document_id, 0.0) + score_getter(item)
        )

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
        current.retrieval_sources = _merge_retrieval_sources(
            current.retrieval_sources,
            result.retrieval_sources,
        )

    for idx, result in enumerate(semantic_results, start=1):
        current = merged.get(_result_key(result))
        if current is None:
            current = result
            merged[_result_key(result)] = current
        current.semantic_score = result.semantic_score
        current.hybrid_score = (current.hybrid_score or 0.0) + _reciprocal_rank(idx)
        current.retrieval_sources = _merge_retrieval_sources(
            current.retrieval_sources,
            result.retrieval_sources,
        )

    return list(merged.values())


def _dedupe_ranked_results(items: list[RankedResult]) -> list[RankedResult]:
    merged: dict[tuple[str, UUID], RankedResult] = {}

    for item in items:
        key = _result_key(item)
        current = merged.get(key)
        if current is None:
            merged[key] = item
            continue
        if item.keyword_score is not None:
            current.keyword_score = max(current.keyword_score or 0.0, item.keyword_score)
        if item.semantic_score is not None:
            current.semantic_score = max(current.semantic_score or 0.0, item.semantic_score)
        if item.hybrid_score is not None:
            current.hybrid_score = max(current.hybrid_score or 0.0, item.hybrid_score)
        current.retrieval_sources = _merge_retrieval_sources(
            current.retrieval_sources,
            item.retrieval_sources,
        )
    return list(merged.values())


def _strongest_ranked_score(item: RankedResult) -> float:
    return max(
        item.keyword_score or 0.0,
        item.semantic_score or 0.0,
        item.hybrid_score or 0.0,
    )


def _sort_ranked_candidates_by_score(
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


def _ranked_metadata_overlap_score(
    query: str,
    *,
    document_title: str | None,
    heading: str | None,
    chunk_text: str | None,
    source_filename: str,
    include_document_context: bool = True,
) -> float:
    title_overlap = _token_coverage(query, document_title) if include_document_context else 0.0
    heading_overlap = _token_coverage(query, heading)
    chunk_overlap = _token_coverage(query, chunk_text)
    filename_overlap = (
        _token_coverage(query, Path(source_filename).stem) if include_document_context else 0.0
    )
    return max(title_overlap, heading_overlap, chunk_overlap, filename_overlap) + (
        0.2 * title_overlap
        + 0.15 * heading_overlap
        + 0.25 * chunk_overlap
        + 0.15 * filename_overlap
    )


def _run_prose_metadata_chunk_search(
    session: Session,
    request: SearchRequest,
    *,
    run_id: UUID | None = None,
    candidate_limit: int = PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT,
) -> list[RankedResult]:
    tokens = sorted(_salient_tokens(request.query))
    if not tokens:
        return []

    conditions = []
    for token in tokens:
        pattern = f"%{token}%"
        conditions.extend(
            [
                Document.title.ilike(pattern),
                DocumentChunk.heading.ilike(pattern),
                Document.source_filename.ilike(pattern),
            ]
        )

    statement = (
        _apply_chunk_filters(_chunk_query(run_id), request.filters)
        .where(or_(*conditions))
        .order_by(DocumentChunk.chunk_index.asc())
        .limit(max(candidate_limit * 20, METADATA_SUPPLEMENT_SCAN_LIMIT))
    )
    rows = session.execute(statement).all()
    candidates: list[RankedResult] = []
    include_document_context = request.filters is None or request.filters.document_id is None
    for chunk, document in rows:
        score = _ranked_metadata_overlap_score(
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
            -_strongest_ranked_score(item),
            item.page_from if item.page_from is not None else 10**9,
            str(item.result_id),
        )
    )
    return _dedupe_ranked_results(candidates)[:candidate_limit]


def _should_run_metadata_supplement(
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
    return strict_keyword_count == 0 and _looks_like_identifier_lookup(query)


def _expand_adjacent_chunk_context(
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
            -_strongest_ranked_score(item),
            item.page_from if item.page_from is not None else 10**9,
            str(item.result_id),
        )
    )

    for seed in chunk_seeds[:PROSE_ADJACENT_SEED_LIMIT]:
        if seed.result_type != "chunk" or seed.chunk_index is None:
            continue
        chunk_statement = _apply_chunk_filters(_chunk_query(run_id), request.filters).where(
            DocumentChunk.document_id == seed.document_id,
            DocumentChunk.run_id == seed.run_id,
            DocumentChunk.chunk_index.in_(
                (max(seed.chunk_index - 1, -1), seed.chunk_index + 1)
            ),
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
                    keyword_score=_strongest_ranked_score(seed) * 0.85,
                    retrieval_sources=("adjacent_context",),
                )
            )
            if len(expanded) >= expansion_limit:
                return expanded
    return expanded


def _candidate_source_breakdown(items: list[RankedResult]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        for source in item.retrieval_sources:
            counter[source] += 1
    return dict(sorted(counter.items()))


def _rerank_results(
    items: list[RankedResult],
    *,
    request: SearchRequest,
    score_getter: Callable[[RankedResult], float],
    tabular_query: bool,
    query_intent: str,
    reranker: SearchReranker | None = None,
) -> list[RerankedResult]:
    active_reranker = reranker or get_default_reranker()
    return active_reranker.rerank(
        items,
        request=request,
        score_getter=score_getter,
        tabular_query=tabular_query,
        query_intent=query_intent,
    )


def _sort_ranked_results(
    items: list[RankedResult],
    *,
    score_getter,
    filters: SearchFilters | None,
    tabular_query: bool,
    query_intent: str,
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
        query_intent=query_intent,
        reranker=reranker,
    )
    return [_to_search_result(candidate.item, candidate.score) for candidate in reranked]


def _merge_hybrid_results(
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
    limit: int,
    filters: SearchFilters | None,
    tabular_query: bool,
    query_intent: str = QUERY_INTENT_PROSE_LOOKUP,
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
        query_intent=query_intent,
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
    harness_overrides: dict[str, dict] | None = None,
) -> SearchExecution:
    start = perf_counter()
    harness = get_search_harness(request.harness_name, harness_overrides)
    active_reranker = reranker or harness.build_reranker()
    tabular_query = _is_tabular_query(request.query)
    query_intent = _classify_query_intent(request.query)
    prose_v3_query = harness.name == "prose_v3" and query_intent in {
        QUERY_INTENT_PROSE_LOOKUP,
        QUERY_INTENT_PROSE_BROAD,
    }
    keyword_candidate_limit = max(
        request.limit * harness.retrieval_profile.keyword_candidate_multiplier,
        harness.retrieval_profile.min_candidate_limit,
    )

    if run_id is None:
        keyword_chunk_results = _run_keyword_chunk_search(
            session, request, candidate_limit=keyword_candidate_limit
        )
        keyword_table_results = _run_keyword_table_search(
            session, request, candidate_limit=keyword_candidate_limit
        )
    else:
        keyword_chunk_results = _run_keyword_chunk_search(
            session,
            request,
            candidate_limit=keyword_candidate_limit,
            run_id=run_id,
        )
        keyword_table_results = _run_keyword_table_search(
            session,
            request,
            candidate_limit=keyword_candidate_limit,
            run_id=run_id,
        )
    keyword_results = [*keyword_chunk_results, *keyword_table_results]
    keyword_results = _sort_ranked_candidates_by_score(
        keyword_results, score_getter=_keyword_score
    )

    keyword_strategy = "strict"
    strict_keyword_count = len(keyword_results)
    if strict_keyword_count == 0:
        if run_id is None:
            keyword_chunk_results = _run_relaxed_keyword_chunk_search(
                session, request, candidate_limit=keyword_candidate_limit
            )
            keyword_table_results = _run_relaxed_keyword_table_search(
                session, request, candidate_limit=keyword_candidate_limit
            )
        else:
            keyword_chunk_results = _run_relaxed_keyword_chunk_search(
                session,
                request,
                candidate_limit=keyword_candidate_limit,
                run_id=run_id,
            )
            keyword_table_results = _run_relaxed_keyword_table_search(
                session,
                request,
                candidate_limit=keyword_candidate_limit,
                run_id=run_id,
            )
        keyword_results = [*keyword_chunk_results, *keyword_table_results]
        if keyword_results:
            keyword_results = _sort_ranked_candidates_by_score(
                keyword_results, score_getter=_keyword_score
            )
            keyword_strategy = "relaxed_or"

    metadata_candidates: list[RankedResult] = []
    metadata_supplement_enabled = hasattr(session, "execute") and _should_run_metadata_supplement(
        query=request.query,
        query_intent=query_intent,
        strict_keyword_count=strict_keyword_count,
        harness_name=harness.name,
    )
    zero_result_metadata_fallback = metadata_supplement_enabled and not keyword_results
    if metadata_supplement_enabled:
        metadata_candidates = _run_prose_metadata_chunk_search(
            session,
            request,
            run_id=run_id,
        )
        keyword_results = _dedupe_ranked_results([*keyword_results, *metadata_candidates])
        keyword_results = _sort_ranked_candidates_by_score(
            keyword_results, score_getter=_keyword_score
        )
        if metadata_candidates:
            if zero_result_metadata_fallback:
                keyword_strategy = "metadata_supplement"
            elif keyword_strategy == "strict":
                keyword_strategy = "strict_plus_metadata"
            elif keyword_strategy == "relaxed_or":
                keyword_strategy = "relaxed_or_plus_metadata"

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
    adjacent_candidates: list[RankedResult] = []
    table_evidence_query = (
        request.filters is not None
        and request.filters.document_id is not None
        and bool(keyword_table_results)
        and not keyword_chunk_results
    )
    effective_tabular_query = tabular_query or table_evidence_query

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
    semantic_results = _sort_ranked_candidates_by_score(
        semantic_results, score_getter=_semantic_score
    )

    if prose_v3_query:
        adjacent_seed_candidates = _dedupe_ranked_results(
            [*keyword_results, *semantic_results, *metadata_candidates]
        )
        adjacent_candidates = _expand_adjacent_chunk_context(
            session,
            request,
            seed_candidates=adjacent_seed_candidates,
            run_id=run_id,
        )
        if adjacent_candidates:
            keyword_results = _dedupe_ranked_results([*keyword_results, *adjacent_candidates])
            keyword_results = _sort_ranked_candidates_by_score(
                keyword_results, score_getter=_keyword_score
            )

    semantic_augmented_with_keyword_context = False
    if request.mode == "semantic" and embedding_status == "completed":
        if prose_v3_query:
            candidate_items = _merge_hybrid_candidates(keyword_results, semantic_results)
            score_getter = _hybrid_score
            semantic_augmented_with_keyword_context = True
        else:
            candidate_items = semantic_results
            score_getter = _semantic_score
        served_mode = "semantic"
    elif request.mode == "hybrid" and embedding_status == "completed":
        candidate_items = _merge_hybrid_candidates(keyword_results, semantic_results)
        score_getter = _hybrid_score
        served_mode = "hybrid"
    elif request.mode == "keyword":
        candidate_items = _dedupe_ranked_results(keyword_results)

    details = {
        **keyword_details,
        "semantic_candidate_count": len(semantic_results),
        "query_intent": query_intent,
        "candidate_source_breakdown": _candidate_source_breakdown(candidate_items),
        "metadata_candidate_count": sum(
            1 for item in candidate_items if "metadata_supplement" in item.retrieval_sources
        ),
        "context_expansion_count": sum(
            1 for item in candidate_items if "adjacent_context" in item.retrieval_sources
        ),
        "requested_mode": request.mode,
        "served_mode": served_mode,
        "harness_name": harness.name,
        "reranker_name": harness.reranker_name,
        "reranker_version": harness.reranker_version,
        "retrieval_profile_name": harness.retrieval_profile_name,
    }
    if semantic_augmented_with_keyword_context:
        details["semantic_augmented_with_keyword_context"] = True
    if fallback_reason is not None:
        details["fallback_reason"] = fallback_reason

    reranked_results = _rerank_results(
        candidate_items,
        request=request,
        score_getter=score_getter,
        tabular_query=effective_tabular_query,
        query_intent=query_intent,
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
