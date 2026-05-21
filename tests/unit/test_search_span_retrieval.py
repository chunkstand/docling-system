from __future__ import annotations

from app.services import search_span_retrieval


def test_keyword_terms_dedupes_short_and_repeated_tokens() -> None:
    terms = search_span_retrieval.keyword_terms("A vent vent stack 701 701")

    assert terms == ["vent", "stack", "701"]


def test_query_multivector_windows_preserves_overlap_and_hash_payload() -> None:
    windows = search_span_retrieval.query_multivector_windows(
        "one two three four five six seven eight"
    )

    assert len(windows) == 2
    assert windows[0]["text"] == "one two three four five six"
    assert windows[1]["text"] == "four five six seven eight"
    assert windows[0]["token_end"] - windows[0]["token_start"] == 6
    assert windows[1]["token_start"] == 3
    assert windows[0]["text_sha256"]
    assert windows[1]["text_sha256"]


def test_late_interaction_match_trace_orders_matches_by_query_vector_index() -> None:
    trace = search_span_retrieval.late_interaction_match_trace(
        query_windows=[
            {
                "query_vector_index": 0,
                "token_start": 0,
                "token_end": 2,
                "text": "one two",
                "text_sha256": "a",
            },
            {
                "query_vector_index": 1,
                "token_start": 2,
                "token_end": 4,
                "text": "three four",
                "text_sha256": "b",
            },
        ],
        query_matches={
            1: {"query_vector_index": 1, "score": 0.8},
            0: {"query_vector_index": 0, "score": 0.9},
        },
        score=0.85,
    )

    assert trace["score"] == 0.85
    assert [match["query_vector_index"] for match in trace["maxsim_matches"]] == [0, 1]
