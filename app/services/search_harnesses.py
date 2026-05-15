from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from typing import Protocol

import app.services.search_query_features as _query_features
from app.schemas.search import SearchFilters, SearchRequest, SearchResult
from app.services import search_ranking as _search_ranking
from app.services.search_harness_overrides import load_applied_search_harness_overrides
from app.services.search_query_features import QueryFeatureSet

DEFAULT_SEARCH_HARNESS_NAME = "default_v1"
QUERY_INTENT_TABULAR = _query_features.QUERY_INTENT_TABULAR
build_query_feature_set = _query_features.build_query_feature_set

RankedResult = _search_ranking.RankedResult
RerankedResult = _search_ranking.RerankedResult
document_query_overlap_features = _search_ranking.document_query_overlap_features
prose_query_match_features = _search_ranking.prose_query_match_features
table_title_match_features = _search_ranking.table_title_match_features
exact_filter_priority = _search_ranking.exact_filter_priority
result_type_priority = _search_ranking.result_type_priority
document_cluster_strengths = _search_ranking.document_cluster_strengths


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
        active_query_features = query_features or build_query_feature_set(request.query)
        base_ranked = sorted(
            items,
            key=lambda item: (
                -score_getter(item),
                item.page_from if item.page_from is not None else 10**9,
                str(item.result_id),
            ),
        )

        cluster_strengths = document_cluster_strengths(
            base_ranked,
            score_getter=score_getter,
            query_intent=query_intent,
        )
        annotated: list[RerankedResult] = []
        for base_rank, item in enumerate(base_ranked, start=1):
            base_score = score_getter(item)
            tabular_table_signal = int(tabular_query and item.result_type == "table")
            title_match = table_title_match_features(item, active_query_features)
            document_overlap = document_query_overlap_features(
                item,
                active_query_features,
            )
            prose_match = prose_query_match_features(item, active_query_features)
            exact_priority = exact_filter_priority(item, request.filters)
            type_priority = result_type_priority(item, tabular_query)
            cluster_strength = cluster_strengths.get(item.document_id, 0.0)
            title_match_boost = (
                title_match["title_exact_match"] * self.config.title_exact_match_bonus
                + title_match["title_token_coverage"] * self.config.title_token_coverage_bonus
            )
            source_filename_exact_match_boost = (
                document_overlap["source_filename_exact_match"]
                * self.config.source_filename_exact_match_bonus
            )
            source_filename_boost = (
                document_overlap["source_filename_token_coverage"]
                * self.config.source_filename_token_coverage_bonus
            )
            document_title_exact_match_boost = (
                document_overlap["document_title_exact_match"]
                * self.config.document_title_exact_match_bonus
            )
            document_title_boost = (
                document_overlap["document_title_token_coverage"]
                * self.config.document_title_token_coverage_bonus
            )
            prose_document_cluster_boost = (
                cluster_strength * self.config.prose_document_cluster_bonus
            )
            heading_boost = (
                prose_match["heading_token_coverage"] * self.config.heading_token_coverage_bonus
            )
            phrase_overlap_boost = (
                prose_match["phrase_overlap"] * self.config.phrase_overlap_bonus
            )
            rare_token_overlap_boost = (
                prose_match["rare_token_overlap"] * self.config.rare_token_overlap_bonus
            )
            adjacent_chunk_context_boost = (
                prose_match["adjacent_chunk_context_signal"]
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
            exact_filter_boost = exact_priority * self.config.exact_filter_bonus
            result_type_priority_boost = type_priority * self.config.result_type_priority_bonus
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
                        "title_exact_match": title_match["title_exact_match"],
                        "title_token_coverage": title_match["title_token_coverage"],
                        "title_match_boost": title_match_boost,
                        "source_filename_exact_match": document_overlap[
                            "source_filename_exact_match"
                        ],
                        "source_filename_exact_match_boost": source_filename_exact_match_boost,
                        "source_filename_token_coverage": document_overlap[
                            "source_filename_token_coverage"
                        ],
                        "source_filename_boost": source_filename_boost,
                        "document_title_exact_match": document_overlap[
                            "document_title_exact_match"
                        ],
                        "document_title_exact_match_boost": document_title_exact_match_boost,
                        "document_title_token_coverage": document_overlap[
                            "document_title_token_coverage"
                        ],
                        "document_title_boost": document_title_boost,
                        "document_cluster_strength": cluster_strength,
                        "prose_document_cluster_boost": prose_document_cluster_boost,
                        "heading_token_coverage": prose_match["heading_token_coverage"],
                        "heading_boost": heading_boost,
                        "phrase_overlap": prose_match["phrase_overlap"],
                        "phrase_overlap_boost": phrase_overlap_boost,
                        "rare_token_overlap": prose_match["rare_token_overlap"],
                        "rare_token_overlap_boost": rare_token_overlap_boost,
                        "adjacent_chunk_context_signal": prose_match[
                            "adjacent_chunk_context_signal"
                        ],
                        "adjacent_chunk_context_boost": adjacent_chunk_context_boost,
                        "late_interaction_signal": late_interaction_signal,
                        "prose_table_penalty": prose_table_penalty,
                        "exact_filter_priority": exact_priority,
                        "exact_filter_boost": exact_filter_boost,
                        "result_type_priority": type_priority,
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


def build_derived_search_harness(
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


def build_search_harness_registry(
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
            registry[harness_name] = build_derived_search_harness(
                harness_name=harness_name,
                spec=override_spec,
                registry=registry,
            )
    return registry


def list_search_harnesses(
    harness_overrides: dict[str, dict] | None = None,
) -> list[SearchHarness]:
    return sorted(
        build_search_harness_registry(harness_overrides).values(),
        key=lambda harness: harness.name,
    )


def get_search_harness(
    name: str | None = None,
    harness_overrides: dict[str, dict] | None = None,
) -> SearchHarness:
    harness_name = name or DEFAULT_SEARCH_HARNESS_NAME
    registry = build_search_harness_registry(harness_overrides)
    try:
        return registry[harness_name]
    except KeyError as exc:
        available = ", ".join(sorted(registry))
        msg = f"Unknown search harness '{harness_name}'. Available: {available}"
        raise ValueError(msg) from exc


def get_default_reranker() -> SearchReranker:
    return get_search_harness().build_reranker()


def rerank_results(
    items: list[RankedResult],
    *,
    request: SearchRequest,
    score_getter: Callable[[RankedResult], float],
    tabular_query: bool,
    query_intent: str,
    reranker: SearchReranker | None = None,
) -> list[RerankedResult]:
    return _search_ranking.rerank_results(
        items,
        request=request,
        score_getter=score_getter,
        tabular_query=tabular_query,
        query_intent=query_intent,
        active_reranker=reranker or get_default_reranker(),
    )


def merge_hybrid_results(
    keyword_results: list[RankedResult],
    semantic_results: list[RankedResult],
    limit: int,
    filters: SearchFilters | None,
    tabular_query: bool,
    query_intent: str = _query_features.QUERY_INTENT_PROSE_LOOKUP,
    query: str | None = None,
) -> list[SearchResult]:
    return _search_ranking.merge_hybrid_results(
        keyword_results,
        semantic_results,
        limit,
        filters,
        tabular_query=tabular_query,
        active_reranker=get_default_reranker(),
        query_intent=query_intent,
        query=query,
    )


_build_derived_search_harness = build_derived_search_harness
_build_search_harness_registry = build_search_harness_registry
_rerank_results = rerank_results
_merge_hybrid_results = merge_hybrid_results
