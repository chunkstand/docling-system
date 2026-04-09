from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentChunkResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    run_id: UUID
    chunk_index: int
    text: str
    heading: str | None
    page_from: int | None
    page_to: int | None
    metadata: dict
    created_at: datetime
