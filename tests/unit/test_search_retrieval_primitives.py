from __future__ import annotations

from app.services import search_retrieval_primitives, search_span_retrieval


def test_search_retrieval_primitives_reexports_span_retrieval_helpers() -> None:
    assert search_retrieval_primitives.keyword_terms is search_span_retrieval.keyword_terms
    assert (
        search_retrieval_primitives.run_keyword_span_chunk_search
        is search_span_retrieval.run_keyword_span_chunk_search
    )
    assert (
        search_retrieval_primitives.run_semantic_span_table_search
        is search_span_retrieval.run_semantic_span_table_search
    )
    assert (
        search_retrieval_primitives.query_multivector_windows
        is search_span_retrieval.query_multivector_windows
    )
    assert (
        search_retrieval_primitives.run_late_interaction_search
        is search_span_retrieval.run_late_interaction_search
    )
