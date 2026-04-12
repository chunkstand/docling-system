from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class QualityFailureStageCountResponse(BaseModel):
    failure_stage: str
    run_count: int


class QualityEvaluationStatusResponse(BaseModel):
    document_id: UUID
    source_filename: str
    title: str | None = None
    latest_run_id: UUID | None = None
    latest_run_status: str | None = None
    latest_validation_status: str | None = None
    evaluation_id: UUID | None = None
    evaluation_status: str
    fixture_name: str | None = None
    query_count: int = 0
    passed_queries: int = 0
    failed_queries: int = 0
    regressed_queries: int = 0
    improved_queries: int = 0
    stable_queries: int = 0
    failed_structural_checks: int = 0
    structural_passed: bool | None = None
    error_message: str | None = None
    updated_at: datetime


class QualityRunFailureResponse(BaseModel):
    document_id: UUID
    source_filename: str
    title: str | None = None
    run_id: UUID
    run_number: int
    status: str
    failure_stage: str | None = None
    error_message: str | None = None
    has_failure_artifact: bool = False
    created_at: datetime
    completed_at: datetime | None = None


class QualitySummaryResponse(BaseModel):
    document_count: int
    latest_runs_completed: int
    documents_with_latest_evaluation: int
    missing_latest_evaluations: int
    completed_latest_evaluations: int
    failed_latest_evaluations: int
    skipped_latest_evaluations: int
    total_failed_queries: int
    documents_with_failed_queries: int
    total_failed_structural_checks: int
    documents_with_structural_failures: int
    failed_run_count: int
    failed_runs_by_stage: list[QualityFailureStageCountResponse]


class QualityFailuresResponse(BaseModel):
    evaluation_failures: list[QualityEvaluationStatusResponse]
    run_failures: list[QualityRunFailureResponse]
