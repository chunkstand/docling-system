from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    run_id: UUID | None = None
    status: str
    duplicate: bool
    recovery_run: bool = False
    active_run_id: UUID | None = None
    active_run_status: str | None = None


class DocumentDetailResponse(BaseModel):
    document_id: UUID
    source_filename: str
    title: str | None
    active_run_id: UUID | None
    active_run_status: str | None
    latest_run_id: UUID | None
    latest_run_status: str | None
    is_searchable: bool
    has_json_artifact: bool = False
    has_markdown_artifact: bool = False
    created_at: datetime
    updated_at: datetime
    latest_error_message: str | None = None
