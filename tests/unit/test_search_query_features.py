from __future__ import annotations

import app.services.search_query_features as query_features
from app.services import search
from app.services.search_query_features import (
    QUERY_INTENT_PROSE_BROAD,
    QUERY_INTENT_PROSE_LOOKUP,
    QUERY_INTENT_TABULAR,
    build_query_feature_set,
    classify_query_intent,
    is_tabular_query,
    looks_like_identifier_lookup,
    metadata_query_tokens,
    token_coverage,
)

SEARCH_FACADE_FUNCTION_ALIASES = {
    "is_tabular_query": "is_tabular_query",
    "_is_tabular_query": "is_tabular_query",
    "_classify_query_intent": "classify_query_intent",
    "_looks_like_identifier_lookup": "looks_like_identifier_lookup",
    "_normalize_text": "normalize_search_text",
    "_salient_tokens": "salient_tokens",
    "_salient_tokens_from_normalized": "salient_tokens_from_normalized",
    "_phrase_tokens_from_normalized": "phrase_tokens_from_normalized",
    "_query_phrases_from_normalized": "query_phrases_from_normalized",
    "_build_query_feature_set": "build_query_feature_set",
    "_coerce_query_feature_set": "coerce_query_feature_set",
    "_token_coverage": "token_coverage",
    "_strong_document_phrase_match": "strong_document_phrase_match",
    "_metadata_query_tokens": "metadata_query_tokens",
}


def test_query_feature_module_preserves_search_facade_compatibility() -> None:
    assert search.QueryFeatureSet is query_features.QueryFeatureSet
    assert search.TABULAR_REFERENCE_PATTERN is query_features.TABULAR_REFERENCE_PATTERN
    assert search.QUERY_INTENT_TABULAR == query_features.QUERY_INTENT_TABULAR
    assert search.QUERY_INTENT_PROSE_LOOKUP == query_features.QUERY_INTENT_PROSE_LOOKUP
    assert search.QUERY_INTENT_PROSE_BROAD == query_features.QUERY_INTENT_PROSE_BROAD

    for facade_name, target_name in SEARCH_FACADE_FUNCTION_ALIASES.items():
        assert getattr(search, facade_name) is getattr(query_features, target_name)


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
