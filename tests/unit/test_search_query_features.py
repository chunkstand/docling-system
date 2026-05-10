from __future__ import annotations

from app.services import search
from app.services.search_query_features import (
    QUERY_INTENT_PROSE_BROAD,
    QUERY_INTENT_PROSE_LOOKUP,
    QUERY_INTENT_TABULAR,
    QueryFeatureSet,
    build_query_feature_set,
    classify_query_intent,
    is_tabular_query,
    looks_like_identifier_lookup,
    metadata_query_tokens,
    token_coverage,
)


def test_query_feature_module_preserves_search_facade_compatibility() -> None:
    assert search.QueryFeatureSet is QueryFeatureSet
    assert search.is_tabular_query is is_tabular_query
    assert search._is_tabular_query is is_tabular_query
    assert search._classify_query_intent is classify_query_intent
    assert search._build_query_feature_set is build_query_feature_set


def test_query_intent_helpers_keep_existing_classification_contract() -> None:
    assert classify_query_intent("TABLE 701.2") == QUERY_INTENT_TABULAR
    assert classify_query_intent("What is the main claim?") == QUERY_INTENT_PROSE_LOOKUP
    assert (
        classify_query_intent(
            "Summarize the wildfire planning constraints and explain how they interact."
        )
        == QUERY_INTENT_PROSE_BROAD
    )
    assert is_tabular_query("row and column limits") is True
    assert is_tabular_query("fseprd1091222") is False


def test_query_feature_helpers_keep_identifier_and_overlap_contracts() -> None:
    query_features = build_query_feature_set("Chalk Buttes Cover Letter")

    assert query_features.normalized_query == "chalk buttes cover letter"
    assert query_features.rare_tokens == frozenset()
    assert token_coverage(query_features, "Chalk Buttes") == 0.5
    assert looks_like_identifier_lookup("fseprd1091222.pdf") is True
    assert looks_like_identifier_lookup("Consolidated BPA MOU 5-1-18") is False
    assert metadata_query_tokens("Chalk Buttes Cover Letter") == [
        "buttes",
        "chalk",
        "cover",
        "letter",
    ]
