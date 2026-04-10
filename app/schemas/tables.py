from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentTableSegmentResponse(BaseModel):
    segment_index: int
    source_table_ref: str | None
    page_from: int | None
    page_to: int | None
    segment_order: int
    metadata: dict


class DocumentTableSummaryResponse(BaseModel):
    table_id: UUID
    document_id: UUID
    run_id: UUID
    table_index: int
    title: str | None
    logical_table_key: str | None = None
    heading: str | None
    page_from: int | None
    page_to: int | None
    row_count: int | None
    col_count: int | None
    preview_text: str
    created_at: datetime


class DocumentTableDetailResponse(DocumentTableSummaryResponse):
    has_json_artifact: bool = False
    has_yaml_artifact: bool = False
    table_version: int | None = None
    lineage_group: str | None = None
    supersedes_table_id: UUID | None = None
    metadata: dict
    segments: list[DocumentTableSegmentResponse]
