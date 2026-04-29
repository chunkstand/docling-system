from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentRun,
    DocumentTable,
    RetrievalEvidenceSpan,
    RetrievalEvidenceSpanMultiVector,
)
from app.services.embeddings import EmbeddingProvider
from app.services.evidence import record_knowledge_operator_run

logger = structlog.get_logger(__name__)

SPAN_SCHEMA_VERSION = "retrieval_evidence_span_v1"
SPAN_WORD_WINDOW = 80
SPAN_WORD_OVERLAP = 20
SPAN_MIN_TRAILING_WORDS = 20
MULTIVECTOR_SCHEMA_VERSION = "retrieval_evidence_span_multivector_v1"
MULTIVECTOR_WORD_WINDOW = 16
MULTIVECTOR_WORD_OVERLAP = 8
MULTIVECTOR_MIN_TRAILING_WORDS = 6


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


@dataclass(frozen=True)
class SpanMultiVectorSpec:
    retrieval_evidence_span_id: UUID
    document_id: UUID
    run_id: UUID
    source_type: str
    source_id: UUID
    vector_index: int
    token_start: int
    token_end: int
    vector_text: str
    content_sha256: str
    metadata: dict

def _normalize_span_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _window_word_ranges(
    value: str,
    *,
    word_window: int,
    word_overlap: int,
    min_trailing_words: int,
) -> list[tuple[int, int, str]]:
    normalized = _normalize_span_text(value)
    if not normalized:
        return []

    words = normalized.split()
    if len(words) <= word_window:
        return [(0, len(words), normalized)]

    windows: list[tuple[int, int, str]] = []
    step = max(word_window - word_overlap, 1)
    start = 0
    while start < len(words):
        end = min(start + word_window, len(words))
        if end == len(words) and windows and end - start < min_trailing_words:
            previous_start, _previous_end, _ = windows[-1]
            windows[-1] = (previous_start, end, " ".join(words[previous_start:end]))
            break
        windows.append((start, end, " ".join(words[start:end])))
        if end == len(words):
            break
        start += step
    return windows


def _window_text(value: str) -> list[tuple[int, str]]:
    return [
        (start, text)
        for start, _end, text in _window_word_ranges(
            value,
            word_window=SPAN_WORD_WINDOW,
            word_overlap=SPAN_WORD_OVERLAP,
            min_trailing_words=SPAN_MIN_TRAILING_WORDS,
        )
    ]


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


def _span_multivector_content_sha256(
    *,
    retrieval_evidence_span_id: UUID,
    vector_index: int,
    token_start: int,
    token_end: int,
    vector_text: str,
    span_content_sha256: str,
    source_snapshot_sha256: str,
) -> str:
    return _payload_sha256(
        {
            "schema_name": "retrieval_evidence_span_multivector_content",
            "schema_version": "1.0",
            "retrieval_evidence_span_id": retrieval_evidence_span_id,
            "vector_index": vector_index,
            "token_start": token_start,
            "token_end": token_end,
            "vector_text": vector_text,
            "span_content_sha256": span_content_sha256,
            "source_snapshot_sha256": source_snapshot_sha256,
        }
    )


def _embedding_sha256(embedding: list[float]) -> str:
    return _payload_sha256(
        {
            "schema_name": "retrieval_evidence_span_multivector_embedding",
            "schema_version": "1.0",
            "embedding": [float(value) for value in embedding],
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


def build_span_multivector_specs(span: RetrievalEvidenceSpan) -> list[SpanMultiVectorSpec]:
    specs: list[SpanMultiVectorSpec] = []
    for vector_index, (token_start, token_end, vector_text) in enumerate(
        _window_word_ranges(
            span.span_text,
            word_window=MULTIVECTOR_WORD_WINDOW,
            word_overlap=MULTIVECTOR_WORD_OVERLAP,
            min_trailing_words=MULTIVECTOR_MIN_TRAILING_WORDS,
        )
    ):
        specs.append(
            SpanMultiVectorSpec(
                retrieval_evidence_span_id=span.id,
                document_id=span.document_id,
                run_id=span.run_id,
                source_type=span.source_type,
                source_id=span.source_id,
                vector_index=vector_index,
                token_start=token_start,
                token_end=token_end,
                vector_text=vector_text,
                content_sha256=_span_multivector_content_sha256(
                    retrieval_evidence_span_id=span.id,
                    vector_index=vector_index,
                    token_start=token_start,
                    token_end=token_end,
                    vector_text=vector_text,
                    span_content_sha256=span.content_sha256,
                    source_snapshot_sha256=span.source_snapshot_sha256,
                ),
                metadata={
                    "schema_name": MULTIVECTOR_SCHEMA_VERSION,
                    "source_span_content_sha256": span.content_sha256,
                    "source_snapshot_sha256": span.source_snapshot_sha256,
                    "word_window": MULTIVECTOR_WORD_WINDOW,
                    "word_overlap": MULTIVECTOR_WORD_OVERLAP,
                    "token_count": token_end - token_start,
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


def rebuild_retrieval_evidence_span_multivectors(
    session: Session,
    run: DocumentRun,
    *,
    embedding_provider: EmbeddingProvider | None = None,
) -> dict:
    if not isinstance(session, Session):
        return {
            "schema_name": "retrieval_evidence_span_multivector_rebuild_summary",
            "schema_version": "1.0",
            "run_id": str(run.id),
            "document_id": str(run.document_id),
            "multivector_count": 0,
            "source_span_count": 0,
            "embedding_status": "skipped_non_sqlalchemy_session",
            "embedding_error": None,
        }

    if embedding_provider is None:
        return {
            "schema_name": "retrieval_evidence_span_multivector_rebuild_summary",
            "schema_version": "1.0",
            "run_id": str(run.id),
            "document_id": str(run.document_id),
            "multivector_count": 0,
            "source_span_count": 0,
            "embedding_status": "skipped_no_embedding_provider",
            "embedding_error": None,
        }

    spans = list(
        session.scalars(
            select(RetrievalEvidenceSpan)
            .where(RetrievalEvidenceSpan.run_id == run.id)
            .order_by(
                RetrievalEvidenceSpan.source_type.asc(),
                RetrievalEvidenceSpan.source_id.asc(),
                RetrievalEvidenceSpan.span_index.asc(),
            )
        )
    )
    specs = [spec for span in spans for spec in build_span_multivector_specs(span)]
    spans_by_id = {span.id: span for span in spans}
    if not specs:
        session.execute(
            delete(RetrievalEvidenceSpanMultiVector).where(
                RetrievalEvidenceSpanMultiVector.run_id == run.id
            )
        )
        session.flush()
        return {
            "schema_name": "retrieval_evidence_span_multivector_rebuild_summary",
            "schema_version": "1.0",
            "run_id": str(run.id),
            "document_id": str(run.document_id),
            "multivector_count": 0,
            "source_span_count": len(spans),
            "embedding_status": "skipped_no_spans",
            "embedding_error": None,
        }

    embedding_status = "completed"
    embedding_error: str | None = None
    embedding_start = utcnow()
    embedding_timer_start = perf_counter()
    try:
        raw_embeddings = embedding_provider.embed_texts([spec.vector_text for spec in specs])
        embeddings = [list(embedding) for embedding in raw_embeddings]
        if len(embeddings) != len(specs):
            raise ValueError(
                f"Embedding provider returned {len(embeddings)} vectors for {len(specs)} specs."
            )
        invalid_dims = sorted(
            {
                len(embedding)
                for embedding in embeddings
                if len(embedding) != 1536
            }
        )
        if invalid_dims:
            raise ValueError(
                "Embedding provider returned invalid multivector dimensions: "
                f"{invalid_dims}; expected 1536."
            )
    except Exception as exc:
        embedding_status = "embedding_failed"
        embedding_error = str(exc)
        logger.warning(
            "retrieval_evidence_span_multivector_embedding_failed",
            run_id=str(run.id),
            document_id=str(run.document_id),
            error=str(exc),
        )
        operator_run = record_knowledge_operator_run(
            session,
            operator_kind="embed",
            operator_name="retrieval_evidence_span_multivector_generation",
            operator_version=MULTIVECTOR_SCHEMA_VERSION,
            status="failed",
            document_id=run.document_id,
            run_id=run.id,
            model_name=str(getattr(embedding_provider, "model", "unknown")),
            config={
                "schema_name": MULTIVECTOR_SCHEMA_VERSION,
                "word_window": MULTIVECTOR_WORD_WINDOW,
                "word_overlap": MULTIVECTOR_WORD_OVERLAP,
                "min_trailing_words": MULTIVECTOR_MIN_TRAILING_WORDS,
            },
            input_payload={
                "run_id": str(run.id),
                "source_span_count": len(spans),
                "requested_multivector_count": len(specs),
            },
            output_payload={
                "embedding_status": embedding_status,
                "embedding_error": embedding_error,
            },
            metrics={
                "source_span_count": len(spans),
                "requested_multivector_count": len(specs),
                "multivector_count": 0,
            },
            metadata={"embedding_error": embedding_error},
            inputs=[
                {
                    "input_kind": "retrieval_evidence_span",
                    "source_table": "retrieval_evidence_spans",
                    "source_id": span.id,
                    "payload": {
                        "source_type": span.source_type,
                        "source_id": str(span.source_id),
                        "span_index": span.span_index,
                        "content_sha256": span.content_sha256,
                        "source_snapshot_sha256": span.source_snapshot_sha256,
                    },
                }
                for span in spans
            ],
            started_at=embedding_start,
            completed_at=utcnow(),
            duration_ms=round((perf_counter() - embedding_timer_start) * 1000, 3),
        )
        session.flush()
        return {
            "schema_name": "retrieval_evidence_span_multivector_rebuild_summary",
            "schema_version": "1.0",
            "run_id": str(run.id),
            "document_id": str(run.document_id),
            "multivector_count": 0,
            "source_span_count": len(spans),
            "embedding_status": embedding_status,
            "embedding_error": embedding_error,
            "generation_operator_run_id": (
                str(operator_run.id) if operator_run is not None else None
            ),
        }

    now = utcnow()
    embedding_model = str(getattr(embedding_provider, "model", "unknown"))
    vector_rows: list[RetrievalEvidenceSpanMultiVector] = []
    session.execute(
        delete(RetrievalEvidenceSpanMultiVector).where(
            RetrievalEvidenceSpanMultiVector.run_id == run.id
        )
    )
    for spec, embedding in zip(specs, embeddings, strict=True):
        embedding_sha256 = _embedding_sha256(embedding)
        row = RetrievalEvidenceSpanMultiVector(
            id=uuid.uuid4(),
            retrieval_evidence_span_id=spec.retrieval_evidence_span_id,
            document_id=spec.document_id,
            run_id=spec.run_id,
            source_type=spec.source_type,
            source_id=spec.source_id,
            vector_index=spec.vector_index,
            token_start=spec.token_start,
            token_end=spec.token_end,
            vector_text=spec.vector_text,
            content_sha256=spec.content_sha256,
            embedding_model=embedding_model,
            embedding_dim=len(embedding),
            embedding_sha256=embedding_sha256,
            embedding=embedding,
            metadata_json={
                **spec.metadata,
                "embedding_status": embedding_status,
                "embedding_model": embedding_model,
                "embedding_sha256": embedding_sha256,
            },
            created_at=now,
        )
        vector_rows.append(row)
        session.add(row)
    session.flush()
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="embed",
        operator_name="retrieval_evidence_span_multivector_generation",
        operator_version=MULTIVECTOR_SCHEMA_VERSION,
        document_id=run.document_id,
        run_id=run.id,
        model_name=embedding_model,
        config={
            "schema_name": MULTIVECTOR_SCHEMA_VERSION,
            "word_window": MULTIVECTOR_WORD_WINDOW,
            "word_overlap": MULTIVECTOR_WORD_OVERLAP,
            "min_trailing_words": MULTIVECTOR_MIN_TRAILING_WORDS,
            "embedding_dim": 1536,
        },
        input_payload={
            "run_id": str(run.id),
            "source_span_count": len(spans),
            "source_span_content_sha256s": [span.content_sha256 for span in spans],
        },
        output_payload={
            "embedding_status": embedding_status,
            "embedding_model": embedding_model,
            "multivector_count": len(vector_rows),
            "multivector_content_sha256s": [row.content_sha256 for row in vector_rows],
            "embedding_sha256s": [row.embedding_sha256 for row in vector_rows],
        },
        metrics={
            "source_span_count": len(spans),
            "multivector_count": len(vector_rows),
            "chunk_multivector_count": sum(1 for row in vector_rows if row.source_type == "chunk"),
            "table_multivector_count": sum(1 for row in vector_rows if row.source_type == "table"),
        },
        metadata={
            "audit_role": (
                "records source retrieval spans and generated span multivectors for "
                "late-interaction retrieval"
            ),
            "embedding_status": embedding_status,
        },
        inputs=[
            {
                "input_kind": "retrieval_evidence_span",
                "source_table": "retrieval_evidence_spans",
                "source_id": span.id,
                "payload": {
                    "source_type": span.source_type,
                    "source_id": str(span.source_id),
                    "span_index": span.span_index,
                    "content_sha256": span.content_sha256,
                    "source_snapshot_sha256": span.source_snapshot_sha256,
                },
            }
            for span in spans
        ],
        outputs=[
            {
                "output_kind": "retrieval_evidence_span_multivector",
                "target_table": "retrieval_evidence_span_multivectors",
                "target_id": row.id,
                "payload": {
                    "retrieval_evidence_span_id": str(row.retrieval_evidence_span_id),
                    "source_span_content_sha256": spans_by_id[
                        row.retrieval_evidence_span_id
                    ].content_sha256,
                    "source_type": row.source_type,
                    "source_id": str(row.source_id),
                    "vector_index": row.vector_index,
                    "token_start": row.token_start,
                    "token_end": row.token_end,
                    "content_sha256": row.content_sha256,
                    "embedding_model": row.embedding_model,
                    "embedding_dim": row.embedding_dim,
                    "embedding_sha256": row.embedding_sha256,
                },
            }
            for row in vector_rows
        ],
        started_at=embedding_start,
        completed_at=utcnow(),
        duration_ms=round((perf_counter() - embedding_timer_start) * 1000, 3),
    )
    if operator_run is not None:
        for row in vector_rows:
            row.metadata_json = {
                **(row.metadata_json or {}),
                "generation_operator_run_id": str(operator_run.id),
            }
    session.flush()
    return {
        "schema_name": "retrieval_evidence_span_multivector_rebuild_summary",
        "schema_version": "1.0",
        "run_id": str(run.id),
        "document_id": str(run.document_id),
        "multivector_count": len(specs),
        "source_span_count": len(spans),
        "embedding_status": embedding_status,
        "embedding_error": embedding_error,
        "embedding_model": embedding_model,
        "generation_operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }


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
    multivector_summary = rebuild_retrieval_evidence_span_multivectors(
        session,
        run,
        embedding_provider=embedding_provider if embedding_status == "completed" else None,
    )
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
        "multivector_summary": multivector_summary,
    }


def ensure_retrieval_evidence_spans_for_search(
    session: Session,
    *,
    run_id: UUID | None = None,
    document_id: UUID | None = None,
) -> dict:
    if not isinstance(session, Session):
        return {
            "schema_name": "retrieval_evidence_span_backfill_summary",
            "schema_version": "1.0",
            "checked_run_count": 0,
            "rebuilt_run_count": 0,
            "rebuilt_runs": [],
        }

    if run_id is not None:
        run_rows = [run] if (run := session.get(DocumentRun, run_id)) is not None else []
    elif document_id is not None:
        document = session.get(Document, document_id)
        run_rows = (
            [run]
            if document is not None
            and document.active_run_id is not None
            and (run := session.get(DocumentRun, document.active_run_id)) is not None
            else []
        )
    else:
        run_rows = list(
            session.scalars(
                select(DocumentRun)
                .join(Document, Document.active_run_id == DocumentRun.id)
                .order_by(DocumentRun.created_at.asc(), DocumentRun.id.asc())
            )
        )

    rebuilt_runs: list[dict] = []
    for run in run_rows:
        if int((run.chunk_count or 0) + (run.table_count or 0)) <= 0:
            continue
        span_count = session.scalar(
            select(func.count())
            .select_from(RetrievalEvidenceSpan)
            .where(RetrievalEvidenceSpan.run_id == run.id)
        )
        if span_count:
            continue
        rebuilt_runs.append(
            rebuild_retrieval_evidence_spans(
                session,
                run,
                embedding_provider=None,
            )
        )

    return {
        "schema_name": "retrieval_evidence_span_backfill_summary",
        "schema_version": "1.0",
        "checked_run_count": len(run_rows),
        "rebuilt_run_count": len(rebuilt_runs),
        "rebuilt_runs": rebuilt_runs,
    }
