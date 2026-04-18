from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SearchStage(StrEnum):
    STRICT_KEYWORD = "strict_keyword"
    RELAXED_KEYWORD = "relaxed_keyword"
    METADATA_SUPPLEMENT = "metadata_supplement"
    SEMANTIC = "semantic"
    ADJACENT_CONTEXT = "adjacent_context"


class SearchCandidateStrategy(StrEnum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    SEMANTIC_WITH_KEYWORD_CONTEXT = "semantic_with_keyword_context"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class SearchExecutionPlan:
    stages: tuple[SearchStage, ...]
    candidate_strategy: SearchCandidateStrategy
    prose_query: bool


def build_search_execution_plan(
    *,
    request_mode: str,
    harness_name: str,
    query_intent: str,
    prose_lookup_intent: str,
    prose_broad_intent: str,
) -> SearchExecutionPlan:
    prose_query = query_intent in {prose_lookup_intent, prose_broad_intent}
    stages: list[SearchStage] = [SearchStage.STRICT_KEYWORD, SearchStage.RELAXED_KEYWORD]
    if prose_query:
        stages.append(SearchStage.METADATA_SUPPLEMENT)
    if request_mode != "keyword":
        stages.append(SearchStage.SEMANTIC)
    if harness_name == "prose_v3" and prose_query:
        stages.append(SearchStage.ADJACENT_CONTEXT)

    if request_mode == "semantic":
        strategy = (
            SearchCandidateStrategy.SEMANTIC_WITH_KEYWORD_CONTEXT
            if harness_name == "prose_v3" and prose_query
            else SearchCandidateStrategy.SEMANTIC
        )
    elif request_mode == "hybrid":
        strategy = SearchCandidateStrategy.HYBRID
    else:
        strategy = SearchCandidateStrategy.KEYWORD

    return SearchExecutionPlan(
        stages=tuple(stages),
        candidate_strategy=strategy,
        prose_query=prose_query,
    )
