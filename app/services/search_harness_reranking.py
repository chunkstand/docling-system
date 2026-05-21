from __future__ import annotations

from collections.abc import Callable

import app.services.search_query_features as _query_features
import app.services.search_ranking as _search_ranking
from app.schemas.search import SearchRequest
from app.services.search_harness_contracts import LinearRerankerConfig
from app.services.search_query_features import QueryFeatureSet

QUERY_INTENT_TABULAR = _query_features.QUERY_INTENT_TABULAR

RankedResult = _search_ranking.RankedResult
RerankedResult = _search_ranking.RerankedResult
document_query_overlap_features = _search_ranking.document_query_overlap_features
prose_query_match_features = _search_ranking.prose_query_match_features
table_title_match_features = _search_ranking.table_title_match_features
exact_filter_priority = _search_ranking.exact_filter_priority
result_type_priority = _search_ranking.result_type_priority
document_cluster_strengths = _search_ranking.document_cluster_strengths


class LinearFeatureSearchReranker:
    def __init__(self, config: LinearRerankerConfig) -> None:
        self.config = config
        self.name = config.reranker_name

    def rerank(
        self,
        items: list[RankedResult],
        *,
        request: SearchRequest,
        score_getter: Callable[[RankedResult], float],
        tabular_query: bool,
        query_intent: str,
        query_features: QueryFeatureSet | None = None,
    ) -> list[RerankedResult]:
        active_query_features = query_features or _query_features.build_query_feature_set(
            request.query
        )
        base_ranked = sorted(
            items,
            key=lambda item: (
                -score_getter(item),
                item.page_from if item.page_from is not None else 10**9,
                str(item.result_id),
            ),
        )

        cluster_strengths = document_cluster_strengths(
            base_ranked,
            score_getter=score_getter,
            query_intent=query_intent,
        )
        annotated: list[RerankedResult] = []
        for base_rank, item in enumerate(base_ranked, start=1):
            base_score = score_getter(item)
            tabular_table_signal = int(tabular_query and item.result_type == "table")
            title_match = table_title_match_features(item, active_query_features)
            document_overlap = document_query_overlap_features(
                item,
                active_query_features,
            )
            prose_match = prose_query_match_features(item, active_query_features)
            exact_priority = exact_filter_priority(item, request.filters)
            type_priority = result_type_priority(item, tabular_query)
            cluster_strength = cluster_strengths.get(item.document_id, 0.0)
            title_match_boost = (
                title_match["title_exact_match"] * self.config.title_exact_match_bonus
                + title_match["title_token_coverage"] * self.config.title_token_coverage_bonus
            )
            source_filename_exact_match_boost = (
                document_overlap["source_filename_exact_match"]
                * self.config.source_filename_exact_match_bonus
            )
            source_filename_boost = (
                document_overlap["source_filename_token_coverage"]
                * self.config.source_filename_token_coverage_bonus
            )
            document_title_exact_match_boost = (
                document_overlap["document_title_exact_match"]
                * self.config.document_title_exact_match_bonus
            )
            document_title_boost = (
                document_overlap["document_title_token_coverage"]
                * self.config.document_title_token_coverage_bonus
            )
            prose_document_cluster_boost = (
                cluster_strength * self.config.prose_document_cluster_bonus
            )
            heading_boost = (
                prose_match["heading_token_coverage"] * self.config.heading_token_coverage_bonus
            )
            phrase_overlap_boost = (
                prose_match["phrase_overlap"] * self.config.phrase_overlap_bonus
            )
            rare_token_overlap_boost = (
                prose_match["rare_token_overlap"] * self.config.rare_token_overlap_bonus
            )
            adjacent_chunk_context_boost = (
                prose_match["adjacent_chunk_context_signal"]
                * self.config.adjacent_chunk_context_bonus
            )
            late_interaction_signal = float(
                "multivector_late_interaction" in item.retrieval_sources
            )
            tabular_boost = tabular_table_signal * self.config.tabular_table_bonus
            prose_table_penalty = (
                self.config.prose_table_penalty
                if query_intent != QUERY_INTENT_TABULAR and item.result_type == "table"
                else 0.0
            )
            exact_filter_boost = exact_priority * self.config.exact_filter_bonus
            result_type_priority_boost = type_priority * self.config.result_type_priority_bonus
            final_score = (
                base_score
                + tabular_boost
                + title_match_boost
                + source_filename_exact_match_boost
                + source_filename_boost
                + document_title_exact_match_boost
                + document_title_boost
                + prose_document_cluster_boost
                + heading_boost
                + phrase_overlap_boost
                + rare_token_overlap_boost
                + adjacent_chunk_context_boost
                - prose_table_penalty
                + exact_filter_boost
                + result_type_priority_boost
            )
            annotated.append(
                RerankedResult(
                    item=item,
                    rank=0,
                    base_rank=base_rank,
                    score=final_score,
                    features={
                        "base_score": base_score,
                        "harness_name": self.config.harness_name,
                        "reranker_name": self.config.reranker_name,
                        "reranker_version": self.config.reranker_version,
                        "retrieval_profile_name": self.config.retrieval_profile_name,
                        "tabular_table_signal": tabular_table_signal,
                        "tabular_boost": tabular_boost,
                        "title_exact_match": title_match["title_exact_match"],
                        "title_token_coverage": title_match["title_token_coverage"],
                        "title_match_boost": title_match_boost,
                        "source_filename_exact_match": document_overlap[
                            "source_filename_exact_match"
                        ],
                        "source_filename_exact_match_boost": source_filename_exact_match_boost,
                        "source_filename_token_coverage": document_overlap[
                            "source_filename_token_coverage"
                        ],
                        "source_filename_boost": source_filename_boost,
                        "document_title_exact_match": document_overlap[
                            "document_title_exact_match"
                        ],
                        "document_title_exact_match_boost": document_title_exact_match_boost,
                        "document_title_token_coverage": document_overlap[
                            "document_title_token_coverage"
                        ],
                        "document_title_boost": document_title_boost,
                        "document_cluster_strength": cluster_strength,
                        "prose_document_cluster_boost": prose_document_cluster_boost,
                        "heading_token_coverage": prose_match["heading_token_coverage"],
                        "heading_boost": heading_boost,
                        "phrase_overlap": prose_match["phrase_overlap"],
                        "phrase_overlap_boost": phrase_overlap_boost,
                        "rare_token_overlap": prose_match["rare_token_overlap"],
                        "rare_token_overlap_boost": rare_token_overlap_boost,
                        "adjacent_chunk_context_signal": prose_match[
                            "adjacent_chunk_context_signal"
                        ],
                        "adjacent_chunk_context_boost": adjacent_chunk_context_boost,
                        "late_interaction_signal": late_interaction_signal,
                        "prose_table_penalty": prose_table_penalty,
                        "exact_filter_priority": exact_priority,
                        "exact_filter_boost": exact_filter_boost,
                        "result_type_priority": type_priority,
                        "result_type_priority_boost": result_type_priority_boost,
                        "query_intent": query_intent,
                        "retrieval_sources": list(item.retrieval_sources),
                        "final_score": final_score,
                    },
                )
            )

        ranked = sorted(
            annotated,
            key=lambda candidate: (
                -candidate.score,
                -candidate.features["exact_filter_priority"],
                -candidate.features["result_type_priority"],
                candidate.item.page_from if candidate.item.page_from is not None else 10**9,
                str(candidate.item.result_id),
            ),
        )[: request.limit]

        for rank, candidate in enumerate(ranked, start=1):
            candidate.rank = rank
        return ranked
