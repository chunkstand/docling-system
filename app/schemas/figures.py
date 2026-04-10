from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentFigureSummaryResponse(BaseModel):
    figure_id: UUID
    document_id: UUID
    run_id: UUID
    figure_index: int
    source_figure_ref: str | None
    caption: str | None
    heading: str | None
    page_from: int | None
    page_to: int | None
    confidence: float | None
    created_at: datetime


class DocumentFigureDetailResponse(DocumentFigureSummaryResponse):
    has_json_artifact: bool = False
    has_yaml_artifact: bool = False
    status: str
    metadata: dict
