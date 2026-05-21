from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LinearRerankerConfig:
    harness_name: str
    reranker_name: str
    reranker_version: str
    retrieval_profile_name: str
    tabular_table_bonus: float
    title_exact_match_bonus: float
    title_token_coverage_bonus: float
    source_filename_exact_match_bonus: float
    source_filename_token_coverage_bonus: float
    document_title_exact_match_bonus: float
    document_title_token_coverage_bonus: float
    prose_document_cluster_bonus: float
    heading_token_coverage_bonus: float
    phrase_overlap_bonus: float
    rare_token_overlap_bonus: float
    adjacent_chunk_context_bonus: float
    prose_table_penalty: float
    exact_filter_bonus: float
    result_type_priority_bonus: float

    def snapshot(self) -> dict:
        return asdict(self)
