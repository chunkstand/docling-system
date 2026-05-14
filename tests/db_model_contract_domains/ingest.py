"""DB model contract fragment for ingest."""

from __future__ import annotations

MODEL_SYMBOLS = ("IngestBatch", "IngestBatchItem", "Document", "DocumentRun")

INGEST_DOMAIN_TABLE_COLUMNS = {
    "ingest_batches": frozenset(
        {
            "completed_at",
            "created_at",
            "duplicate_count",
            "error_message",
            "failed_count",
            "file_count",
            "id",
            "queued_count",
            "recovery_queued_count",
            "recursive",
            "root_path",
            "source_type",
            "status",
        }
    ),
    "ingest_batch_items": frozenset(
        {
            "batch_id",
            "created_at",
            "document_id",
            "duplicate",
            "error_message",
            "file_size_bytes",
            "id",
            "recovery_run",
            "relative_path",
            "run_id",
            "sha256",
            "source_filename",
            "source_path",
            "status",
            "status_code",
        }
    ),
    "documents": frozenset(
        {
            "active_run_id",
            "created_at",
            "id",
            "latest_run_id",
            "metadata_textsearch",
            "mime_type",
            "page_count",
            "sha256",
            "source_filename",
            "source_path",
            "title",
            "updated_at",
        }
    ),
    "document_runs": frozenset(
        {
            "attempts",
            "chunk_count",
            "completed_at",
            "created_at",
            "docling_json_path",
            "document_id",
            "embedding_dim",
            "embedding_model",
            "error_message",
            "failure_artifact_path",
            "failure_stage",
            "figure_count",
            "id",
            "last_heartbeat_at",
            "locked_at",
            "locked_by",
            "next_attempt_at",
            "run_number",
            "started_at",
            "status",
            "table_count",
            "validation_results",
            "validation_status",
            "yaml_path",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "documents": frozenset({"ix_documents_metadata_textsearch", "ix_documents_updated_at"}),
    "ingest_batches": frozenset(
        {"ix_ingest_batches_created_at", "ix_ingest_batches_status_created_at"}
    ),
    "ingest_batch_items": frozenset(
        {
            "ix_ingest_batch_items_batch_id",
            "ix_ingest_batch_items_document_id",
            "ix_ingest_batch_items_run_id",
            "ix_ingest_batch_items_status",
        }
    ),
    "document_runs": frozenset(
        {
            "ix_document_runs_locked_at",
            "ix_document_runs_status_completed_at",
            "ix_document_runs_status_next_attempt_at",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
    "documents": {
        "ix_documents_metadata_textsearch": ("metadata_textsearch",),
        "ix_documents_updated_at": ("updated_at",),
    },
    "ingest_batches": {
        "ix_ingest_batches_created_at": ("created_at",),
        "ix_ingest_batches_status_created_at": ("status", "created_at"),
    },
    "ingest_batch_items": {
        "ix_ingest_batch_items_batch_id": ("batch_id",),
        "ix_ingest_batch_items_document_id": ("document_id",),
        "ix_ingest_batch_items_run_id": ("run_id",),
        "ix_ingest_batch_items_status": ("status",),
    },
    "document_runs": {
        "ix_document_runs_locked_at": ("locked_at",),
        "ix_document_runs_status_completed_at": ("status", "completed_at"),
        "ix_document_runs_status_next_attempt_at": ("status", "next_attempt_at"),
    },
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "ingest_batch_items": frozenset({"uq_ingest_batch_items_batch_relative_path"}),
    "document_runs": frozenset({"uq_document_runs_doc_run_number"}),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "ingest_batch_items": {
        "uq_ingest_batch_items_batch_relative_path": ("batch_id", "relative_path")
    },
    "document_runs": {"uq_document_runs_doc_run_number": ("document_id", "run_number")},
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
