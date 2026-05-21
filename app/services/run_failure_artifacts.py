from __future__ import annotations

import json
from pathlib import Path

from app.core.time import utcnow
from app.db.public.ingest import Document, DocumentRun
from app.services.storage import StorageService
from app.services.validation import ValidationReport


def write_failure_artifact(
    storage_service: StorageService | None,
    document: Document | None,
    run: DocumentRun,
    exc: Exception,
    *,
    failure_stage: str | None,
    report: ValidationReport | None = None,
) -> Path | None:
    if storage_service is None:
        return None

    document_id = getattr(document, "id", None) or getattr(run, "document_id", None)
    if document_id is None:
        return None

    failure_path = storage_service.get_failure_artifact_path(document_id, run.id)
    payload = {
        "schema_version": "1.0",
        "document_id": str(document_id),
        "run_id": str(run.id),
        "source_filename": getattr(document, "source_filename", None),
        "source_path": getattr(document, "source_path", None),
        "run_number": getattr(run, "run_number", None),
        "status": getattr(run, "status", None),
        "attempts": getattr(run, "attempts", None),
        "failure_stage": failure_stage,
        "failure_type": exc.__class__.__name__,
        "error_message": str(exc),
        "created_at": utcnow().isoformat(),
        "validation_status": getattr(run, "validation_status", None),
        "docling_json_path": getattr(run, "docling_json_path", None),
        "yaml_path": getattr(run, "yaml_path", None),
        "chunk_count": getattr(run, "chunk_count", None),
        "table_count": getattr(run, "table_count", None),
        "figure_count": getattr(run, "figure_count", None),
        "embedding_model": getattr(run, "embedding_model", None),
        "embedding_dim": getattr(run, "embedding_dim", None),
        "validation_results": getattr(run, "validation_results_json", None) or {},
        "validation_report": report.details if report is not None else None,
    }
    failure_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return failure_path
