from __future__ import annotations

import re
import uuid
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from time import perf_counter
from typing import Protocol
from uuid import UUID

from sqlalchemy import Float, Select, and_, cast, false, func, or_, select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentTable,
    RetrievalEvidenceSpan,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
)
from app.schemas.search import (
    SearchEvidenceSpan,
    SearchFilters,
    SearchRequest,
    SearchResult,
    SearchScores,
)
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.evidence import record_knowledge_operator_run
from app.services.search_harness_overrides import load_applied_search_harness_overrides
from app.services.search_plan import (
    SearchCandidateStrategy,
    SearchStage,
    build_search_execution_plan,
)
from app.services.telemetry import observe_search_results

DEFAULT_SEARCH_HARNESS_NAME = "default_v1"
QUERY_INTENT_TABULAR = "tabular"
QUERY_INTENT_PROSE_LOOKUP = "prose_lookup"
QUERY_INTENT_PROSE_BROAD = "prose_broad"
PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT = 12
PROSE_ADJACENT_EXPANSION_LIMIT = 12
PROSE_ADJACENT_SEED_LIMIT = 6
SEARCH_RESULT_SPAN_LIMIT = 5
TABULAR_REFERENCE_PATTERN = re.compile(r"\b\d+(?:\.\d+)+(?:\s*\(\s*\d+\s*\))?\b")


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
    evidence_operator_run_ids: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class QueryFeatureSet:
    normalized_query: str
    normalized_tokens: frozenset[str]
    salient_tokens: frozenset[str]
    rare_tokens: frozenset[str]
    phrases: frozenset[str]


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
        query_features: QueryFeatureSet | None = None,
    ) -> list[RerankedResult]: ...


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

METADATA_SUPPLEMENT_DIRECT_CHUNK_MULTIPLIER = 4
METADATA_SUPPLEMENT_DOCUMENT_LIMIT = 8
METADATA_SUPPLEMENT_DOCUMENT_CHUNK_MULTIPLIER = 6
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
        query_features: QueryFeatureSet | None = None,
    ) -> list[RerankedResult]:
        active_query_features = query_features or _build_query_feature_set(request.query)
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
            title_match_features = _table_title_match_features(item, active_query_features)
            document_overlap_features = _document_query_overlap_features(
                item,
                active_query_features,
            )
            prose_match_features = _prose_query_match_features(item, active_query_features)
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
                        "heading_token_coverage": prose_match_features["heading_token_coverage"],
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


def _document_query(run_id: UUID | None = None) -> Select:
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


def _apply_document_filters(statement: Select, filters: SearchFilters | None) -> Select:
    if filters is None:
        return statement
    if filters.result_type == "table":
        return statement.where(false())
    if filters.document_id is not None:
        statement = statement.where(Document.id == filters.document_id)
    return statement


def _apply_span_filters(statement: Select, filters: SearchFilters | None) -> Select:
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
    score: float,
) -> RankedEvidenceSpan:
    return RankedEvidenceSpan(
        retrieval_evidence_span_id=span.id,
        source_type=span.source_type,
        source_id=span.source_id,
        span_index=span.span_index,
        score_kind=score_kind,
        score=float(score),
        page_from=span.page_from,
        page_to=span.page_to,
        text_excerpt=span.span_text,
        content_sha256=span.content_sha256,
        source_snapshot_sha256=span.source_snapshot_sha256,
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


def _keyword_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9]+", query.lower()):
        if len(token) <= 1 or token in seen:
            continue
        seen.add(token)
        terms.append(token)
    return terms


def _supports_retrieval_span_search(session: Session | None) -> bool:
    return isinstance(session, Session)


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


def _run_keyword_span_chunk_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
    relaxed: bool = False,
) -> list[RankedResult]:
    if not _supports_retrieval_span_search(session):
        return []
    tsquery = (
        _build_relaxed_tsquery(request.query)
        if relaxed
        else func.plainto_tsquery("english", request.query)
    )
    if tsquery is None:
        return []
    rank = cast(func.ts_rank_cd(RetrievalEvidenceSpan.textsearch, tsquery), Float)
    statement = (
        _apply_span_filters(_span_chunk_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(RetrievalEvidenceSpan.textsearch.op("@@")(tsquery))
        .order_by(
            rank.desc(), DocumentChunk.chunk_index.asc(), RetrievalEvidenceSpan.span_index.asc()
        )
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_span_chunks(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="span_keyword_relaxed" if relaxed else "span_keyword",
    )


def _run_keyword_span_table_search(
    session: Session,
    request: SearchRequest,
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
    relaxed: bool = False,
) -> list[RankedResult]:
    if not _supports_retrieval_span_search(session):
        return []
    tsquery = (
        _build_relaxed_tsquery(request.query)
        if relaxed
        else func.plainto_tsquery("english", request.query)
    )
    if tsquery is None:
        return []
    rank = cast(func.ts_rank_cd(RetrievalEvidenceSpan.textsearch, tsquery), Float)
    statement = (
        _apply_span_filters(_span_table_query(run_id), request.filters)
        .add_columns(rank.label("score"))
        .where(RetrievalEvidenceSpan.textsearch.op("@@")(tsquery))
        .order_by(
            rank.desc(), DocumentTable.table_index.asc(), RetrievalEvidenceSpan.span_index.asc()
        )
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_span_tables(
        session.execute(statement).all(),
        "keyword",
        retrieval_source="span_keyword_relaxed" if relaxed else "span_keyword",
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


def _run_semantic_span_chunk_search(
    session: Session,
    request: SearchRequest,
    query_embedding: list[float],
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    if not _supports_retrieval_span_search(session):
        return []
    distance = RetrievalEvidenceSpan.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        _apply_span_filters(_span_chunk_query(run_id), request.filters)
        .add_columns(similarity.label("score"))
        .where(RetrievalEvidenceSpan.embedding.is_not(None))
        .order_by(
            distance.asc(), DocumentChunk.chunk_index.asc(), RetrievalEvidenceSpan.span_index.asc()
        )
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_span_chunks(
        session.execute(statement).all(),
        "semantic",
        retrieval_source="span_semantic",
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


def _run_semantic_span_table_search(
    session: Session,
    request: SearchRequest,
    query_embedding: list[float],
    candidate_limit: int | None = None,
    *,
    run_id: UUID | None = None,
) -> list[RankedResult]:
    if not _supports_retrieval_span_search(session):
        return []
    distance = RetrievalEvidenceSpan.embedding.cosine_distance(query_embedding)
    similarity = cast(1 - distance, Float)
    statement = (
        _apply_span_filters(_span_table_query(run_id), request.filters)
        .add_columns(similarity.label("score"))
        .where(RetrievalEvidenceSpan.embedding.is_not(None))
        .order_by(
            distance.asc(), DocumentTable.table_index.asc(), RetrievalEvidenceSpan.span_index.asc()
        )
        .limit(candidate_limit or request.limit)
    )
    return _hydrate_ranked_span_tables(
        session.execute(statement).all(),
        "semantic",
        retrieval_source="span_semantic",
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


is_tabular_query = _is_tabular_query


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
    return _salient_tokens_from_normalized(_normalize_text(value))


def _salient_tokens_from_normalized(normalized: str) -> set[str]:
    if not normalized:
        return set()
    return {
        token for token in normalized.split() if len(token) >= 3 and token not in _QUERY_STOPWORDS
    }


def _phrase_tokens_from_normalized(normalized: str) -> list[str]:
    return [token for token in normalized.split() if token not in _QUERY_STOPWORDS]


def _query_phrases_from_normalized(normalized: str, phrase_size: int = 2) -> set[str]:
    tokens = _phrase_tokens_from_normalized(normalized)
    if len(tokens) < phrase_size:
        return set()
    return {
        " ".join(tokens[idx : idx + phrase_size]) for idx in range(len(tokens) - phrase_size + 1)
    }


def _build_query_feature_set(query: str | None) -> QueryFeatureSet:
    normalized_query = _normalize_text(query)
    normalized_tokens = frozenset(normalized_query.split()) if normalized_query else frozenset()
    salient_tokens = frozenset(_salient_tokens_from_normalized(normalized_query))
    return QueryFeatureSet(
        normalized_query=normalized_query,
        normalized_tokens=normalized_tokens,
        salient_tokens=salient_tokens,
        rare_tokens=frozenset(token for token in salient_tokens if len(token) >= 7),
        phrases=frozenset(_query_phrases_from_normalized(normalized_query)),
    )


def _coerce_query_feature_set(
    query_or_features: QueryFeatureSet | str | None,
) -> QueryFeatureSet:
    if isinstance(query_or_features, QueryFeatureSet):
        return query_or_features
    return _build_query_feature_set(query_or_features)


def _token_coverage(query_or_features: QueryFeatureSet | str | None, value: str | None) -> float:
    query_tokens = _coerce_query_feature_set(query_or_features).salient_tokens
    value_tokens = _salient_tokens(value)
    if not query_tokens or not value_tokens:
        return 0.0
    return len(query_tokens & value_tokens) / len(query_tokens)


def _strong_document_phrase_match(
    query_or_features: QueryFeatureSet | str | None,
    value: str | None,
) -> float:
    normalized_query = _coerce_query_feature_set(query_or_features).normalized_query
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


def _document_query_overlap_features(
    item: RankedResult,
    query_or_features: QueryFeatureSet | str | None,
) -> dict[str, float]:
    return {
        "source_filename_exact_match": _strong_document_phrase_match(
            query_or_features,
            Path(item.source_filename).stem,
        ),
        "source_filename_token_coverage": _token_coverage(
            query_or_features,
            Path(item.source_filename).stem,
        ),
        "document_title_exact_match": _strong_document_phrase_match(
            query_or_features,
            item.document_title,
        ),
        "document_title_token_coverage": _token_coverage(
            query_or_features,
            item.document_title,
        ),
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


def _prose_query_match_features(
    item: RankedResult,
    query_or_features: QueryFeatureSet | str | None,
) -> dict[str, float]:
    query_features = _coerce_query_feature_set(query_or_features)
    result_text = _normalize_text(_prose_result_text(item))
    result_tokens = set(result_text.split())
    heading_value = item.heading or item.table_heading
    return {
        "heading_token_coverage": _token_coverage(query_features, heading_value),
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


def _merge_evidence_spans(
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


def _table_title_match_features(
    item: RankedResult,
    query_or_features: QueryFeatureSet | str | None,
) -> dict[str, float]:
    if query_or_features is None or item.result_type != "table":
        return {"title_exact_match": 0.0, "title_token_coverage": 0.0}
    query_features = _coerce_query_feature_set(query_or_features)
    normalized_query = query_features.normalized_query
    title_value = " ".join(part for part in (item.table_title, item.table_heading) if part)
    normalized_title = _normalize_text(title_value)
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
        document_score_sums[item.document_id] = document_score_sums.get(
            item.document_id, 0.0
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
            )
            for span in item.evidence_spans
        ],
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
        current.evidence_spans = _merge_evidence_spans(
            current.evidence_spans,
            result.evidence_spans,
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
        current.evidence_spans = _merge_evidence_spans(
            current.evidence_spans,
            result.evidence_spans,
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
        current.evidence_spans = _merge_evidence_spans(
            current.evidence_spans,
            item.evidence_spans,
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


def _metadata_query_tokens(value: str | None) -> list[str]:
    normalized = _normalize_text(value)
    return sorted(set(_phrase_tokens_from_normalized(normalized)))


def _metadata_tsquery(config: str, tokens: list[str]):
    if not tokens:
        return None
    return func.to_tsquery(config, " | ".join(tokens))


def _run_prose_metadata_chunk_search(
    session: Session,
    request: SearchRequest,
    *,
    run_id: UUID | None = None,
    candidate_limit: int = PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT,
) -> list[RankedResult]:
    metadata_tokens = _metadata_query_tokens(request.query)
    content_tokens = sorted(_salient_tokens(request.query))
    document_tsquery = _metadata_tsquery("simple", metadata_tokens)
    content_tsquery = _metadata_tsquery("english", content_tokens)
    if document_tsquery is None and content_tsquery is None:
        return []

    chunk_rows: list[tuple[DocumentChunk, Document]] = []
    if content_tsquery is not None:
        chunk_rank = func.ts_rank_cd(DocumentChunk.textsearch, content_tsquery)
        chunk_statement = (
            _apply_chunk_filters(_chunk_query(run_id), request.filters)
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
            _apply_document_filters(_document_query(run_id), request.filters)
            .where(or_(*document_conditions))
            .order_by(document_rank.desc(), Document.id.asc())
            .limit(max(candidate_limit * 2, METADATA_SUPPLEMENT_DOCUMENT_LIMIT))
        )
        document_rows = session.execute(document_statement).scalars().all()

    if document_rows:
        document_ids = [document.id for document in document_rows]
        hydration_statement = _apply_chunk_filters(_chunk_query(run_id), request.filters).where(
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
    query_features = _build_query_feature_set(request.query)
    return active_reranker.rerank(
        items,
        request=request,
        score_getter=score_getter,
        tabular_query=tabular_query,
        query_intent=query_intent,
        query_features=query_features,
    )


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


def _unique_uuid(values: Iterable[UUID]) -> UUID | None:
    unique_values = {value for value in values if value is not None}
    return next(iter(unique_values)) if len(unique_values) == 1 else None


def _ranked_result_evidence_payload(item: RankedResult, index: int) -> dict:
    return {
        "candidate_index": index,
        "result_type": item.result_type,
        "result_id": str(item.result_id),
        "document_id": str(item.document_id),
        "run_id": str(item.run_id),
        "source_filename": item.source_filename,
        "page_from": item.page_from,
        "page_to": item.page_to,
        "keyword_score": item.keyword_score,
        "semantic_score": item.semantic_score,
        "hybrid_score": item.hybrid_score,
        "retrieval_sources": list(item.retrieval_sources),
        "evidence_spans": [
            {
                "retrieval_evidence_span_id": str(span.retrieval_evidence_span_id),
                "source_type": span.source_type,
                "source_id": str(span.source_id),
                "span_index": span.span_index,
                "score_kind": span.score_kind,
                "score": span.score,
                "page_from": span.page_from,
                "page_to": span.page_to,
                "text_excerpt": span.text_excerpt,
                "content_sha256": span.content_sha256,
                "source_snapshot_sha256": span.source_snapshot_sha256,
            }
            for span in item.evidence_spans
        ],
        "label": _result_label(item),
    }


def _reranked_result_evidence_payload(
    candidate: RerankedResult,
    result_row: SearchRequestResult,
) -> dict:
    return {
        "search_request_result_id": str(result_row.id),
        "rank": candidate.rank,
        "base_rank": candidate.base_rank,
        "score": candidate.score,
        "result_type": candidate.item.result_type,
        "result_id": str(candidate.item.result_id),
        "document_id": str(candidate.item.document_id),
        "run_id": str(candidate.item.run_id),
        "page_from": candidate.item.page_from,
        "page_to": candidate.item.page_to,
        "source_filename": candidate.item.source_filename,
        "label": _result_label(candidate.item),
        "preview_text": _result_preview(candidate.item),
        "evidence_spans": [
            {
                "retrieval_evidence_span_id": str(span.retrieval_evidence_span_id),
                "source_type": span.source_type,
                "source_id": str(span.source_id),
                "span_index": span.span_index,
                "score_kind": span.score_kind,
                "score": span.score,
                "page_from": span.page_from,
                "page_to": span.page_to,
                "text_excerpt": span.text_excerpt,
                "content_sha256": span.content_sha256,
                "source_snapshot_sha256": span.source_snapshot_sha256,
            }
            for span in candidate.item.evidence_spans
        ],
        "features": candidate.features,
    }


def _persist_search_operator_runs(
    session: Session,
    *,
    search_request: SearchRequestRecord,
    request: SearchRequest,
    candidate_items: list[RankedResult],
    reranked_results: list[RerankedResult],
    result_rows: list[SearchRequestResult],
    details: dict,
    harness_config: dict,
    reranker_name: str,
    reranker_version: str,
    retrieval_profile_name: str,
    duration_ms: float,
) -> list[UUID]:
    candidate_payloads = [
        _ranked_result_evidence_payload(item, index)
        for index, item in enumerate(candidate_items, start=1)
    ]
    result_payloads = [
        _reranked_result_evidence_payload(candidate, result_row)
        for candidate, result_row in zip(reranked_results, result_rows, strict=True)
    ]
    document_id = _unique_uuid(item.document_id for item in candidate_items)
    run_id = _unique_uuid(item.run_id for item in candidate_items)
    request_payload = {
        "query": request.query,
        "mode": request.mode,
        "filters": (
            request.filters.model_dump(mode="json", exclude_none=True) if request.filters else {}
        ),
        "limit": request.limit,
        "harness_name": search_request.harness_name,
    }
    operator_run_ids: list[UUID] = []
    retrieve_run = record_knowledge_operator_run(
        session,
        operator_kind="retrieve",
        operator_name="search_candidate_generation",
        operator_version=retrieval_profile_name,
        document_id=document_id,
        run_id=run_id,
        search_request_id=search_request.id,
        config={
            "harness_name": search_request.harness_name,
            "retrieval_profile": harness_config.get("retrieval_profile", {}),
            "execution_details": {
                key: details.get(key)
                for key in (
                    "keyword_strategy",
                    "requested_mode",
                    "served_mode",
                    "query_intent",
                    "fallback_reason",
                )
                if key in details
            },
        },
        input_payload=request_payload,
        output_payload={"candidates": candidate_payloads},
        metrics={
            "candidate_count": len(candidate_payloads),
            "keyword_candidate_count": details.get("keyword_candidate_count", 0),
            "semantic_candidate_count": details.get("semantic_candidate_count", 0),
            "metadata_candidate_count": details.get("metadata_candidate_count", 0),
            "span_candidate_count": details.get("span_candidate_count", 0),
            "context_expansion_count": details.get("context_expansion_count", 0),
        },
        metadata={
            "candidate_source_breakdown": details.get("candidate_source_breakdown", {}),
            "search_request_id": str(search_request.id),
        },
        inputs=[
            {
                "input_kind": "search_request",
                "source_table": "search_requests",
                "source_id": search_request.id,
                "payload": request_payload,
            }
        ],
        outputs=[
            {
                "output_kind": "candidate_set",
                "payload": {
                    "candidate_count": len(candidate_payloads),
                    "candidates": candidate_payloads,
                },
            }
        ],
        duration_ms=duration_ms,
    )
    if retrieve_run is not None:
        operator_run_ids.append(retrieve_run.id)

    rerank_run = record_knowledge_operator_run(
        session,
        operator_kind="rerank",
        operator_name=reranker_name,
        operator_version=reranker_version,
        parent_operator_run_id=getattr(retrieve_run, "id", None),
        document_id=document_id,
        run_id=run_id,
        search_request_id=search_request.id,
        config=harness_config.get("reranker", {}),
        input_payload={"candidates": candidate_payloads},
        output_payload={"ranked_results": result_payloads},
        metrics={
            "candidate_count": len(candidate_payloads),
            "result_count": len(result_payloads),
            "table_hit_count": search_request.table_hit_count,
        },
        metadata={
            "harness_name": search_request.harness_name,
            "retrieval_profile_name": retrieval_profile_name,
        },
        inputs=[
            {
                "input_kind": "candidate_set",
                "source_table": "knowledge_operator_runs",
                "source_id": getattr(retrieve_run, "id", None),
                "payload": {
                    "candidate_count": len(candidate_payloads),
                },
            }
        ],
        outputs=[
            {
                "output_kind": "ranked_result",
                "target_table": "search_request_results",
                "target_id": result_row.id,
                "payload": payload,
            }
            for payload, result_row in zip(result_payloads, result_rows, strict=True)
        ],
        duration_ms=duration_ms,
    )
    if rerank_run is not None:
        operator_run_ids.append(rerank_run.id)

    judge_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="deterministic_evidence_selection",
        operator_version="v1",
        parent_operator_run_id=getattr(rerank_run, "id", None),
        document_id=document_id,
        run_id=run_id,
        search_request_id=search_request.id,
        config={
            "selection_policy": "top_k_after_rerank",
            "limit": request.limit,
            "harness_name": search_request.harness_name,
        },
        input_payload={"ranked_results": result_payloads},
        output_payload={"selected_results": result_payloads},
        metrics={
            "selected_result_count": len(result_payloads),
            "table_hit_count": search_request.table_hit_count,
        },
        metadata={
            "audit_role": "records which ranked evidence was selected for downstream use",
        },
        inputs=[
            {
                "input_kind": "ranked_results",
                "source_table": "knowledge_operator_runs",
                "source_id": getattr(rerank_run, "id", None),
                "payload": {"result_count": len(result_payloads)},
            }
        ],
        outputs=[
            {
                "output_kind": "selected_evidence",
                "target_table": "search_request_results",
                "target_id": result_row.id,
                "payload": payload,
            }
            for payload, result_row in zip(result_payloads, result_rows, strict=True)
        ],
        duration_ms=duration_ms,
    )
    if judge_run is not None:
        operator_run_ids.append(judge_run.id)
    return operator_run_ids


def _persist_search_result_spans(
    session: Session,
    *,
    search_request_id: UUID,
    reranked_results: list[RerankedResult],
    result_rows: list[SearchRequestResult],
    created_at,
) -> None:
    for candidate, result_row in zip(reranked_results, result_rows, strict=True):
        for span_rank, span in enumerate(
            candidate.item.evidence_spans[:SEARCH_RESULT_SPAN_LIMIT],
            start=1,
        ):
            session.add(
                SearchRequestResultSpan(
                    id=uuid.uuid4(),
                    search_request_id=search_request_id,
                    search_request_result_id=result_row.id,
                    retrieval_evidence_span_id=span.retrieval_evidence_span_id,
                    span_rank=span_rank,
                    score_kind=span.score_kind,
                    score=span.score,
                    source_type=span.source_type,
                    source_id=span.source_id,
                    span_index=span.span_index,
                    page_from=span.page_from,
                    page_to=span.page_to,
                    text_excerpt=span.text_excerpt,
                    content_sha256=span.content_sha256,
                    source_snapshot_sha256=span.source_snapshot_sha256,
                    metadata_json={
                        "retrieval_source_count": len(candidate.item.retrieval_sources),
                        "retrieval_sources": list(candidate.item.retrieval_sources),
                    },
                    created_at=created_at,
                )
            )
    session.flush()


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
    candidate_items: list[RankedResult],
    reranked_results: list[RerankedResult],
) -> tuple[UUID | None, list[UUID]]:
    if session is None or not hasattr(session, "add"):
        return None, []

    created_at = utcnow()
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

    result_rows: list[SearchRequestResult] = []
    for candidate in reranked_results:
        item = candidate.item
        result_row = SearchRequestResult(
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
        result_rows.append(result_row)
        session.add(result_row)

    session.flush()
    _persist_search_result_spans(
        session,
        search_request_id=search_request.id,
        reranked_results=reranked_results,
        result_rows=result_rows,
        created_at=created_at,
    )
    operator_run_ids = _persist_search_operator_runs(
        session,
        search_request=search_request,
        request=request,
        candidate_items=candidate_items,
        reranked_results=reranked_results,
        result_rows=result_rows,
        details=details,
        harness_config=harness_config,
        reranker_name=reranker_name,
        reranker_version=reranker_version,
        retrieval_profile_name=retrieval_profile_name,
        duration_ms=duration_ms,
    )
    return search_request.id, operator_run_ids


def _load_keyword_candidates(
    session: Session,
    request: SearchRequest,
    *,
    candidate_limit: int,
    run_id: UUID | None,
    relaxed: bool = False,
) -> tuple[list[RankedResult], list[RankedResult]]:
    if relaxed:
        chunk_loader = _run_relaxed_keyword_chunk_search
        table_loader = _run_relaxed_keyword_table_search
    else:
        chunk_loader = _run_keyword_chunk_search
        table_loader = _run_keyword_table_search

    if run_id is None:
        chunk_results = chunk_loader(session, request, candidate_limit=candidate_limit)
        table_results = table_loader(session, request, candidate_limit=candidate_limit)
        span_chunk_results = _run_keyword_span_chunk_search(
            session,
            request,
            candidate_limit=candidate_limit,
            relaxed=relaxed,
        )
        span_table_results = _run_keyword_span_table_search(
            session,
            request,
            candidate_limit=candidate_limit,
            relaxed=relaxed,
        )
    else:
        chunk_results = chunk_loader(
            session,
            request,
            candidate_limit=candidate_limit,
            run_id=run_id,
        )
        table_results = table_loader(
            session,
            request,
            candidate_limit=candidate_limit,
            run_id=run_id,
        )
        span_chunk_results = _run_keyword_span_chunk_search(
            session,
            request,
            candidate_limit=candidate_limit,
            run_id=run_id,
            relaxed=relaxed,
        )
        span_table_results = _run_keyword_span_table_search(
            session,
            request,
            candidate_limit=candidate_limit,
            run_id=run_id,
            relaxed=relaxed,
        )
    return (
        _dedupe_ranked_results([*chunk_results, *span_chunk_results]),
        _dedupe_ranked_results([*table_results, *span_table_results]),
    )


def _load_semantic_candidates(
    session: Session,
    request: SearchRequest,
    *,
    query_embedding: list[float],
    candidate_limit: int,
    run_id: UUID | None,
) -> list[RankedResult]:
    if run_id is None:
        semantic_results = _run_semantic_chunk_search(
            session,
            request,
            query_embedding,
            candidate_limit=candidate_limit,
        )
        semantic_results.extend(
            _run_semantic_table_search(
                session,
                request,
                query_embedding,
                candidate_limit=candidate_limit,
            )
        )
        semantic_results.extend(
            _run_semantic_span_chunk_search(
                session,
                request,
                query_embedding,
                candidate_limit=candidate_limit,
            )
        )
        semantic_results.extend(
            _run_semantic_span_table_search(
                session,
                request,
                query_embedding,
                candidate_limit=candidate_limit,
            )
        )
    else:
        semantic_results = _run_semantic_chunk_search(
            session,
            request,
            query_embedding,
            candidate_limit=candidate_limit,
            run_id=run_id,
        )
        semantic_results.extend(
            _run_semantic_table_search(
                session,
                request,
                query_embedding,
                candidate_limit=candidate_limit,
                run_id=run_id,
            )
        )
        semantic_results.extend(
            _run_semantic_span_chunk_search(
                session,
                request,
                query_embedding,
                candidate_limit=candidate_limit,
                run_id=run_id,
            )
        )
        semantic_results.extend(
            _run_semantic_span_table_search(
                session,
                request,
                query_embedding,
                candidate_limit=candidate_limit,
                run_id=run_id,
            )
        )
    semantic_results = _dedupe_ranked_results(semantic_results)
    return _sort_ranked_candidates_by_score(semantic_results, score_getter=_semantic_score)


def _apply_metadata_supplement_stage(
    session: Session,
    request: SearchRequest,
    *,
    query_intent: str,
    strict_keyword_count: int,
    harness_name: str,
    keyword_results: list[RankedResult],
    keyword_strategy: str,
    run_id: UUID | None,
) -> tuple[list[RankedResult], list[RankedResult], str]:
    metadata_enabled = hasattr(session, "execute") and _should_run_metadata_supplement(
        query=request.query,
        query_intent=query_intent,
        strict_keyword_count=strict_keyword_count,
        harness_name=harness_name,
    )
    if not metadata_enabled:
        return keyword_results, [], keyword_strategy

    metadata_candidates = _run_prose_metadata_chunk_search(
        session,
        request,
        run_id=run_id,
    )
    if not metadata_candidates:
        return keyword_results, [], keyword_strategy

    merged_results = _dedupe_ranked_results([*keyword_results, *metadata_candidates])
    merged_results = _sort_ranked_candidates_by_score(merged_results, score_getter=_keyword_score)
    if not keyword_results:
        next_keyword_strategy = "metadata_supplement"
    elif keyword_strategy == "strict":
        next_keyword_strategy = "strict_plus_metadata"
    elif keyword_strategy == "relaxed_or":
        next_keyword_strategy = "relaxed_or_plus_metadata"
    else:
        next_keyword_strategy = keyword_strategy
    return merged_results, metadata_candidates, next_keyword_strategy


def _resolve_candidate_items(
    *,
    candidate_strategy: SearchCandidateStrategy,
    request_mode: str,
    embedding_status: str,
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
) -> tuple[list[RankedResult], Callable[[RankedResult], float], str, bool]:
    served_mode = request_mode if request_mode == "keyword" else "keyword"
    if request_mode == "semantic" and embedding_status == "completed":
        if candidate_strategy == SearchCandidateStrategy.SEMANTIC_WITH_KEYWORD_CONTEXT:
            return (
                _merge_hybrid_candidates(keyword_results, semantic_results),
                _hybrid_score,
                "semantic",
                True,
            )
        return semantic_results, _semantic_score, "semantic", False

    if request_mode == "hybrid" and embedding_status == "completed":
        return (
            _merge_hybrid_candidates(keyword_results, semantic_results),
            _hybrid_score,
            "hybrid",
            False,
        )

    return _dedupe_ranked_results(keyword_results), _keyword_score, served_mode, False


def _build_search_execution_details(
    *,
    keyword_results: list[RankedResult],
    strict_keyword_count: int,
    keyword_strategy: str,
    semantic_results: list[RankedResult],
    candidate_items: list[RankedResult],
    query_intent: str,
    requested_mode: str,
    served_mode: str,
    harness: SearchHarness,
    fallback_reason: str | None,
    semantic_augmented_with_keyword_context: bool,
) -> dict:
    details = {
        "keyword_candidate_count": len(keyword_results),
        "keyword_strict_candidate_count": strict_keyword_count,
        "keyword_strategy": keyword_strategy,
        "semantic_candidate_count": len(semantic_results),
        "query_intent": query_intent,
        "candidate_source_breakdown": _candidate_source_breakdown(candidate_items),
        "metadata_candidate_count": sum(
            1 for item in candidate_items if "metadata_supplement" in item.retrieval_sources
        ),
        "span_candidate_count": sum(1 for item in candidate_items if item.evidence_spans),
        "context_expansion_count": sum(
            1 for item in candidate_items if "adjacent_context" in item.retrieval_sources
        ),
        "requested_mode": requested_mode,
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
    return details


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
    execution_plan = build_search_execution_plan(
        request_mode=request.mode,
        harness_name=harness.name,
        query_intent=query_intent,
        prose_lookup_intent=QUERY_INTENT_PROSE_LOOKUP,
        prose_broad_intent=QUERY_INTENT_PROSE_BROAD,
    )
    keyword_candidate_limit = max(
        request.limit * harness.retrieval_profile.keyword_candidate_multiplier,
        harness.retrieval_profile.min_candidate_limit,
    )
    keyword_chunk_results: list[RankedResult] = []
    keyword_table_results: list[RankedResult] = []
    keyword_results: list[RankedResult] = []
    keyword_strategy = "strict"
    strict_keyword_count = 0
    metadata_candidates: list[RankedResult] = []
    embedding_status = "skipped"
    embedding_error: str | None = None
    fallback_reason: str | None = None
    semantic_results: list[RankedResult] = []
    adjacent_candidates: list[RankedResult] = []
    for stage in execution_plan.stages:
        if stage == SearchStage.STRICT_KEYWORD:
            keyword_chunk_results, keyword_table_results = _load_keyword_candidates(
                session,
                request,
                candidate_limit=keyword_candidate_limit,
                run_id=run_id,
            )
            keyword_results = _sort_ranked_candidates_by_score(
                [*keyword_chunk_results, *keyword_table_results],
                score_getter=_keyword_score,
            )
            strict_keyword_count = len(keyword_results)
        elif stage == SearchStage.RELAXED_KEYWORD and strict_keyword_count == 0:
            keyword_chunk_results, keyword_table_results = _load_keyword_candidates(
                session,
                request,
                candidate_limit=keyword_candidate_limit,
                run_id=run_id,
                relaxed=True,
            )
            keyword_results = [*keyword_chunk_results, *keyword_table_results]
            if keyword_results:
                keyword_results = _sort_ranked_candidates_by_score(
                    keyword_results,
                    score_getter=_keyword_score,
                )
                keyword_strategy = "relaxed_or"
        elif stage == SearchStage.METADATA_SUPPLEMENT:
            keyword_results, metadata_candidates, keyword_strategy = (
                _apply_metadata_supplement_stage(
                    session,
                    request,
                    query_intent=query_intent,
                    strict_keyword_count=strict_keyword_count,
                    harness_name=harness.name,
                    keyword_results=keyword_results,
                    keyword_strategy=keyword_strategy,
                    run_id=run_id,
                )
            )
        elif stage == SearchStage.SEMANTIC:
            provider = embedding_provider
            if provider is None:
                try:
                    provider = get_embedding_provider()
                except Exception as exc:
                    embedding_status = "provider_unavailable"
                    embedding_error = str(exc)
                    fallback_reason = "embedding_provider_unavailable"
                    continue

            try:
                query_embedding = provider.embed_texts([request.query])[0]
                embedding_status = "completed"
                semantic_candidate_limit = max(
                    request.limit * harness.retrieval_profile.semantic_candidate_multiplier,
                    harness.retrieval_profile.min_candidate_limit,
                )
                semantic_results = _load_semantic_candidates(
                    session,
                    request,
                    query_embedding=query_embedding,
                    candidate_limit=semantic_candidate_limit,
                    run_id=run_id,
                )
            except Exception as exc:
                embedding_status = "embedding_failed"
                embedding_error = str(exc)
                fallback_reason = "embedding_failed"
        elif stage == SearchStage.ADJACENT_CONTEXT and execution_plan.prose_query:
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
                    keyword_results,
                    score_getter=_keyword_score,
                )

    table_evidence_query = (
        request.filters is not None
        and request.filters.document_id is not None
        and bool(keyword_table_results)
        and not keyword_chunk_results
    )
    effective_tabular_query = tabular_query or table_evidence_query

    candidate_items, score_getter, served_mode, semantic_augmented_with_keyword_context = (
        _resolve_candidate_items(
            candidate_strategy=execution_plan.candidate_strategy,
            request_mode=request.mode,
            embedding_status=embedding_status,
            keyword_results=keyword_results,
            semantic_results=semantic_results,
        )
    )
    details = _build_search_execution_details(
        keyword_results=keyword_results,
        strict_keyword_count=strict_keyword_count,
        keyword_strategy=keyword_strategy,
        semantic_results=semantic_results,
        candidate_items=candidate_items,
        query_intent=query_intent,
        requested_mode=request.mode,
        served_mode=served_mode,
        harness=harness,
        fallback_reason=fallback_reason,
        semantic_augmented_with_keyword_context=semantic_augmented_with_keyword_context,
    )

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
    request_id, evidence_operator_run_ids = _persist_search_execution(
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
        candidate_items=candidate_items,
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
        evidence_operator_run_ids=evidence_operator_run_ids,
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
