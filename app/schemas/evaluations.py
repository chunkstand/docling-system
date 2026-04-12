from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EvaluationSummaryResponse(BaseModel):
    evaluation_id: UUID
    run_id: UUID
    corpus_name: str
    fixture_name: str | None = None
    status: str
    query_count: int = 0
    passed_queries: int = 0
    failed_queries: int = 0
    regressed_queries: int = 0
    improved_queries: int = 0
    stable_queries: int = 0
    baseline_run_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class EvaluationQueryResultResponse(BaseModel):
    query_text: str
    mode: str
    evaluation_kind: str = "retrieval"
    expected_result_type: str | None = None
    expected_top_n: int | None = None
    passed: bool
    candidate_rank: int | None = None
    baseline_rank: int | None = None
    rank_delta: int | None = None
    candidate_score: float | None = None
    baseline_score: float | None = None
    candidate_result_type: str | None = None
    baseline_result_type: str | None = None
    candidate_label: str | None = None
    baseline_label: str | None = None
    details: dict


class EvaluationDetailResponse(EvaluationSummaryResponse):
    summary: dict
    query_results: list[EvaluationQueryResultResponse]
