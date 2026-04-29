from __future__ import annotations

import uuid
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
from app.services.retrieval_span_specs import (
    MULTIVECTOR_MIN_TRAILING_WORDS,
    MULTIVECTOR_SCHEMA_VERSION,
    MULTIVECTOR_WORD_OVERLAP,
    MULTIVECTOR_WORD_WINDOW,
    SPAN_WORD_WINDOW,
    SourceSpanSpec,
    build_chunk_span_specs,
    build_span_multivector_specs,
    build_table_span_specs,
)

logger = structlog.get_logger(__name__)

__all__ = [
    "MULTIVECTOR_WORD_WINDOW",
    "SPAN_WORD_WINDOW",
    "_embedding_sha256",
    "build_chunk_span_specs",
    "build_span_multivector_specs",
    "build_table_span_specs",
    "ensure_retrieval_evidence_spans_for_search",
    "rebuild_retrieval_evidence_span_multivectors",
    "rebuild_retrieval_evidence_spans",
]


def _embedding_sha256(embedding: list[float]) -> str:
    return _payload_sha256(
        {
            "schema_name": "retrieval_evidence_span_multivector_embedding",
            "schema_version": "1.0",
            "embedding": [float(value) for value in embedding],
        }
    )


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
            {len(embedding) for embedding in embeddings if len(embedding) != 1536}
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
