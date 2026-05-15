from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

import app.services.search_execution_orchestration as _search_execution_orchestration
import app.services.search_execution_persistence as _search_execution_persistence
import app.services.search_harnesses as _search_harnesses
import app.services.search_hydration as _search_hydration
import app.services.search_metadata_supplement as _search_metadata_supplement
import app.services.search_query_features as _query_features
import app.services.search_retrieval_primitives as _search_retrieval_primitives
from app.schemas.search import SearchRequest, SearchResult
from app.services import search_ranking as _search_ranking
from app.services.embeddings import EmbeddingProvider, get_embedding_provider  # noqa: F401
from app.services.retrieval_spans import (  # noqa: F401
    ensure_retrieval_evidence_spans_for_search,
)
from app.services.telemetry import observe_search_results  # noqa: F401

DEFAULT_SEARCH_HARNESS_NAME = _search_harnesses.DEFAULT_SEARCH_HARNESS_NAME
QUERY_INTENT_TABULAR = _query_features.QUERY_INTENT_TABULAR
QUERY_INTENT_PROSE_LOOKUP = _query_features.QUERY_INTENT_PROSE_LOOKUP
QUERY_INTENT_PROSE_BROAD = _query_features.QUERY_INTENT_PROSE_BROAD
PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT = (
    _search_metadata_supplement.PROSE_SUPPLEMENTARY_CANDIDATE_LIMIT
)
PROSE_ADJACENT_EXPANSION_LIMIT = _search_metadata_supplement.PROSE_ADJACENT_EXPANSION_LIMIT
PROSE_ADJACENT_SEED_LIMIT = _search_metadata_supplement.PROSE_ADJACENT_SEED_LIMIT
LATE_INTERACTION_QUERY_WORD_WINDOW = (
    _search_retrieval_primitives.LATE_INTERACTION_QUERY_WORD_WINDOW
)
LATE_INTERACTION_QUERY_WORD_OVERLAP = (
    _search_retrieval_primitives.LATE_INTERACTION_QUERY_WORD_OVERLAP
)
LATE_INTERACTION_FETCH_MULTIPLIER = (
    _search_retrieval_primitives.LATE_INTERACTION_FETCH_MULTIPLIER
)
METADATA_SUPPLEMENT_DIRECT_CHUNK_MULTIPLIER = (
    _search_metadata_supplement.METADATA_SUPPLEMENT_DIRECT_CHUNK_MULTIPLIER
)
METADATA_SUPPLEMENT_DOCUMENT_LIMIT = _search_metadata_supplement.METADATA_SUPPLEMENT_DOCUMENT_LIMIT
METADATA_SUPPLEMENT_DOCUMENT_CHUNK_MULTIPLIER = (
    _search_metadata_supplement.METADATA_SUPPLEMENT_DOCUMENT_CHUNK_MULTIPLIER
)
METADATA_SUPPLEMENT_SCORE_SCALE = _search_metadata_supplement.METADATA_SUPPLEMENT_SCORE_SCALE
TABULAR_REFERENCE_PATTERN = _query_features.TABULAR_REFERENCE_PATTERN
QueryFeatureSet = _query_features.QueryFeatureSet
SearchReranker = _search_harnesses.SearchReranker
SearchRetrievalProfile = _search_harnesses.SearchRetrievalProfile
LinearRerankerConfig = _search_harnesses.LinearRerankerConfig
SearchHarness = _search_harnesses.SearchHarness
DEFAULT_RETRIEVAL_PROFILE = _search_harnesses.DEFAULT_RETRIEVAL_PROFILE
WIDE_RETRIEVAL_PROFILE = _search_harnesses.WIDE_RETRIEVAL_PROFILE
PROSE_RETRIEVAL_PROFILE = _search_harnesses.PROSE_RETRIEVAL_PROFILE
MULTIVECTOR_RETRIEVAL_PROFILE = _search_harnesses.MULTIVECTOR_RETRIEVAL_PROFILE
SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS = (
    _search_harnesses.SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS
)
SEARCH_HARNESS_RERANKER_OVERRIDE_FIELDS = (
    _search_harnesses.SEARCH_HARNESS_RERANKER_OVERRIDE_FIELDS
)
LinearFeatureSearchReranker = _search_harnesses.LinearFeatureSearchReranker
_build_derived_search_harness = _search_harnesses._build_derived_search_harness
_build_search_harness_registry = _search_harnesses._build_search_harness_registry
list_search_harnesses = _search_harnesses.list_search_harnesses
get_search_harness = _search_harnesses.get_search_harness
get_default_reranker = _search_harnesses.get_default_reranker
_rerank_results = _search_harnesses._rerank_results
_merge_hybrid_results = _search_harnesses._merge_hybrid_results
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
_chunk_query = _search_retrieval_primitives._chunk_query
_table_query = _search_retrieval_primitives._table_query
_document_query = _search_retrieval_primitives._document_query
_apply_chunk_filters = _search_retrieval_primitives._apply_chunk_filters
_apply_table_filters = _search_retrieval_primitives._apply_table_filters
_apply_document_filters = _search_retrieval_primitives._apply_document_filters
_apply_span_filters = _search_retrieval_primitives._apply_span_filters
_keyword_terms = _search_retrieval_primitives._keyword_terms
_build_relaxed_tsquery = _search_retrieval_primitives._build_relaxed_tsquery
_run_keyword_chunk_search = _search_retrieval_primitives._run_keyword_chunk_search
_run_relaxed_keyword_chunk_search = _search_retrieval_primitives._run_relaxed_keyword_chunk_search
_run_keyword_table_search = _search_retrieval_primitives._run_keyword_table_search
_run_relaxed_keyword_table_search = _search_retrieval_primitives._run_relaxed_keyword_table_search
_run_keyword_span_chunk_search = _search_retrieval_primitives._run_keyword_span_chunk_search
_run_keyword_span_table_search = _search_retrieval_primitives._run_keyword_span_table_search
_run_semantic_chunk_search = _search_retrieval_primitives._run_semantic_chunk_search
_run_semantic_span_chunk_search = _search_retrieval_primitives._run_semantic_span_chunk_search
_run_semantic_table_search = _search_retrieval_primitives._run_semantic_table_search
_run_semantic_span_table_search = _search_retrieval_primitives._run_semantic_span_table_search
_query_multivector_windows = _search_retrieval_primitives._query_multivector_windows
_multivector_span_query = _search_retrieval_primitives._multivector_span_query
_late_interaction_match_trace = _search_retrieval_primitives._late_interaction_match_trace
_run_late_interaction_search = _search_retrieval_primitives._run_late_interaction_search
_ranked_metadata_overlap_score = _search_metadata_supplement._ranked_metadata_overlap_score
_metadata_tsquery = _search_metadata_supplement._metadata_tsquery
_run_prose_metadata_chunk_search = _search_metadata_supplement._run_prose_metadata_chunk_search
_should_run_metadata_supplement = _search_metadata_supplement._should_run_metadata_supplement
_expand_adjacent_chunk_context = _search_metadata_supplement._expand_adjacent_chunk_context


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
