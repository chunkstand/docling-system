from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

from app.schemas.search import SearchRequest
from app.services import search_execution_orchestration as _search_execution_orchestration
from app.services.search import RankedResult
from app.services.search_plan import SearchCandidateStrategy


def _ranked_chunk(
    *,
    result_id: UUID | None = None,
    keyword_score: float | None = None,
    semantic_score: float | None = None,
    retrieval_sources: tuple[str, ...] = ("keyword_primary",),
    evidence_spans: tuple = (),
) -> RankedResult:
    return RankedResult(
        result_type="chunk",
        result_id=result_id or uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="doc.pdf",
        document_title="Doc",
        page_from=1,
        page_to=1,
        chunk_index=0,
        chunk_text="chunk text",
        heading="Heading",
        keyword_score=keyword_score,
        semantic_score=semantic_score,
        retrieval_sources=retrieval_sources,
        evidence_spans=evidence_spans,
    )


def _dedupe(items: list[RankedResult]) -> list[RankedResult]:
    seen: set[tuple[str, UUID]] = set()
    deduped: list[RankedResult] = []
    for item in items:
        key = (item.result_type, item.result_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _sort(
    items: list[RankedResult],
    *,
    score_getter,
) -> list[RankedResult]:
    return sorted(items, key=score_getter, reverse=True)


def _deps(**overrides) -> _search_execution_orchestration.SearchExecutionOrchestrationDependencies:
    defaults = {
        "get_search_harness": lambda name, overrides=None: None,
        "_is_tabular_query": lambda query: False,
        "_classify_query_intent": lambda query: "prose_lookup",
        "QUERY_INTENT_PROSE_LOOKUP": "prose_lookup",
        "QUERY_INTENT_PROSE_BROAD": "prose_broad",
        "ensure_retrieval_evidence_spans_for_search": lambda *args, **kwargs: {},
        "_run_keyword_chunk_search": lambda *args, **kwargs: [],
        "_run_relaxed_keyword_chunk_search": lambda *args, **kwargs: [],
        "_run_keyword_table_search": lambda *args, **kwargs: [],
        "_run_relaxed_keyword_table_search": lambda *args, **kwargs: [],
        "_run_keyword_span_chunk_search": lambda *args, **kwargs: [],
        "_run_keyword_span_table_search": lambda *args, **kwargs: [],
        "_dedupe_ranked_results": _dedupe,
        "_sort_ranked_candidates_by_score": _sort,
        "_keyword_score": lambda item: float(item.keyword_score or 0.0),
        "_run_semantic_chunk_search": lambda *args, **kwargs: [],
        "_run_semantic_table_search": lambda *args, **kwargs: [],
        "_run_semantic_span_chunk_search": lambda *args, **kwargs: [],
        "_run_semantic_span_table_search": lambda *args, **kwargs: [],
        "_semantic_score": lambda item: float(item.semantic_score or 0.0),
        "_run_prose_metadata_chunk_search": lambda *args, **kwargs: [],
        "_should_run_metadata_supplement": lambda **kwargs: False,
        "_merge_hybrid_candidates": lambda keyword, semantic: [*keyword, *semantic],
        "_hybrid_score": lambda item: float(item.hybrid_score or 0.0),
        "_candidate_source_breakdown": lambda items: {
            source: sum(source in item.retrieval_sources for item in items)
            for source in {
                source_name
                for item in items
                for source_name in item.retrieval_sources
            }
        },
        "get_embedding_provider": lambda: None,
        "_query_multivector_windows": lambda query: [],
        "_run_late_interaction_search": lambda *args, **kwargs: ([], None),
        "_expand_adjacent_chunk_context": lambda *args, **kwargs: [],
        "_rerank_results": lambda *args, **kwargs: [],
        "_ensure_reranked_result_evidence_spans": lambda *args, **kwargs: None,
        "_to_search_result": lambda item, score: item,
        "observe_search_results": lambda table_hits, mixed_request: None,
        "_persist_search_execution": lambda *args, **kwargs: (None, []),
    }
    defaults.update(overrides)
    return _search_execution_orchestration.SearchExecutionOrchestrationDependencies.from_namespace(
        defaults
    )


def test_load_keyword_candidates_dedupes_primary_and_span_rows() -> None:
    shared_id = uuid4()
    shared = _ranked_chunk(result_id=shared_id, keyword_score=0.7)
    extra = _ranked_chunk(keyword_score=0.4)
    deps = _deps(
        _run_keyword_chunk_search=lambda *args, **kwargs: [shared],
        _run_keyword_span_chunk_search=lambda *args, **kwargs: [shared, extra],
    )

    chunk_results, table_results = _search_execution_orchestration._load_keyword_candidates(
        deps,
        session=None,
        request=SearchRequest(query="vent stack", mode="keyword", limit=5),
        candidate_limit=10,
        run_id=None,
    )

    assert [item.result_id for item in chunk_results] == [shared_id, extra.result_id]
    assert table_results == []


def test_load_keyword_candidates_uses_relaxed_scoped_loaders() -> None:
    observed: dict[str, object] = {}
    scoped_run_id = uuid4()
    relaxed = _ranked_chunk(keyword_score=0.5)
    deps = _deps(
        _run_relaxed_keyword_chunk_search=lambda *args, **kwargs: observed.update(
            chunk_run_id=kwargs.get("run_id")
        )
        or [relaxed],
        _run_relaxed_keyword_table_search=lambda *args, **kwargs: observed.update(
            table_run_id=kwargs.get("run_id")
        )
        or [],
        _run_keyword_span_chunk_search=lambda *args, **kwargs: observed.update(
            span_chunk_run_id=kwargs.get("run_id"),
            span_chunk_relaxed=kwargs.get("relaxed"),
        )
        or [],
        _run_keyword_span_table_search=lambda *args, **kwargs: observed.update(
            span_table_run_id=kwargs.get("run_id"),
            span_table_relaxed=kwargs.get("relaxed"),
        )
        or [],
    )

    chunk_results, _ = _search_execution_orchestration._load_keyword_candidates(
        deps,
        session=None,
        request=SearchRequest(query="vent stack", mode="keyword", limit=5),
        candidate_limit=10,
        run_id=scoped_run_id,
        relaxed=True,
    )

    assert chunk_results == [relaxed]
    assert observed == {
        "chunk_run_id": scoped_run_id,
        "table_run_id": scoped_run_id,
        "span_chunk_run_id": scoped_run_id,
        "span_chunk_relaxed": True,
        "span_table_run_id": scoped_run_id,
        "span_table_relaxed": True,
    }


def test_load_semantic_candidates_dedupes_and_sorts_descending() -> None:
    shared_id = uuid4()
    strongest = _ranked_chunk(result_id=shared_id, semantic_score=0.9)
    weaker_duplicate = _ranked_chunk(result_id=shared_id, semantic_score=0.3)
    other = _ranked_chunk(semantic_score=0.5)
    deps = _deps(
        _run_semantic_chunk_search=lambda *args, **kwargs: [strongest],
        _run_semantic_table_search=lambda *args, **kwargs: [],
        _run_semantic_span_chunk_search=lambda *args, **kwargs: [weaker_duplicate],
        _run_semantic_span_table_search=lambda *args, **kwargs: [other],
    )

    results = _search_execution_orchestration._load_semantic_candidates(
        deps,
        session=None,
        request=SearchRequest(query="vent stack", mode="semantic", limit=5),
        query_embedding=[0.1, 0.2],
        candidate_limit=10,
        run_id=None,
    )

    assert [item.result_id for item in results] == [shared_id, other.result_id]
    assert results[0].semantic_score == 0.9


def test_resolve_candidate_items_uses_hybrid_context_for_semantic_prose_queries() -> None:
    keyword_item = _ranked_chunk(keyword_score=0.8)
    semantic_item = _ranked_chunk(semantic_score=0.9)
    merged = [keyword_item, semantic_item]
    deps = _deps(
        _merge_hybrid_candidates=lambda keyword, semantic: merged,
        _hybrid_score=lambda item: 1.0,
    )

    items, score_getter, served_mode, augmented = (
        _search_execution_orchestration._resolve_candidate_items(
            deps,
            candidate_strategy=SearchCandidateStrategy.SEMANTIC_WITH_KEYWORD_CONTEXT,
            request_mode="semantic",
            embedding_status="completed",
            keyword_results=[keyword_item],
            semantic_results=[semantic_item],
        )
    )

    assert items == merged
    assert score_getter(keyword_item) == 1.0
    assert served_mode == "semantic"
    assert augmented is True


def test_build_search_execution_details_counts_metadata_context_and_spans() -> None:
    metadata_item = _ranked_chunk(
        keyword_score=0.8,
        retrieval_sources=("metadata_supplement",),
    )
    context_item = _ranked_chunk(
        keyword_score=0.7,
        retrieval_sources=("adjacent_context",),
        evidence_spans=(SimpleNamespace(),),
    )
    semantic_item = _ranked_chunk(
        semantic_score=0.6,
        retrieval_sources=("semantic_primary",),
    )
    deps = _deps(
        _candidate_source_breakdown=lambda items: {
            "metadata_supplement": 1,
            "adjacent_context": 1,
            "semantic_primary": 1,
        }
    )

    details = _search_execution_orchestration._build_search_execution_details(
        deps,
        keyword_results=[metadata_item, context_item],
        strict_keyword_count=1,
        keyword_strategy="strict_plus_metadata",
        semantic_results=[semantic_item],
        candidate_items=[metadata_item, context_item, semantic_item],
        query_intent="prose_lookup",
        requested_mode="hybrid",
        served_mode="hybrid",
        harness=SimpleNamespace(
            name="prose_v3",
            reranker_name="linear_feature_reranker",
            reranker_version="v1",
            retrieval_profile_name="prose_v3",
        ),
        fallback_reason="embedding_failed",
        semantic_augmented_with_keyword_context=True,
        late_interaction_details={"candidate_count": 2},
    )

    assert details["keyword_candidate_count"] == 2
    assert details["keyword_strict_candidate_count"] == 1
    assert details["metadata_candidate_count"] == 1
    assert details["span_candidate_count"] == 1
    assert details["context_expansion_count"] == 1
    assert details["late_interaction_candidate_count"] == 2
    assert details["semantic_augmented_with_keyword_context"] is True
    assert details["fallback_reason"] == "embedding_failed"
