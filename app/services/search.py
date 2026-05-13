from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Protocol
from uuid import UUID

from sqlalchemy import Float, Select, and_, cast, false, func, or_, select
from sqlalchemy.orm import Session

import app.services.search_execution_orchestration as _search_execution_orchestration
import app.services.search_execution_persistence as _search_execution_persistence
import app.services.search_hydration as _search_hydration
import app.services.search_query_features as _query_features
from app.core.hashes import payload_sha256 as _payload_sha256
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentTable,
    RetrievalEvidenceSpan,
    RetrievalEvidenceSpanMultiVector,
)
from app.schemas.search import (
    SearchFilters,
    SearchRequest,
    SearchResult,
)
from app.services import search_ranking as _search_ranking
from app.services.embeddings import EmbeddingProvider, get_embedding_provider  # noqa: F401
from app.services.retrieval_spans import (  # noqa: F401
    ensure_retrieval_evidence_spans_for_search,
)
from app.services.search_harness_overrides import load_applied_search_harness_overrides
from app.services.search_query_features import QueryFeatureSet
from app.services.telemetry import observe_search_results  # noqa: F401

DEFAULT_SEARCH_HARNESS_NAME = "default_v1"
QUERY_INTENT_TABULAR = _query_features.QUERY_INTENT_TABULAR
QUERY_INTENT_PROSE_LOOKUP = _query_features.QUERY_INTENT_PROSE_LOOKUP
QUERY_INTENT_PROSE_BROAD = _query_features.QUERY_INTENT_PROSE_BROAD
PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT = 12
PROSE_ADJACENT_EXPANSION_LIMIT = 12
PROSE_ADJACENT_SEED_LIMIT = 6
LATE_INTERACTION_QUERY_WORD_WINDOW = 6
LATE_INTERACTION_QUERY_WORD_OVERLAP = 3
LATE_INTERACTION_FETCH_MULTIPLIER = 4
TABULAR_REFERENCE_PATTERN = _query_features.TABULAR_REFERENCE_PATTERN
is_tabular_query = _query_features.is_tabular_query
_is_tabular_query = is_tabular_query
_classify_query_intent = _query_features.classify_query_intent
_looks_like_identifier_lookup = _query_features.looks_like_identifier_lookup
_normalize_text = _query_features.normalize_search_text
_salient_tokens = _query_features.salient_tokens
_salient_tokens_from_normalized = _query_features.salient_tokens_from_normalized
_phrase_tokens_from_normalized = _query_features.phrase_tokens_from_normalized
_query_phrases_from_normalized = _query_features.query_phrases_from_normalized
_build_query_feature_set = _query_features.build_query_feature_set
_coerce_query_feature_set = _query_features.coerce_query_feature_set
_token_coverage = _query_features.token_coverage
_strong_document_phrase_match = _query_features.strong_document_phrase_match
_metadata_query_tokens = _query_features.metadata_query_tokens

RankedEvidenceSpan = _search_ranking.RankedEvidenceSpan
RankedResult = _search_ranking.RankedResult
RerankedResult = _search_ranking.RerankedResult
_document_query_overlap_features = _search_ranking.document_query_overlap_features
_prose_result_text = _search_ranking.prose_result_text
_prose_query_match_features = _search_ranking.prose_query_match_features
_merge_retrieval_sources = _search_ranking.merge_retrieval_sources
_merge_evidence_spans = _search_ranking.merge_evidence_spans
_table_title_match_features = _search_ranking.table_title_match_features
_exact_filter_priority = _search_ranking.exact_filter_priority
_result_type_priority = _search_ranking.result_type_priority
_document_cluster_strengths = _search_ranking.document_cluster_strengths
_to_search_result = _search_ranking.to_search_result
_result_key = _search_ranking.result_key
_keyword_score = _search_ranking.keyword_score
_semantic_score = _search_ranking.semantic_score
_hybrid_score = _search_ranking.hybrid_score
_merge_hybrid_candidates = _search_ranking.merge_hybrid_candidates
_dedupe_ranked_results = _search_ranking.dedupe_ranked_results
_strongest_ranked_score = _search_ranking.strongest_ranked_score
_sort_ranked_candidates_by_score = _search_ranking.sort_ranked_candidates_by_score
_candidate_source_breakdown = _search_ranking.candidate_source_breakdown
_span_chunk_query = _search_hydration._span_chunk_query
_span_table_query = _search_hydration._span_table_query
_hydrate_ranked_chunks = _search_hydration._hydrate_ranked_chunks
_span_evidence_payload = _search_hydration._span_evidence_payload
_hydrate_ranked_span_chunks = _search_hydration._hydrate_ranked_span_chunks
_hydrate_ranked_tables = _search_hydration._hydrate_ranked_tables
_hydrate_ranked_span_tables = _search_hydration._hydrate_ranked_span_tables
_supports_retrieval_span_search = _search_hydration._supports_retrieval_span_search
_load_source_evidence_spans = _search_hydration._load_source_evidence_spans
_ensure_reranked_result_evidence_spans = (
    _search_hydration._ensure_reranked_result_evidence_spans
)
_hydrate_late_interaction_results = _search_hydration._hydrate_late_interaction_results
_ranked_result_evidence_payload = (
    _search_execution_persistence._ranked_result_evidence_payload
)
_reranked_result_evidence_payload = (
    _search_execution_persistence._reranked_result_evidence_payload
)
_persist_search_operator_runs = (
    _search_execution_persistence._persist_search_operator_runs
)
_persist_search_result_spans = (
    _search_execution_persistence._persist_search_result_spans
)
_persist_search_execution = _search_execution_persistence._persist_search_execution
record_knowledge_operator_run = _search_execution_persistence.record_knowledge_operator_run


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
    late_interaction_enabled: bool = False
    late_interaction_candidate_multiplier: int = 6
    late_interaction_min_candidate_limit: int = 24

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
MULTIVECTOR_RETRIEVAL_PROFILE = SearchRetrievalProfile(
    name="multivector_v1",
    keyword_candidate_multiplier=7,
    semantic_candidate_multiplier=7,
    min_candidate_limit=28,
    late_interaction_enabled=True,
    late_interaction_candidate_multiplier=8,
    late_interaction_min_candidate_limit=32,
)

METADATA_SUPPLEMENT_DIRECT_CHUNK_MULTIPLIER = 4
METADATA_SUPPLEMENT_DOCUMENT_LIMIT = 8
METADATA_SUPPLEMENT_DOCUMENT_CHUNK_MULTIPLIER = 6
METADATA_SUPPLEMENT_SCORE_SCALE = 4.0

SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS = {
    "keyword_candidate_multiplier",
    "semantic_candidate_multiplier",
    "min_candidate_limit",
    "late_interaction_enabled",
    "late_interaction_candidate_multiplier",
    "late_interaction_min_candidate_limit",
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
    "multivector_v1": SearchHarness(
        name="multivector_v1",
        retrieval_profile=MULTIVECTOR_RETRIEVAL_PROFILE,
        reranker_config=LinearRerankerConfig(
            harness_name="multivector_v1",
            reranker_name="linear_feature_reranker",
            reranker_version="v4",
            retrieval_profile_name=MULTIVECTOR_RETRIEVAL_PROFILE.name,
            tabular_table_bonus=0.08,
            title_exact_match_bonus=0.05,
            title_token_coverage_bonus=0.03,
            source_filename_exact_match_bonus=4.0,
            source_filename_token_coverage_bonus=0.045,
            document_title_exact_match_bonus=2.25,
            document_title_token_coverage_bonus=0.04,
            prose_document_cluster_bonus=0.04,
            heading_token_coverage_bonus=0.03,
            phrase_overlap_bonus=0.03,
            rare_token_overlap_bonus=0.04,
            adjacent_chunk_context_bonus=0.0,
            prose_table_penalty=0.0,
            exact_filter_bonus=0.02,
            result_type_priority_bonus=0.008,
        ),
        metadata={
            "retrieval_family": "multivector_late_interaction",
            "audit_note": (
                "Uses retrieval evidence span multivectors and records query-to-span "
                "max-sim traces when embeddings are available."
            ),
        },
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
            late_interaction_signal = float(
                "multivector_late_interaction" in item.retrieval_sources
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
                        "late_interaction_signal": late_interaction_signal,
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

def _query_multivector_windows(query: str) -> list[dict]:
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
                "text_sha256": _payload_sha256({"query_vector_text": normalized}),
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
                "text_sha256": _payload_sha256(
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


def _multivector_span_query(
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


def _late_interaction_match_trace(
    *,
    query_windows: list[dict],
    query_matches: dict[int, dict],
    score: float,
) -> dict:
    ordered_matches = [
        query_matches[index]
        for index in sorted(query_matches)
    ]
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


def _run_late_interaction_search(
    session: Session,
    request: SearchRequest,
    *,
    query_windows: list[dict],
    query_vectors: list[list[float]],
    candidate_limit: int,
    run_id: UUID | None,
) -> tuple[list[RankedResult], dict]:
    if not _supports_retrieval_span_search(session) or not query_vectors:
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
            _apply_span_filters(_multivector_span_query(run_id), request.filters)
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
            "trace": _late_interaction_match_trace(
                query_windows=query_windows,
                query_matches=query_matches,
                score=score,
            ),
        }

    results = _hydrate_late_interaction_results(
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


def _rerank_results(
    items: list[RankedResult],
    *,
    request: SearchRequest,
    score_getter: Callable[[RankedResult], float],
    tabular_query: bool,
    query_intent: str,
    reranker: SearchReranker | None = None,
) -> list[RerankedResult]:
    return _search_ranking.rerank_results(items, request=request, score_getter=score_getter, tabular_query=tabular_query, query_intent=query_intent, active_reranker=reranker or get_default_reranker())  # noqa: E501


def _merge_hybrid_results(
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
    limit: int,
    filters: SearchFilters | None,
    tabular_query: bool,
    query_intent: str = QUERY_INTENT_PROSE_LOOKUP,
    query: str | None = None,
) -> list[SearchResult]:
    return _search_ranking.merge_hybrid_results(keyword_results, semantic_results, limit, filters, tabular_query=tabular_query, active_reranker=get_default_reranker(), query_intent=query_intent, query=query)  # noqa: E501


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
    return _search_execution_orchestration.execute_search(
        session=session,
        request=request,
        embedding_provider=embedding_provider,
        run_id=run_id,
        origin=origin,
        evaluation_id=evaluation_id,
        parent_request_id=parent_request_id,
        reranker=reranker,
        harness_overrides=harness_overrides,
        execution_type=SearchExecution,
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
