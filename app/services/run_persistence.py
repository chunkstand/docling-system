from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utcnow
from app.db.public.document_artifacts import (
    DocumentChunk,
    DocumentFigure,
    DocumentTable,
    DocumentTableSegment,
)
from app.db.public.ingest import Document, DocumentRun
from app.services.docling_parser import ParsedDocument, ParsedFigure, ParsedTable
from app.services.embeddings import EmbeddingProvider
from app.services.storage import StorageService
from app.services.telemetry import increment, increment_many


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
    table_payload = table.artifact_payload(
        document_id=str(document.id),
        run_id=str(run.id),
        table_id=str(table_id),
        logical_table_key=logical_table_key,
        created_at=created_at.isoformat(),
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
    figure_payload = figure.artifact_payload(
        document_id=str(document.id),
        run_id=str(run.id),
        figure_id=str(figure_id),
        created_at=created_at.isoformat(),
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
    now = utcnow()
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
    now = utcnow()

    table_metric_counts: dict[str, float] = {}
    for table in parsed.tables:
        table_id = uuid.uuid4()
        lineage = lineage_assignments.get(table.table_index, {})
        table_metadata = {
            key: value for key, value in (table.metadata or {}).items() if key != "audit"
        }
        table.metadata = table_metadata
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
        table.metadata = {**table.metadata, "audit": audit}
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
        table_metric_counts["logical_tables_persisted_total"] = (
            table_metric_counts.get("logical_tables_persisted_total", 0) + 1
        )
        table_metric_counts["table_segments_persisted_total"] = table_metric_counts.get(
            "table_segments_persisted_total", 0
        ) + len(table.segments)
        if table.metadata.get("is_merged"):
            table_metric_counts["continuation_merges_total"] = (
                table_metric_counts.get("continuation_merges_total", 0) + 1
            )
        if table.metadata.get("ambiguous_continuation_candidate"):
            table_metric_counts["ambiguous_continuations_total"] = (
                table_metric_counts.get("ambiguous_continuations_total", 0) + 1
            )
        removed_rows = table.metadata.get("header_rows_removed_count", 0)
        if removed_rows:
            table_metric_counts["repeated_header_rows_removed_total"] = table_metric_counts.get(
                "repeated_header_rows_removed_total", 0
            ) + float(removed_rows)
    increment_many(table_metric_counts)


def _replace_run_figures(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
    storage_service: StorageService,
) -> None:
    session.query(DocumentFigure).filter(DocumentFigure.run_id == run.id).delete()
    now = utcnow()

    for figure in parsed.figures:
        figure_id = uuid.uuid4()
        figure.metadata = {
            key: value for key, value in (figure.metadata or {}).items() if key != "audit"
        }
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
        figure.metadata = {**figure.metadata, "audit": audit}
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
    except Exception:
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
    document.updated_at = utcnow()
    session.commit()


def _mark_run_validating(session: Session, run: DocumentRun) -> None:
    run.status = "validating"
    run.last_heartbeat_at = utcnow()
    session.commit()
