from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_storage_service,
    require_api_capability,
    require_api_key_for_mutations,
    response_field,
    storage_file_response,
)
from app.api.errors import api_error
from app.db.models import DocumentFigure, DocumentRun, DocumentTable
from app.db.session import get_db_session
from app.schemas.chunks import DocumentChunkResponse
from app.schemas.documents import (
    DocumentDetailResponse,
    DocumentRunSummaryResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
)
from app.schemas.evaluations import EvaluationDetailResponse
from app.schemas.figures import DocumentFigureDetailResponse, DocumentFigureSummaryResponse
from app.schemas.tables import DocumentTableDetailResponse, DocumentTableSummaryResponse
from app.services.chunks import get_active_chunks
from app.services.documents import (
    get_document_detail,
    get_document_run_summary,
    get_latest_document_evaluation_detail,
    ingest_upload,
    list_document_runs,
    list_documents,
    reprocess_document,
)
from app.services.eval_workbench import explain_latest_document_evaluation
from app.services.figures import get_active_figure_detail, get_active_figures
from app.services.tables import get_active_table_detail, get_active_tables

router = APIRouter()


@router.get(
    "/documents",
    response_model=list[DocumentSummaryResponse],
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_documents(
    limit: int = Query(default=50, ge=1, le=10000),
    session: Session = Depends(get_db_session),
) -> list[DocumentSummaryResponse]:
    return list_documents(session, limit=limit)


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("documents:upload")),
    ],
)
def create_document(
    response: Response,
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    payload, status_code = ingest_upload(
        session=session,
        upload=file,
        storage_service=get_storage_service(),
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    run_id = response_field(payload, "run_id")
    if run_id is not None:
        response.headers["Location"] = f"/runs/{run_id}"
    return payload


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_document(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentDetailResponse:
    return get_document_detail(session, document_id)


@router.get(
    "/documents/{document_id}/runs",
    response_model=list[DocumentRunSummaryResponse],
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_document_runs(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentRunSummaryResponse]:
    return list_document_runs(session, document_id)


@router.get(
    "/runs/{run_id}",
    response_model=DocumentRunSummaryResponse,
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_document_run(
    run_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentRunSummaryResponse:
    return get_document_run_summary(session, run_id)


@router.get(
    "/documents/{document_id}/evaluations/latest",
    response_model=EvaluationDetailResponse,
    dependencies=[Depends(require_api_capability("quality:read"))],
)
def read_latest_document_evaluation(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> EvaluationDetailResponse:
    return get_latest_document_evaluation_detail(session, document_id)


@router.get(
    "/documents/{document_id}/evaluations/latest/explain",
    dependencies=[Depends(require_api_capability("quality:read"))],
)
def explain_latest_document_evaluation_route(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> dict:
    return explain_latest_document_evaluation(session, document_id)


@router.get(
    "/documents/{document_id}/chunks",
    response_model=list[DocumentChunkResponse],
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_document_chunks(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentChunkResponse]:
    return get_active_chunks(session, document_id)


@router.get(
    "/documents/{document_id}/tables",
    response_model=list[DocumentTableSummaryResponse],
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_document_tables(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentTableSummaryResponse]:
    return get_active_tables(session, document_id)


@router.get(
    "/documents/{document_id}/tables/{table_id}",
    response_model=DocumentTableDetailResponse,
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_document_table(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentTableDetailResponse:
    return get_active_table_detail(session, document_id, table_id)


@router.get(
    "/documents/{document_id}/figures",
    response_model=list[DocumentFigureSummaryResponse],
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_document_figures(
    document_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[DocumentFigureSummaryResponse]:
    return get_active_figures(session, document_id)


@router.get(
    "/documents/{document_id}/figures/{figure_id}",
    response_model=DocumentFigureDetailResponse,
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_document_figure(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
) -> DocumentFigureDetailResponse:
    return get_active_figure_detail(session, document_id, figure_id)


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=DocumentUploadResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("documents:reprocess")),
    ],
)
def reprocess_existing_document(
    document_id: UUID,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    payload = reprocess_document(session, document_id, idempotency_key=idempotency_key)
    response.status_code = 202
    run_id = response_field(payload, "run_id")
    if run_id is not None:
        response.headers["Location"] = f"/runs/{run_id}"
    return payload


@router.get(
    "/runs/{run_id}/failure-artifact",
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_run_failure_artifact(
    run_id: UUID,
    session: Session = Depends(get_db_session),
):
    run = session.get(DocumentRun, run_id)
    if run is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_run_not_found",
            "Document run not found.",
            run_id=str(run_id),
        )
    return storage_file_response(
        get_storage_service().build_failure_artifact_path(run.document_id, run.id),
        media_type="application/json",
        not_found_detail="Run failure artifact not found.",
        not_found_error_code="run_failure_artifact_not_found",
        not_found_context={"run_id": str(run_id), "document_id": str(run.document_id)},
    )


@router.get(
    "/documents/{document_id}/artifacts/json",
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_docling_json_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_json_artifact or document.active_run_id is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_artifact_not_found",
            "Document JSON artifact not found.",
            document_id=str(document_id),
            artifact_format="json",
        )
    run = session.get(DocumentRun, document.active_run_id)
    if run is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_artifact_not_found",
            "Document JSON artifact not found.",
            document_id=str(document_id),
            artifact_format="json",
        )
    return storage_file_response(
        get_storage_service().build_docling_json_path(document_id, run.id),
        not_found_detail="Document JSON artifact not found.",
        not_found_error_code="document_artifact_not_found",
        not_found_context={"document_id": str(document_id), "artifact_format": "json"},
    )


@router.get(
    "/documents/{document_id}/artifacts/yaml",
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_yaml_artifact(
    document_id: UUID,
    session: Session = Depends(get_db_session),
):
    document = get_document_detail(session, document_id)
    if not document.has_yaml_artifact or document.active_run_id is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_artifact_not_found",
            "Document YAML artifact not found.",
            document_id=str(document_id),
            artifact_format="yaml",
        )
    run = session.get(DocumentRun, document.active_run_id)
    if run is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "document_artifact_not_found",
            "Document YAML artifact not found.",
            document_id=str(document_id),
            artifact_format="yaml",
        )
    return storage_file_response(
        get_storage_service().build_yaml_path(document_id, run.id),
        not_found_detail="Document YAML artifact not found.",
        not_found_error_code="document_artifact_not_found",
        not_found_context={"document_id": str(document_id), "artifact_format": "yaml"},
    )


def _get_active_table_row(
    session: Session, document_id: UUID, table_id: UUID
) -> DocumentTable | None:
    document = get_document_detail(session, document_id)
    if document.active_run_id is None:
        return None
    table = session.get(DocumentTable, table_id)
    if table is None or table.run_id != document.active_run_id or table.document_id != document_id:
        return None
    return table


def _get_active_figure_row(
    session: Session, document_id: UUID, figure_id: UUID
) -> DocumentFigure | None:
    document = get_document_detail(session, document_id)
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


@router.get(
    "/documents/{document_id}/tables/{table_id}/artifacts/json",
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_table_json_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "table_not_found",
            "Table not found.",
            document_id=str(document_id),
            table_id=str(table_id),
        )
    return storage_file_response(
        get_storage_service().build_table_json_path(document_id, table.run_id, table.table_index),
        not_found_detail="Table JSON artifact not found.",
        not_found_error_code="table_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "table_id": str(table_id),
            "artifact_format": "json",
        },
    )


@router.get(
    "/documents/{document_id}/tables/{table_id}/artifacts/yaml",
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_table_yaml_artifact(
    document_id: UUID,
    table_id: UUID,
    session: Session = Depends(get_db_session),
):
    table = _get_active_table_row(session, document_id, table_id)
    if table is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "table_not_found",
            "Table not found.",
            document_id=str(document_id),
            table_id=str(table_id),
        )
    return storage_file_response(
        get_storage_service().build_table_yaml_path(document_id, table.run_id, table.table_index),
        not_found_detail="Table YAML artifact not found.",
        not_found_error_code="table_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "table_id": str(table_id),
            "artifact_format": "yaml",
        },
    )


@router.get(
    "/documents/{document_id}/figures/{figure_id}/artifacts/json",
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_figure_json_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "figure_not_found",
            "Figure not found.",
            document_id=str(document_id),
            figure_id=str(figure_id),
        )
    return storage_file_response(
        get_storage_service().build_figure_json_path(
            document_id,
            figure.run_id,
            figure.figure_index,
        ),
        not_found_detail="Figure JSON artifact not found.",
        not_found_error_code="figure_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "figure_id": str(figure_id),
            "artifact_format": "json",
        },
    )


@router.get(
    "/documents/{document_id}/figures/{figure_id}/artifacts/yaml",
    dependencies=[Depends(require_api_capability("documents:inspect"))],
)
def read_figure_yaml_artifact(
    document_id: UUID,
    figure_id: UUID,
    session: Session = Depends(get_db_session),
):
    figure = _get_active_figure_row(session, document_id, figure_id)
    if figure is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "figure_not_found",
            "Figure not found.",
            document_id=str(document_id),
            figure_id=str(figure_id),
        )
    return storage_file_response(
        get_storage_service().build_figure_yaml_path(
            document_id,
            figure.run_id,
            figure.figure_index,
        ),
        not_found_detail="Figure YAML artifact not found.",
        not_found_error_code="figure_artifact_not_found",
        not_found_context={
            "document_id": str(document_id),
            "figure_id": str(figure_id),
            "artifact_format": "yaml",
        },
    )
