from __future__ import annotations

from dataclasses import replace

from app.services.search_harness_contracts import (
    LinearRerankerConfig,
    SearchHarness,
    SearchRetrievalProfile,
)
from app.services.search_harness_overrides import load_applied_search_harness_overrides

DEFAULT_SEARCH_HARNESS_NAME = "default_v1"

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
            prose_table_penalty=0.03,
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
