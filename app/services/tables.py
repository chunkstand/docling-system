from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import DocumentTable, DocumentTableSegment
from app.schemas.tables import (
    DocumentTableDetailResponse,
    DocumentTableSegmentResponse,
    DocumentTableSummaryResponse,
)
from app.services.documents import get_document_or_404


def get_active_tables(session: Session, document_id: UUID) -> list[DocumentTableSummaryResponse]:
    document = get_document_or_404(session, document_id)
    if document.active_run_id is None:
        return []

    rows = session.execute(
        select(DocumentTable)
        .where(
            DocumentTable.document_id == document_id,
            DocumentTable.run_id == document.active_run_id,
        )
        .order_by(DocumentTable.table_index)
    ).scalars()

    return [
        DocumentTableSummaryResponse(
            table_id=row.id,
            document_id=row.document_id,
            run_id=row.run_id,
            table_index=row.table_index,
            title=row.title,
            logical_table_key=row.logical_table_key,
            heading=row.heading,
            page_from=row.page_from,
            page_to=row.page_to,
            row_count=row.row_count,
            col_count=row.col_count,
            preview_text=row.preview_text,
            created_at=row.created_at,
        )
        for row in rows
    ]


def get_active_table_detail(
    session: Session, document_id: UUID, table_id: UUID
) -> DocumentTableDetailResponse:
    document = get_document_or_404(session, document_id)
    if document.active_run_id is None:
        raise api_error(
            404,
            "table_not_found",
            "Table not found.",
            document_id=str(document_id),
            table_id=str(table_id),
        )

    table = session.execute(
        select(DocumentTable).where(
            DocumentTable.id == table_id,
            DocumentTable.document_id == document_id,
            DocumentTable.run_id == document.active_run_id,
        )
    ).scalar_one_or_none()
    if table is None:
        raise api_error(
            404,
            "table_not_found",
            "Table not found.",
            document_id=str(document_id),
            table_id=str(table_id),
        )

    segments = session.execute(
        select(DocumentTableSegment)
        .where(
            DocumentTableSegment.table_id == table.id,
            DocumentTableSegment.run_id == table.run_id,
        )
        .order_by(DocumentTableSegment.segment_order, DocumentTableSegment.segment_index)
    ).scalars()

    return DocumentTableDetailResponse(
        table_id=table.id,
        document_id=table.document_id,
        run_id=table.run_id,
        table_index=table.table_index,
        title=table.title,
        logical_table_key=table.logical_table_key,
        heading=table.heading,
        page_from=table.page_from,
        page_to=table.page_to,
        row_count=table.row_count,
        col_count=table.col_count,
        preview_text=table.preview_text,
        created_at=table.created_at,
        has_json_artifact=bool(table.json_path),
        has_yaml_artifact=bool(table.yaml_path),
        table_version=table.table_version,
        lineage_group=table.lineage_group,
        supersedes_table_id=table.supersedes_table_id,
        metadata=table.metadata_json,
        segments=[
            DocumentTableSegmentResponse(
                segment_index=segment.segment_index,
                source_table_ref=segment.source_table_ref,
                page_from=segment.page_from,
                page_to=segment.page_to,
                segment_order=segment.segment_order,
                metadata=segment.metadata_json,
            )
            for segment in segments
        ],
    )
