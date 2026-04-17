from __future__ import annotations

import hashlib
import json
import os
import socket
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import Select, and_, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentFigure,
    DocumentRun,
    DocumentTable,
    DocumentTableSegment,
    RunStatus,
)
from app.services.docling_parser import DoclingParser, ParsedDocument, ParsedFigure, ParsedTable
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.evaluations import (
    ensure_auto_evaluation_fixture,
    evaluate_run,
    resolve_baseline_run_id,
)
from app.services.storage import StorageService
from app.services.telemetry import increment
from app.services.validation import ValidationReport, validate_persisted_run


class ValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        super().__init__(report.summary)
        self.report = report


def _utcnow() -> datetime:
    return datetime.now(UTC)


def get_worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


logger = get_logger(__name__)


def is_retryable_error(exc: Exception) -> bool:
    return not isinstance(exc, ValueError)


def requeue_stale_runs(session: Session, storage_service: StorageService | None = None) -> int:
    settings = get_settings()
    stale_before = _utcnow() - timedelta(seconds=settings.worker_lease_timeout_seconds)
    stale_runs = session.execute(
        select(DocumentRun).where(
            DocumentRun.status.in_([RunStatus.PROCESSING.value, RunStatus.VALIDATING.value]),
            DocumentRun.last_heartbeat_at.is_not(None),
            DocumentRun.last_heartbeat_at < stale_before,
        )
    ).scalars()

    updated = 0
    for run in stale_runs:
        run.locked_at = None
        run.locked_by = None
        run.last_heartbeat_at = None
        if run.attempts >= settings.worker_max_attempts:
            run.status = RunStatus.FAILED.value
            run.completed_at = _utcnow()
            run.validation_status = run.validation_status or "failed"
            run.error_message = run.error_message or "Run exceeded max attempts after stale lease."
            run.failure_stage = run.failure_stage or "stale_lease"
            failure_path = _write_failure_artifact(
                storage_service,
                None,
                run,
                RuntimeError(run.error_message),
                failure_stage=run.failure_stage,
            )
            run.failure_artifact_path = str(failure_path) if failure_path is not None else None
        else:
            run.status = RunStatus.RETRY_WAIT.value
            run.next_attempt_at = _utcnow()
        updated += 1

    if updated:
        session.commit()
        logger.info("stale_runs_requeued", count=updated)

    return updated


def claim_next_run(session: Session, worker_id: str) -> DocumentRun | None:
    now = _utcnow()
    eligible_query: Select[tuple[DocumentRun]] = (
        select(DocumentRun)
        .where(
            or_(
                DocumentRun.status == RunStatus.QUEUED.value,
                and_(
                    DocumentRun.status == RunStatus.RETRY_WAIT.value,
                    or_(DocumentRun.next_attempt_at.is_(None), DocumentRun.next_attempt_at <= now),
                ),
            )
        )
        .order_by(DocumentRun.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    run = session.execute(eligible_query).scalar_one_or_none()
    if run is None:
        session.rollback()
        return None

    run.status = RunStatus.PROCESSING.value
    run.locked_at = now
    run.locked_by = worker_id
    run.last_heartbeat_at = now
    run.started_at = run.started_at or now
    run.next_attempt_at = None
    run.validation_status = "pending"
    run.validation_results_json = {}
    run.failure_stage = None
    run.attempts += 1
    session.commit()
    session.refresh(run)
    logger.info(
        "run_claimed", run_id=str(run.id), document_id=str(run.document_id), worker_id=worker_id
    )
    return run


def heartbeat_run(session: Session, run: DocumentRun) -> None:
    run.last_heartbeat_at = _utcnow()
    session.commit()


def _refresh_run_lease(session_factory, run_id: UUID, worker_id: str) -> bool:
    with session_factory() as heartbeat_session:
        result = heartbeat_session.execute(
            update(DocumentRun)
            .where(
                DocumentRun.id == run_id,
                DocumentRun.locked_by == worker_id,
                DocumentRun.status.in_([RunStatus.PROCESSING.value, RunStatus.VALIDATING.value]),
            )
            .values(last_heartbeat_at=_utcnow())
        )
        heartbeat_session.commit()
        return bool(result.rowcount)


@contextmanager
def run_lease_heartbeat(run_id: UUID, *, worker_id: str | None):
    from app.db.session import get_session_factory

    settings = get_settings()
    interval_seconds = settings.worker_heartbeat_seconds
    if worker_id is None or interval_seconds <= 0:
        yield
        return

    session_factory = get_session_factory()
    stop_event = threading.Event()

    def _loop() -> None:
        while not stop_event.wait(interval_seconds):
            try:
                if not _refresh_run_lease(session_factory, run_id, worker_id):
                    return
            except Exception as exc:
                logger.warning(
                    "run_lease_heartbeat_failed",
                    run_id=str(run_id),
                    worker_id=worker_id,
                    error=str(exc),
                )

    heartbeat_thread = threading.Thread(
        target=_loop,
        name=f"run-heartbeat-{run_id}",
        daemon=True,
    )
    heartbeat_thread.start()
    try:
        yield
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=max(1, interval_seconds))


def _write_failure_artifact(
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
        "created_at": _utcnow().isoformat(),
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


def _persist_parsed_artifacts(
    storage_service: StorageService,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
) -> tuple[Path, Path]:
    json_path = storage_service.get_docling_json_path(document.id, run.id)
    yaml_path = storage_service.get_yaml_path(document.id, run.id)
    json_path.write_text(parsed.docling_json)
    yaml_path.write_text(parsed.yaml_text)
    return json_path, yaml_path


def _persist_table_artifacts(
    storage_service: StorageService,
    document: Document,
    run: DocumentRun,
    table: ParsedTable,
    *,
    table_id: UUID,
    logical_table_key: str | None,
    created_at: datetime,
) -> tuple[Path, Path, str, str]:
    base_payload = table.artifact_payload(
        document_id=str(document.id),
        run_id=str(run.id),
        table_id=str(table_id),
        logical_table_key=logical_table_key,
        created_at=created_at.isoformat(),
        artifact_sha256="",
    )
    artifact_seed = hashlib.sha256(
        json.dumps(base_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    table_payload = table.artifact_payload(
        document_id=str(document.id),
        run_id=str(run.id),
        table_id=str(table_id),
        logical_table_key=logical_table_key,
        created_at=created_at.isoformat(),
        artifact_sha256=artifact_seed,
    )
    json_path = storage_service.get_table_json_path(document.id, run.id, table.table_index)
    yaml_path = storage_service.get_table_yaml_path(document.id, run.id, table.table_index)
    json_bytes = json.dumps(table_payload, indent=2).encode("utf-8")
    yaml_bytes = yaml.safe_dump(table_payload, sort_keys=False, allow_unicode=True).encode("utf-8")
    json_path.write_bytes(json_bytes)
    yaml_path.write_bytes(yaml_bytes)
    return (
        json_path,
        yaml_path,
        hashlib.sha256(json_bytes).hexdigest(),
        hashlib.sha256(yaml_bytes).hexdigest(),
    )


def _persist_figure_artifacts(
    storage_service: StorageService,
    document: Document,
    run: DocumentRun,
    figure: ParsedFigure,
    *,
    figure_id: UUID,
    created_at: datetime,
) -> tuple[Path, Path, str, str]:
    base_payload = figure.artifact_payload(
        document_id=str(document.id),
        run_id=str(run.id),
        figure_id=str(figure_id),
        created_at=created_at.isoformat(),
        artifact_sha256="",
    )
    artifact_seed = hashlib.sha256(
        json.dumps(base_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    figure_payload = figure.artifact_payload(
        document_id=str(document.id),
        run_id=str(run.id),
        figure_id=str(figure_id),
        created_at=created_at.isoformat(),
        artifact_sha256=artifact_seed,
    )
    json_path = storage_service.get_figure_json_path(document.id, run.id, figure.figure_index)
    yaml_path = storage_service.get_figure_yaml_path(document.id, run.id, figure.figure_index)
    json_bytes = json.dumps(figure_payload, indent=2).encode("utf-8")
    yaml_bytes = yaml.safe_dump(figure_payload, sort_keys=False, allow_unicode=True).encode("utf-8")
    json_path.write_bytes(json_bytes)
    yaml_path.write_bytes(yaml_bytes)
    return (
        json_path,
        yaml_path,
        hashlib.sha256(json_bytes).hexdigest(),
        hashlib.sha256(yaml_bytes).hexdigest(),
    )


def _stable_table_key_source(table: ParsedTable) -> str | None:
    if not table.title:
        return None
    return (
        f"{table.title.strip().lower()}|{(table.heading or '').strip().lower()}|{table.col_count}"
    )


def _build_lineage_assignments(
    session: Session, document: Document, parsed: ParsedDocument
) -> dict[int, dict[str, object | None]]:
    key_counts: dict[str, int] = {}
    for table in parsed.tables:
        source = _stable_table_key_source(table)
        if source is not None:
            key_counts[source] = key_counts.get(source, 0) + 1

    previous_by_key: dict[str, DocumentTable] = {}
    if document.active_run_id is not None:
        previous_tables = (
            session.execute(
                select(DocumentTable).where(DocumentTable.run_id == document.active_run_id)
            )
            .scalars()
            .all()
        )
        for previous in previous_tables:
            if previous.logical_table_key:
                previous_by_key[previous.logical_table_key] = previous

    assignments: dict[int, dict[str, object | None]] = {}
    for table in parsed.tables:
        source = _stable_table_key_source(table)
        if source is None or key_counts.get(source, 0) != 1:
            assignments[table.table_index] = {
                "logical_table_key": None,
                "table_version": None,
                "supersedes_table_id": None,
                "lineage_group": None,
            }
            continue

        logical_table_key = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        previous = previous_by_key.get(logical_table_key)
        assignments[table.table_index] = {
            "logical_table_key": logical_table_key,
            "table_version": (previous.table_version or 1) + 1 if previous else 1,
            "supersedes_table_id": previous.id if previous else None,
            "lineage_group": previous.lineage_group or logical_table_key
            if previous
            else logical_table_key,
        }

    return assignments


def _replace_run_chunks(
    session: Session, document: Document, run: DocumentRun, parsed: ParsedDocument
) -> None:
    session.query(DocumentChunk).filter(DocumentChunk.run_id == run.id).delete()
    now = _utcnow()
    for chunk in parsed.chunks:
        session.add(
            DocumentChunk(
                document_id=document.id,
                run_id=run.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                heading=chunk.heading,
                page_from=chunk.page_from,
                page_to=chunk.page_to,
                metadata_json=chunk.metadata,
                embedding=chunk.embedding,
                created_at=now,
            )
        )


def _replace_run_tables(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
    storage_service: StorageService,
    lineage_assignments: dict[int, dict[str, object | None]],
) -> None:
    session.query(DocumentTableSegment).filter(DocumentTableSegment.run_id == run.id).delete()
    session.query(DocumentTable).filter(DocumentTable.run_id == run.id).delete()
    now = _utcnow()

    for table in parsed.tables:
        table_id = uuid.uuid4()
        lineage = lineage_assignments.get(table.table_index, {})
        try:
            json_path, yaml_path, json_sha, yaml_sha = _persist_table_artifacts(
                storage_service,
                document,
                run,
                table,
                table_id=table_id,
                logical_table_key=lineage.get("logical_table_key"),
                created_at=now,
            )
        except Exception:
            increment("table_artifact_write_failures_total")
            raise
        audit = {
            "extractor_version": "docling",
            "profile_name": "standard_pdf",
            "fallback_used": False,
            "source_segment_refs": [segment.source_table_ref for segment in table.segments],
            "page_from": table.page_from,
            "page_to": table.page_to,
            "json_artifact_sha256": json_sha,
            "yaml_artifact_sha256": yaml_sha,
            "search_text_sha256": hashlib.sha256(table.search_text.encode("utf-8")).hexdigest(),
        }
        merge_metadata_sha = hashlib.sha256(
            json.dumps(table.metadata, sort_keys=True).encode("utf-8")
        ).hexdigest()
        audit["merge_metadata_sha256"] = merge_metadata_sha
        table.metadata.setdefault("audit", audit)
        table_row = DocumentTable(
            id=table_id,
            document_id=document.id,
            run_id=run.id,
            table_index=table.table_index,
            title=table.title,
            logical_table_key=lineage.get("logical_table_key"),
            table_version=lineage.get("table_version"),
            supersedes_table_id=lineage.get("supersedes_table_id"),
            lineage_group=lineage.get("lineage_group"),
            heading=table.heading,
            page_from=table.page_from,
            page_to=table.page_to,
            row_count=table.row_count,
            col_count=table.col_count,
            status="persisted",
            search_text=table.search_text,
            preview_text=table.preview_text,
            metadata_json=table.metadata,
            embedding=table.embedding,
            json_path=str(json_path),
            yaml_path=str(yaml_path),
            created_at=now,
        )
        session.add(table_row)
        session.flush()

        for segment in table.segments:
            session.add(
                DocumentTableSegment(
                    table_id=table_row.id,
                    run_id=run.id,
                    segment_index=segment.segment_index,
                    source_table_ref=segment.source_table_ref,
                    page_from=segment.page_from,
                    page_to=segment.page_to,
                    segment_order=segment.segment_order,
                    metadata_json=segment.metadata,
                    created_at=now,
                )
            )
        increment("logical_tables_persisted_total")
        increment("table_segments_persisted_total", len(table.segments))
        if table.metadata.get("is_merged"):
            increment("continuation_merges_total")
        if table.metadata.get("ambiguous_continuation_candidate"):
            increment("ambiguous_continuations_total")
        removed_rows = table.metadata.get("header_rows_removed_count", 0)
        if removed_rows:
            increment("repeated_header_rows_removed_total", float(removed_rows))


def _replace_run_figures(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
    storage_service: StorageService,
) -> None:
    session.query(DocumentFigure).filter(DocumentFigure.run_id == run.id).delete()
    now = _utcnow()

    for figure in parsed.figures:
        figure_id = uuid.uuid4()
        json_path, yaml_path, json_sha, yaml_sha = _persist_figure_artifacts(
            storage_service,
            document,
            run,
            figure,
            figure_id=figure_id,
            created_at=now,
        )
        audit = {
            "extractor_version": "docling",
            "profile_name": "standard_pdf",
            "fallback_used": figure.metadata.get("caption_resolution_source") != "explicit_ref",
            "page_from": figure.page_from,
            "page_to": figure.page_to,
            "json_artifact_sha256": json_sha,
            "yaml_artifact_sha256": yaml_sha,
        }
        figure.metadata.setdefault("audit", audit)
        session.add(
            DocumentFigure(
                id=figure_id,
                document_id=document.id,
                run_id=run.id,
                figure_index=figure.figure_index,
                source_figure_ref=figure.source_figure_ref,
                caption=figure.caption,
                heading=figure.heading,
                page_from=figure.page_from,
                page_to=figure.page_to,
                confidence=figure.confidence,
                status="persisted",
                metadata_json=figure.metadata,
                json_path=str(json_path),
                yaml_path=str(yaml_path),
                created_at=now,
            )
        )


def _apply_embeddings(
    parsed: ParsedDocument, embedding_provider: EmbeddingProvider | None, run: DocumentRun
) -> None:
    if embedding_provider is None:
        run.embedding_model = None
        run.embedding_dim = None
        return

    settings = get_settings()
    chunk_texts = [chunk.text for chunk in parsed.chunks]
    table_texts = [table.search_text for table in parsed.tables]

    try:
        chunk_embeddings = embedding_provider.embed_texts(chunk_texts)
        table_embeddings = embedding_provider.embed_texts(table_texts)
    except Exception as exc:
        logger.warning("embedding_generation_failed", run_id=str(run.id), error=str(exc))
        increment("table_embedding_failures_total", len(parsed.tables))
        run.embedding_model = None
        run.embedding_dim = None
        return

    for chunk, embedding in zip(parsed.chunks, chunk_embeddings, strict=True):
        chunk.embedding = embedding
    for table, embedding in zip(parsed.tables, table_embeddings, strict=True):
        table.embedding = embedding

    run.embedding_model = settings.openai_embedding_model
    run.embedding_dim = settings.embedding_dim


def _mark_run_persisted(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
    json_path: Path,
    yaml_path: Path,
) -> None:
    run.docling_json_path = str(json_path)
    run.yaml_path = str(yaml_path)
    run.chunk_count = len(parsed.chunks)
    run.table_count = len(parsed.tables)
    run.figure_count = len(parsed.figures)
    run.validation_status = "pending"
    document.latest_run_id = run.id
    document.updated_at = _utcnow()
    session.commit()


def _mark_run_validating(session: Session, run: DocumentRun) -> None:
    run.status = RunStatus.VALIDATING.value
    run.last_heartbeat_at = _utcnow()
    session.commit()


def finalize_run_success(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
    report: ValidationReport,
    *,
    storage_service: StorageService | None = None,
) -> None:
    now = _utcnow()
    run.locked_at = None
    run.locked_by = None
    run.last_heartbeat_at = None
    run.next_attempt_at = None
    run.chunk_count = len(parsed.chunks)
    run.table_count = len(parsed.tables)
    run.figure_count = len(parsed.figures)
    run.validation_status = "passed"
    run.validation_results_json = report.details
    run.failure_stage = None
    run.completed_at = now
    run.status = RunStatus.COMPLETED.value
    run.error_message = None
    if run.failure_artifact_path and storage_service is not None:
        storage_service.delete_file_if_exists(Path(run.failure_artifact_path))
    run.failure_artifact_path = None
    session.query(DocumentTable).filter(DocumentTable.run_id == run.id).update(
        {"status": "validated"}
    )
    session.query(DocumentFigure).filter(DocumentFigure.run_id == run.id).update(
        {"status": "validated"}
    )

    document.active_run_id = run.id
    document.latest_run_id = run.id
    document.title = parsed.title
    document.page_count = parsed.page_count
    document.updated_at = now
    session.commit()


def finalize_run_failure(
    session: Session,
    run: DocumentRun,
    exc: Exception,
    report: ValidationReport | None = None,
    failure_stage: str | None = None,
    *,
    storage_service: StorageService | None = None,
    document: Document | None = None,
) -> None:
    settings = get_settings()
    now = _utcnow()
    run.locked_at = None
    run.locked_by = None
    run.last_heartbeat_at = None
    run.error_message = str(exc)
    run.failure_stage = failure_stage
    run.validation_results_json = getattr(run, "validation_results_json", None) or {}
    run.validation_results_json["failure_type"] = exc.__class__.__name__
    if failure_stage:
        run.validation_results_json["failure_stage"] = failure_stage
    if report is not None:
        run.validation_status = "failed"
        run.validation_results_json = {**report.details, **run.validation_results_json}
        session.query(DocumentTable).filter(DocumentTable.run_id == run.id).update(
            {"status": "rejected"}
        )
        session.query(DocumentFigure).filter(DocumentFigure.run_id == run.id).update(
            {"status": "rejected"}
        )

    attempts = int(getattr(run, "attempts", settings.worker_max_attempts))
    if is_retryable_error(exc) and attempts < settings.worker_max_attempts:
        backoff_seconds = min(60, 2 ** max(attempts - 1, 0))
        run.status = RunStatus.RETRY_WAIT.value
        run.next_attempt_at = now + timedelta(seconds=backoff_seconds)
    else:
        run.status = RunStatus.FAILED.value
        run.completed_at = now

    failure_path = _write_failure_artifact(
        storage_service,
        document,
        run,
        exc,
        failure_stage=failure_stage,
        report=report,
    )
    run.failure_artifact_path = str(failure_path) if failure_path is not None else None

    session.commit()


def process_run(
    session: Session,
    run_id: UUID,
    storage_service: StorageService,
    parser: DoclingParser,
    embedding_provider: EmbeddingProvider | None = None,
) -> None:
    run = session.get(DocumentRun, run_id)
    if run is None:
        raise ValueError(f"Run {run_id} does not exist.")

    document = session.get(Document, run.document_id)
    if document is None:
        raise ValueError(f"Document {run.document_id} does not exist.")
    if not Path(document.source_path).exists():
        raise ValueError("Source file missing before worker pickup.")
    prior_active_run_id = document.active_run_id

    with run_lease_heartbeat(run.id, worker_id=run.locked_by):
        try:
            failure_stage = "parse"
            logger.info("run_processing_started", run_id=str(run.id), document_id=str(document.id))
            heartbeat_run(session, run)
            parse_kwargs: dict[str, str] = {}
            source_filename = getattr(document, "source_filename", None)
            if source_filename is not None:
                parse_kwargs["source_filename"] = source_filename
            parsed = parser.parse_pdf(Path(document.source_path), **parse_kwargs)
            increment("tables_detected_total", len(parsed.raw_table_segments))
            heartbeat_run(session, run)
            failure_stage = "embedding"
            _apply_embeddings(parsed, embedding_provider, run)
            lineage_assignments = _build_lineage_assignments(session, document, parsed)

            failure_stage = "artifact_write"
            json_path, yaml_path = _persist_parsed_artifacts(storage_service, document, run, parsed)
            failure_stage = "chunk_persist"
            _replace_run_chunks(session, document, run, parsed)
            failure_stage = "table_persist"
            _replace_run_tables(
                session,
                document,
                run,
                parsed,
                storage_service,
                lineage_assignments,
            )
            failure_stage = "figure_persist"
            _replace_run_figures(session, document, run, parsed, storage_service)
            failure_stage = "run_persist"
            _mark_run_persisted(session, document, run, parsed, json_path, yaml_path)
            failure_stage = "validation"
            _mark_run_validating(session, run)
            heartbeat_run(session, run)

            report = validate_persisted_run(session, document, run, parsed)
            if not report.passed:
                raise ValidationError(report)

            ensure_auto_evaluation_fixture(session, document, run, title=parsed.title)
            heartbeat_run(session, run)
            evaluation = evaluate_run(
                session,
                document,
                run,
                baseline_run_id=resolve_baseline_run_id(run.id, prior_active_run_id),
            )
            logger.info(
                "run_evaluation_completed",
                run_id=str(run.id),
                document_id=str(document.id),
                evaluation_status=evaluation.status,
                fixture_name=evaluation.fixture_name,
            )

            failure_stage = "promotion"
            finalize_run_success(
                session,
                document,
                run,
                parsed,
                report,
                storage_service=storage_service,
            )
            logger.info(
                "run_processing_completed",
                run_id=str(run.id),
                document_id=str(document.id),
                chunk_count=len(parsed.chunks),
                table_count=len(parsed.tables),
                figure_count=len(parsed.figures),
                page_count=parsed.page_count,
            )
        except Exception as exc:
            session.rollback()
            run = session.get(DocumentRun, run_id)
            if run is None:
                raise
            report = exc.report if isinstance(exc, ValidationError) else None
            finalize_run_failure(
                session,
                run,
                exc,
                report=report,
                failure_stage=failure_stage,
                storage_service=storage_service,
                document=document,
            )
            logger.exception(
                "run_processing_failed",
                run_id=str(run.id),
                document_id=str(document.id),
                error=str(exc),
            )


def run_worker_loop() -> None:
    from app.db.session import get_session_factory

    settings = get_settings()
    session_factory = get_session_factory()
    storage_service = StorageService()
    parser = DoclingParser()
    try:
        embedding_provider = get_embedding_provider()
    except Exception as exc:
        embedding_provider = None
        logger.warning("embedding_provider_unavailable", error=str(exc))
    worker_id = get_worker_identity()

    while True:
        with session_factory() as session:
            requeue_stale_runs(session, storage_service=storage_service)
            run = claim_next_run(session, worker_id)
            if run is None:
                time.sleep(settings.worker_poll_seconds)
                continue

            process_run(
                session=session,
                run_id=run.id,
                storage_service=storage_service,
                parser=parser,
                embedding_provider=embedding_provider,
            )
