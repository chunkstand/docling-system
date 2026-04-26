from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.db.models import DocumentFigure, DocumentRun, DocumentTable
from app.schemas.chunks import DocumentChunkResponse
from app.schemas.documents import (
    DocumentDetailResponse,
    DocumentRunSummaryResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
)
from app.schemas.figures import DocumentFigureDetailResponse, DocumentFigureSummaryResponse
from app.schemas.tables import DocumentTableDetailResponse, DocumentTableSummaryResponse
from app.services import chunks, documents, figures, runs, tables
from app.services.docling_parser import DoclingParser
from app.services.embeddings import EmbeddingProvider
from app.services.storage import StorageService


class RunLifecycleCapability(Protocol):
    def list_documents(
        self,
        session: Session,
        *,
        limit: int = 50,
    ) -> list[DocumentSummaryResponse]: ...

    def ingest_upload(
        self,
        *,
        session: Session,
        upload: UploadFile,
        storage_service: StorageService,
        idempotency_key: str | None = None,
    ) -> tuple[DocumentUploadResponse, int]: ...

    def get_document_detail(
        self,
        session: Session,
        document_id: UUID,
    ) -> DocumentDetailResponse: ...

    def list_document_runs(
        self,
        session: Session,
        document_id: UUID,
    ) -> list[DocumentRunSummaryResponse]: ...

    def get_document_run_summary(
        self,
        session: Session,
        run_id: UUID,
    ) -> DocumentRunSummaryResponse: ...

    def reprocess_document(
        self,
        session: Session,
        document_id: UUID,
        *,
        idempotency_key: str | None = None,
    ) -> DocumentUploadResponse: ...

    def get_active_chunks(
        self,
        session: Session,
        document_id: UUID,
    ) -> list[DocumentChunkResponse]: ...

    def get_active_tables(
        self,
        session: Session,
        document_id: UUID,
    ) -> list[DocumentTableSummaryResponse]: ...

    def get_active_table_detail(
        self,
        session: Session,
        document_id: UUID,
        table_id: UUID,
    ) -> DocumentTableDetailResponse: ...

    def get_active_figures(
        self,
        session: Session,
        document_id: UUID,
    ) -> list[DocumentFigureSummaryResponse]: ...

    def get_active_figure_detail(
        self,
        session: Session,
        document_id: UUID,
        figure_id: UUID,
    ) -> DocumentFigureDetailResponse: ...

    def get_run_row(self, session: Session, run_id: UUID) -> DocumentRun | None: ...

    def get_active_table_row(
        self,
        session: Session,
        document_id: UUID,
        table_id: UUID,
    ) -> DocumentTable | None: ...

    def get_active_figure_row(
        self,
        session: Session,
        document_id: UUID,
        figure_id: UUID,
    ) -> DocumentFigure | None: ...

    def process_run(
        self,
        session: Session,
        run_id: UUID,
        storage_service: StorageService,
        parser: DoclingParser,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None: ...

    def run_worker_loop(self) -> None: ...


class ServicesRunLifecycleCapability:
    def list_documents(self, session: Session, *, limit: int = 50) -> list[DocumentSummaryResponse]:
        return documents.list_documents(session, limit=limit)

    def ingest_upload(
        self,
        *,
        session: Session,
        upload: UploadFile,
        storage_service: StorageService,
        idempotency_key: str | None = None,
    ) -> tuple[DocumentUploadResponse, int]:
        return documents.ingest_upload(
            session=session,
            upload=upload,
            storage_service=storage_service,
            idempotency_key=idempotency_key,
        )

    def get_document_detail(self, session: Session, document_id: UUID) -> DocumentDetailResponse:
        return documents.get_document_detail(session, document_id)

    def list_document_runs(
        self,
        session: Session,
        document_id: UUID,
    ) -> list[DocumentRunSummaryResponse]:
        return documents.list_document_runs(session, document_id)

    def get_document_run_summary(
        self,
        session: Session,
        run_id: UUID,
    ) -> DocumentRunSummaryResponse:
        return documents.get_document_run_summary(session, run_id)

    def reprocess_document(
        self,
        session: Session,
        document_id: UUID,
        *,
        idempotency_key: str | None = None,
    ) -> DocumentUploadResponse:
        return documents.reprocess_document(session, document_id, idempotency_key=idempotency_key)

    def get_active_chunks(
        self,
        session: Session,
        document_id: UUID,
    ) -> list[DocumentChunkResponse]:
        return chunks.get_active_chunks(session, document_id)

    def get_active_tables(
        self,
        session: Session,
        document_id: UUID,
    ) -> list[DocumentTableSummaryResponse]:
        return tables.get_active_tables(session, document_id)

    def get_active_table_detail(
        self,
        session: Session,
        document_id: UUID,
        table_id: UUID,
    ) -> DocumentTableDetailResponse:
        return tables.get_active_table_detail(session, document_id, table_id)

    def get_active_figures(
        self,
        session: Session,
        document_id: UUID,
    ) -> list[DocumentFigureSummaryResponse]:
        return figures.get_active_figures(session, document_id)

    def get_active_figure_detail(
        self,
        session: Session,
        document_id: UUID,
        figure_id: UUID,
    ) -> DocumentFigureDetailResponse:
        return figures.get_active_figure_detail(session, document_id, figure_id)

    def get_run_row(self, session: Session, run_id: UUID) -> DocumentRun | None:
        return session.get(DocumentRun, run_id)

    def get_active_table_row(
        self,
        session: Session,
        document_id: UUID,
        table_id: UUID,
    ) -> DocumentTable | None:
        document = self.get_document_detail(session, document_id)
        if document.active_run_id is None:
            return None
        table = session.get(DocumentTable, table_id)
        if (
            table is None
            or table.run_id != document.active_run_id
            or table.document_id != document_id
        ):
            return None
        return table

    def get_active_figure_row(
        self,
        session: Session,
        document_id: UUID,
        figure_id: UUID,
    ) -> DocumentFigure | None:
        document = self.get_document_detail(session, document_id)
        if document.active_run_id is None:
            return None
        figure = session.get(DocumentFigure, figure_id)
        if (
            figure is None
            or figure.run_id != document.active_run_id
            or figure.document_id != document_id
        ):
            return None
        return figure

    def process_run(
        self,
        session: Session,
        run_id: UUID,
        storage_service: StorageService,
        parser: DoclingParser,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        runs.process_run(
            session,
            run_id,
            storage_service,
            parser,
            embedding_provider=embedding_provider,
        )

    def run_worker_loop(self) -> None:
        runs.run_worker_loop()

run_lifecycle: RunLifecycleCapability = ServicesRunLifecycleCapability()
