from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashes import file_sha256 as _file_sha256
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentFigure,
    DocumentRun,
    DocumentTable,
    DocumentTableSegment,
    KnowledgeOperatorInput,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
    RetrievalEvidenceSpanMultiVector,
    SearchRequestResult,
    SearchRequestResultSpan,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import uuid_values as _uuid_values


def io_payload(row: KnowledgeOperatorInput | KnowledgeOperatorOutput, *, kind_field: str) -> dict:
    payload = {
        "id": str(row.id),
        "operator_run_id": str(row.operator_run_id),
        kind_field: getattr(row, kind_field),
        "source_table": getattr(row, "source_table", None),
        "source_id": str(getattr(row, "source_id", None) or "") or None,
        "target_table": getattr(row, "target_table", None),
        "target_id": str(getattr(row, "target_id", None) or "") or None,
        "artifact_path": row.artifact_path,
        "artifact_sha256": row.artifact_sha256,
        "payload": row.payload_json or {},
        "created_at": row.created_at,
    }
    return {key: value for key, value in payload.items() if value is not None}


def operator_run_payload(
    row: KnowledgeOperatorRun,
    *,
    inputs: list[KnowledgeOperatorInput],
    outputs: list[KnowledgeOperatorOutput],
) -> dict:
    return {
        "id": row.id,
        "parent_operator_run_id": row.parent_operator_run_id,
        "operator_kind": row.operator_kind,
        "operator_name": row.operator_name,
        "operator_version": row.operator_version,
        "status": row.status,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "search_request_id": row.search_request_id,
        "search_harness_evaluation_id": row.search_harness_evaluation_id,
        "agent_task_id": row.agent_task_id,
        "agent_task_attempt_id": row.agent_task_attempt_id,
        "model_name": row.model_name,
        "model_version": row.model_version,
        "prompt_sha256": row.prompt_sha256,
        "config_sha256": row.config_sha256,
        "input_sha256": row.input_sha256,
        "output_sha256": row.output_sha256,
        "metrics": row.metrics_json or {},
        "metadata": row.metadata_json or {},
        "started_at": row.started_at,
        "completed_at": row.completed_at,
        "duration_ms": row.duration_ms,
        "created_at": row.created_at,
        "inputs": [io_payload(item, kind_field="input_kind") for item in inputs],
        "outputs": [io_payload(item, kind_field="output_kind") for item in outputs],
    }


def select_by_ids(session: Session, model, ids: Iterable[UUID]) -> dict[UUID, Any]:
    unique_ids = {value for value in ids if value is not None}
    if not unique_ids:
        return {}
    return {row.id: row for row in session.scalars(select(model).where(model.id.in_(unique_ids)))}


def document_payload(row: Document | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "source_filename": row.source_filename,
        "sha256": row.sha256,
        "mime_type": row.mime_type,
        "title": row.title,
        "page_count": row.page_count,
        "active_run_id": row.active_run_id,
        "latest_run_id": row.latest_run_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def run_payload(row: DocumentRun | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "document_id": row.document_id,
        "run_number": row.run_number,
        "status": row.status,
        "docling_json_path": row.docling_json_path,
        "yaml_path": row.yaml_path,
        "chunk_count": row.chunk_count,
        "table_count": row.table_count,
        "figure_count": row.figure_count,
        "embedding_model": row.embedding_model,
        "embedding_dim": row.embedding_dim,
        "validation_status": row.validation_status,
        "validation_results": row.validation_results_json or {},
        "created_at": row.created_at,
        "started_at": row.started_at,
        "completed_at": row.completed_at,
    }


def manifest_run_payload(row: DocumentRun | None) -> dict | None:
    payload = run_payload(row)
    if payload is None:
        return None
    payload["artifact_hashes"] = {
        "docling_json_sha256": _file_sha256(row.docling_json_path),
        "document_yaml_sha256": _file_sha256(row.yaml_path),
    }
    return payload


def chunk_payload(row: DocumentChunk | None) -> dict | None:
    if row is None:
        return None
    payload = {
        "id": row.id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "chunk_index": row.chunk_index,
        "heading": row.heading,
        "page_from": row.page_from,
        "page_to": row.page_to,
        "text": row.text,
        "metadata": row.metadata_json or {},
        "created_at": row.created_at,
    }
    payload["text_sha256"] = payload_sha256({"text": row.text})
    return payload


def table_segment_payload(row: DocumentTableSegment) -> dict:
    return {
        "id": row.id,
        "table_id": row.table_id,
        "run_id": row.run_id,
        "segment_index": row.segment_index,
        "source_table_ref": row.source_table_ref,
        "page_from": row.page_from,
        "page_to": row.page_to,
        "segment_order": row.segment_order,
        "metadata": row.metadata_json or {},
        "created_at": row.created_at,
    }


def table_payload(
    row: DocumentTable | None,
    *,
    segments: list[DocumentTableSegment],
) -> dict | None:
    if row is None:
        return None
    payload = {
        "id": row.id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "table_index": row.table_index,
        "title": row.title,
        "logical_table_key": row.logical_table_key,
        "table_version": row.table_version,
        "supersedes_table_id": row.supersedes_table_id,
        "lineage_group": row.lineage_group,
        "heading": row.heading,
        "page_from": row.page_from,
        "page_to": row.page_to,
        "row_count": row.row_count,
        "col_count": row.col_count,
        "status": row.status,
        "search_text": row.search_text,
        "preview_text": row.preview_text,
        "metadata": row.metadata_json or {},
        "json_path": row.json_path,
        "yaml_path": row.yaml_path,
        "segments": [table_segment_payload(segment) for segment in segments],
        "created_at": row.created_at,
    }
    payload["search_text_sha256"] = payload_sha256({"search_text": row.search_text})
    payload["preview_text_sha256"] = payload_sha256({"preview_text": row.preview_text})
    return payload


def figure_payload(row: DocumentFigure | None) -> dict | None:
    if row is None:
        return None
    payload = {
        "id": row.id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "figure_index": row.figure_index,
        "source_figure_ref": row.source_figure_ref,
        "caption": row.caption,
        "heading": row.heading,
        "page_from": row.page_from,
        "page_to": row.page_to,
        "confidence": row.confidence,
        "status": row.status,
        "metadata": row.metadata_json or {},
        "json_path": row.json_path,
        "yaml_path": row.yaml_path,
        "created_at": row.created_at,
    }
    payload["caption_sha256"] = payload_sha256({"caption": row.caption})
    return payload


def late_interaction_matches(metadata: dict | None) -> list[dict]:
    late_interaction = (metadata or {}).get("late_interaction") or {}
    matches = late_interaction.get("maxsim_matches") or []
    return [match for match in matches if isinstance(match, dict)]


def late_interaction_span_vector_ids(metadata: dict | None) -> list[UUID]:
    return _uuid_values(
        match.get("span_vector_id") for match in late_interaction_matches(metadata)
    )


def span_multivector_payload(row: RetrievalEvidenceSpanMultiVector) -> dict:
    payload = {
        "span_vector_id": row.id,
        "retrieval_evidence_span_id": row.retrieval_evidence_span_id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "vector_index": row.vector_index,
        "token_start": row.token_start,
        "token_end": row.token_end,
        "vector_text": row.vector_text,
        "content_sha256": row.content_sha256,
        "embedding_model": row.embedding_model,
        "embedding_dim": row.embedding_dim,
        "embedding_sha256": row.embedding_sha256,
        "metadata": row.metadata_json or {},
        "created_at": row.created_at,
    }
    payload["span_vector_snapshot_sha256"] = payload_sha256(payload)
    return payload


def load_multivector_generation_links(
    session: Session,
    vector_ids: Iterable[UUID],
) -> dict[UUID, list[dict]]:
    unique_vector_ids = {value for value in vector_ids if value is not None}
    if not unique_vector_ids:
        return {}

    rows = session.execute(
        select(KnowledgeOperatorOutput, KnowledgeOperatorRun)
        .join(
            KnowledgeOperatorRun,
            KnowledgeOperatorRun.id == KnowledgeOperatorOutput.operator_run_id,
        )
        .where(
            KnowledgeOperatorOutput.target_table == "retrieval_evidence_span_multivectors",
            KnowledgeOperatorOutput.target_id.in_(unique_vector_ids),
            KnowledgeOperatorRun.operator_name == "retrieval_evidence_span_multivector_generation",
        )
        .order_by(
            KnowledgeOperatorOutput.target_id.asc(),
            KnowledgeOperatorRun.created_at.asc(),
            KnowledgeOperatorOutput.output_index.asc(),
        )
    ).all()
    links_by_vector_id: dict[UUID, list[dict]] = {}
    for output_row, operator_run in rows:
        if output_row.target_id is None:
            continue
        links_by_vector_id.setdefault(output_row.target_id, []).append(
            {
                "generation_operator_run_id": operator_run.id,
                "generation_operator_name": operator_run.operator_name,
                "generation_operator_version": operator_run.operator_version,
                "generation_operator_status": operator_run.status,
                "generation_output_id": output_row.id,
                "generation_output_sha256": payload_sha256(output_row.payload_json or {}),
            }
        )
    return links_by_vector_id


def search_result_span_payload(
    row: SearchRequestResultSpan,
    *,
    span_vectors_by_id: dict[UUID, RetrievalEvidenceSpanMultiVector] | None = None,
    generation_links_by_vector_id: dict[UUID, list[dict]] | None = None,
) -> dict:
    metadata = row.metadata_json or {}
    span_vectors_by_id = span_vectors_by_id or {}
    generation_links_by_vector_id = generation_links_by_vector_id or {}
    vector_payloads = [
        {
            **span_multivector_payload(vector_row),
            "generation_operator_runs": generation_links_by_vector_id.get(vector_row.id, []),
        }
        for vector_id in late_interaction_span_vector_ids(metadata)
        if (vector_row := span_vectors_by_id.get(vector_id)) is not None
    ]
    payload = {
        "search_request_result_span_id": row.id,
        "retrieval_evidence_span_id": row.retrieval_evidence_span_id,
        "span_rank": row.span_rank,
        "score_kind": row.score_kind,
        "score": row.score,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "span_index": row.span_index,
        "page_from": row.page_from,
        "page_to": row.page_to,
        "text_excerpt": row.text_excerpt,
        "content_sha256": row.content_sha256,
        "source_snapshot_sha256": row.source_snapshot_sha256,
        "metadata": metadata,
        "created_at": row.created_at,
    }
    if vector_payloads:
        payload["late_interaction_multivectors"] = vector_payloads
    return payload


def result_payload(
    row: SearchRequestResult,
    *,
    source_snapshot_sha256: str | None,
    retrieval_evidence_spans: list[dict] | None = None,
) -> dict:
    return {
        "search_request_result_id": row.id,
        "rank": row.rank,
        "base_rank": row.base_rank,
        "result_type": row.result_type,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "chunk_id": row.chunk_id,
        "table_id": row.table_id,
        "score": row.score,
        "keyword_score": row.keyword_score,
        "semantic_score": row.semantic_score,
        "hybrid_score": row.hybrid_score,
        "rerank_features": row.rerank_features_json or {},
        "page_from": row.page_from,
        "page_to": row.page_to,
        "source_filename": row.source_filename,
        "label": row.label,
        "preview_text": row.preview_text,
        "source_snapshot_sha256": source_snapshot_sha256,
        "retrieval_evidence_spans": retrieval_evidence_spans or [],
    }


def source_evidence_payloads(
    session: Session,
    result_rows: list[SearchRequestResult],
) -> list[dict]:
    result_ids = [row.id for row in result_rows]
    documents_by_id = select_by_ids(session, Document, (row.document_id for row in result_rows))
    runs_by_id = select_by_ids(session, DocumentRun, (row.run_id for row in result_rows))
    chunks_by_id = select_by_ids(
        session,
        DocumentChunk,
        (row.chunk_id for row in result_rows if row.chunk_id is not None),
    )
    tables_by_id = select_by_ids(
        session,
        DocumentTable,
        (row.table_id for row in result_rows if row.table_id is not None),
    )
    table_ids = set(tables_by_id)
    segments_by_table_id: dict[UUID, list[DocumentTableSegment]] = {
        table_id: [] for table_id in table_ids
    }
    if table_ids:
        segment_rows = session.scalars(
            select(DocumentTableSegment)
            .where(DocumentTableSegment.table_id.in_(table_ids))
            .order_by(
                DocumentTableSegment.table_id.asc(),
                DocumentTableSegment.segment_order.asc(),
                DocumentTableSegment.segment_index.asc(),
            )
        )
        for segment in segment_rows:
            segments_by_table_id.setdefault(segment.table_id, []).append(segment)

    spans_by_result_id: dict[UUID, list[SearchRequestResultSpan]] = {
        result_id: [] for result_id in result_ids
    }
    if result_ids:
        span_rows = session.scalars(
            select(SearchRequestResultSpan)
            .where(SearchRequestResultSpan.search_request_result_id.in_(result_ids))
            .order_by(
                SearchRequestResultSpan.search_request_result_id.asc(),
                SearchRequestResultSpan.span_rank.asc(),
            )
        )
        for span in span_rows:
            spans_by_result_id.setdefault(span.search_request_result_id, []).append(span)

    span_vectors_by_id = select_by_ids(
        session,
        RetrievalEvidenceSpanMultiVector,
        (
            vector_id
            for spans in spans_by_result_id.values()
            for span in spans
            for vector_id in late_interaction_span_vector_ids(span.metadata_json or {})
        ),
    )
    generation_links_by_vector_id = load_multivector_generation_links(
        session,
        span_vectors_by_id,
    )

    payloads: list[dict] = []
    for result in result_rows:
        document = documents_by_id.get(result.document_id)
        run = runs_by_id.get(result.run_id)
        chunk_payload_value = None
        table_payload_value = None
        if result.result_type == "chunk" and result.chunk_id is not None:
            chunk_payload_value = chunk_payload(chunks_by_id.get(result.chunk_id))
        if result.result_type == "table" and result.table_id is not None:
            table_payload_value = table_payload(
                tables_by_id.get(result.table_id),
                segments=segments_by_table_id.get(result.table_id, []),
            )
        payload = {
            "search_request_result_id": result.id,
            "rank": result.rank,
            "result_type": result.result_type,
            "source_id": result.chunk_id if result.result_type == "chunk" else result.table_id,
            "document": document_payload(document),
            "run": run_payload(run),
            "chunk": chunk_payload_value,
            "table": table_payload_value,
            "retrieval_evidence_spans": [
                search_result_span_payload(
                    span,
                    span_vectors_by_id=span_vectors_by_id,
                    generation_links_by_vector_id=generation_links_by_vector_id,
                )
                for span in spans_by_result_id.get(result.id, [])
            ],
        }
        payload["source_snapshot_sha256"] = payload_sha256(payload)
        payloads.append(payload)
    return payloads
