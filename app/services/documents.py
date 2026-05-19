from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.services.document_ingest import allowed_ingest_roots, ingest_local_file, ingest_upload
from app.services.document_run_queue import create_run_for_existing_document, reprocess_document
from app.services.document_run_views import (
    get_document_detail,
    get_document_or_404,
    get_document_run_summary,
    list_document_runs,
    list_documents,
)
from app.services.document_run_views import (
    to_run_summary as _to_run_summary,
)

__all__ = [
    "_to_run_summary", "allowed_ingest_roots",
    "create_run_for_existing_document", "get_document_detail",
    "get_document_or_404",
    "get_document_run_summary",
    "get_latest_document_evaluation",
    "get_latest_document_evaluation_detail",
    "ingest_local_file", "ingest_upload",
    "list_document_runs", "list_documents", "reprocess_document",
]


def get_latest_document_evaluation(session: Session, document_id: UUID):
    import app.services.evaluations as evaluation_service

    document = get_document_or_404(session, document_id)
    return evaluation_service.get_latest_document_evaluation(session, document)


def get_latest_document_evaluation_detail(session: Session, document_id: UUID):
    evaluation = get_latest_document_evaluation(session, document_id)
    if evaluation is None:
        raise api_error(
            404,
            "document_evaluation_not_found",
            "No evaluation found for the document.",
            document_id=str(document_id),
        )
    return evaluation
