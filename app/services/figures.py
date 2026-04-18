from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentFigure
from app.schemas.figures import DocumentFigureDetailResponse, DocumentFigureSummaryResponse
from app.services.documents import get_document_or_404


def get_active_figures(session: Session, document_id: UUID) -> list[DocumentFigureSummaryResponse]:
    document = get_document_or_404(session, document_id)
    if document.active_run_id is None:
        return []

    rows = session.execute(
        select(DocumentFigure)
        .where(
            DocumentFigure.document_id == document_id,
            DocumentFigure.run_id == document.active_run_id,
        )
        .order_by(DocumentFigure.figure_index)
    ).scalars()

    return [
        DocumentFigureSummaryResponse(
            figure_id=row.id,
            document_id=row.document_id,
            run_id=row.run_id,
            figure_index=row.figure_index,
            source_figure_ref=row.source_figure_ref,
            caption=row.caption,
            heading=row.heading,
            page_from=row.page_from,
            page_to=row.page_to,
            confidence=row.confidence,
            created_at=row.created_at,
        )
        for row in rows
    ]


def get_active_figure_detail(
    session: Session, document_id: UUID, figure_id: UUID
) -> DocumentFigureDetailResponse:
    document = get_document_or_404(session, document_id)
    if document.active_run_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Figure not found.")

    figure = session.execute(
        select(DocumentFigure).where(
            DocumentFigure.id == figure_id,
            DocumentFigure.document_id == document_id,
            DocumentFigure.run_id == document.active_run_id,
        )
    ).scalar_one_or_none()
    if figure is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Figure not found.")

    return DocumentFigureDetailResponse(
        figure_id=figure.id,
        document_id=figure.document_id,
        run_id=figure.run_id,
        figure_index=figure.figure_index,
        source_figure_ref=figure.source_figure_ref,
        caption=figure.caption,
        heading=figure.heading,
        page_from=figure.page_from,
        page_to=figure.page_to,
        confidence=figure.confidence,
        created_at=figure.created_at,
        has_json_artifact=bool(figure.json_path),
        has_yaml_artifact=bool(figure.yaml_path),
        status=figure.status,
        metadata=figure.metadata_json,
    )
