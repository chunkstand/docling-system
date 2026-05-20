from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import SearchRequest
from app.services.embeddings import EmbeddingProvider
from app.services.search_plan import (
    SearchCandidateStrategy,
    SearchStage,
    build_search_execution_plan,
)

ScoreGetter = Callable[[Any], float]


def _required(namespace: Mapping[str, Any], name: str) -> Any:
    if name not in namespace:
        raise KeyError(f"search orchestration dependency '{name}' is not available")
    return namespace[name]

@dataclass(frozen=True)
class SearchExecutionOrchestrationDependencies:
    namespace: Mapping[str, Any]

    @classmethod
    def from_execution_type(
        cls,
        execution_type: type[Any],
    ) -> SearchExecutionOrchestrationDependencies:
        return cls.from_namespace(vars(sys.modules[execution_type.__module__]))

    @classmethod
    def from_namespace(
        cls,
        namespace: Mapping[str, Any],
    ) -> SearchExecutionOrchestrationDependencies:
        return cls(namespace=namespace)

    def __getattr__(self, name: str) -> Any:
        namespace_key = {
            "is_tabular_query": "_is_tabular_query",
            "classify_query_intent": "_classify_query_intent",
            "prose_lookup_intent": "QUERY_INTENT_PROSE_LOOKUP",
            "prose_broad_intent": "QUERY_INTENT_PROSE_BROAD",
        }.get(name)
        if namespace_key is None:
            namespace_key = (
                name
                if name
                in {
                    "get_search_harness",
                    "ensure_retrieval_evidence_spans_for_search",
                    "get_embedding_provider",
                    "observe_search_results",
                }
                else f"_{name}"
            )
        return _required(self.namespace, namespace_key)


def _load_keyword_candidates(
    deps: SearchExecutionOrchestrationDependencies,
    session: Session,
    request: SearchRequest,
    *,
    candidate_limit: int,
    run_id: UUID | None,
    relaxed: bool = False,
) -> tuple[list[Any], list[Any]]:
    if relaxed:
        chunk_loader = deps.run_relaxed_keyword_chunk_search
        table_loader = deps.run_relaxed_keyword_table_search
    else:
        chunk_loader = deps.run_keyword_chunk_search
        table_loader = deps.run_keyword_table_search

    run_kwargs = {"candidate_limit": candidate_limit}
    span_kwargs = {"candidate_limit": candidate_limit, "relaxed": relaxed}
    if run_id is not None:
        run_kwargs["run_id"] = run_id
        span_kwargs["run_id"] = run_id
    chunk_results = chunk_loader(session, request, **run_kwargs)
    table_results = table_loader(session, request, **run_kwargs)
    span_chunk_results = deps.run_keyword_span_chunk_search(session, request, **span_kwargs)
    span_table_results = deps.run_keyword_span_table_search(session, request, **span_kwargs)
    return (
        deps.dedupe_ranked_results([*chunk_results, *span_chunk_results]),
        deps.dedupe_ranked_results([*table_results, *span_table_results]),
    )

def _load_semantic_candidates(
    deps: SearchExecutionOrchestrationDependencies,
    session: Session,
    request: SearchRequest,
    *,
    query_embedding: list[float],
    candidate_limit: int,
    run_id: UUID | None,
) -> list[Any]:
    search_kwargs = {"candidate_limit": candidate_limit}
    if run_id is not None:
        search_kwargs["run_id"] = run_id
    loaders = (
        deps.run_semantic_chunk_search,
        deps.run_semantic_table_search,
        deps.run_semantic_span_chunk_search,
        deps.run_semantic_span_table_search,
    )
    semantic_results: list[Any] = []
    for loader in loaders:
        semantic_results.extend(loader(session, request, query_embedding, **search_kwargs))
    semantic_results = deps.dedupe_ranked_results(semantic_results)
    return deps.sort_ranked_candidates_by_score(
        semantic_results,
        score_getter=deps.semantic_score,
    )

def _apply_metadata_supplement_stage(
    deps: SearchExecutionOrchestrationDependencies,
    session: Session,
    request: SearchRequest,
    *,
    query_intent: str,
    strict_keyword_count: int,
    harness_name: str,
    keyword_results: list[Any],
    keyword_strategy: str,
    run_id: UUID | None,
) -> tuple[list[Any], list[Any], str]:
    keyword_chunk_count = sum(1 for item in keyword_results if item.result_type == "chunk")
    keyword_table_count = len(keyword_results) - keyword_chunk_count
    metadata_enabled = hasattr(session, "execute") and deps.should_run_metadata_supplement(
        query=request.query,
        query_intent=query_intent,
        strict_keyword_count=strict_keyword_count,
        keyword_chunk_count=keyword_chunk_count,
        keyword_table_count=keyword_table_count,
        harness_name=harness_name,
    )
    if not metadata_enabled:
        return keyword_results, [], keyword_strategy

    metadata_candidates = deps.run_prose_metadata_chunk_search(
        session,
        request,
        run_id=run_id,
    )
    if not metadata_candidates:
        return keyword_results, [], keyword_strategy

    merged_results = deps.dedupe_ranked_results([*keyword_results, *metadata_candidates])
    merged_results = deps.sort_ranked_candidates_by_score(
        merged_results,
        score_getter=deps.keyword_score,
    )
    if not keyword_results:
        next_keyword_strategy = "metadata_supplement"
    else:
        next_keyword_strategy = {
            "strict": "strict_plus_metadata",
            "relaxed_or": "relaxed_or_plus_metadata",
        }.get(keyword_strategy, keyword_strategy)
    return merged_results, metadata_candidates, next_keyword_strategy


def _resolve_candidate_items(
    deps: SearchExecutionOrchestrationDependencies,
    *,
    candidate_strategy: SearchCandidateStrategy,
    request_mode: str,
    embedding_status: str,
    keyword_results: list[Any],
    semantic_results: list[Any],
) -> tuple[list[Any], ScoreGetter, str, bool]:
    served_mode = request_mode if request_mode == "keyword" else "keyword"
    if request_mode == "semantic" and embedding_status == "completed":
        if candidate_strategy == SearchCandidateStrategy.SEMANTIC_WITH_KEYWORD_CONTEXT:
            return (
                deps.merge_hybrid_candidates(keyword_results, semantic_results),
                deps.hybrid_score,
                "semantic",
                True,
            )
        return semantic_results, deps.semantic_score, "semantic", False

    if request_mode == "hybrid" and embedding_status == "completed":
        return (
            deps.merge_hybrid_candidates(keyword_results, semantic_results),
            deps.hybrid_score,
            "hybrid",
            False,
        )

    return deps.dedupe_ranked_results(keyword_results), deps.keyword_score, served_mode, False


def _build_search_execution_details(
    deps: SearchExecutionOrchestrationDependencies,
    *,
    keyword_results: list[Any],
    strict_keyword_count: int,
    keyword_strategy: str,
    semantic_results: list[Any],
    candidate_items: list[Any],
    query_intent: str,
    requested_mode: str,
    served_mode: str,
    harness: Any,
    fallback_reason: str | None,
    semantic_augmented_with_keyword_context: bool,
    late_interaction_details: dict | None,
) -> dict:
    details = {
        "keyword_candidate_count": len(keyword_results),
        "keyword_strict_candidate_count": strict_keyword_count,
        "keyword_strategy": keyword_strategy,
        "semantic_candidate_count": len(semantic_results),
        "query_intent": query_intent,
        "candidate_source_breakdown": deps.candidate_source_breakdown(candidate_items),
        "metadata_candidate_count": sum(
            1 for item in candidate_items if "metadata_supplement" in item.retrieval_sources
        ),
        "span_candidate_count": sum(1 for item in candidate_items if item.evidence_spans),
        "context_expansion_count": sum(
            1 for item in candidate_items if "adjacent_context" in item.retrieval_sources
        ),
        "late_interaction_candidate_count": (
            int(late_interaction_details.get("candidate_count") or 0)
            if late_interaction_details
            else 0
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
    if late_interaction_details is not None:
        details["late_interaction"] = late_interaction_details
    if fallback_reason is not None:
        details["fallback_reason"] = fallback_reason
    return details


def execute_search(
    *,
    session: Session,
    request: SearchRequest,
    embedding_provider: EmbeddingProvider | None = None,
    run_id: UUID | None = None,
    origin: str = "api",
    evaluation_id: UUID | None = None,
    parent_request_id: UUID | None = None,
    reranker: Any | None = None,
    harness_overrides: dict[str, dict] | None = None,
    execution_type: type[Any],
) -> Any:
    deps = SearchExecutionOrchestrationDependencies.from_execution_type(execution_type)
    start = perf_counter()
    harness = deps.get_search_harness(request.harness_name, harness_overrides)
    active_reranker = reranker or harness.build_reranker()
    tabular_query = deps.is_tabular_query(request.query)
    query_intent = deps.classify_query_intent(request.query)
    execution_plan = build_search_execution_plan(
        request_mode=request.mode,
        harness_name=harness.name,
        query_intent=query_intent,
        prose_lookup_intent=deps.prose_lookup_intent,
        prose_broad_intent=deps.prose_broad_intent,
    )
    span_backfill_summary = deps.ensure_retrieval_evidence_spans_for_search(
        session,
        run_id=run_id,
        document_id=request.filters.document_id if request.filters else None,
    )
    keyword_candidate_limit = max(
        request.limit * harness.retrieval_profile.keyword_candidate_multiplier,
        harness.retrieval_profile.min_candidate_limit,
    )
    keyword_chunk_results: list[Any] = []
    keyword_table_results: list[Any] = []
    keyword_results: list[Any] = []
    keyword_strategy = "strict"
    strict_keyword_count = 0
    metadata_candidates: list[Any] = []
    embedding_status = "skipped"
    embedding_error: str | None = None
    fallback_reason: str | None = None
    semantic_results: list[Any] = []
    late_interaction_details: dict | None = None

    for stage in execution_plan.stages:
        if stage == SearchStage.STRICT_KEYWORD:
            keyword_chunk_results, keyword_table_results = _load_keyword_candidates(
                deps,
                session,
                request,
                candidate_limit=keyword_candidate_limit,
                run_id=run_id,
            )
            keyword_results = deps.sort_ranked_candidates_by_score(
                [*keyword_chunk_results, *keyword_table_results],
                score_getter=deps.keyword_score,
            )
            strict_keyword_count = len(keyword_results)
            continue

        if stage == SearchStage.RELAXED_KEYWORD and strict_keyword_count == 0:
            keyword_chunk_results, keyword_table_results = _load_keyword_candidates(
                deps,
                session,
                request,
                candidate_limit=keyword_candidate_limit,
                run_id=run_id,
                relaxed=True,
            )
            keyword_results = [*keyword_chunk_results, *keyword_table_results]
            if keyword_results:
                keyword_results = deps.sort_ranked_candidates_by_score(
                    keyword_results,
                    score_getter=deps.keyword_score,
                )
                keyword_strategy = "relaxed_or"
            continue

        if stage == SearchStage.METADATA_SUPPLEMENT:
            keyword_results, metadata_candidates, keyword_strategy = (
                _apply_metadata_supplement_stage(
                    deps,
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
            continue

        if stage == SearchStage.SEMANTIC:
            provider = embedding_provider
            if provider is None:
                try:
                    provider = deps.get_embedding_provider()
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
                    deps,
                    session,
                    request,
                    query_embedding=query_embedding,
                    candidate_limit=semantic_candidate_limit,
                    run_id=run_id,
                )
                if harness.retrieval_profile.late_interaction_enabled:
                    try:
                        query_windows = deps.query_multivector_windows(request.query)
                        query_vectors = provider.embed_texts(
                            [window["text"] for window in query_windows]
                        )
                        late_interaction_candidate_limit = max(
                            request.limit
                            * harness.retrieval_profile.late_interaction_candidate_multiplier,
                            harness.retrieval_profile.late_interaction_min_candidate_limit,
                        )
                        late_interaction_results, late_interaction_details = (
                            deps.run_late_interaction_search(
                                session,
                                request,
                                query_windows=query_windows,
                                query_vectors=query_vectors,
                                candidate_limit=late_interaction_candidate_limit,
                                run_id=run_id,
                            )
                        )
                        semantic_results = deps.sort_ranked_candidates_by_score(
                            deps.dedupe_ranked_results(
                                [*semantic_results, *late_interaction_results]
                            ),
                            score_getter=deps.semantic_score,
                        )
                    except Exception as exc:
                        late_interaction_details = {
                            "status": "failed",
                            "error": str(exc),
                            "candidate_count": 0,
                        }
            except Exception as exc:
                embedding_status = "embedding_failed"
                embedding_error = str(exc)
                fallback_reason = "embedding_failed"
            continue

        if stage == SearchStage.ADJACENT_CONTEXT and execution_plan.prose_query:
            adjacent_seed_candidates = deps.dedupe_ranked_results(
                [*keyword_results, *semantic_results, *metadata_candidates]
            )
            adjacent_candidates = deps.expand_adjacent_chunk_context(
                session,
                request,
                seed_candidates=adjacent_seed_candidates,
                run_id=run_id,
            )
            if adjacent_candidates:
                keyword_results = deps.dedupe_ranked_results(
                    [*keyword_results, *adjacent_candidates]
                )
                keyword_results = deps.sort_ranked_candidates_by_score(
                    keyword_results,
                    score_getter=deps.keyword_score,
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
            deps,
            candidate_strategy=execution_plan.candidate_strategy,
            request_mode=request.mode,
            embedding_status=embedding_status,
            keyword_results=keyword_results,
            semantic_results=semantic_results,
        )
    )
    details = _build_search_execution_details(
        deps,
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
        late_interaction_details=late_interaction_details,
    )
    if span_backfill_summary.get("rebuilt_run_count"):
        details["retrieval_span_backfill"] = span_backfill_summary

    reranked_results = deps.rerank_results(
        candidate_items,
        request=request,
        score_getter=score_getter,
        tabular_query=effective_tabular_query,
        query_intent=query_intent,
        reranker=active_reranker,
    )
    deps.ensure_reranked_result_evidence_spans(session, request, reranked_results)
    details["selected_result_span_count"] = sum(
        1 for candidate in reranked_results if candidate.item.evidence_spans
    )
    results = [
        deps.to_search_result(candidate.item, candidate.score)
        for candidate in reranked_results
    ]

    table_hit_count = sum(1 for item in results if item.result_type == "table")
    deps.observe_search_results(
        table_hit_count,
        mixed_request=request.mode == "hybrid",
    )
    duration_ms = round((perf_counter() - start) * 1000, 3)
    request_id, evidence_operator_run_ids = deps.persist_search_execution(
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

    return execution_type(
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
