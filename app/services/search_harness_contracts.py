from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Protocol

import app.services.search_harness_reranking as _reranking
from app.schemas.search import SearchRequest
from app.services.search_harness_reranker_config import LinearRerankerConfig

if TYPE_CHECKING:
    from app.services.search_query_features import QueryFeatureSet
    from app.services.search_ranking import RankedResult, RerankedResult


class SearchReranker(Protocol):
    name: str

    def rerank(
        self,
        items: list[RankedResult],
        *,
        request: SearchRequest,
        score_getter: Callable[[RankedResult], float],
        tabular_query: bool,
        query_intent: str,
        query_features: QueryFeatureSet | None = None,
    ) -> list[RerankedResult]: ...


@dataclass(frozen=True)
class SearchRetrievalProfile:
    name: str
    keyword_candidate_multiplier: int
    semantic_candidate_multiplier: int
    min_candidate_limit: int
    late_interaction_enabled: bool = False
    late_interaction_candidate_multiplier: int = 6
    late_interaction_min_candidate_limit: int = 24

    def snapshot(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SearchHarness:
    name: str
    retrieval_profile: SearchRetrievalProfile
    reranker_config: LinearRerankerConfig
    base_harness_name: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def reranker_name(self) -> str:
        return self.reranker_config.reranker_name

    @property
    def reranker_version(self) -> str:
        return self.reranker_config.reranker_version

    @property
    def retrieval_profile_name(self) -> str:
        return self.retrieval_profile.name

    @property
    def config_snapshot(self) -> dict:
        snapshot = {
            "harness_name": self.name,
            "retrieval_profile": self.retrieval_profile.snapshot(),
            "reranker": self.reranker_config.snapshot(),
        }
        if self.base_harness_name is not None:
            snapshot["base_harness_name"] = self.base_harness_name
        if self.metadata:
            snapshot["metadata"] = self.metadata
        return snapshot

    def build_reranker(self) -> SearchReranker:
        return _reranking.LinearFeatureSearchReranker(self.reranker_config)
