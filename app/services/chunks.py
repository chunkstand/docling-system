from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.schemas.chunks import DocumentChunkResponse
from app.services.documents import get_document_or_404


def get_active_chunks(session: Session, document_id: UUID) -> list[DocumentChunkResponse]:
    document = get_document_or_404(session, document_id)
    if document.active_run_id is None:
        return []

    rows = session.execute(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.run_id == document.active_run_id,
        )
        .order_by(DocumentChunk.chunk_index)
    ).scalars()

    return [
        DocumentChunkResponse(
            chunk_id=row.id,
            document_id=row.document_id,
            run_id=row.run_id,
            chunk_index=row.chunk_index,
            text=row.text,
            heading=row.heading,
            page_from=row.page_from,
            page_to=row.page_to,
            metadata=row.metadata_json,
            created_at=row.created_at,
        )
        for row in rows
    ]
