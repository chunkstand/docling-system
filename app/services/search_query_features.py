from __future__ import annotations

import re
from dataclasses import dataclass

QUERY_INTENT_TABULAR = "tabular"
QUERY_INTENT_PROSE_LOOKUP = "prose_lookup"
QUERY_INTENT_PROSE_BROAD = "prose_broad"
TABULAR_REFERENCE_PATTERN = re.compile(r"\b\d+(?:\.\d+)+(?:\s*\(\s*\d+\s*\))?\b")


@dataclass(frozen=True)
class QueryFeatureSet:
    normalized_query: str
    normalized_tokens: frozenset[str]
    salient_tokens: frozenset[str]
    rare_tokens: frozenset[str]
    phrases: frozenset[str]


_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    }
)


def is_tabular_query(query: str) -> bool:
    normalized = query.lower()
    if any(token in normalized for token in ("table", "row", "column")):
        return True
    if any(op in normalized for op in (">", "<", ">=", "<=", "greater than", "less than")):
        return True
    if TABULAR_REFERENCE_PATTERN.search(normalized):
        return True
    return False


def classify_query_intent(query: str) -> str:
    if is_tabular_query(query):
        return QUERY_INTENT_TABULAR
    normalized = normalize_search_text(query)
    if not normalized:
        return QUERY_INTENT_PROSE_LOOKUP
    salient_count = len(salient_tokens(query))
    if (
        "?" in query
        or normalized.startswith(
            (
                "what ",
                "what is ",
                "what does ",
                "which ",
                "who ",
                "when ",
                "where ",
                "how many ",
                "how much ",
                "does ",
                "is ",
                "are ",
            )
        )
        or salient_count <= 6
    ):
        return QUERY_INTENT_PROSE_LOOKUP
    return QUERY_INTENT_PROSE_BROAD


def looks_like_identifier_lookup(query: str) -> bool:
    normalized = normalize_search_text(query)
    if not normalized:
        return False
    stripped = query.strip().lower()
    if stripped.endswith(".pdf"):
        return True
    compact = re.sub(r"\s+", "", stripped)
    has_alpha = any(char.isalpha() for char in compact)
    has_digit = any(char.isdigit() for char in compact)
    if " " not in stripped and has_alpha and has_digit and len(compact) >= 6:
        return True
    return (
        len(compact) >= 8
        and any(separator in stripped for separator in ("_", "-"))
        and len(stripped.split()) <= 3
    )


def normalize_search_text(value: str | None) -> str:
    if not value:
        return ""
    expanded = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", expanded)
    expanded = re.sub(r"(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])", " ", expanded)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", expanded.lower())).strip()


def salient_tokens(value: str | None) -> set[str]:
    return salient_tokens_from_normalized(normalize_search_text(value))


def salient_tokens_from_normalized(normalized: str) -> set[str]:
    if not normalized:
        return set()
    return {
        token for token in normalized.split() if len(token) >= 3 and token not in _QUERY_STOPWORDS
    }


def phrase_tokens_from_normalized(normalized: str) -> list[str]:
    return [token for token in normalized.split() if token not in _QUERY_STOPWORDS]


def query_phrases_from_normalized(normalized: str, phrase_size: int = 2) -> set[str]:
    tokens = phrase_tokens_from_normalized(normalized)
    if len(tokens) < phrase_size:
        return set()
    return {
        " ".join(tokens[idx : idx + phrase_size]) for idx in range(len(tokens) - phrase_size + 1)
    }


def build_query_feature_set(query: str | None) -> QueryFeatureSet:
    normalized_query = normalize_search_text(query)
    normalized_tokens = frozenset(normalized_query.split()) if normalized_query else frozenset()
    active_salient_tokens = frozenset(salient_tokens_from_normalized(normalized_query))
    return QueryFeatureSet(
        normalized_query=normalized_query,
        normalized_tokens=normalized_tokens,
        salient_tokens=active_salient_tokens,
        rare_tokens=frozenset(token for token in active_salient_tokens if len(token) >= 7),
        phrases=frozenset(query_phrases_from_normalized(normalized_query)),
    )


def coerce_query_feature_set(query_or_features: QueryFeatureSet | str | None) -> QueryFeatureSet:
    if isinstance(query_or_features, QueryFeatureSet):
        return query_or_features
    return build_query_feature_set(query_or_features)


def token_coverage(query_or_features: QueryFeatureSet | str | None, value: str | None) -> float:
    query_tokens = coerce_query_feature_set(query_or_features).salient_tokens
    value_tokens = salient_tokens(value)
    if not query_tokens or not value_tokens:
        return 0.0
    return len(query_tokens & value_tokens) / len(query_tokens)


def strong_document_phrase_match(
    query_or_features: QueryFeatureSet | str | None,
    value: str | None,
) -> float:
    normalized_query = coerce_query_feature_set(query_or_features).normalized_query
    normalized_value = normalize_search_text(value)
    if not normalized_query or not normalized_value:
        return 0.0

    value_tokens = normalized_value.split()
    if len(value_tokens) < 2 and len(normalized_value) < 8:
        return 0.0

    if normalized_query in normalized_value:
        return 1.0
    if normalized_value in normalized_query:
        return 1.0
    return 0.0


def metadata_query_tokens(value: str | None) -> list[str]:
    normalized = normalize_search_text(value)
    return sorted(set(phrase_tokens_from_normalized(normalized)))
