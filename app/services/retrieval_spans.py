from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import DocumentChunk, DocumentRun, DocumentTable, RetrievalEvidenceSpan
from app.services.embeddings import EmbeddingProvider

logger = structlog.get_logger(__name__)

SPAN_SCHEMA_VERSION = "retrieval_evidence_span_v1"
SPAN_WORD_WINDOW = 80
SPAN_WORD_OVERLAP = 20
SPAN_MIN_TRAILING_WORDS = 20


@dataclass(frozen=True)
class SourceSpanSpec:
    source_type: str
    source_id: UUID
    chunk_id: UUID | None
    table_id: UUID | None
    span_index: int
    span_text: str
    heading: str | None
    page_from: int | None
    page_to: int | None
    content_sha256: str
    source_snapshot_sha256: str
    metadata: dict


def _payload_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_span_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _window_text(value: str) -> list[tuple[int, str]]:
    normalized = _normalize_span_text(value)
    if not normalized:
        return []

    words = normalized.split()
    if len(words) <= SPAN_WORD_WINDOW:
        return [(0, normalized)]

    windows: list[tuple[int, str]] = []
    step = SPAN_WORD_WINDOW - SPAN_WORD_OVERLAP
    start = 0
    while start < len(words):
        end = min(start + SPAN_WORD_WINDOW, len(words))
        if end == len(words) and windows and end - start < SPAN_MIN_TRAILING_WORDS:
            previous_start, _ = windows[-1]
            windows[-1] = (previous_start, " ".join(words[previous_start:end]))
            break
        windows.append((start, " ".join(words[start:end])))
        if end == len(words):
            break
        start += step
    return windows


def _chunk_source_snapshot(chunk: DocumentChunk) -> dict:
    return {
        "schema_name": "retrieval_source_snapshot",
        "schema_version": "1.0",
        "source_type": "chunk",
        "source_id": chunk.id,
        "document_id": chunk.document_id,
        "run_id": chunk.run_id,
        "chunk_index": chunk.chunk_index,
        "heading": chunk.heading,
        "page_from": chunk.page_from,
        "page_to": chunk.page_to,
        "text": chunk.text,
        "metadata": chunk.metadata_json or {},
    }


def _table_source_snapshot(table: DocumentTable) -> dict:
    return {
        "schema_name": "retrieval_source_snapshot",
        "schema_version": "1.0",
        "source_type": "table",
        "source_id": table.id,
        "document_id": table.document_id,
        "run_id": table.run_id,
        "table_index": table.table_index,
        "title": table.title,
        "heading": table.heading,
        "logical_table_key": table.logical_table_key,
        "table_version": table.table_version,
        "lineage_group": table.lineage_group,
        "page_from": table.page_from,
        "page_to": table.page_to,
        "row_count": table.row_count,
        "col_count": table.col_count,
        "search_text": table.search_text,
        "preview_text": table.preview_text,
        "metadata": table.metadata_json or {},
    }


def _span_content_sha256(
    *,
    source_type: str,
    source_id: UUID,
    span_index: int,
    span_text: str,
    source_snapshot_sha256: str,
) -> str:
    return _payload_sha256(
        {
            "schema_name": "retrieval_evidence_span_content",
            "schema_version": "1.0",
            "source_type": source_type,
            "source_id": source_id,
            "span_index": span_index,
            "span_text": span_text,
            "source_snapshot_sha256": source_snapshot_sha256,
        }
    )


def build_chunk_span_specs(chunk: DocumentChunk) -> list[SourceSpanSpec]:
    source_snapshot_sha256 = _payload_sha256(_chunk_source_snapshot(chunk))
    specs: list[SourceSpanSpec] = []
    for span_index, (word_start, span_text) in enumerate(_window_text(chunk.text)):
        specs.append(
            SourceSpanSpec(
                source_type="chunk",
                source_id=chunk.id,
                chunk_id=chunk.id,
                table_id=None,
                span_index=span_index,
                span_text=span_text,
                heading=chunk.heading,
                page_from=chunk.page_from,
                page_to=chunk.page_to,
                content_sha256=_span_content_sha256(
                    source_type="chunk",
                    source_id=chunk.id,
                    span_index=span_index,
                    span_text=span_text,
                    source_snapshot_sha256=source_snapshot_sha256,
                ),
                source_snapshot_sha256=source_snapshot_sha256,
                metadata={
                    "schema_name": SPAN_SCHEMA_VERSION,
                    "source_chunk_index": chunk.chunk_index,
                    "word_start": word_start,
                    "word_count": len(span_text.split()),
                },
            )
        )
    return specs


def build_table_span_specs(table: DocumentTable) -> list[SourceSpanSpec]:
    source_snapshot_sha256 = _payload_sha256(_table_source_snapshot(table))
    heading = " ".join(part for part in (table.title, table.heading) if part) or None
    specs: list[SourceSpanSpec] = []
    for span_index, (word_start, span_text) in enumerate(_window_text(table.search_text)):
        specs.append(
            SourceSpanSpec(
                source_type="table",
                source_id=table.id,
                chunk_id=None,
                table_id=table.id,
                span_index=span_index,
                span_text=span_text,
                heading=heading,
                page_from=table.page_from,
                page_to=table.page_to,
                content_sha256=_span_content_sha256(
                    source_type="table",
                    source_id=table.id,
                    span_index=span_index,
                    span_text=span_text,
                    source_snapshot_sha256=source_snapshot_sha256,
                ),
                source_snapshot_sha256=source_snapshot_sha256,
                metadata={
                    "schema_name": SPAN_SCHEMA_VERSION,
                    "source_table_index": table.table_index,
                    "logical_table_key": table.logical_table_key,
                    "word_start": word_start,
                    "word_count": len(span_text.split()),
                },
            )
        )
    return specs


def _build_span_specs(session: Session, run_id: UUID) -> list[SourceSpanSpec]:
    session.flush()
    chunk_rows = list(
        session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.run_id == run_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
    )
    table_rows = list(
        session.scalars(
            select(DocumentTable)
            .where(DocumentTable.run_id == run_id)
            .order_by(DocumentTable.table_index.asc())
        )
    )
    specs: list[SourceSpanSpec] = []
    for chunk in chunk_rows:
        specs.extend(build_chunk_span_specs(chunk))
    for table in table_rows:
        specs.extend(build_table_span_specs(table))
    return specs


def rebuild_retrieval_evidence_spans(
    session: Session,
    run: DocumentRun,
    *,
    embedding_provider: EmbeddingProvider | None = None,
) -> dict:
    if not isinstance(session, Session):
        return {
            "schema_name": "retrieval_evidence_span_rebuild_summary",
            "schema_version": "1.0",
            "run_id": str(run.id),
            "document_id": str(run.document_id),
            "span_count": 0,
            "chunk_span_count": 0,
            "table_span_count": 0,
            "embedding_status": "skipped_non_sqlalchemy_session",
            "embedding_error": None,
        }

    specs = _build_span_specs(session, run.id)
    session.execute(delete(RetrievalEvidenceSpan).where(RetrievalEvidenceSpan.run_id == run.id))
    now = utcnow()

    embeddings: list[list[float] | None] = [None] * len(specs)
    embedding_status = "skipped"
    embedding_error: str | None = None
    if specs and embedding_provider is not None:
        try:
            raw_embeddings = embedding_provider.embed_texts([spec.span_text for spec in specs])
            embeddings = [list(embedding) for embedding in raw_embeddings]
            embedding_status = "completed"
        except Exception as exc:
            embedding_status = "embedding_failed"
            embedding_error = str(exc)
            embeddings = [None] * len(specs)
            logger.warning(
                "retrieval_evidence_span_embedding_failed",
                run_id=str(run.id),
                document_id=str(run.document_id),
                error=str(exc),
            )

    for spec, embedding in zip(specs, embeddings, strict=True):
        session.add(
            RetrievalEvidenceSpan(
                id=uuid.uuid4(),
                document_id=run.document_id,
                run_id=run.id,
                source_type=spec.source_type,
                source_id=spec.source_id,
                chunk_id=spec.chunk_id,
                table_id=spec.table_id,
                span_index=spec.span_index,
                span_text=spec.span_text,
                heading=spec.heading,
                page_from=spec.page_from,
                page_to=spec.page_to,
                content_sha256=spec.content_sha256,
                source_snapshot_sha256=spec.source_snapshot_sha256,
                metadata_json={
                    **spec.metadata,
                    "embedding_status": embedding_status,
                    **({"embedding_error": embedding_error} if embedding_error else {}),
                },
                embedding=embedding,
                created_at=now,
            )
        )
    session.flush()
    return {
        "schema_name": "retrieval_evidence_span_rebuild_summary",
        "schema_version": "1.0",
        "run_id": str(run.id),
        "document_id": str(run.document_id),
        "span_count": len(specs),
        "chunk_span_count": sum(1 for spec in specs if spec.source_type == "chunk"),
        "table_span_count": sum(1 for spec in specs if spec.source_type == "table"),
        "embedding_status": embedding_status,
        "embedding_error": embedding_error,
    }
