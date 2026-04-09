from __future__ import annotations

import uvicorn
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, File, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.models import DocumentRun
from app.db.session import get_db_session
from app.schemas.chunks import DocumentChunkResponse
from app.schemas.documents import DocumentDetailResponse, DocumentUploadResponse
from app.schemas.search import SearchRequest, SearchResult
from app.services.documents import get_document_detail, ingest_upload, reprocess_document
from app.services.runs import get_active_chunks
from app.services.search import search_chunks
from app.services.storage import StorageService


app = FastAPI(title="Docling System", version="0.1.0")


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return StorageService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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


@app.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkResponse])
def read_document_chunks(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentChunkResponse]:
    return get_active_chunks(session, document_id)


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


@app.get("/documents/{document_id}/artifacts/markdown")
def read_markdown_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_markdown_artifact or document.active_run_id is None:
        return Response(status_code=404)
    run = session.get(DocumentRun, document.active_run_id)
    if run is None or not run.markdown_path:
        return Response(status_code=404)
    return FileResponse(Path(run.markdown_path))


@app.post("/search", response_model=list[SearchResult])
def search_documents(
    request: SearchRequest,
    session: Session = Depends(get_db_session),
) -> list[SearchResult]:
    return search_chunks(session, request)


def run() -> None:
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=False)
