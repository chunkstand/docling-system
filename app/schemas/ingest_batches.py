from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IngestBatchItemResponse(BaseModel):
    batch_item_id: UUID
    relative_path: str
    source_filename: str
    source_path: str
    file_size_bytes: int | None = None
    sha256: str | None = None
    status: str
    status_code: int | None = None
    document_id: UUID | None = None
    run_id: UUID | None = None
    current_run_status: str | None = None
    resolved_status: str | None = None
    resolution_reason: str | None = None
    resolved_document_id: UUID | None = None
    resolved_run_id: UUID | None = None
    resolved_at: datetime | None = None
    duplicate: bool = False
    recovery_run: bool = False
    error_message: str | None = None
    created_at: datetime


class IngestBatchSummaryResponse(BaseModel):
    batch_id: UUID
    source_type: str
    status: str
    root_path: str | None = None
    recursive: bool = False
    file_count: int = 0
    queued_count: int = 0
    recovery_queued_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    run_status_counts: dict[str, int] = Field(default_factory=dict)
    resolution_counts: dict[str, int] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class IngestBatchDetailResponse(IngestBatchSummaryResponse):
    items: list[IngestBatchItemResponse] = Field(default_factory=list)
