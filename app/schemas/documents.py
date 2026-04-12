from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.evaluations import EvaluationSummaryResponse


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    run_id: UUID | None = None
    status: str
    duplicate: bool
    recovery_run: bool = False
    active_run_id: UUID | None = None
    active_run_status: str | None = None


class DocumentSummaryResponse(BaseModel):
    document_id: UUID
    source_filename: str
    title: str | None
    active_run_id: UUID | None
    active_run_status: str | None
    latest_run_id: UUID | None
    latest_run_status: str | None
    latest_validation_status: str | None = None
    latest_run_promoted: bool = False
    table_count: int = 0
    has_table_artifacts: bool = False
    figure_count: int = 0
    has_figure_artifacts: bool = False
    latest_evaluation: EvaluationSummaryResponse | None = None
    updated_at: datetime


class DocumentDetailResponse(BaseModel):
    document_id: UUID
    source_filename: str
    title: str | None
    active_run_id: UUID | None
    active_run_status: str | None
    latest_run_id: UUID | None
    latest_run_status: str | None
    latest_validation_status: str | None = None
    latest_run_promoted: bool = False
    is_searchable: bool
    has_json_artifact: bool = False
    has_yaml_artifact: bool = False
    table_count: int = 0
    has_table_artifacts: bool = False
    figure_count: int = 0
    has_figure_artifacts: bool = False
    latest_evaluation: EvaluationSummaryResponse | None = None
    created_at: datetime
    updated_at: datetime
    latest_error_message: str | None = None


class DocumentRunSummaryResponse(BaseModel):
    run_id: UUID
    run_number: int
    status: str
    attempts: int
    validation_status: str | None = None
    chunk_count: int | None = None
    table_count: int | None = None
    figure_count: int | None = None
    error_message: str | None = None
    failure_stage: str | None = None
    has_failure_artifact: bool = False
    is_active_run: bool = False
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
