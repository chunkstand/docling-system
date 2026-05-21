from __future__ import annotations

from collections.abc import Callable

import app.services.search_harness_contracts as _contracts
import app.services.search_harness_registry as _registry
import app.services.search_harness_reranking as _reranking
import app.services.search_query_features as _query_features
import app.services.search_ranking as _search_ranking
from app.schemas.search import SearchFilters, SearchRequest, SearchResult

QUERY_INTENT_TABULAR = _query_features.QUERY_INTENT_TABULAR
build_query_feature_set = _query_features.build_query_feature_set

RankedResult = _search_ranking.RankedResult
RerankedResult = _search_ranking.RerankedResult
SearchReranker = _contracts.SearchReranker
SearchRetrievalProfile = _contracts.SearchRetrievalProfile
LinearRerankerConfig = _contracts.LinearRerankerConfig
SearchHarness = _contracts.SearchHarness
DEFAULT_SEARCH_HARNESS_NAME = _registry.DEFAULT_SEARCH_HARNESS_NAME
DEFAULT_RETRIEVAL_PROFILE = _registry.DEFAULT_RETRIEVAL_PROFILE
WIDE_RETRIEVAL_PROFILE = _registry.WIDE_RETRIEVAL_PROFILE
PROSE_RETRIEVAL_PROFILE = _registry.PROSE_RETRIEVAL_PROFILE
MULTIVECTOR_RETRIEVAL_PROFILE = _registry.MULTIVECTOR_RETRIEVAL_PROFILE
SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS = _registry.SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS
SEARCH_HARNESS_RERANKER_OVERRIDE_FIELDS = _registry.SEARCH_HARNESS_RERANKER_OVERRIDE_FIELDS
LinearFeatureSearchReranker = _reranking.LinearFeatureSearchReranker
build_derived_search_harness = _registry.build_derived_search_harness
build_search_harness_registry = _registry.build_search_harness_registry
list_search_harnesses = _registry.list_search_harnesses
get_search_harness = _registry.get_search_harness


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
