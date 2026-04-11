from __future__ import annotations

import uvicorn
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, File, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.db.models import DocumentFigure, DocumentRun, DocumentTable
from app.db.session import get_db_session
from app.schemas.chunks import DocumentChunkResponse
from app.schemas.documents import DocumentDetailResponse, DocumentSummaryResponse, DocumentUploadResponse
from app.schemas.evaluations import EvaluationDetailResponse
from app.schemas.figures import DocumentFigureDetailResponse, DocumentFigureSummaryResponse
from app.schemas.search import SearchRequest, SearchResult
from app.schemas.tables import DocumentTableDetailResponse, DocumentTableSummaryResponse
from app.services.chunks import get_active_chunks
from app.services.documents import (
    get_document_detail,
    get_latest_document_evaluation_detail,
    ingest_upload,
    list_documents,
    reprocess_document,
)
from app.services.figures import get_active_figure_detail, get_active_figures
from app.services.search import search_documents
from app.services.storage import StorageService
from app.services.tables import get_active_table_detail, get_active_tables
from app.services.telemetry import snapshot_metrics


app = FastAPI(title="Docling System", version="0.1.0")
UI_DIR = Path(__file__).resolve().parent.parent / "ui"
app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return StorageService()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, float]:
    return snapshot_metrics()


@app.get("/documents", response_model=list[DocumentSummaryResponse])
def read_documents(session: Session = Depends(get_db_session)) -> list[DocumentSummaryResponse]:
    return list_documents(session)


@app.post("/documents", response_model=DocumentUploadResponse)
async def create_document(
    response: Response,
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    payload, status_code = await ingest_upload(
        session=session,
        upload=file,
        storage_service=get_storage_service(),
    )
    response.status_code = status_code
    return payload


@app.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def read_document(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentDetailResponse:
    return get_document_detail(session, document_id)


@app.get("/documents/{document_id}/evaluations/latest", response_model=EvaluationDetailResponse)
def read_latest_document_evaluation(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> EvaluationDetailResponse:
    return get_latest_document_evaluation_detail(session, document_id)


@app.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkResponse])
def read_document_chunks(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentChunkResponse]:
    return get_active_chunks(session, document_id)


@app.get("/documents/{document_id}/tables", response_model=list[DocumentTableSummaryResponse])
def read_document_tables(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentTableSummaryResponse]:
    return get_active_tables(session, document_id)


@app.get("/documents/{document_id}/tables/{table_id}", response_model=DocumentTableDetailResponse)
def read_document_table(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentTableDetailResponse:
    return get_active_table_detail(session, document_id, table_id)


@app.get("/documents/{document_id}/figures", response_model=list[DocumentFigureSummaryResponse])
def read_document_figures(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentFigureSummaryResponse]:
    return get_active_figures(session, document_id)


@app.get("/documents/{document_id}/figures/{figure_id}", response_model=DocumentFigureDetailResponse)
def read_document_figure(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentFigureDetailResponse:
    return get_active_figure_detail(session, document_id, figure_id)


@app.post("/documents/{document_id}/reprocess", response_model=DocumentUploadResponse)
def reprocess_existing_document(
    document_id: UUID,
    response: Response,
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    response.status_code = 202
    return reprocess_document(session, document_id)


@app.get("/documents/{document_id}/artifacts/json")
def read_docling_json_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_json_artifact or document.active_run_id is None:
        return Response(status_code=404)
    run = session.get(DocumentRun, document.active_run_id)
    if run is None or not run.docling_json_path:
        return Response(status_code=404)
    return FileResponse(Path(run.docling_json_path))


@app.get("/documents/{document_id}/artifacts/yaml")
def read_yaml_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_yaml_artifact or document.active_run_id is None:
        return Response(status_code=404)
    run = session.get(DocumentRun, document.active_run_id)
    if run is None or not run.yaml_path:
        return Response(status_code=404)
    return FileResponse(Path(run.yaml_path))


def _get_active_table_row(session: Session, document_id: UUID, table_id: UUID) -> DocumentTable | None:
    document = get_document_detail(session, document_id)
    if document.active_run_id is None:
        return None
    table = session.get(DocumentTable, table_id)
    if table is None or table.run_id != document.active_run_id or table.document_id != document_id:
        return None
    return table


def _get_active_figure_row(session: Session, document_id: UUID, figure_id: UUID) -> DocumentFigure | None:
    document = get_document_detail(session, document_id)
    if document.active_run_id is None:
        return None
    figure = session.get(DocumentFigure, figure_id)
    if figure is None or figure.run_id != document.active_run_id or figure.document_id != document_id:
        return None
    return figure


@app.get("/documents/{document_id}/tables/{table_id}/artifacts/json")
def read_table_json_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None or not table.json_path:
        return Response(status_code=404)
    return FileResponse(Path(table.json_path))


@app.get("/documents/{document_id}/tables/{table_id}/artifacts/yaml")
def read_table_yaml_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None or not table.yaml_path:
        return Response(status_code=404)
    return FileResponse(Path(table.yaml_path))


@app.get("/documents/{document_id}/figures/{figure_id}/artifacts/json")
def read_figure_json_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None or not figure.json_path:
        return Response(status_code=404)
    return FileResponse(Path(figure.json_path))


@app.get("/documents/{document_id}/figures/{figure_id}/artifacts/yaml")
def read_figure_yaml_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None or not figure.yaml_path:
        return Response(status_code=404)
    return FileResponse(Path(figure.yaml_path))


@app.post("/search", response_model=list[SearchResult])
def search_corpus(
    request: SearchRequest,
    session: Session = Depends(get_db_session),
) -> list[SearchResult]:
    return search_documents(session, request)


def run() -> None:
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
