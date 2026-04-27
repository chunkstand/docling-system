from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    AgentTaskVerification,
    ClaimEvidenceDerivation,
    Document,
    DocumentChunk,
    DocumentFigure,
    DocumentRun,
    DocumentTable,
    DocumentTableSegment,
    EvidenceManifest,
    EvidencePackageExport,
    EvidenceTraceEdge,
    EvidenceTraceNode,
    KnowledgeOperatorInput,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
    RetrievalEvidenceSpanMultiVector,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
    SemanticAssertion,
    SemanticAssertionEvidence,
    SemanticFact,
    SemanticFactEvidence,
)
from app.services.semantic_governance import (
    record_technical_report_prov_export_governance_event,
    semantic_governance_chain_for_audit,
)
from app.services.storage import StorageService

TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND = "technical_report_prov_export"
TECHNICAL_REPORT_PROV_EXPORT_FILENAME = "technical_report_prov_export.json"
TECHNICAL_REPORT_PROV_EXPORT_RECEIPT_SCHEMA = "technical_report_prov_export_receipt"
PROV_EXPORT_RECEIPT_SIGNATURE_ALGORITHM = "hmac-sha256"
_PROV_INTEGRITY_EXCLUDED_FIELDS = {"frozen_export", "prov_integrity"}


def payload_sha256(payload: Any | None) -> str | None:
    if payload is None:
        return None
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_payload(payload: Any | None) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        value = payload
    else:
        value = {"value": payload}
    return json.loads(json.dumps(value, default=str, sort_keys=True))


def _uuid_or_none(value: Any | None) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _uuid_values(values: Iterable[Any]) -> list[UUID]:
    result: list[UUID] = []
    seen: set[UUID] = set()
    for value in values:
        try:
            uuid_value = _uuid_or_none(value)
        except (TypeError, ValueError):
            continue
        if uuid_value is not None and uuid_value not in seen:
            result.append(uuid_value)
            seen.add(uuid_value)
    return result


def _file_sha256(path: str | None) -> str | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_inputs(
    session: Session,
    *,
    operator_run_id: UUID,
    rows: Iterable[dict[str, Any]],
    created_at,
) -> None:
    for index, row in enumerate(rows):
        session.add(
            KnowledgeOperatorInput(
                id=uuid.uuid4(),
                operator_run_id=operator_run_id,
                input_index=int(row.get("input_index", index)),
                input_kind=str(row.get("input_kind") or row.get("kind") or "input"),
                source_table=row.get("source_table"),
                source_id=_uuid_or_none(row.get("source_id")),
                artifact_path=row.get("artifact_path"),
                artifact_sha256=row.get("artifact_sha256"),
                payload_json=_json_payload(row.get("payload")),
                created_at=created_at,
            )
        )


def _record_outputs(
    session: Session,
    *,
    operator_run_id: UUID,
    rows: Iterable[dict[str, Any]],
    created_at,
) -> None:
    for index, row in enumerate(rows):
        session.add(
            KnowledgeOperatorOutput(
                id=uuid.uuid4(),
                operator_run_id=operator_run_id,
                output_index=int(row.get("output_index", index)),
                output_kind=str(row.get("output_kind") or row.get("kind") or "output"),
                target_table=row.get("target_table"),
                target_id=_uuid_or_none(row.get("target_id")),
                artifact_path=row.get("artifact_path"),
                artifact_sha256=row.get("artifact_sha256"),
                payload_json=_json_payload(row.get("payload")),
                created_at=created_at,
            )
        )


def record_knowledge_operator_run(
    session: Session | None,
    *,
    operator_kind: str,
    operator_name: str,
    operator_version: str | None = None,
    status: str = "completed",
    parent_operator_run_id: UUID | None = None,
    document_id: UUID | None = None,
    run_id: UUID | None = None,
    search_request_id: UUID | None = None,
    search_harness_evaluation_id: UUID | None = None,
    agent_task_id: UUID | None = None,
    agent_task_attempt_id: UUID | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    prompt_sha256: str | None = None,
    config: Any | None = None,
    input_payload: Any | None = None,
    output_payload: Any | None = None,
    metrics: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    inputs: Iterable[dict[str, Any]] = (),
    outputs: Iterable[dict[str, Any]] = (),
    started_at=None,
    completed_at=None,
    duration_ms: float | None = None,
) -> KnowledgeOperatorRun | None:
    if session is None or not hasattr(session, "add"):
        return None

    created_at = utcnow()
    completed_at = completed_at or created_at
    run = KnowledgeOperatorRun(
        id=uuid.uuid4(),
        parent_operator_run_id=parent_operator_run_id,
        operator_kind=operator_kind,
        operator_name=operator_name,
        operator_version=operator_version,
        status=status,
        document_id=document_id,
        run_id=run_id,
        search_request_id=search_request_id,
        search_harness_evaluation_id=search_harness_evaluation_id,
        agent_task_id=agent_task_id,
        agent_task_attempt_id=agent_task_attempt_id,
        model_name=model_name,
        model_version=model_version,
        prompt_sha256=prompt_sha256,
        config_sha256=payload_sha256(config),
        input_sha256=payload_sha256(input_payload),
        output_sha256=payload_sha256(output_payload),
        metrics_json=_json_payload(metrics),
        metadata_json=_json_payload(metadata),
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        created_at=created_at,
    )
    session.add(run)
    session.flush()
    _record_inputs(session, operator_run_id=run.id, rows=inputs, created_at=created_at)
    _record_outputs(session, operator_run_id=run.id, rows=outputs, created_at=created_at)
    session.flush()
    return run


def _io_payload(row: KnowledgeOperatorInput | KnowledgeOperatorOutput, *, kind_field: str) -> dict:
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


def _operator_run_payload(
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
        "inputs": [_io_payload(item, kind_field="input_kind") for item in inputs],
        "outputs": [_io_payload(item, kind_field="output_kind") for item in outputs],
    }


def _select_by_ids(session: Session, model, ids: Iterable[UUID]) -> dict[UUID, Any]:
    unique_ids = {value for value in ids if value is not None}
    if not unique_ids:
        return {}
    return {row.id: row for row in session.scalars(select(model).where(model.id.in_(unique_ids)))}


def _document_payload(row: Document | None) -> dict | None:
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


def _run_payload(row: DocumentRun | None) -> dict | None:
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


def _manifest_run_payload(row: DocumentRun | None) -> dict | None:
    payload = _run_payload(row)
    if payload is None:
        return None
    payload["artifact_hashes"] = {
        "docling_json_sha256": _file_sha256(row.docling_json_path),
        "document_yaml_sha256": _file_sha256(row.yaml_path),
    }
    return payload


def _chunk_payload(row: DocumentChunk | None) -> dict | None:
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


def _table_segment_payload(row: DocumentTableSegment) -> dict:
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


def _table_payload(
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
        "segments": [_table_segment_payload(segment) for segment in segments],
        "created_at": row.created_at,
    }
    payload["search_text_sha256"] = payload_sha256({"search_text": row.search_text})
    payload["preview_text_sha256"] = payload_sha256({"preview_text": row.preview_text})
    return payload


def _figure_payload(row: DocumentFigure | None) -> dict | None:
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


def _late_interaction_matches(metadata: dict | None) -> list[dict]:
    late_interaction = (metadata or {}).get("late_interaction") or {}
    matches = late_interaction.get("maxsim_matches") or []
    return [match for match in matches if isinstance(match, dict)]


def _late_interaction_span_vector_ids(metadata: dict | None) -> list[UUID]:
    return _uuid_values(
        match.get("span_vector_id") for match in _late_interaction_matches(metadata)
    )


def _span_multivector_payload(row: RetrievalEvidenceSpanMultiVector) -> dict:
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


def _load_multivector_generation_links(
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
            KnowledgeOperatorRun.operator_name
            == "retrieval_evidence_span_multivector_generation",
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


def _search_result_span_payload(
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
            **_span_multivector_payload(vector_row),
            "generation_operator_runs": generation_links_by_vector_id.get(vector_row.id, []),
        }
        for vector_id in _late_interaction_span_vector_ids(metadata)
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


def _result_payload(
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


def _source_evidence_payloads(
    session: Session,
    result_rows: list[SearchRequestResult],
) -> list[dict]:
    result_ids = [row.id for row in result_rows]
    documents_by_id = _select_by_ids(session, Document, (row.document_id for row in result_rows))
    runs_by_id = _select_by_ids(session, DocumentRun, (row.run_id for row in result_rows))
    chunks_by_id = _select_by_ids(
        session,
        DocumentChunk,
        (row.chunk_id for row in result_rows if row.chunk_id is not None),
    )
    tables_by_id = _select_by_ids(
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

    span_vectors_by_id = _select_by_ids(
        session,
        RetrievalEvidenceSpanMultiVector,
        (
            vector_id
            for spans in spans_by_result_id.values()
            for span in spans
            for vector_id in _late_interaction_span_vector_ids(span.metadata_json or {})
        ),
    )
    generation_links_by_vector_id = _load_multivector_generation_links(
        session,
        span_vectors_by_id,
    )

    payloads: list[dict] = []
    for result in result_rows:
        document = documents_by_id.get(result.document_id)
        run = runs_by_id.get(result.run_id)
        chunk_payload = None
        table_payload = None
        if result.result_type == "chunk" and result.chunk_id is not None:
            chunk_payload = _chunk_payload(chunks_by_id.get(result.chunk_id))
        if result.result_type == "table" and result.table_id is not None:
            table_payload = _table_payload(
                tables_by_id.get(result.table_id),
                segments=segments_by_table_id.get(result.table_id, []),
            )
        payload = {
            "search_request_result_id": result.id,
            "rank": result.rank,
            "result_type": result.result_type,
            "source_id": result.chunk_id if result.result_type == "chunk" else result.table_id,
            "document": _document_payload(document),
            "run": _run_payload(run),
            "chunk": chunk_payload,
            "table": table_payload,
            "retrieval_evidence_spans": [
                _search_result_span_payload(
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


def get_search_evidence_package(session: Session, search_request_id: UUID) -> dict:
    request_row = session.get(SearchRequestRecord, search_request_id)
    if request_row is None:
        raise ValueError(f"Search request '{search_request_id}' was not found.")

    result_rows = list(
        session.scalars(
            select(SearchRequestResult)
            .where(SearchRequestResult.search_request_id == search_request_id)
            .order_by(SearchRequestResult.rank.asc())
        )
    )
    source_evidence = _source_evidence_payloads(session, result_rows)
    source_evidence_by_result_id = {
        str(row["search_request_result_id"]): row for row in source_evidence
    }
    multivector_generation_operator_ids = _uuid_values(
        link.get("generation_operator_run_id")
        for item in source_evidence
        for span in item.get("retrieval_evidence_spans", [])
        for vector in span.get("late_interaction_multivectors", [])
        for link in vector.get("generation_operator_runs", [])
    )

    operator_filter = KnowledgeOperatorRun.search_request_id == search_request_id
    if multivector_generation_operator_ids:
        operator_filter = or_(
            operator_filter,
            KnowledgeOperatorRun.id.in_(multivector_generation_operator_ids),
        )
    operator_rows = list(
        session.scalars(
            select(KnowledgeOperatorRun)
            .where(operator_filter)
            .order_by(
                KnowledgeOperatorRun.created_at.asc(),
                KnowledgeOperatorRun.id.asc(),
            )
        )
    )
    operator_ids = [row.id for row in operator_rows]
    input_rows: list[KnowledgeOperatorInput] = []
    output_rows: list[KnowledgeOperatorOutput] = []
    if operator_ids:
        input_rows = list(
            session.scalars(
                select(KnowledgeOperatorInput)
                .where(KnowledgeOperatorInput.operator_run_id.in_(operator_ids))
                .order_by(KnowledgeOperatorInput.input_index.asc(), KnowledgeOperatorInput.id.asc())
            )
        )
        output_rows = list(
            session.scalars(
                select(KnowledgeOperatorOutput)
                .where(KnowledgeOperatorOutput.operator_run_id.in_(operator_ids))
                .order_by(
                    KnowledgeOperatorOutput.output_index.asc(),
                    KnowledgeOperatorOutput.id.asc(),
                )
            )
        )

    inputs_by_run: dict[UUID, list[KnowledgeOperatorInput]] = {row.id: [] for row in operator_rows}
    outputs_by_run: dict[UUID, list[KnowledgeOperatorOutput]] = {
        row.id: [] for row in operator_rows
    }
    for row in input_rows:
        inputs_by_run.setdefault(row.operator_run_id, []).append(row)
    for row in output_rows:
        outputs_by_run.setdefault(row.operator_run_id, []).append(row)

    late_interaction_span_payloads = [
        span
        for item in source_evidence
        for span in item.get("retrieval_evidence_spans", [])
        if span.get("score_kind") == "late_interaction_maxsim"
    ]
    late_interaction_vector_payloads = [
        vector
        for span in late_interaction_span_payloads
        for vector in span.get("late_interaction_multivectors", [])
    ]
    provenance_edges = _search_evidence_provenance_edges(
        search_request_id=search_request_id,
        source_evidence=source_evidence,
    )
    package = {
        "schema_name": "search_evidence_package",
        "schema_version": "1.0",
        "search_request": {
            "id": request_row.id,
            "query_text": request_row.query_text,
            "mode": request_row.mode,
            "filters": request_row.filters_json or {},
            "origin": request_row.origin,
            "harness_name": request_row.harness_name,
            "reranker_name": request_row.reranker_name,
            "reranker_version": request_row.reranker_version,
            "retrieval_profile_name": request_row.retrieval_profile_name,
            "harness_config": request_row.harness_config_json or {},
            "embedding_status": request_row.embedding_status,
            "candidate_count": request_row.candidate_count,
            "result_count": request_row.result_count,
            "table_hit_count": request_row.table_hit_count,
            "created_at": request_row.created_at,
        },
        "operator_runs": [
            _operator_run_payload(
                row,
                inputs=inputs_by_run.get(row.id, []),
                outputs=outputs_by_run.get(row.id, []),
            )
            for row in operator_rows
        ],
        "results": [
            _result_payload(
                row,
                source_snapshot_sha256=source_evidence_by_result_id.get(str(row.id), {}).get(
                    "source_snapshot_sha256"
                ),
                retrieval_evidence_spans=[
                    dict(span)
                    for span in source_evidence_by_result_id.get(str(row.id), {}).get(
                        "retrieval_evidence_spans", []
                    )
                ],
            )
            for row in result_rows
        ],
        "source_evidence": source_evidence,
        "provenance_edges": provenance_edges,
        "audit_checklist": {
            "has_retrieve_run": any(row.operator_kind == "retrieve" for row in operator_rows),
            "has_rerank_run": any(row.operator_kind == "rerank" for row in operator_rows),
            "has_judge_run": any(row.operator_kind == "judge" for row in operator_rows),
            "has_multivector_generation_run": any(
                row.operator_name == "retrieval_evidence_span_multivector_generation"
                for row in operator_rows
            ),
            "has_config_hashes": all(
                row.config_sha256
                for row in operator_rows
                if row.operator_kind in {"retrieve", "rerank", "embed"}
            ),
            "result_count_matches": len(result_rows) == request_row.result_count,
            "has_source_snapshots": bool(source_evidence),
            "all_results_have_source_snapshot": len(source_evidence) == len(result_rows),
            "all_results_have_source_record": all(
                item.get(str(item.get("result_type"))) is not None for item in source_evidence
            ),
            "all_results_reference_active_run": all(
                item.get("document") is not None
                and item.get("run") is not None
                and str(item["document"].get("active_run_id")) == str(item["run"].get("id"))
                for item in source_evidence
            ),
            "all_result_runs_validation_passed": all(
                item.get("run") is not None and item["run"].get("validation_status") == "passed"
                for item in source_evidence
            ),
            "all_source_snapshots_hashed": all(
                bool(item.get("source_snapshot_sha256")) for item in source_evidence
            ),
            "has_retrieval_evidence_spans": any(
                item.get("retrieval_evidence_spans") for item in source_evidence
            ),
            "all_results_have_retrieval_evidence_spans": all(
                bool(item.get("retrieval_evidence_spans")) for item in source_evidence
            ),
            "all_span_citations_hashed": all(
                bool(span.get("content_sha256")) and bool(span.get("source_snapshot_sha256"))
                for item in source_evidence
                for span in item.get("retrieval_evidence_spans", [])
            ),
            "late_interaction_trace_count": len(late_interaction_span_payloads),
            "late_interaction_span_vector_count": len(late_interaction_vector_payloads),
            "late_interaction_generation_operator_count": len(
                set(multivector_generation_operator_ids)
            ),
            "all_late_interaction_vectors_materialized": all(
                len(span.get("late_interaction_multivectors", []))
                == len(_late_interaction_matches(span.get("metadata") or {}))
                for span in late_interaction_span_payloads
            ),
            "all_late_interaction_vectors_hashed": (
                not late_interaction_span_payloads
                or bool(late_interaction_vector_payloads)
                and all(
                    bool(vector.get("content_sha256"))
                    and bool(vector.get("embedding_sha256"))
                    and bool(vector.get("span_vector_snapshot_sha256"))
                    for vector in late_interaction_vector_payloads
                )
            ),
        },
    }
    package["trace_graph"] = _build_search_evidence_trace_graph(package)
    package["package_sha256"] = payload_sha256(package)
    return package


def _search_evidence_export_values(package: dict[str, Any]) -> dict[str, list[str]]:
    source_evidence = list(package.get("source_evidence") or [])
    retrieval_spans = [
        span
        for item in source_evidence
        for span in item.get("retrieval_evidence_spans", [])
    ]
    late_interaction_vectors = [
        vector
        for span in retrieval_spans
        for vector in span.get("late_interaction_multivectors", [])
    ]
    operator_runs = list(package.get("operator_runs") or [])
    return {
        "source_snapshot_sha256s": _string_values(
            [
                *(item.get("source_snapshot_sha256") for item in source_evidence),
                *(span.get("source_snapshot_sha256") for span in retrieval_spans),
                *(
                    vector.get("span_vector_snapshot_sha256")
                    for vector in late_interaction_vectors
                ),
            ]
        ),
        "operator_run_ids": _string_values(
            run.get("operator_run_id") for run in operator_runs
        ),
        "document_ids": _string_values(
            (item.get("document") or {}).get("id") for item in source_evidence
        ),
        "run_ids": _string_values(
            (item.get("run") or {}).get("id") for item in source_evidence
        ),
    }


def persist_search_evidence_package_export(
    session: Session,
    *,
    search_request_id: UUID,
    agent_task_id: UUID | None = None,
    agent_task_artifact_id: UUID | None = None,
) -> EvidencePackageExport:
    package = get_search_evidence_package(session, search_request_id)
    export_values = _search_evidence_export_values(package)
    trace_graph = package.get("trace_graph") or {}
    now = utcnow()
    export = EvidencePackageExport(
        id=uuid.uuid4(),
        package_kind="search_request",
        search_request_id=search_request_id,
        agent_task_id=agent_task_id,
        agent_task_artifact_id=agent_task_artifact_id,
        package_sha256=str(package["package_sha256"]),
        trace_sha256=trace_graph.get("trace_sha256"),
        package_payload_json=_json_payload(package),
        source_snapshot_sha256s_json=export_values["source_snapshot_sha256s"],
        operator_run_ids_json=export_values["operator_run_ids"],
        document_ids_json=export_values["document_ids"],
        run_ids_json=export_values["run_ids"],
        claim_ids_json=[],
        export_status="completed",
        created_at=now,
    )
    session.add(export)
    session.flush()
    _persist_search_evidence_package_trace_graph(
        session,
        export_row=export,
        package_payload=package,
    )
    return export


def export_search_evidence_package(
    session: Session,
    *,
    search_request_id: UUID,
) -> dict[str, Any]:
    export = persist_search_evidence_package_export(
        session,
        search_request_id=search_request_id,
    )
    nodes, edges = _search_evidence_trace_rows(session, export.id)
    return _search_evidence_package_export_response(session, export, nodes, edges)


def get_search_evidence_package_export_trace(
    session: Session,
    evidence_package_export_id: UUID,
) -> dict[str, Any]:
    export = session.get(EvidencePackageExport, evidence_package_export_id)
    if export is None or export.package_kind != "search_request":
        raise ValueError(
            f"Search evidence package export '{evidence_package_export_id}' was not found."
        )
    _ensure_search_evidence_package_trace_graph(session, export)
    nodes, edges = _search_evidence_trace_rows(session, export.id)
    return _search_evidence_package_trace_response(session, export, nodes, edges)


_ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES = {
    "matched_source_record",
    "matched_page_span",
}


def _source_record_key(source_type: Any, source_id: Any) -> str | None:
    if source_type is None or source_id is None or source_id == "":
        return None
    source_type_value = str(source_type).strip().lower()
    if source_type_value not in {"chunk", "table"}:
        return None
    return f"source:{source_type_value}:{source_id}"


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _source_page_span(
    *,
    document_id: Any,
    run_id: Any,
    page_from: Any,
    page_to: Any,
) -> dict[str, Any] | None:
    page_from_value = _int_or_none(page_from)
    if page_from_value is None or document_id is None or run_id is None:
        return None
    page_to_value = _int_or_none(page_to) or page_from_value
    return {
        "document_id": str(document_id),
        "run_id": str(run_id),
        "page_from": page_from_value,
        "page_to": page_to_value,
        "key": f"page:{document_id}:{run_id}:{page_from_value}:{page_to_value}",
    }


def _page_spans_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("document_id") != right.get("document_id"):
        return False
    if left.get("run_id") != right.get("run_id"):
        return False
    return int(left["page_from"]) <= int(right["page_to"]) and int(right["page_from"]) <= int(
        left["page_to"]
    )


def _card_source_record_keys(card: dict[str, Any]) -> list[str]:
    metadata = card.get("metadata") or {}
    source_type = str(card.get("source_type") or "").strip().lower()
    source_record_keys = [
        _source_record_key("chunk", card.get("chunk_id") or metadata.get("chunk_id")),
        _source_record_key("table", card.get("table_id") or metadata.get("table_id")),
    ]
    if source_type in {"chunk", "table"}:
        source_record_keys.append(
            _source_record_key(
                source_type,
                card.get("source_locator") or metadata.get("source_locator"),
            )
        )
    return _string_values(source_record_keys)


def _card_page_span(card: dict[str, Any]) -> dict[str, Any] | None:
    return _source_page_span(
        document_id=card.get("document_id"),
        run_id=card.get("run_id"),
        page_from=card.get("page_from"),
        page_to=card.get("page_to"),
    )


def _search_export_source_coverage(export: EvidencePackageExport) -> dict[str, Any]:
    source_record_keys: list[str] = []
    source_page_spans: list[dict[str, Any]] = []
    package = export.package_payload_json or {}
    for source_item in package.get("source_evidence") or []:
        document = source_item.get("document") or {}
        run = source_item.get("run") or {}
        source_record_keys.append(
            _source_record_key(source_item.get("result_type"), source_item.get("source_id"))
        )
        for source_type, payload_key in (("chunk", "chunk"), ("table", "table")):
            source_payload = source_item.get(payload_key) or {}
            source_record_keys.append(
                _source_record_key(source_type, source_payload.get("id"))
            )
            source_page_spans.append(
                _source_page_span(
                    document_id=source_payload.get("document_id") or document.get("id"),
                    run_id=source_payload.get("run_id") or run.get("id"),
                    page_from=source_payload.get("page_from"),
                    page_to=source_payload.get("page_to"),
                )
            )
        for span in source_item.get("retrieval_evidence_spans") or []:
            source_record_keys.append(
                _source_record_key(span.get("source_type"), span.get("source_id"))
            )
            source_page_spans.append(
                _source_page_span(
                    document_id=document.get("id"),
                    run_id=run.get("id"),
                    page_from=span.get("page_from"),
                    page_to=span.get("page_to"),
                )
            )
    return {
        "source_record_keys": set(_string_values(source_record_keys)),
        "source_page_spans": [
            span
            for span in {
                span["key"]: span
                for span in source_page_spans
                if span and span.get("key")
            }.values()
        ],
        "source_result_count": len(package.get("source_evidence") or []),
    }


def _recomputed_card_source_coverage(
    card: dict[str, Any],
    exports_by_id: dict[UUID, EvidencePackageExport],
) -> dict[str, Any]:
    expected_record_keys = set(_card_source_record_keys(card))
    expected_page_span = _card_page_span(card)
    linked_export_ids = _uuid_values(card.get("source_evidence_package_export_ids") or [])
    matched_record_keys: set[str] = set()
    matched_page_span_keys: set[str] = set()
    matching_export_ids: set[str] = set()
    linked_export_count = 0
    for export_id in linked_export_ids:
        export = exports_by_id.get(export_id)
        if export is None or export.package_kind != "search_request":
            continue
        linked_export_count += 1
        coverage = _search_export_source_coverage(export)
        record_overlap = expected_record_keys & coverage["source_record_keys"]
        if record_overlap:
            matched_record_keys.update(record_overlap)
            matching_export_ids.add(str(export.id))
        if expected_page_span is not None:
            overlapping_spans = [
                span
                for span in coverage["source_page_spans"]
                if _page_spans_overlap(expected_page_span, span)
            ]
            if overlapping_spans:
                matched_page_span_keys.update(span["key"] for span in overlapping_spans)
                matching_export_ids.add(str(export.id))

    if expected_record_keys and matched_record_keys == expected_record_keys:
        recomputed_status = "matched_source_record"
    elif expected_page_span is not None and matched_page_span_keys:
        recomputed_status = "matched_page_span"
    else:
        recomputed_status = "missing"
    return {
        "evidence_card_id": str(card.get("evidence_card_id")),
        "reported_match_status": card.get("source_evidence_match_status"),
        "recomputed_match_status": recomputed_status,
        "expected_source_record_keys": sorted(expected_record_keys),
        "matched_source_record_keys": sorted(matched_record_keys),
        "expected_page_span": expected_page_span,
        "matched_page_span_keys": sorted(matched_page_span_keys),
        "linked_source_evidence_package_export_ids": [
            str(export_id) for export_id in linked_export_ids
        ],
        "matching_source_evidence_package_export_ids": sorted(matching_export_ids),
        "linked_search_export_count": linked_export_count,
        "complete": recomputed_status in _ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES,
    }


def _report_card_requires_source_match(card: dict[str, Any]) -> bool:
    source_type = str(card.get("source_type") or "").strip().lower()
    evidence_kind = str(card.get("evidence_kind") or "").strip().lower()
    return (
        source_type in {"chunk", "table", "figure"}
        or evidence_kind in {"source_evidence", "semantic_fact"}
        or bool(card.get("evidence_ids"))
    )


def technical_report_search_evidence_closure_payload(
    session: Session,
    draft_payload: dict[str, Any],
) -> dict[str, Any]:
    claims = list(draft_payload.get("claims") or [])
    evidence_cards = list(draft_payload.get("evidence_cards") or [])
    package_exports = list(draft_payload.get("source_evidence_package_exports") or [])
    expected_export_ids = _uuid_values(
        [
            *(row.get("evidence_package_export_id") for row in package_exports),
            *(
                value
                for card in evidence_cards
                for value in (card.get("source_evidence_package_export_ids") or [])
            ),
            *(
                value
                for claim in claims
                for value in (claim.get("source_evidence_package_export_ids") or [])
            ),
        ]
    )
    exports_by_id = _select_by_ids(session, EvidencePackageExport, set(expected_export_ids))
    missing_export_ids = [
        str(export_id) for export_id in expected_export_ids if export_id not in exports_by_id
    ]
    non_search_export_ids: list[str] = []
    trace_summaries: list[dict[str, Any]] = []
    incomplete_trace_export_ids: list[str] = []
    for export_id in expected_export_ids:
        export = exports_by_id.get(export_id)
        if export is None:
            continue
        if export.package_kind != "search_request":
            non_search_export_ids.append(str(export.id))
            continue
        _ensure_search_evidence_package_trace_graph(session, export)
        nodes, edges = _search_evidence_trace_rows(session, export.id)
        integrity = _search_evidence_trace_integrity_payload(session, export, nodes, edges)
        if not integrity["complete"]:
            incomplete_trace_export_ids.append(str(export.id))
        trace_summaries.append(
            {
                "evidence_package_export_id": str(export.id),
                "search_request_id": str(export.search_request_id)
                if export.search_request_id
                else None,
                "package_sha256": export.package_sha256,
                "trace_sha256": export.trace_sha256,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "trace_integrity": integrity,
            }
        )

    claims_missing_source_exports = sorted(
        str(claim.get("claim_id"))
        for claim in claims
        if not claim.get("source_evidence_package_export_ids")
    )
    cited_card_ids = {
        str(card_id)
        for claim in claims
        for card_id in (claim.get("evidence_card_ids") or [])
    }
    cited_source_cards = [
        card
        for card in evidence_cards
        if str(card.get("evidence_card_id")) in cited_card_ids
        and _report_card_requires_source_match(card)
    ]
    card_source_coverages = [
        _recomputed_card_source_coverage(card, exports_by_id) for card in cited_source_cards
    ]
    cited_cards_missing_source_exports = sorted(
        str(card.get("evidence_card_id"))
        for card in cited_source_cards
        if not card.get("source_evidence_package_export_ids")
    )
    cited_cards_without_acceptable_source_match = sorted(
        str(card.get("evidence_card_id"))
        for card in cited_source_cards
        if card.get("source_evidence_match_status")
        not in _ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES
    )
    cited_cards_without_source_record_match = sorted(
        str(card.get("evidence_card_id"))
        for card in cited_source_cards
        if card.get("source_evidence_match_status") != "matched_source_record"
    )
    cited_cards_with_document_run_fallback = sorted(
        str(card.get("evidence_card_id"))
        for card in cited_source_cards
        if card.get("source_evidence_match_status") == "matched_document_run_fallback"
    )
    cited_cards_without_recomputed_source_coverage = sorted(
        row["evidence_card_id"]
        for row in card_source_coverages
        if row["recomputed_match_status"] not in _ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES
    )
    cited_cards_with_expected_record_without_recomputed_record_match = sorted(
        row["evidence_card_id"]
        for row in card_source_coverages
        if row["expected_source_record_keys"]
        and row["recomputed_match_status"] != "matched_source_record"
    )
    reported_recomputed_match_mismatches = sorted(
        row["evidence_card_id"]
        for row in card_source_coverages
        if row["reported_match_status"] != row["recomputed_match_status"]
    )
    source_evidence_match_status_counts: dict[str, int] = {}
    for card in cited_source_cards:
        status = str(card.get("source_evidence_match_status") or "missing")
        source_evidence_match_status_counts[status] = (
            source_evidence_match_status_counts.get(status, 0) + 1
        )
    recomputed_source_evidence_match_status_counts: dict[str, int] = {}
    for coverage in card_source_coverages:
        status = str(coverage["recomputed_match_status"] or "missing")
        recomputed_source_evidence_match_status_counts[status] = (
            recomputed_source_evidence_match_status_counts.get(status, 0) + 1
        )
    expected_source_record_keys = {
        key
        for coverage in card_source_coverages
        for key in coverage["expected_source_record_keys"]
    }
    matched_source_record_keys = {
        key
        for coverage in card_source_coverages
        for key in coverage["matched_source_record_keys"]
    }
    source_record_recall = (
        round(len(matched_source_record_keys) / len(expected_source_record_keys), 4)
        if expected_source_record_keys
        else 1.0
    )
    complete = (
        bool(claims)
        and bool(expected_export_ids)
        and not missing_export_ids
        and not non_search_export_ids
        and not incomplete_trace_export_ids
        and not claims_missing_source_exports
        and not cited_cards_missing_source_exports
        and not cited_cards_without_acceptable_source_match
        and not cited_cards_without_recomputed_source_coverage
        and not cited_cards_with_expected_record_without_recomputed_record_match
        and not reported_recomputed_match_mismatches
    )
    return {
        "schema_name": "technical_report_search_evidence_closure",
        "schema_version": "1.0",
        "complete": complete,
        "claim_count": len(claims),
        "cited_source_card_count": len(cited_source_cards),
        "card_source_coverage": card_source_coverages,
        "expected_source_evidence_package_export_count": len(expected_export_ids),
        "persisted_source_evidence_package_export_count": len(trace_summaries),
        "trace_complete_count": sum(
            1 for row in trace_summaries if row["trace_integrity"]["complete"]
        ),
        "expected_source_record_key_count": len(expected_source_record_keys),
        "matched_source_record_key_count": len(matched_source_record_keys),
        "source_record_recall": source_record_recall,
        "missing_source_evidence_package_export_count": len(missing_export_ids),
        "non_search_source_evidence_package_export_count": len(non_search_export_ids),
        "incomplete_trace_count": len(incomplete_trace_export_ids),
        "claims_missing_source_evidence_package_export_count": len(
            claims_missing_source_exports
        ),
        "cited_cards_missing_source_evidence_package_export_count": len(
            cited_cards_missing_source_exports
        ),
        "cited_cards_without_acceptable_source_evidence_match_count": len(
            cited_cards_without_acceptable_source_match
        ),
        "cited_cards_without_source_record_match_count": len(
            cited_cards_without_source_record_match
        ),
        "cited_cards_with_document_run_fallback_match_count": len(
            cited_cards_with_document_run_fallback
        ),
        "cited_cards_without_recomputed_source_coverage_count": len(
            cited_cards_without_recomputed_source_coverage
        ),
        "cited_cards_with_expected_record_without_recomputed_record_match_count": len(
            cited_cards_with_expected_record_without_recomputed_record_match
        ),
        "reported_recomputed_match_mismatch_count": len(
            reported_recomputed_match_mismatches
        ),
        "source_evidence_match_status_counts": source_evidence_match_status_counts,
        "recomputed_source_evidence_match_status_counts": (
            recomputed_source_evidence_match_status_counts
        ),
        "expected_source_evidence_package_export_ids": [
            str(export_id) for export_id in expected_export_ids
        ],
        "missing_source_evidence_package_export_ids": missing_export_ids,
        "non_search_source_evidence_package_export_ids": non_search_export_ids,
        "incomplete_trace_export_ids": sorted(incomplete_trace_export_ids),
        "claims_missing_source_evidence_package_export_ids": claims_missing_source_exports,
        "cited_cards_missing_source_evidence_package_export_ids": (
            cited_cards_missing_source_exports
        ),
        "cited_cards_without_acceptable_source_evidence_match_ids": (
            cited_cards_without_acceptable_source_match
        ),
        "cited_cards_without_source_record_match_ids": cited_cards_without_source_record_match,
        "cited_cards_with_document_run_fallback_match_ids": (
            cited_cards_with_document_run_fallback
        ),
        "cited_cards_without_recomputed_source_coverage_ids": (
            cited_cards_without_recomputed_source_coverage
        ),
        "cited_cards_with_expected_record_without_recomputed_record_match_ids": (
            cited_cards_with_expected_record_without_recomputed_record_match
        ),
        "reported_recomputed_match_mismatch_ids": reported_recomputed_match_mismatches,
        "trace_summaries": trace_summaries,
    }


_DERIVATION_MUTABLE_FIELDS = {
    "derivation_rule",
    "evidence_package_export_id",
    "evidence_package_sha256",
    "derivation_sha256",
    "source_snapshot_sha256s",
}


def _string_values(values: Iterable[Any]) -> list[str]:
    return [str(value) for value in dict.fromkeys(values) if value is not None and value != ""]


def _clean_mapping(value: dict[str, Any], *, drop_fields: set[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in drop_fields}


def _evidence_card_snapshot(card: dict[str, Any]) -> dict[str, Any]:
    clean_card = _clean_mapping(
        card,
        drop_fields={
            "evidence_package_export_id",
            "evidence_package_sha256",
            "source_snapshot_sha256s",
        },
    )
    return {
        **clean_card,
        "evidence_card_sha256": payload_sha256(clean_card),
    }


def build_technical_report_derivation_package(draft_payload: dict[str, Any]) -> dict[str, Any]:
    evidence_cards = [
        _evidence_card_snapshot(dict(card)) for card in draft_payload.get("evidence_cards", [])
    ]
    cards_by_id = {
        str(card.get("evidence_card_id")): card
        for card in evidence_cards
        if card.get("evidence_card_id")
    }
    graph_context = list(draft_payload.get("graph_context") or [])
    document_refs = list(draft_payload.get("document_refs") or [])
    package_claims: list[dict[str, Any]] = []

    for raw_claim in draft_payload.get("claims", []):
        claim = _clean_mapping(dict(raw_claim), drop_fields=_DERIVATION_MUTABLE_FIELDS)
        evidence_card_ids = _string_values(claim.get("evidence_card_ids") or [])
        graph_edge_ids = _string_values(claim.get("graph_edge_ids") or [])
        source_snapshot_sha256s = _string_values(
            cards_by_id[card_id].get("evidence_card_sha256")
            for card_id in evidence_card_ids
            if card_id in cards_by_id
        )
        if not source_snapshot_sha256s and graph_edge_ids:
            source_snapshot_sha256s = _string_values(
                [
                    payload_sha256(
                        {
                            "graph_edge_ids": graph_edge_ids,
                            "claim_id": claim.get("claim_id"),
                        }
                    )
                ]
            )
        package_claims.append(
            {
                "claim_id": claim.get("claim_id"),
                "section_id": claim.get("section_id"),
                "rendered_text": claim.get("rendered_text"),
                "concept_keys": _string_values(claim.get("concept_keys") or []),
                "evidence_card_ids": evidence_card_ids,
                "graph_edge_ids": graph_edge_ids,
                "fact_ids": _string_values(claim.get("fact_ids") or []),
                "assertion_ids": _string_values(claim.get("assertion_ids") or []),
                "source_document_ids": _string_values(claim.get("source_document_ids") or []),
                "source_snapshot_sha256s": source_snapshot_sha256s,
                "derivation_rule": "technical_report_claim_contract_v1",
            }
        )

    package_core = {
        "schema_name": "technical_report_claim_derivation_package",
        "schema_version": "1.0",
        "title": draft_payload.get("title"),
        "harness_task_id": str(draft_payload.get("harness_task_id") or ""),
        "generator_mode": draft_payload.get("generator_mode"),
        "generator_model": draft_payload.get("generator_model"),
        "document_refs": document_refs,
        "evidence_cards": evidence_cards,
        "graph_context": graph_context,
        "claims": package_claims,
    }
    package_sha256 = payload_sha256(package_core)
    claim_derivations: list[dict[str, Any]] = []
    for claim in package_claims:
        derivation_seed = {
            **claim,
            "evidence_package_sha256": package_sha256,
        }
        claim_derivations.append(
            {
                **claim,
                "evidence_package_sha256": package_sha256,
                "derivation_sha256": payload_sha256(derivation_seed),
            }
        )
    return {
        **package_core,
        "package_sha256": package_sha256,
        "claim_derivations": claim_derivations,
        "source_snapshot_sha256s": _string_values(
            value
            for claim in claim_derivations
            for value in claim.get("source_snapshot_sha256s", [])
        ),
        "document_ids": _string_values(
            [
                *[row.get("document_id") for row in document_refs if isinstance(row, dict)],
                *[
                    row.get("document_id")
                    for row in evidence_cards
                    if isinstance(row, dict) and row.get("document_id")
                ],
            ]
        ),
        "run_ids": _string_values(
            row.get("run_id")
            for row in evidence_cards
            if isinstance(row, dict) and row.get("run_id")
        ),
        "claim_ids": _string_values(claim.get("claim_id") for claim in claim_derivations),
    }


def apply_technical_report_derivation_links(
    draft_payload: dict[str, Any],
    *,
    evidence_package_export_id: UUID | None = None,
) -> dict[str, Any]:
    package = build_technical_report_derivation_package(draft_payload)
    package_sha256 = package["package_sha256"]
    source_snapshot_sha256s = list(package["source_snapshot_sha256s"])
    derivations_by_claim_id = {
        str(row["claim_id"]): row for row in package["claim_derivations"] if row.get("claim_id")
    }
    for card in draft_payload.get("evidence_cards", []):
        if evidence_package_export_id is not None:
            card["evidence_package_export_id"] = str(evidence_package_export_id)
        card["evidence_package_sha256"] = package_sha256
        snapshot = _evidence_card_snapshot(dict(card))
        card["source_snapshot_sha256s"] = _string_values([snapshot.get("evidence_card_sha256")])
    for claim in draft_payload.get("claims", []):
        derivation = derivations_by_claim_id.get(str(claim.get("claim_id")))
        if not derivation:
            continue
        claim["derivation_rule"] = derivation["derivation_rule"]
        if evidence_package_export_id is not None:
            claim["evidence_package_export_id"] = str(evidence_package_export_id)
        claim["evidence_package_sha256"] = package_sha256
        claim["derivation_sha256"] = derivation["derivation_sha256"]
        claim["source_snapshot_sha256s"] = list(derivation["source_snapshot_sha256s"])
    if evidence_package_export_id is not None:
        draft_payload["evidence_package_export_id"] = str(evidence_package_export_id)
    draft_payload["evidence_package_sha256"] = package_sha256
    draft_payload["source_snapshot_sha256s"] = source_snapshot_sha256s
    draft_payload["claim_derivations"] = package["claim_derivations"]
    return package


def persist_technical_report_evidence_export(
    session: Session,
    *,
    draft_payload: dict[str, Any],
    agent_task_id: UUID,
    agent_task_artifact_id: UUID | None = None,
) -> EvidencePackageExport:
    package = apply_technical_report_derivation_links(draft_payload)
    now = utcnow()
    export = EvidencePackageExport(
        id=uuid.uuid4(),
        package_kind="technical_report_claims",
        agent_task_id=agent_task_id,
        agent_task_artifact_id=agent_task_artifact_id,
        package_sha256=package["package_sha256"],
        package_payload_json=_json_payload(package),
        source_snapshot_sha256s_json=list(package["source_snapshot_sha256s"]),
        operator_run_ids_json=[],
        document_ids_json=list(package["document_ids"]),
        run_ids_json=list(package["run_ids"]),
        claim_ids_json=list(package["claim_ids"]),
        export_status="completed",
        created_at=now,
    )
    session.add(export)
    session.flush()
    apply_technical_report_derivation_links(
        draft_payload,
        evidence_package_export_id=export.id,
    )
    for derivation in package["claim_derivations"]:
        session.add(
            ClaimEvidenceDerivation(
                id=uuid.uuid4(),
                evidence_package_export_id=export.id,
                agent_task_id=agent_task_id,
                claim_id=str(derivation["claim_id"]),
                claim_text=derivation.get("rendered_text"),
                derivation_rule=str(derivation["derivation_rule"]),
                evidence_card_ids_json=list(derivation["evidence_card_ids"]),
                graph_edge_ids_json=list(derivation["graph_edge_ids"]),
                fact_ids_json=list(derivation["fact_ids"]),
                assertion_ids_json=list(derivation["assertion_ids"]),
                source_document_ids_json=list(derivation["source_document_ids"]),
                source_snapshot_sha256s_json=list(derivation["source_snapshot_sha256s"]),
                evidence_package_sha256=str(derivation["evidence_package_sha256"]),
                derivation_sha256=str(derivation["derivation_sha256"]),
                created_at=now,
            )
        )
    session.flush()
    return export


def attach_artifact_to_evidence_export(
    session: Session,
    *,
    evidence_package_export_id: UUID,
    agent_task_artifact_id: UUID,
) -> None:
    export = session.get(EvidencePackageExport, evidence_package_export_id)
    if export is None:
        return
    export.agent_task_artifact_id = agent_task_artifact_id
    session.flush()


def attach_operator_run_to_evidence_export(
    session: Session,
    *,
    evidence_package_export_id: UUID,
    operator_run_id: UUID,
) -> None:
    export = session.get(EvidencePackageExport, evidence_package_export_id)
    if export is None:
        return
    export.operator_run_ids_json = _string_values(
        [*(export.operator_run_ids_json or []), operator_run_id]
    )
    session.flush()


def _evidence_export_payload(row: EvidencePackageExport) -> dict:
    return {
        "evidence_package_export_id": row.id,
        "package_kind": row.package_kind,
        "search_request_id": row.search_request_id,
        "agent_task_id": row.agent_task_id,
        "agent_task_artifact_id": row.agent_task_artifact_id,
        "package_sha256": row.package_sha256,
        "trace_sha256": row.trace_sha256,
        "source_snapshot_sha256s": row.source_snapshot_sha256s_json or [],
        "operator_run_ids": row.operator_run_ids_json or [],
        "document_ids": row.document_ids_json or [],
        "run_ids": row.run_ids_json or [],
        "claim_ids": row.claim_ids_json or [],
        "export_status": row.export_status,
        "created_at": row.created_at,
    }


def _claim_derivation_payload(row: ClaimEvidenceDerivation) -> dict:
    return {
        "claim_evidence_derivation_id": row.id,
        "evidence_package_export_id": row.evidence_package_export_id,
        "agent_task_id": row.agent_task_id,
        "claim_id": row.claim_id,
        "claim_text": row.claim_text,
        "derivation_rule": row.derivation_rule,
        "evidence_card_ids": row.evidence_card_ids_json or [],
        "graph_edge_ids": row.graph_edge_ids_json or [],
        "fact_ids": row.fact_ids_json or [],
        "assertion_ids": row.assertion_ids_json or [],
        "source_document_ids": row.source_document_ids_json or [],
        "source_snapshot_sha256s": row.source_snapshot_sha256s_json or [],
        "evidence_package_sha256": row.evidence_package_sha256,
        "derivation_sha256": row.derivation_sha256,
        "created_at": row.created_at,
    }


def _task_payload(row: AgentTask | None) -> dict | None:
    if row is None:
        return None
    return {
        "task_id": row.id,
        "task_type": row.task_type,
        "status": row.status,
        "workflow_version": row.workflow_version,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "completed_at": row.completed_at,
    }


def _artifact_payload(row: AgentTaskArtifact) -> dict:
    return {
        "artifact_id": row.id,
        "task_id": row.task_id,
        "artifact_kind": row.artifact_kind,
        "storage_path": row.storage_path,
        "created_at": row.created_at,
    }


def _provenance_export_receipt_payload(row: AgentTaskArtifact) -> dict:
    payload = _json_payload(row.payload_json or {})
    frozen_export = payload.get("frozen_export") or {}
    receipt = _frozen_export_receipt(payload)
    return {
        "artifact_id": row.id,
        "task_id": row.task_id,
        "artifact_kind": row.artifact_kind,
        "storage_path": row.storage_path,
        "export_payload_sha256": frozen_export.get("export_payload_sha256"),
        "prov_hash_basis_sha256": frozen_export.get("prov_hash_basis_sha256"),
        "export_receipt": receipt,
        "receipt_integrity": _prov_export_receipt_integrity(payload),
    }


def _immutability_event_payload(row: AgentTaskArtifactImmutabilityEvent) -> dict:
    return {
        "event_id": row.id,
        "artifact_id": row.artifact_id,
        "task_id": row.task_id,
        "event_kind": row.event_kind,
        "mutation_operation": row.mutation_operation,
        "frozen_artifact_kind": row.frozen_artifact_kind,
        "attempted_artifact_kind": row.attempted_artifact_kind,
        "frozen_storage_path": row.frozen_storage_path,
        "attempted_storage_path": row.attempted_storage_path,
        "frozen_payload_sha256": row.frozen_payload_sha256,
        "attempted_payload_sha256": row.attempted_payload_sha256,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _verification_payload(row: AgentTaskVerification | None) -> dict | None:
    if row is None:
        return None
    return {
        "verification_id": row.id,
        "target_task_id": row.target_task_id,
        "verification_task_id": row.verification_task_id,
        "verifier_type": row.verifier_type,
        "outcome": row.outcome,
        "metrics": row.metrics_json or {},
        "reasons": row.reasons_json or [],
        "details": row.details_json or {},
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


def _operator_run_summary(row: KnowledgeOperatorRun) -> dict:
    return {
        "operator_run_id": row.id,
        "parent_operator_run_id": row.parent_operator_run_id,
        "operator_kind": row.operator_kind,
        "operator_name": row.operator_name,
        "operator_version": row.operator_version,
        "status": row.status,
        "agent_task_id": row.agent_task_id,
        "search_request_id": row.search_request_id,
        "config_sha256": row.config_sha256,
        "input_sha256": row.input_sha256,
        "output_sha256": row.output_sha256,
        "metrics": row.metrics_json or {},
        "created_at": row.created_at,
    }


def _semantic_assertion_payload(row: SemanticAssertion) -> dict:
    return {
        "assertion_id": row.id,
        "semantic_pass_id": row.semantic_pass_id,
        "concept_id": row.concept_id,
        "assertion_kind": row.assertion_kind,
        "epistemic_status": row.epistemic_status,
        "context_scope": row.context_scope,
        "review_status": row.review_status,
        "matched_terms": row.matched_terms_json or [],
        "source_types": row.source_types_json or [],
        "evidence_count": row.evidence_count,
        "confidence": row.confidence,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_assertion_evidence_payload(row: SemanticAssertionEvidence) -> dict:
    return {
        "evidence_id": row.id,
        "assertion_id": row.assertion_id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "source_type": row.source_type,
        "source_locator": row.source_locator,
        "chunk_id": row.chunk_id,
        "table_id": row.table_id,
        "figure_id": row.figure_id,
        "page_from": row.page_from,
        "page_to": row.page_to,
        "matched_terms": row.matched_terms_json or [],
        "excerpt": row.excerpt,
        "source_label": row.source_label,
        "source_artifact_path": row.source_artifact_path,
        "source_artifact_sha256": row.source_artifact_sha256,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_fact_payload(row: SemanticFact) -> dict:
    return {
        "fact_id": row.id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "semantic_pass_id": row.semantic_pass_id,
        "ontology_snapshot_id": row.ontology_snapshot_id,
        "subject_entity_id": row.subject_entity_id,
        "relation_key": row.relation_key,
        "relation_label": row.relation_label,
        "object_entity_id": row.object_entity_id,
        "object_value_text": row.object_value_text,
        "source_assertion_id": row.source_assertion_id,
        "review_status": row.review_status,
        "confidence": row.confidence,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_fact_evidence_payload(row: SemanticFactEvidence) -> dict:
    return {
        "fact_evidence_id": row.id,
        "fact_id": row.fact_id,
        "assertion_id": row.assertion_id,
        "assertion_evidence_id": row.assertion_evidence_id,
        "created_at": row.created_at,
    }


def _export_document_run_map(export: EvidencePackageExport) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    payload = export.package_payload_json or {}
    for card in payload.get("evidence_cards") or []:
        document_id = card.get("document_id")
        run_id = card.get("run_id")
        if document_id and run_id:
            mapping.setdefault(str(document_id), set()).add(str(run_id))
    if not mapping:
        run_ids = {str(value) for value in export.run_ids_json or []}
        for document_id in export.document_ids_json or []:
            mapping[str(document_id)] = set(run_ids)
    return mapping


def _change_impact_payload(
    session: Session,
    exports: list[EvidencePackageExport],
) -> dict:
    impacts: list[dict[str, Any]] = []
    if not exports:
        return {
            "impacted": True,
            "impact_count": 1,
            "impacts": [
                {
                    "impact_type": "missing_evidence_export",
                    "reason": "No frozen evidence package export is linked to the report draft.",
                }
            ],
        }
    document_ids = {
        UUID(str(document_id))
        for export in exports
        for document_id in (export.document_ids_json or [])
    }
    documents_by_id = _select_by_ids(session, Document, document_ids)
    for export in exports:
        for document_id, exported_run_ids in _export_document_run_map(export).items():
            document = documents_by_id.get(UUID(document_id))
            if document is None:
                impacts.append(
                    {
                        "impact_type": "source_document_missing",
                        "evidence_package_export_id": str(export.id),
                        "document_id": document_id,
                    }
                )
                continue
            active_run_id = str(document.active_run_id) if document.active_run_id else None
            latest_run_id = str(document.latest_run_id) if document.latest_run_id else None
            if active_run_id not in exported_run_ids:
                impacts.append(
                    {
                        "impact_type": "active_run_changed",
                        "evidence_package_export_id": str(export.id),
                        "document_id": document_id,
                        "exported_run_ids": sorted(exported_run_ids),
                        "current_active_run_id": active_run_id,
                    }
                )
            if latest_run_id and latest_run_id not in exported_run_ids:
                impacts.append(
                    {
                        "impact_type": "newer_run_available",
                        "evidence_package_export_id": str(export.id),
                        "document_id": document_id,
                        "exported_run_ids": sorted(exported_run_ids),
                        "current_latest_run_id": latest_run_id,
                    }
                )
    return {
        "impacted": bool(impacts),
        "impact_count": len(impacts),
        "impacts": impacts,
    }


def _technical_report_integrity_payload(
    draft_payload: dict[str, Any],
    exports: list[EvidencePackageExport],
    derivations: list[ClaimEvidenceDerivation],
) -> dict:
    from app.schemas.agent_tasks import TechnicalReportDraftPayload

    canonical_draft_payload = (
        TechnicalReportDraftPayload.model_validate(draft_payload).model_dump(mode="json")
        if draft_payload
        else {}
    )
    recomputed_package = build_technical_report_derivation_package(canonical_draft_payload)
    expected_package_sha256 = str(recomputed_package.get("package_sha256") or "")
    expected_derivations_by_claim_id = {
        str(row.get("claim_id")): row
        for row in recomputed_package.get("claim_derivations", [])
        if row.get("claim_id")
    }
    draft_package_sha256 = draft_payload.get("evidence_package_sha256")
    draft_package_hash_matches = bool(draft_package_sha256) and (
        draft_package_sha256 == expected_package_sha256
    )
    export_package_hash_mismatch_count = sum(
        1 for row in exports if row.package_sha256 != expected_package_sha256
    )
    export_package_hash_matches = bool(exports) and export_package_hash_mismatch_count == 0
    stored_claim_ids = {row.claim_id for row in derivations}
    missing_claim_derivation_ids = sorted(
        claim_id
        for claim_id in expected_derivations_by_claim_id
        if claim_id not in stored_claim_ids
    )
    mismatched_claim_ids: list[str] = []
    package_mismatched_claim_ids: list[str] = []
    for row in derivations:
        expected_derivation = expected_derivations_by_claim_id.get(str(row.claim_id))
        expected_derivation_sha256 = (
            str(expected_derivation.get("derivation_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if row.derivation_sha256 != expected_derivation_sha256:
            mismatched_claim_ids.append(str(row.claim_id))
        if row.evidence_package_sha256 != expected_package_sha256:
            package_mismatched_claim_ids.append(str(row.claim_id))

    return {
        "expected_evidence_package_sha256": expected_package_sha256,
        "draft_evidence_package_sha256": draft_package_sha256,
        "draft_package_hash_matches": draft_package_hash_matches,
        "export_package_hash_matches": export_package_hash_matches,
        "export_package_hash_mismatch_count": export_package_hash_mismatch_count,
        "expected_claim_derivation_count": len(expected_derivations_by_claim_id),
        "stored_claim_derivation_count": len(derivations),
        "claim_derivation_count_matches": len(derivations) == len(expected_derivations_by_claim_id),
        "claim_derivation_hash_mismatch_count": len(mismatched_claim_ids),
        "claim_package_hash_mismatch_count": len(package_mismatched_claim_ids),
        "missing_claim_derivation_count": len(missing_claim_derivation_ids),
        "mismatched_claim_ids": sorted(mismatched_claim_ids),
        "package_mismatched_claim_ids": sorted(package_mismatched_claim_ids),
        "missing_claim_derivation_ids": missing_claim_derivation_ids,
    }


TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND = "technical_report_court_evidence"


def _passed_technical_report_verification(
    session: Session,
    verification_task_id: UUID,
) -> AgentTaskVerification | None:
    return session.scalar(
        select(AgentTaskVerification)
        .where(
            AgentTaskVerification.verification_task_id == verification_task_id,
            AgentTaskVerification.verifier_type == "technical_report_gate",
            AgentTaskVerification.outcome == "passed",
        )
        .order_by(AgentTaskVerification.created_at.desc())
    )


def _latest_passed_technical_report_verification_task_id(
    session: Session,
    draft_task_id: UUID,
) -> UUID | None:
    row = session.scalar(
        select(AgentTaskVerification)
        .where(
            AgentTaskVerification.target_task_id == draft_task_id,
            AgentTaskVerification.verifier_type == "technical_report_gate",
            AgentTaskVerification.outcome == "passed",
        )
        .order_by(AgentTaskVerification.created_at.desc())
    )
    return row.verification_task_id if row is not None else None


def _verification_task_id_for_manifest(session: Session, task: AgentTask) -> UUID:
    if task.task_type == "verify_technical_report":
        if _passed_technical_report_verification(session, task.id) is None:
            raise ValueError(
                "Evidence manifests require a passed technical report verification task."
            )
        return task.id
    if task.task_type == "draft_technical_report":
        verification_task_id = _latest_passed_technical_report_verification_task_id(
            session,
            task.id,
        )
        if verification_task_id is None:
            raise ValueError(
                "Evidence manifests require a passed technical report verification task."
            )
        return verification_task_id
    raise ValueError("Evidence manifests are supported for technical report tasks only.")


def _existing_evidence_manifest(
    session: Session,
    verification_task_id: UUID,
) -> EvidenceManifest | None:
    return session.scalar(
        select(EvidenceManifest)
        .where(
            EvidenceManifest.verification_task_id == verification_task_id,
            EvidenceManifest.manifest_kind == TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND,
        )
        .order_by(EvidenceManifest.created_at.desc())
    )


def _semantic_trace_payload(
    session: Session,
    *,
    assertion_ids: list[UUID],
    fact_ids: list[UUID],
    evidence_ids: list[UUID],
) -> dict[str, Any]:
    assertions_by_id = _select_by_ids(session, SemanticAssertion, assertion_ids)
    facts_by_id = _select_by_ids(session, SemanticFact, fact_ids)
    assertion_evidence_by_id: dict[UUID, SemanticAssertionEvidence] = {}
    if evidence_ids:
        assertion_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticAssertionEvidence)
                    .where(SemanticAssertionEvidence.id.in_(evidence_ids))
                    .order_by(SemanticAssertionEvidence.created_at, SemanticAssertionEvidence.id)
                )
            }
        )
    if assertion_ids:
        assertion_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticAssertionEvidence)
                    .where(SemanticAssertionEvidence.assertion_id.in_(assertion_ids))
                    .order_by(SemanticAssertionEvidence.created_at, SemanticAssertionEvidence.id)
                )
            }
        )

    fact_evidence_by_id: dict[UUID, SemanticFactEvidence] = {}
    if fact_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.fact_id.in_(fact_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )
    if assertion_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.assertion_id.in_(assertion_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )
    if evidence_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.assertion_evidence_id.in_(evidence_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )

    return {
        "assertions": [
            _semantic_assertion_payload(row)
            for row in sorted(assertions_by_id.values(), key=lambda item: str(item.id))
        ],
        "facts": [
            _semantic_fact_payload(row)
            for row in sorted(facts_by_id.values(), key=lambda item: str(item.id))
        ],
        "assertion_evidence": [
            _semantic_assertion_evidence_payload(row)
            for row in sorted(assertion_evidence_by_id.values(), key=lambda item: str(item.id))
        ],
        "fact_evidence": [
            _semantic_fact_evidence_payload(row)
            for row in sorted(fact_evidence_by_id.values(), key=lambda item: str(item.id))
        ],
    }


def _source_record_payloads_from_semantic_trace(
    session: Session,
    assertion_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chunk_ids = _uuid_values(row.get("chunk_id") for row in assertion_evidence)
    table_ids = _uuid_values(row.get("table_id") for row in assertion_evidence)
    figure_ids = _uuid_values(row.get("figure_id") for row in assertion_evidence)
    chunks_by_id = _select_by_ids(session, DocumentChunk, chunk_ids)
    tables_by_id = _select_by_ids(session, DocumentTable, table_ids)
    figures_by_id = _select_by_ids(session, DocumentFigure, figure_ids)
    segments_by_table_id: dict[UUID, list[DocumentTableSegment]] = {
        table_id: [] for table_id in tables_by_id
    }
    if table_ids:
        for segment in session.scalars(
            select(DocumentTableSegment)
            .where(DocumentTableSegment.table_id.in_(table_ids))
            .order_by(
                DocumentTableSegment.table_id.asc(),
                DocumentTableSegment.segment_order.asc(),
                DocumentTableSegment.segment_index.asc(),
            )
        ):
            segments_by_table_id.setdefault(segment.table_id, []).append(segment)

    records: list[dict[str, Any]] = []
    for evidence in assertion_evidence:
        chunk_id = _uuid_or_none(evidence.get("chunk_id"))
        table_id = _uuid_or_none(evidence.get("table_id"))
        figure_id = _uuid_or_none(evidence.get("figure_id"))
        table_payload = (
            _table_payload(
                tables_by_id.get(table_id),
                segments=segments_by_table_id.get(table_id, []),
            )
            if table_id is not None
            else None
        )
        records.append(
            {
                "record_kind": "semantic_assertion_source",
                "evidence_id": evidence.get("evidence_id"),
                "source_type": evidence.get("source_type"),
                "source_locator": evidence.get("source_locator"),
                "source_artifact_sha256": evidence.get("source_artifact_sha256"),
                "chunk": _chunk_payload(chunks_by_id.get(chunk_id)) if chunk_id else None,
                "table": table_payload,
                "figure": _figure_payload(figures_by_id.get(figure_id)) if figure_id else None,
            }
        )
    return records


def _report_evidence_card_source_records(evidence_cards: list[dict[str, Any]]) -> list[dict]:
    return [
        {
            "record_kind": "technical_report_evidence_card",
            "evidence_card_id": card.get("evidence_card_id"),
            "evidence_kind": card.get("evidence_kind"),
            "source_type": card.get("source_type"),
            "document_id": card.get("document_id"),
            "run_id": card.get("run_id"),
            "page_from": card.get("page_from"),
            "page_to": card.get("page_to"),
            "source_artifact_api_path": card.get("source_artifact_api_path"),
            "evidence_card_sha256": _evidence_card_snapshot(dict(card)).get("evidence_card_sha256"),
            "source_snapshot_sha256s": card.get("source_snapshot_sha256s") or [],
        }
        for card in evidence_cards
    ]


def _technical_report_provenance_edges(
    *,
    source_documents: list[dict],
    document_runs: list[dict],
    evidence_exports: list[dict],
    evidence_cards: list[dict],
    claims: list[dict],
    claim_derivations: list[dict],
    semantic_trace: dict[str, Any],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for export in evidence_exports:
        if export.get("package_kind") == "search_request" and export.get("search_request_id"):
            edges.append(
                {
                    "edge_type": "search_request_to_evidence_package_export",
                    "from": {"table": "search_requests", "id": export.get("search_request_id")},
                    "to": {
                        "table": "evidence_package_exports",
                        "id": export.get("evidence_package_export_id"),
                    },
                }
            )
    for run in document_runs:
        if run.get("document_id"):
            edges.append(
                {
                    "edge_type": "source_document_to_document_run",
                    "from": {"table": "documents", "id": run.get("document_id")},
                    "to": {"table": "document_runs", "id": run.get("id")},
                }
            )
    for evidence in semantic_trace["assertion_evidence"]:
        target_id = evidence.get(f"{evidence.get('source_type')}_id")
        if target_id:
            edges.append(
                {
                    "edge_type": "document_run_to_source_record",
                    "from": {"table": "document_runs", "id": evidence.get("run_id")},
                    "to": {
                        "table": f"document_{evidence.get('source_type')}s",
                        "id": target_id,
                    },
                }
            )
    for card in evidence_cards:
        for export_id in card.get("source_evidence_package_export_ids") or []:
            edges.append(
                {
                    "edge_type": "search_evidence_export_to_report_card",
                    "from": {"table": "evidence_package_exports", "id": export_id},
                    "to": {
                        "table": "technical_report_evidence_cards",
                        "id": card.get("evidence_card_id"),
                    },
                }
            )
        for evidence_id in card.get("evidence_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_evidence_to_report_card",
                    "from": {"table": "semantic_assertion_evidence", "id": evidence_id},
                    "to": {
                        "table": "technical_report_evidence_cards",
                        "id": card.get("evidence_card_id"),
                    },
                }
            )
    for claim in claims:
        for export_id in claim.get("source_evidence_package_export_ids") or []:
            edges.append(
                {
                    "edge_type": "search_evidence_export_to_claim",
                    "from": {"table": "evidence_package_exports", "id": export_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for card_id in claim.get("evidence_card_ids") or []:
            edges.append(
                {
                    "edge_type": "report_card_to_claim",
                    "from": {"table": "technical_report_evidence_cards", "id": card_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
    for derivation in claim_derivations:
        edges.append(
            {
                "edge_type": "claim_to_derivation_hash",
                "from": {
                    "table": "technical_report_claims",
                    "id": derivation.get("claim_id"),
                },
                "to": {
                    "table": "claim_evidence_derivations",
                    "id": derivation.get("claim_evidence_derivation_id"),
                },
                "derivation_sha256": derivation.get("derivation_sha256"),
            }
        )
    for document in source_documents:
        edges.append(
            {
                "edge_type": "source_pdf_checksum",
                "from": {"table": "source_pdf", "sha256": document.get("sha256")},
                "to": {"table": "documents", "id": document.get("id")},
            }
        )
    return edges


def build_technical_report_evidence_manifest_payload(
    session: Session,
    task_id: UUID,
) -> dict[str, Any]:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    audit_bundle = get_agent_task_audit_bundle(session, verification_task_id)
    draft_payload = audit_bundle["draft"]
    evidence_cards = list(draft_payload.get("evidence_cards") or [])
    claims = list(draft_payload.get("claims") or [])
    evidence_exports = list(audit_bundle.get("evidence_package_exports") or [])
    source_evidence_closure = dict(audit_bundle.get("source_evidence_closure") or {})
    claim_derivations = list(audit_bundle.get("claim_derivations") or [])
    operator_runs = list(audit_bundle.get("operator_runs") or [])
    document_ids = _uuid_values(
        [
            *[row.get("document_id") for row in draft_payload.get("document_refs") or []],
            *[card.get("document_id") for card in evidence_cards],
            *[
                document_id
                for claim in claims
                for document_id in (claim.get("source_document_ids") or [])
            ],
            *[
                document_id
                for export in evidence_exports
                for document_id in (export.get("document_ids") or [])
            ],
        ]
    )
    run_ids = _uuid_values(
        [
            *[row.get("run_id") for row in draft_payload.get("document_refs") or []],
            *[card.get("run_id") for card in evidence_cards],
            *[run_id for export in evidence_exports for run_id in (export.get("run_ids") or [])],
        ]
    )
    assertion_ids = _uuid_values(
        [
            *[
                assertion_id
                for card in evidence_cards
                for assertion_id in (card.get("assertion_ids") or [])
            ],
            *[
                assertion_id
                for claim in claims
                for assertion_id in (claim.get("assertion_ids") or [])
            ],
        ]
    )
    fact_ids = _uuid_values(
        [
            *[fact_id for card in evidence_cards for fact_id in (card.get("fact_ids") or [])],
            *[fact_id for claim in claims for fact_id in (claim.get("fact_ids") or [])],
        ]
    )
    evidence_ids = _uuid_values(
        evidence_id for card in evidence_cards for evidence_id in (card.get("evidence_ids") or [])
    )
    documents_by_id = _select_by_ids(session, Document, document_ids)
    runs_by_id = _select_by_ids(session, DocumentRun, run_ids)
    semantic_trace = _semantic_trace_payload(
        session,
        assertion_ids=assertion_ids,
        fact_ids=fact_ids,
        evidence_ids=evidence_ids,
    )
    source_documents = [
        _document_payload(row)
        for row in sorted(documents_by_id.values(), key=lambda item: str(item.id))
    ]
    document_runs = [
        _manifest_run_payload(row)
        for row in sorted(runs_by_id.values(), key=lambda item: str(item.id))
    ]
    source_records = [
        *_report_evidence_card_source_records(evidence_cards),
        *_source_record_payloads_from_semantic_trace(
            session,
            semantic_trace["assertion_evidence"],
        ),
    ]
    search_request_ids = _string_values(
        [
            *[row.get("search_request_id") for row in operator_runs],
            *[row.get("search_request_id") for row in evidence_exports],
        ]
    )
    operator_run_ids = _string_values(
        [
            *(row.get("operator_run_id") for row in operator_runs),
            *[
                operator_run_id
                for export in evidence_exports
                for operator_run_id in (export.get("operator_run_ids") or [])
            ],
        ]
    )
    source_snapshot_sha256s = _string_values(
        [
            *(draft_payload.get("source_snapshot_sha256s") or []),
            *[value for claim in claims for value in (claim.get("source_snapshot_sha256s") or [])],
            *[
                value
                for export in evidence_exports
                for value in (export.get("source_snapshot_sha256s") or [])
            ],
        ]
    )
    provenance_edges = _technical_report_provenance_edges(
        source_documents=source_documents,
        document_runs=document_runs,
        evidence_exports=evidence_exports,
        evidence_cards=evidence_cards,
        claims=claims,
        claim_derivations=claim_derivations,
        semantic_trace=semantic_trace,
    )
    checklist = {
        "has_source_documents": bool(source_documents),
        "all_source_documents_hashed": bool(source_documents)
        and all(document.get("sha256") for document in source_documents),
        "has_document_runs": bool(document_runs),
        "all_document_runs_validation_passed": bool(document_runs)
        and all(run.get("validation_status") == "passed" for run in document_runs),
        "has_evidence_cards": bool(evidence_cards),
        "has_claims": bool(claims),
        "has_claim_derivations": len(claim_derivations) == len(claims) and bool(claims),
        "has_semantic_trace": bool(
            semantic_trace["assertions"]
            or semantic_trace["facts"]
            or draft_payload.get("graph_context")
        ),
        "has_generation_operator_run": audit_bundle["audit_checklist"].get(
            "has_generation_operator_run",
            False,
        ),
        "has_verification_operator_run": audit_bundle["audit_checklist"].get(
            "has_verification_operator_run",
            False,
        ),
        "verification_passed": audit_bundle["audit_checklist"].get(
            "verification_passed",
            False,
        ),
        "hash_integrity_verified": audit_bundle["audit_checklist"].get(
            "hash_integrity_verified",
            False,
        ),
        "has_frozen_source_evidence_packages": audit_bundle["audit_checklist"].get(
            "has_frozen_source_evidence_packages",
            False,
        ),
        "source_evidence_trace_integrity_verified": audit_bundle["audit_checklist"].get(
            "source_evidence_trace_integrity_verified",
            False,
        ),
        "generation_evidence_closed": audit_bundle["audit_checklist"].get(
            "generation_evidence_closed",
            False,
        ),
        "change_impact_clear": audit_bundle["audit_checklist"].get(
            "change_impact_clear",
            False,
        ),
        "has_provenance_edges": bool(provenance_edges),
    }
    checklist["complete"] = all(checklist.values())
    return {
        "schema_name": "technical_report_evidence_manifest",
        "schema_version": "1.0",
        "manifest_kind": TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND,
        "task": audit_bundle["task"],
        "draft_task": audit_bundle["draft_task"],
        "verification_task": audit_bundle["verification_task"],
        "source_documents": source_documents,
        "document_runs": document_runs,
        "source_records": source_records,
        "semantic_trace": semantic_trace,
        "retrieval_trace": {
            "search_request_ids": search_request_ids,
            "ranking_operator_runs": [
                row
                for row in operator_runs
                if row.get("operator_kind") in {"retrieve", "rerank", "judge"}
            ],
            "search_evidence_package_exports": [
                row for row in evidence_exports if row.get("package_kind") == "search_request"
            ],
            "search_evidence_package_trace_summaries": list(
                audit_bundle.get("search_evidence_package_traces") or []
            ),
            "source_evidence_closure": source_evidence_closure,
        },
        "report_trace": {
            "evidence_cards": evidence_cards,
            "claims": claims,
            "claim_derivations": claim_derivations,
            "evidence_package_exports": evidence_exports,
            "evidence_package_integrity": audit_bundle["integrity"],
            "verification": audit_bundle["verification_record"],
            "operator_runs": operator_runs,
        },
        "provenance_edges": provenance_edges,
        "change_impact": audit_bundle["change_impact"],
        "audit_checklist": checklist,
        "source_snapshot_sha256s": source_snapshot_sha256s,
        "document_ids": _string_values(document_ids),
        "run_ids": _string_values(run_ids),
        "claim_ids": _string_values(claim.get("claim_id") for claim in claims),
        "search_request_ids": search_request_ids,
        "operator_run_ids": operator_run_ids,
    }


_TRACE_NODE_KIND_BY_TABLE = {
    "source_pdf": "source_pdf",
    "documents": "source_document",
    "document_runs": "document_run",
    "document_chunks": "source_chunk",
    "document_tables": "source_table",
    "document_figures": "source_figure",
    "semantic_assertions": "semantic_assertion",
    "semantic_assertion_evidence": "semantic_assertion_evidence",
    "semantic_facts": "semantic_fact",
    "semantic_fact_evidence": "semantic_fact_evidence",
    "technical_report_evidence_cards": "evidence_card",
    "technical_report_claims": "technical_report_claim",
    "claim_evidence_derivations": "claim_derivation",
    "evidence_package_exports": "evidence_package_export",
    "knowledge_operator_runs": "operator_run",
    "agent_tasks": "agent_task",
    "agent_task_verifications": "verification_record",
    "search_requests": "search_request",
    "search_request_results": "search_result",
    "search_request_result_spans": "selected_retrieval_span",
    "retrieval_evidence_spans": "retrieval_evidence_span",
    "retrieval_evidence_span_multivectors": "retrieval_evidence_span_multivector",
    "evidence_manifests": "evidence_manifest",
}


def _uuid_or_none_safe(value: Any | None) -> UUID | None:
    if value is None or value == "":
        return None
    try:
        return _uuid_or_none(value)
    except (TypeError, ValueError):
        return None


def _trace_payload_sha256(payload: dict[str, Any]) -> str:
    return str(payload_sha256(_json_payload(payload)))


def _trace_node_key(source_table: str, source_ref: Any) -> str:
    return f"{source_table}:{source_ref}"


def _put_trace_node(
    nodes: dict[str, dict[str, Any]],
    *,
    source_table: str,
    source_ref: Any,
    node_kind: str | None = None,
    source_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    normalized_source_ref = str(source_ref)
    key = _trace_node_key(source_table, normalized_source_ref)
    node_payload = {
        "source_table": source_table,
        "source_ref": normalized_source_ref,
        **_json_payload(payload),
    }
    if source_id is not None:
        node_payload["source_id"] = str(source_id)
    existing = nodes.get(key)
    if existing is not None and not existing["payload"].get("placeholder"):
        return key
    nodes[key] = {
        "node_key": key,
        "node_kind": node_kind or _TRACE_NODE_KIND_BY_TABLE.get(source_table, source_table),
        "source_table": source_table,
        "source_id": source_id,
        "source_ref": normalized_source_ref,
        "content_sha256": _trace_payload_sha256(node_payload),
        "payload": node_payload,
    }
    return key


def _put_trace_node_from_id(
    nodes: dict[str, dict[str, Any]],
    *,
    source_table: str,
    source_id: Any,
    node_kind: str | None = None,
    payload: dict[str, Any] | None = None,
) -> str | None:
    parsed_source_id = _uuid_or_none_safe(source_id)
    if parsed_source_id is None:
        return None
    return _put_trace_node(
        nodes,
        source_table=source_table,
        source_ref=parsed_source_id,
        source_id=parsed_source_id,
        node_kind=node_kind,
        payload=payload,
    )


def _put_trace_node_from_ref(
    nodes: dict[str, dict[str, Any]],
    ref: dict[str, Any],
) -> str:
    source_table = str(ref.get("table") or "unknown")
    source_ref = ref.get("id") or ref.get("sha256") or ref.get("ref") or "unknown"
    source_id = _uuid_or_none_safe(ref.get("id"))
    return _put_trace_node(
        nodes,
        source_table=source_table,
        source_ref=source_ref,
        source_id=source_id,
        payload={"placeholder": True, "ref": ref},
    )


def _put_trace_edge(
    edges: list[dict[str, Any]],
    *,
    edge_key: str,
    edge_kind: str,
    from_node_key: str | None,
    to_node_key: str | None,
    derivation_sha256: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    if not from_node_key or not to_node_key:
        return
    edge_payload = {
        "edge_kind": edge_kind,
        "from_node_key": from_node_key,
        "to_node_key": to_node_key,
        **_json_payload(payload),
    }
    if derivation_sha256:
        edge_payload["derivation_sha256"] = derivation_sha256
    edges.append(
        {
            "edge_key": edge_key,
            "edge_kind": edge_kind,
            "from_node_key": from_node_key,
            "to_node_key": to_node_key,
            "derivation_sha256": derivation_sha256,
            "content_sha256": _trace_payload_sha256(edge_payload),
            "payload": edge_payload,
        }
    )


def _trace_graph_canonical_payload(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_name": "technical_report_evidence_trace_graph",
        "schema_version": "1.0",
        "nodes": [
            {
                "node_key": node["node_key"],
                "node_kind": node["node_kind"],
                "source_table": node.get("source_table"),
                "source_id": str(node["source_id"]) if node.get("source_id") else None,
                "source_ref": node.get("source_ref"),
                "content_sha256": node["content_sha256"],
                "payload": _json_payload(node.get("payload")),
            }
            for node in sorted(nodes, key=lambda item: item["node_key"])
        ],
        "edges": [
            {
                "edge_key": edge["edge_key"],
                "edge_kind": edge["edge_kind"],
                "from_node_key": edge["from_node_key"],
                "to_node_key": edge["to_node_key"],
                "derivation_sha256": edge.get("derivation_sha256"),
                "content_sha256": edge["content_sha256"],
                "payload": _json_payload(edge.get("payload")),
            }
            for edge in sorted(edges, key=lambda item: item["edge_key"])
        ],
    }


def _trace_graph_sha256(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> str:
    return str(payload_sha256(_trace_graph_canonical_payload(nodes, edges)))


def _search_evidence_provenance_edges(
    *,
    search_request_id: UUID,
    source_evidence: list[dict],
) -> list[dict]:
    edges: list[dict] = []
    for item in source_evidence:
        search_result_id = item.get("search_request_result_id")
        if search_result_id:
            edge_payload = {
                "edge_type": "search_request_selected_result",
                "search_request_id": str(search_request_id),
                "search_request_result_id": str(search_result_id),
            }
            edges.append(
                {
                    **edge_payload,
                    "from": {"table": "search_requests", "id": str(search_request_id)},
                    "to": {"table": "search_request_results", "id": str(search_result_id)},
                    "derivation_sha256": payload_sha256(edge_payload),
                }
            )
        for span in item.get("retrieval_evidence_spans", []):
            result_span_id = span.get("search_request_result_span_id")
            source_span_id = span.get("retrieval_evidence_span_id")
            if search_result_id and result_span_id:
                edge_payload = {
                    "edge_type": "selected_span_supports_search_result",
                    "search_request_result_span_id": str(result_span_id),
                    "search_request_result_id": str(search_result_id),
                    "score_kind": span.get("score_kind"),
                }
                edges.append(
                    {
                        **edge_payload,
                        "from": {
                            "table": "search_request_result_spans",
                            "id": str(result_span_id),
                        },
                        "to": {"table": "search_request_results", "id": str(search_result_id)},
                        "derivation_sha256": payload_sha256(edge_payload),
                    }
                )
            if source_span_id and result_span_id:
                edge_payload = {
                    "edge_type": "retrieval_span_cited_as_selected_span",
                    "retrieval_evidence_span_id": str(source_span_id),
                    "search_request_result_span_id": str(result_span_id),
                    "content_sha256": span.get("content_sha256"),
                }
                edges.append(
                    {
                        **edge_payload,
                        "from": {"table": "retrieval_evidence_spans", "id": str(source_span_id)},
                        "to": {
                            "table": "search_request_result_spans",
                            "id": str(result_span_id),
                        },
                        "derivation_sha256": payload_sha256(edge_payload),
                    }
                )
            for vector in span.get("late_interaction_multivectors", []):
                span_vector_id = vector.get("span_vector_id")
                if span_vector_id and result_span_id:
                    edge_payload = {
                        "edge_type": "span_vector_matched_selected_span",
                        "span_vector_id": str(span_vector_id),
                        "search_request_result_span_id": str(result_span_id),
                        "content_sha256": vector.get("content_sha256"),
                        "embedding_sha256": vector.get("embedding_sha256"),
                    }
                    edges.append(
                        {
                            **edge_payload,
                            "from": {
                                "table": "retrieval_evidence_span_multivectors",
                                "id": str(span_vector_id),
                            },
                            "to": {
                                "table": "search_request_result_spans",
                                "id": str(result_span_id),
                            },
                            "derivation_sha256": payload_sha256(edge_payload),
                        }
                    )
                for link in vector.get("generation_operator_runs", []):
                    generation_operator_run_id = link.get("generation_operator_run_id")
                    if source_span_id and generation_operator_run_id:
                        edge_payload = {
                            "edge_type": "source_span_input_to_multivector_generation",
                            "retrieval_evidence_span_id": str(source_span_id),
                            "generation_operator_run_id": str(generation_operator_run_id),
                            "content_sha256": span.get("content_sha256"),
                        }
                        edges.append(
                            {
                                **edge_payload,
                                "from": {
                                    "table": "retrieval_evidence_spans",
                                    "id": str(source_span_id),
                                },
                                "to": {
                                    "table": "knowledge_operator_runs",
                                    "id": str(generation_operator_run_id),
                                },
                                "derivation_sha256": payload_sha256(edge_payload),
                            }
                        )
                    if generation_operator_run_id and span_vector_id:
                        edge_payload = {
                            "edge_type": "multivector_generation_output",
                            "generation_operator_run_id": str(generation_operator_run_id),
                            "span_vector_id": str(span_vector_id),
                            "generation_output_id": str(link.get("generation_output_id")),
                            "generation_output_sha256": link.get("generation_output_sha256"),
                        }
                        edges.append(
                            {
                                **edge_payload,
                                "from": {
                                    "table": "knowledge_operator_runs",
                                    "id": str(generation_operator_run_id),
                                },
                                "to": {
                                    "table": "retrieval_evidence_span_multivectors",
                                    "id": str(span_vector_id),
                                },
                                "derivation_sha256": payload_sha256(edge_payload),
                            }
                        )
    return edges


def _search_trace_graph_payload(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_name": "search_evidence_trace_graph",
        "schema_version": "1.0",
        "nodes": [
            {
                "node_key": node["node_key"],
                "node_kind": node["node_kind"],
                "source_table": node.get("source_table"),
                "source_id": str(node["source_id"]) if node.get("source_id") else None,
                "source_ref": node.get("source_ref"),
                "content_sha256": node["content_sha256"],
                "payload": _json_payload(node.get("payload")),
            }
            for node in sorted(nodes, key=lambda item: item["node_key"])
        ],
        "edges": [
            {
                "edge_key": edge["edge_key"],
                "edge_kind": edge["edge_kind"],
                "from_node_key": edge["from_node_key"],
                "to_node_key": edge["to_node_key"],
                "derivation_sha256": edge.get("derivation_sha256"),
                "content_sha256": edge["content_sha256"],
                "payload": _json_payload(edge.get("payload")),
            }
            for edge in sorted(edges, key=lambda item: item["edge_key"])
        ],
    }


def _search_trace_graph_sha256(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> str:
    return str(payload_sha256(_search_trace_graph_payload(nodes, edges)))


def _build_search_evidence_trace_graph(package: dict[str, Any]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    search_request = package.get("search_request") or {}
    search_request_id = search_request.get("id")
    _put_trace_node_from_id(
        nodes,
        source_table="search_requests",
        source_id=search_request_id,
        payload=search_request,
    )
    for operator_run in package.get("operator_runs") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="knowledge_operator_runs",
            source_id=operator_run.get("operator_run_id"),
            payload=operator_run,
        )
    for item in package.get("source_evidence") or []:
        result_id = item.get("search_request_result_id")
        _put_trace_node_from_id(
            nodes,
            source_table="search_request_results",
            source_id=result_id,
            payload={
                "search_request_result_id": str(result_id),
                "rank": item.get("rank"),
                "result_type": item.get("result_type"),
            },
        )
        for span in item.get("retrieval_evidence_spans", []):
            _put_trace_node_from_id(
                nodes,
                source_table="search_request_result_spans",
                source_id=span.get("search_request_result_span_id"),
                payload=span,
            )
            _put_trace_node_from_id(
                nodes,
                source_table="retrieval_evidence_spans",
                source_id=span.get("retrieval_evidence_span_id"),
                payload={
                    "retrieval_evidence_span_id": str(
                        span.get("retrieval_evidence_span_id")
                    ),
                    "source_type": span.get("source_type"),
                    "source_id": str(span.get("source_id")),
                    "span_index": span.get("span_index"),
                    "content_sha256": span.get("content_sha256"),
                    "source_snapshot_sha256": span.get("source_snapshot_sha256"),
                },
            )
            for vector in span.get("late_interaction_multivectors", []):
                _put_trace_node_from_id(
                    nodes,
                    source_table="retrieval_evidence_span_multivectors",
                    source_id=vector.get("span_vector_id"),
                    payload=vector,
                )
    for index, provenance_edge in enumerate(package.get("provenance_edges") or []):
        from_node_key = _put_trace_node_from_ref(nodes, provenance_edge.get("from") or {})
        to_node_key = _put_trace_node_from_ref(nodes, provenance_edge.get("to") or {})
        _put_trace_edge(
            edges,
            edge_key=f"search_evidence:{index}:{provenance_edge.get('edge_type')}",
            edge_kind=str(provenance_edge.get("edge_type") or "provenance_edge"),
            from_node_key=from_node_key,
            to_node_key=to_node_key,
            derivation_sha256=provenance_edge.get("derivation_sha256"),
            payload={
                "source": "search_evidence_package",
                "provenance_edge_index": index,
                "provenance_edge": provenance_edge,
            },
        )

    node_specs = sorted(nodes.values(), key=lambda item: item["node_key"])
    edge_specs = sorted(edges, key=lambda item: item["edge_key"])
    graph = _search_trace_graph_payload(node_specs, edge_specs)
    graph["trace_sha256"] = _search_trace_graph_sha256(node_specs, edge_specs)
    return graph


def _build_evidence_trace_graph_specs(
    *,
    manifest_row: EvidenceManifest,
    manifest_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    manifest_node_key = _put_trace_node(
        nodes,
        source_table="evidence_manifests",
        source_ref=manifest_row.id,
        source_id=manifest_row.id,
        payload={
            "evidence_manifest_id": str(manifest_row.id),
            "manifest_kind": manifest_row.manifest_kind,
            "manifest_sha256": manifest_row.manifest_sha256,
            "manifest_status": manifest_row.manifest_status,
            "verification_task_id": str(manifest_row.verification_task_id),
        },
    )

    task_node_keys: dict[str, str] = {}
    for payload_key, node_kind in (
        ("task", "agent_task"),
        ("draft_task", "draft_task"),
        ("verification_task", "verification_task"),
    ):
        task_payload = manifest_payload.get(payload_key) or {}
        task_node_key = _put_trace_node_from_id(
            nodes,
            source_table="agent_tasks",
            source_id=task_payload.get("task_id"),
            node_kind=node_kind,
            payload=task_payload,
        )
        if task_node_key:
            task_node_keys[payload_key] = task_node_key

    for document in manifest_payload.get("source_documents") or []:
        document_node_key = _put_trace_node_from_id(
            nodes,
            source_table="documents",
            source_id=document.get("id"),
            payload=document,
        )
        if document.get("sha256"):
            source_pdf_node_key = _put_trace_node(
                nodes,
                source_table="source_pdf",
                source_ref=document["sha256"],
                payload={
                    "sha256": document["sha256"],
                    "source_filename": document.get("source_filename"),
                    "document_id": document.get("id"),
                },
            )
            _put_trace_edge(
                edges,
                edge_key=f"materialized:source_pdf_checksum:{document['sha256']}",
                edge_kind="source_pdf_checksum",
                from_node_key=source_pdf_node_key,
                to_node_key=document_node_key,
                payload={"source": "materialized_trace", "document_id": document.get("id")},
            )

    for run in manifest_payload.get("document_runs") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="document_runs",
            source_id=run.get("id"),
            payload=run,
        )

    for record in manifest_payload.get("source_records") or []:
        if record.get("record_kind") == "technical_report_evidence_card":
            _put_trace_node(
                nodes,
                source_table="technical_report_evidence_cards",
                source_ref=record.get("evidence_card_id"),
                payload=record,
            )
        if record.get("evidence_id"):
            _put_trace_node_from_id(
                nodes,
                source_table="semantic_assertion_evidence",
                source_id=record.get("evidence_id"),
                payload=record,
            )
        for source_type, source_table in (
            ("chunk", "document_chunks"),
            ("table", "document_tables"),
            ("figure", "document_figures"),
        ):
            source_payload = record.get(source_type)
            if source_payload:
                _put_trace_node_from_id(
                    nodes,
                    source_table=source_table,
                    source_id=source_payload.get("id"),
                    payload=source_payload,
                )

    semantic_trace = manifest_payload.get("semantic_trace") or {}
    for assertion in semantic_trace.get("assertions") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="semantic_assertions",
            source_id=assertion.get("assertion_id"),
            payload=assertion,
        )
    for evidence in semantic_trace.get("assertion_evidence") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="semantic_assertion_evidence",
            source_id=evidence.get("evidence_id"),
            payload=evidence,
        )
    for fact in semantic_trace.get("facts") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="semantic_facts",
            source_id=fact.get("fact_id"),
            payload=fact,
        )
    for evidence in semantic_trace.get("fact_evidence") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="semantic_fact_evidence",
            source_id=evidence.get("fact_evidence_id"),
            payload=evidence,
        )

    report_trace = manifest_payload.get("report_trace") or {}
    for card in report_trace.get("evidence_cards") or []:
        _put_trace_node(
            nodes,
            source_table="technical_report_evidence_cards",
            source_ref=card.get("evidence_card_id"),
            payload=card,
        )
    for claim in report_trace.get("claims") or []:
        _put_trace_node(
            nodes,
            source_table="technical_report_claims",
            source_ref=claim.get("claim_id"),
            payload=claim,
        )
    for derivation in report_trace.get("claim_derivations") or []:
        derivation_id = derivation.get("claim_evidence_derivation_id")
        if derivation_id:
            _put_trace_node_from_id(
                nodes,
                source_table="claim_evidence_derivations",
                source_id=derivation_id,
                payload=derivation,
            )
        else:
            _put_trace_node(
                nodes,
                source_table="claim_evidence_derivations",
                source_ref=f"claim:{derivation.get('claim_id')}",
                payload=derivation,
            )
    for export in report_trace.get("evidence_package_exports") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="evidence_package_exports",
            source_id=export.get("evidence_package_export_id"),
            payload=export,
        )
    for operator_run in report_trace.get("operator_runs") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="knowledge_operator_runs",
            source_id=operator_run.get("operator_run_id"),
            payload=operator_run,
        )

    verification = report_trace.get("verification") or {}
    verification_record_node_key = _put_trace_node_from_id(
        nodes,
        source_table="agent_task_verifications",
        source_id=verification.get("verification_id"),
        payload=verification,
    )

    for search_request_id in manifest_payload.get("search_request_ids") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="search_requests",
            source_id=search_request_id,
            payload={"search_request_id": str(search_request_id)},
        )

    for index, provenance_edge in enumerate(manifest_payload.get("provenance_edges") or []):
        from_node_key = _put_trace_node_from_ref(nodes, provenance_edge.get("from") or {})
        to_node_key = _put_trace_node_from_ref(nodes, provenance_edge.get("to") or {})
        _put_trace_edge(
            edges,
            edge_key=f"manifest:{index}:{provenance_edge.get('edge_type')}",
            edge_kind=str(provenance_edge.get("edge_type") or "provenance_edge"),
            from_node_key=from_node_key,
            to_node_key=to_node_key,
            derivation_sha256=provenance_edge.get("derivation_sha256"),
            payload={
                "source": "manifest_provenance_edges",
                "manifest_edge_index": index,
                "provenance_edge": provenance_edge,
            },
        )

    draft_node_key = task_node_keys.get("draft_task")
    verification_task_node_key = task_node_keys.get("verification_task")
    _put_trace_edge(
        edges,
        edge_key="lifecycle:draft_task_to_verification_task",
        edge_kind="draft_task_to_verification_task",
        from_node_key=draft_node_key,
        to_node_key=verification_task_node_key,
        payload={"source": "materialized_trace"},
    )
    _put_trace_edge(
        edges,
        edge_key="lifecycle:verification_task_to_manifest",
        edge_kind="verification_task_to_manifest",
        from_node_key=verification_task_node_key,
        to_node_key=manifest_node_key,
        payload={"source": "materialized_trace"},
    )
    _put_trace_edge(
        edges,
        edge_key="lifecycle:verification_record_to_manifest",
        edge_kind="verification_record_to_manifest",
        from_node_key=verification_record_node_key,
        to_node_key=manifest_node_key,
        payload={"source": "materialized_trace"},
    )
    for export in report_trace.get("evidence_package_exports") or []:
        export_node_key = _trace_node_key(
            "evidence_package_exports",
            export.get("evidence_package_export_id"),
        )
        _put_trace_edge(
            edges,
            edge_key=f"manifest_contains:evidence_package_export:{export_node_key}",
            edge_kind="evidence_package_export_to_manifest",
            from_node_key=export_node_key,
            to_node_key=manifest_node_key,
            payload={"source": "materialized_trace"},
        )
    for operator_run in report_trace.get("operator_runs") or []:
        operator_node_key = _trace_node_key(
            "knowledge_operator_runs",
            operator_run.get("operator_run_id"),
        )
        _put_trace_edge(
            edges,
            edge_key=f"manifest_contains:operator_run:{operator_node_key}",
            edge_kind="operator_run_to_manifest",
            from_node_key=operator_node_key,
            to_node_key=manifest_node_key,
            payload={"source": "materialized_trace"},
        )
        parent_operator_id = operator_run.get("parent_operator_run_id")
        if parent_operator_id:
            parent_node_key = _put_trace_node_from_id(
                nodes,
                source_table="knowledge_operator_runs",
                source_id=parent_operator_id,
                payload={"operator_run_id": str(parent_operator_id), "placeholder": True},
            )
            _put_trace_edge(
                edges,
                edge_key=(f"operator_parent:{parent_node_key}->{operator_node_key}"),
                edge_kind="operator_run_parent_child",
                from_node_key=parent_node_key,
                to_node_key=operator_node_key,
                payload={"source": "materialized_trace"},
            )

    node_specs = sorted(nodes.values(), key=lambda item: item["node_key"])
    edge_specs = sorted(edges, key=lambda item: item["edge_key"])
    return node_specs, edge_specs, _trace_graph_sha256(node_specs, edge_specs)


def _persist_evidence_trace_graph(
    session: Session,
    *,
    manifest_row: EvidenceManifest,
    manifest_payload: dict[str, Any],
) -> None:
    node_specs, edge_specs, trace_sha256 = _build_evidence_trace_graph_specs(
        manifest_row=manifest_row,
        manifest_payload=manifest_payload,
    )
    session.execute(
        delete(EvidenceTraceEdge).where(EvidenceTraceEdge.evidence_manifest_id == manifest_row.id)
    )
    session.execute(
        delete(EvidenceTraceNode).where(EvidenceTraceNode.evidence_manifest_id == manifest_row.id)
    )
    session.flush()

    now = utcnow()
    node_rows_by_key: dict[str, EvidenceTraceNode] = {}
    for spec in node_specs:
        row = EvidenceTraceNode(
            id=uuid.uuid4(),
            evidence_manifest_id=manifest_row.id,
            node_key=spec["node_key"],
            node_kind=spec["node_kind"],
            source_table=spec.get("source_table"),
            source_id=spec.get("source_id"),
            source_ref=spec.get("source_ref"),
            content_sha256=spec["content_sha256"],
            payload_json=_json_payload(spec["payload"]),
            created_at=now,
        )
        node_rows_by_key[row.node_key] = row
        session.add(row)
    session.flush()

    for spec in edge_specs:
        from_node = node_rows_by_key.get(spec["from_node_key"])
        to_node = node_rows_by_key.get(spec["to_node_key"])
        if from_node is None or to_node is None:
            continue
        session.add(
            EvidenceTraceEdge(
                id=uuid.uuid4(),
                evidence_manifest_id=manifest_row.id,
                edge_key=spec["edge_key"],
                edge_kind=spec["edge_kind"],
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                from_node_key=spec["from_node_key"],
                to_node_key=spec["to_node_key"],
                derivation_sha256=spec.get("derivation_sha256"),
                content_sha256=spec["content_sha256"],
                payload_json=_json_payload(spec["payload"]),
                created_at=now,
            )
        )
    manifest_row.trace_sha256 = trace_sha256
    session.flush()


def _search_trace_specs_from_package(
    package_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    graph = package_payload.get("trace_graph")
    if not isinstance(graph, dict):
        graph = _build_search_evidence_trace_graph(package_payload)
    node_specs = [
        {
            "node_key": str(node["node_key"]),
            "node_kind": str(node["node_kind"]),
            "source_table": node.get("source_table"),
            "source_id": _uuid_or_none_safe(node.get("source_id")),
            "source_ref": node.get("source_ref"),
            "content_sha256": str(node["content_sha256"]),
            "payload": _json_payload(node.get("payload")),
        }
        for node in graph.get("nodes", [])
    ]
    edge_specs = [
        {
            "edge_key": str(edge["edge_key"]),
            "edge_kind": str(edge["edge_kind"]),
            "from_node_key": str(edge["from_node_key"]),
            "to_node_key": str(edge["to_node_key"]),
            "derivation_sha256": edge.get("derivation_sha256"),
            "content_sha256": str(edge["content_sha256"]),
            "payload": _json_payload(edge.get("payload")),
        }
        for edge in graph.get("edges", [])
    ]
    return node_specs, edge_specs, str(
        graph.get("trace_sha256") or _search_trace_graph_sha256(node_specs, edge_specs)
    )


def _persist_search_evidence_package_trace_graph(
    session: Session,
    *,
    export_row: EvidencePackageExport,
    package_payload: dict[str, Any],
) -> None:
    node_specs, edge_specs, trace_sha256 = _search_trace_specs_from_package(package_payload)
    session.execute(
        delete(EvidenceTraceEdge).where(
            EvidenceTraceEdge.evidence_package_export_id == export_row.id
        )
    )
    session.execute(
        delete(EvidenceTraceNode).where(
            EvidenceTraceNode.evidence_package_export_id == export_row.id
        )
    )
    session.flush()

    now = utcnow()
    node_rows_by_key: dict[str, EvidenceTraceNode] = {}
    for spec in node_specs:
        row = EvidenceTraceNode(
            id=uuid.uuid4(),
            evidence_manifest_id=None,
            evidence_package_export_id=export_row.id,
            node_key=spec["node_key"],
            node_kind=spec["node_kind"],
            source_table=spec.get("source_table"),
            source_id=spec.get("source_id"),
            source_ref=spec.get("source_ref"),
            content_sha256=spec["content_sha256"],
            payload_json=_json_payload(spec["payload"]),
            created_at=now,
        )
        node_rows_by_key[row.node_key] = row
        session.add(row)
    session.flush()

    for spec in edge_specs:
        from_node = node_rows_by_key.get(spec["from_node_key"])
        to_node = node_rows_by_key.get(spec["to_node_key"])
        if from_node is None or to_node is None:
            continue
        session.add(
            EvidenceTraceEdge(
                id=uuid.uuid4(),
                evidence_manifest_id=None,
                evidence_package_export_id=export_row.id,
                edge_key=spec["edge_key"],
                edge_kind=spec["edge_kind"],
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                from_node_key=spec["from_node_key"],
                to_node_key=spec["to_node_key"],
                derivation_sha256=spec.get("derivation_sha256"),
                content_sha256=spec["content_sha256"],
                payload_json=_json_payload(spec["payload"]),
                created_at=now,
            )
        )
    export_row.trace_sha256 = trace_sha256
    session.flush()


def _evidence_trace_rows(
    session: Session,
    manifest_id: UUID,
) -> tuple[list[EvidenceTraceNode], list[EvidenceTraceEdge]]:
    nodes = list(
        session.scalars(
            select(EvidenceTraceNode)
            .where(EvidenceTraceNode.evidence_manifest_id == manifest_id)
            .order_by(EvidenceTraceNode.node_key.asc())
        )
    )
    edges = list(
        session.scalars(
            select(EvidenceTraceEdge)
            .where(EvidenceTraceEdge.evidence_manifest_id == manifest_id)
            .order_by(EvidenceTraceEdge.edge_key.asc())
        )
    )
    return nodes, edges


def _search_evidence_trace_rows(
    session: Session,
    evidence_package_export_id: UUID,
) -> tuple[list[EvidenceTraceNode], list[EvidenceTraceEdge]]:
    nodes = list(
        session.scalars(
            select(EvidenceTraceNode)
            .where(EvidenceTraceNode.evidence_package_export_id == evidence_package_export_id)
            .order_by(EvidenceTraceNode.node_key.asc())
        )
    )
    edges = list(
        session.scalars(
            select(EvidenceTraceEdge)
            .where(EvidenceTraceEdge.evidence_package_export_id == evidence_package_export_id)
            .order_by(EvidenceTraceEdge.edge_key.asc())
        )
    )
    return nodes, edges


def _trace_node_row_payload(row: EvidenceTraceNode) -> dict[str, Any]:
    return {
        "node_id": row.id,
        "node_key": row.node_key,
        "node_kind": row.node_kind,
        "source_table": row.source_table,
        "source_id": row.source_id,
        "source_ref": row.source_ref,
        "content_sha256": row.content_sha256,
        "payload": row.payload_json or {},
        "created_at": row.created_at,
    }


def _trace_edge_row_payload(row: EvidenceTraceEdge) -> dict[str, Any]:
    return {
        "edge_id": row.id,
        "edge_key": row.edge_key,
        "edge_kind": row.edge_kind,
        "from_node_id": row.from_node_id,
        "to_node_id": row.to_node_id,
        "from_node_key": row.from_node_key,
        "to_node_key": row.to_node_key,
        "derivation_sha256": row.derivation_sha256,
        "content_sha256": row.content_sha256,
        "payload": row.payload_json or {},
        "created_at": row.created_at,
    }


def _trace_node_spec_from_row(row: EvidenceTraceNode) -> dict[str, Any]:
    return {
        "node_key": row.node_key,
        "node_kind": row.node_kind,
        "source_table": row.source_table,
        "source_id": row.source_id,
        "source_ref": row.source_ref,
        "content_sha256": row.content_sha256,
        "payload": row.payload_json or {},
    }


def _trace_edge_spec_from_row(row: EvidenceTraceEdge) -> dict[str, Any]:
    return {
        "edge_key": row.edge_key,
        "edge_kind": row.edge_kind,
        "from_node_key": row.from_node_key,
        "to_node_key": row.to_node_key,
        "derivation_sha256": row.derivation_sha256,
        "content_sha256": row.content_sha256,
        "payload": row.payload_json or {},
    }


def _evidence_trace_integrity_payload(
    session: Session,
    row: EvidenceManifest,
    nodes: list[EvidenceTraceNode],
    edges: list[EvidenceTraceEdge],
) -> dict[str, Any]:
    persisted_trace_sha256 = _trace_graph_sha256(
        (_trace_node_spec_from_row(node) for node in nodes),
        (_trace_edge_spec_from_row(edge) for edge in edges),
    )
    node_payload_hash_mismatch_count = sum(
        1 for node in nodes if _trace_payload_sha256(node.payload_json or {}) != node.content_sha256
    )
    edge_payload_hash_mismatch_count = sum(
        1 for edge in edges if _trace_payload_sha256(edge.payload_json or {}) != edge.content_sha256
    )
    recomputed_trace_sha256 = None
    recomputation_error = None
    try:
        recomputed_manifest_payload = build_technical_report_evidence_manifest_payload(
            session,
            row.verification_task_id,
        )
        recomputed_nodes, recomputed_edges, recomputed_trace_sha256 = (
            _build_evidence_trace_graph_specs(
                manifest_row=row,
                manifest_payload=recomputed_manifest_payload,
            )
        )
    except ValueError as exc:
        recomputation_error = str(exc)
        recomputed_nodes = []
        recomputed_edges = []

    persisted_trace_hash_matches = bool(row.trace_sha256) and (
        persisted_trace_sha256 == row.trace_sha256
    )
    recomputed_trace_hash_matches = bool(row.trace_sha256) and (
        recomputed_trace_sha256 == row.trace_sha256
    )
    persisted_trace_matches_recomputed = (
        persisted_trace_sha256 == recomputed_trace_sha256
        if recomputed_trace_sha256 is not None
        else False
    )
    return {
        "stored_trace_sha256": row.trace_sha256,
        "persisted_trace_sha256": persisted_trace_sha256,
        "recomputed_trace_sha256": recomputed_trace_sha256,
        "persisted_trace_hash_matches": persisted_trace_hash_matches,
        "recomputed_trace_hash_matches": recomputed_trace_hash_matches,
        "persisted_trace_matches_recomputed": persisted_trace_matches_recomputed,
        "node_payload_hash_mismatch_count": node_payload_hash_mismatch_count,
        "edge_payload_hash_mismatch_count": edge_payload_hash_mismatch_count,
        "node_count_matches_recomputed": (
            len(nodes) == len(recomputed_nodes) if recomputed_trace_sha256 else False
        ),
        "edge_count_matches_recomputed": (
            len(edges) == len(recomputed_edges) if recomputed_trace_sha256 else False
        ),
        "recomputation_error": recomputation_error,
        "complete": (
            row.manifest_status == "completed"
            and bool(nodes)
            and bool(edges)
            and node_payload_hash_mismatch_count == 0
            and edge_payload_hash_mismatch_count == 0
            and persisted_trace_hash_matches
            and recomputed_trace_hash_matches
            and persisted_trace_matches_recomputed
        ),
    }


def _search_evidence_trace_integrity_payload(
    session: Session,
    row: EvidencePackageExport,
    nodes: list[EvidenceTraceNode],
    edges: list[EvidenceTraceEdge],
) -> dict[str, Any]:
    stored_payload = row.package_payload_json or {}
    stored_payload_hash_basis = _clean_mapping(
        stored_payload,
        drop_fields={"package_sha256"},
    )
    stored_payload_sha256 = payload_sha256(stored_payload_hash_basis)
    stored_payload_trace_sha256 = (
        stored_payload.get("trace_graph", {}).get("trace_sha256")
        if isinstance(stored_payload.get("trace_graph"), dict)
        else None
    )
    persisted_trace_sha256 = _search_trace_graph_sha256(
        (_trace_node_spec_from_row(node) for node in nodes),
        (_trace_edge_spec_from_row(edge) for edge in edges),
    )
    node_payload_hash_mismatch_count = sum(
        1 for node in nodes if _trace_payload_sha256(node.payload_json or {}) != node.content_sha256
    )
    edge_payload_hash_mismatch_count = sum(
        1 for edge in edges if _trace_payload_sha256(edge.payload_json or {}) != edge.content_sha256
    )
    recomputed_package_sha256 = None
    recomputed_trace_sha256 = None
    recomputation_error = None
    recomputed_nodes: list[dict[str, Any]] = []
    recomputed_edges: list[dict[str, Any]] = []
    try:
        if row.search_request_id is None:
            raise ValueError("Search evidence package export is missing search_request_id.")
        recomputed_package = get_search_evidence_package(session, row.search_request_id)
        recomputed_package_sha256 = str(recomputed_package["package_sha256"])
        recomputed_nodes, recomputed_edges, recomputed_trace_sha256 = (
            _search_trace_specs_from_package(recomputed_package)
        )
    except ValueError as exc:
        recomputation_error = str(exc)

    stored_payload_hash_matches = stored_payload_sha256 == row.package_sha256
    stored_payload_trace_hash_matches = bool(row.trace_sha256) and (
        stored_payload_trace_sha256 == row.trace_sha256
    )
    persisted_trace_hash_matches = bool(row.trace_sha256) and (
        persisted_trace_sha256 == row.trace_sha256
    )
    recomputed_package_hash_matches = bool(recomputed_package_sha256) and (
        recomputed_package_sha256 == row.package_sha256
    )
    recomputed_trace_hash_matches = bool(row.trace_sha256) and (
        recomputed_trace_sha256 == row.trace_sha256
    )
    persisted_trace_matches_recomputed = (
        persisted_trace_sha256 == recomputed_trace_sha256
        if recomputed_trace_sha256 is not None
        else False
    )
    return {
        "stored_package_sha256": row.package_sha256,
        "stored_payload_sha256": stored_payload_sha256,
        "stored_trace_sha256": row.trace_sha256,
        "stored_payload_trace_sha256": stored_payload_trace_sha256,
        "persisted_trace_sha256": persisted_trace_sha256,
        "recomputed_package_sha256": recomputed_package_sha256,
        "recomputed_trace_sha256": recomputed_trace_sha256,
        "stored_payload_hash_matches": stored_payload_hash_matches,
        "stored_payload_trace_hash_matches": stored_payload_trace_hash_matches,
        "persisted_trace_hash_matches": persisted_trace_hash_matches,
        "recomputed_package_hash_matches": recomputed_package_hash_matches,
        "recomputed_trace_hash_matches": recomputed_trace_hash_matches,
        "persisted_trace_matches_recomputed": persisted_trace_matches_recomputed,
        "node_payload_hash_mismatch_count": node_payload_hash_mismatch_count,
        "edge_payload_hash_mismatch_count": edge_payload_hash_mismatch_count,
        "node_count_matches_recomputed": (
            len(nodes) == len(recomputed_nodes) if recomputed_trace_sha256 else False
        ),
        "edge_count_matches_recomputed": (
            len(edges) == len(recomputed_edges) if recomputed_trace_sha256 else False
        ),
        "recomputation_error": recomputation_error,
        "complete": (
            row.export_status == "completed"
            and bool(nodes)
            and bool(edges)
            and node_payload_hash_mismatch_count == 0
            and edge_payload_hash_mismatch_count == 0
            and stored_payload_hash_matches
            and stored_payload_trace_hash_matches
            and persisted_trace_hash_matches
            and recomputed_package_hash_matches
            and recomputed_trace_hash_matches
            and persisted_trace_matches_recomputed
        ),
    }


def _ensure_search_evidence_package_trace_graph(
    session: Session,
    row: EvidencePackageExport,
) -> EvidencePackageExport:
    node_count = session.scalar(
        select(func.count())
        .select_from(EvidenceTraceNode)
        .where(EvidenceTraceNode.evidence_package_export_id == row.id)
    )
    if row.trace_sha256 and node_count:
        return row
    _persist_search_evidence_package_trace_graph(
        session,
        export_row=row,
        package_payload=row.package_payload_json or {},
    )
    session.flush()
    return row


def _search_evidence_package_export_response(
    session: Session,
    row: EvidencePackageExport,
    nodes: list[EvidenceTraceNode],
    edges: list[EvidenceTraceEdge],
) -> dict[str, Any]:
    return {
        "schema_name": "search_evidence_package_export",
        "schema_version": "1.0",
        **_evidence_export_payload(row),
        "trace_api_path": f"/search/evidence-package-exports/{row.id}/trace-graph",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "trace_integrity": _search_evidence_trace_integrity_payload(
            session,
            row,
            nodes,
            edges,
        ),
    }


def _search_evidence_package_trace_response(
    session: Session,
    row: EvidencePackageExport,
    nodes: list[EvidenceTraceNode],
    edges: list[EvidenceTraceEdge],
) -> dict[str, Any]:
    return {
        "schema_name": "search_evidence_package_trace",
        "schema_version": "1.0",
        "evidence_package_export_id": str(row.id),
        "search_request_id": str(row.search_request_id) if row.search_request_id else None,
        "package_kind": row.package_kind,
        "package_sha256": row.package_sha256,
        "trace_sha256": row.trace_sha256,
        "export_status": row.export_status,
        "created_at": row.created_at,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "multivector_edge_count": sum(
            1
            for edge in edges
            if edge.edge_kind
            in {
                "source_span_input_to_multivector_generation",
                "multivector_generation_output",
                "span_vector_matched_selected_span",
            }
        ),
        "nodes": [_trace_node_row_payload(node) for node in nodes],
        "edges": [_trace_edge_row_payload(edge) for edge in edges],
        "trace_integrity": _search_evidence_trace_integrity_payload(
            session,
            row,
            nodes,
            edges,
        ),
    }


def _evidence_manifest_integrity_payload(
    session: Session,
    row: EvidenceManifest,
) -> dict[str, Any]:
    stored_payload = row.manifest_payload_json or {}
    stored_payload_sha256 = payload_sha256(stored_payload)
    recomputed_manifest_sha256 = None
    recomputation_error = None
    try:
        recomputed_payload = build_technical_report_evidence_manifest_payload(
            session,
            row.verification_task_id,
        )
        recomputed_manifest_sha256 = payload_sha256(recomputed_payload)
    except ValueError as exc:
        recomputation_error = str(exc)

    stored_payload_hash_matches = stored_payload_sha256 == row.manifest_sha256
    recomputed_manifest_hash_matches = recomputed_manifest_sha256 == row.manifest_sha256
    stored_payload_matches_recomputed = (
        stored_payload_sha256 == recomputed_manifest_sha256
        if recomputed_manifest_sha256 is not None
        else False
    )
    return {
        "stored_manifest_sha256": row.manifest_sha256,
        "stored_payload_sha256": stored_payload_sha256,
        "recomputed_manifest_sha256": recomputed_manifest_sha256,
        "stored_payload_hash_matches": stored_payload_hash_matches,
        "recomputed_manifest_hash_matches": recomputed_manifest_hash_matches,
        "stored_payload_matches_recomputed": stored_payload_matches_recomputed,
        "recomputation_error": recomputation_error,
        "manifest_status": row.manifest_status,
        "complete": (
            row.manifest_status == "completed"
            and stored_payload_hash_matches
            and recomputed_manifest_hash_matches
            and stored_payload_matches_recomputed
        ),
    }


def _evidence_manifest_response(session: Session, row: EvidenceManifest) -> dict[str, Any]:
    return {
        **(row.manifest_payload_json or {}),
        "evidence_manifest_id": str(row.id),
        "manifest_sha256": row.manifest_sha256,
        "trace_sha256": row.trace_sha256,
        "manifest_status": row.manifest_status,
        "created_at": row.created_at,
        "manifest_integrity": _evidence_manifest_integrity_payload(session, row),
    }


def _evidence_manifest_row_from_payload(
    *,
    verification_task_id: UUID,
    payload: dict[str, Any],
    manifest_sha256: str,
) -> EvidenceManifest:
    evidence_exports = payload["report_trace"]["evidence_package_exports"]
    return EvidenceManifest(
        id=uuid.uuid4(),
        manifest_kind=TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND,
        agent_task_id=verification_task_id,
        draft_task_id=_uuid_or_none(payload["draft_task"].get("task_id")),
        verification_task_id=verification_task_id,
        evidence_package_export_id=(
            _uuid_or_none(evidence_exports[0].get("evidence_package_export_id"))
            if evidence_exports
            else None
        ),
        manifest_sha256=manifest_sha256,
        manifest_payload_json=_json_payload(payload),
        source_snapshot_sha256s_json=list(payload["source_snapshot_sha256s"]),
        document_ids_json=list(payload["document_ids"]),
        run_ids_json=list(payload["run_ids"]),
        claim_ids_json=list(payload["claim_ids"]),
        search_request_ids_json=list(payload["search_request_ids"]),
        operator_run_ids_json=list(payload["operator_run_ids"]),
        manifest_status="completed",
        created_at=utcnow(),
    )


def _update_evidence_manifest_row_from_payload(
    row: EvidenceManifest,
    *,
    payload: dict[str, Any],
    manifest_sha256: str,
) -> EvidenceManifest:
    evidence_exports = payload["report_trace"]["evidence_package_exports"]
    row.draft_task_id = _uuid_or_none(payload["draft_task"].get("task_id"))
    row.evidence_package_export_id = (
        _uuid_or_none(evidence_exports[0].get("evidence_package_export_id"))
        if evidence_exports
        else None
    )
    row.manifest_sha256 = manifest_sha256
    row.manifest_payload_json = _json_payload(payload)
    row.source_snapshot_sha256s_json = list(payload["source_snapshot_sha256s"])
    row.document_ids_json = list(payload["document_ids"])
    row.run_ids_json = list(payload["run_ids"])
    row.claim_ids_json = list(payload["claim_ids"])
    row.search_request_ids_json = list(payload["search_request_ids"])
    row.operator_run_ids_json = list(payload["operator_run_ids"])
    row.manifest_status = "completed"
    return row


def persist_technical_report_evidence_manifest(
    session: Session,
    *,
    task_id: UUID,
) -> EvidenceManifest:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    existing = _existing_evidence_manifest(session, verification_task_id)
    if existing is not None:
        return existing
    payload = build_technical_report_evidence_manifest_payload(session, verification_task_id)
    manifest_sha256 = str(payload_sha256(payload))
    row = _evidence_manifest_row_from_payload(
        verification_task_id=verification_task_id,
        payload=payload,
        manifest_sha256=manifest_sha256,
    )
    session.add(row)
    session.flush()
    _persist_evidence_trace_graph(session, manifest_row=row, manifest_payload=payload)
    return row


def refresh_technical_report_evidence_manifest(
    session: Session,
    *,
    task_id: UUID,
) -> EvidenceManifest:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    payload = build_technical_report_evidence_manifest_payload(session, verification_task_id)
    manifest_sha256 = str(payload_sha256(payload))
    row = _existing_evidence_manifest(session, verification_task_id)
    if row is None:
        row = _evidence_manifest_row_from_payload(
            verification_task_id=verification_task_id,
            payload=payload,
            manifest_sha256=manifest_sha256,
        )
        session.add(row)
    else:
        _update_evidence_manifest_row_from_payload(
            row,
            payload=payload,
            manifest_sha256=manifest_sha256,
        )
    _persist_evidence_trace_graph(session, manifest_row=row, manifest_payload=payload)
    session.flush()
    return row


def _ensure_evidence_trace_graph(
    session: Session,
    row: EvidenceManifest,
) -> EvidenceManifest:
    if row.trace_sha256:
        return row
    _persist_evidence_trace_graph(
        session,
        manifest_row=row,
        manifest_payload=row.manifest_payload_json or {},
    )
    session.flush()
    return row


def get_agent_task_evidence_manifest(session: Session, task_id: UUID) -> dict[str, Any]:
    row = persist_technical_report_evidence_manifest(session, task_id=task_id)
    _ensure_evidence_trace_graph(session, row)
    return _evidence_manifest_response(session, row)


def get_agent_task_evidence_trace(session: Session, task_id: UUID) -> dict[str, Any]:
    row = persist_technical_report_evidence_manifest(session, task_id=task_id)
    _ensure_evidence_trace_graph(session, row)
    nodes, edges = _evidence_trace_rows(session, row.id)
    return {
        "schema_name": "technical_report_evidence_trace",
        "schema_version": "1.0",
        "evidence_manifest_id": str(row.id),
        "manifest_kind": row.manifest_kind,
        "manifest_sha256": row.manifest_sha256,
        "trace_sha256": row.trace_sha256,
        "manifest_status": row.manifest_status,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "manifest_provenance_edge_count": sum(
            1
            for edge in edges
            if (edge.payload_json or {}).get("source") == "manifest_provenance_edges"
        ),
        "nodes": [_trace_node_row_payload(node) for node in nodes],
        "edges": [_trace_edge_row_payload(edge) for edge in edges],
        "trace_integrity": _evidence_trace_integrity_payload(session, row, nodes, edges),
    }


def _prov_identifier(table: str | None, value: Any) -> str | None:
    if table is None or value is None or value == "":
        return None
    normalized_table = str(table).replace("_", "-")
    return f"docling:{normalized_table}/{value}"


def _prov_entity(
    entities: dict[str, dict[str, Any]],
    entity_id: str | None,
    *,
    label: str,
    entity_type: str,
    **attrs: Any,
) -> None:
    if entity_id is None:
        return
    payload = {
        "prov:label": label,
        "prov:type": entity_type,
        **{key: value for key, value in attrs.items() if value is not None and value != []},
    }
    existing = entities.get(entity_id)
    if existing is None:
        entities[entity_id] = payload
        return
    existing.update({key: value for key, value in payload.items() if value is not None})


def _prov_activity(
    activities: dict[str, dict[str, Any]],
    activity_id: str | None,
    *,
    label: str,
    activity_type: str,
    started_at: Any = None,
    ended_at: Any = None,
    **attrs: Any,
) -> None:
    if activity_id is None:
        return
    payload = {
        "prov:label": label,
        "prov:type": activity_type,
        "prov:startTime": started_at,
        "prov:endTime": ended_at,
        **{key: value for key, value in attrs.items() if value is not None and value != []},
    }
    activities[activity_id] = {key: value for key, value in payload.items() if value is not None}


def _prov_relation(
    relations: dict[str, dict[str, Any]],
    relation_prefix: str,
    *,
    sequence: int,
    **attrs: Any,
) -> None:
    relations[f"docling:{relation_prefix}/{sequence:06d}"] = {
        key: value for key, value in attrs.items() if value is not None
    }


def _prov_missing_relation_references(
    relations: dict[str, dict[str, Any]],
    *,
    relation_type: str,
    reference_field: str,
    declared_ids: set[str],
) -> list[dict[str, Any]]:
    missing_references: list[dict[str, Any]] = []
    for relation_id, relation in sorted(relations.items()):
        reference_id = relation.get(reference_field)
        if not reference_id or reference_id not in declared_ids:
            missing_references.append(
                {
                    "relation_type": relation_type,
                    "relation_id": relation_id,
                    "reference_field": reference_field,
                    "reference_id": reference_id,
                }
            )
    return missing_references


def _prov_export_integrity_payload(prov_export: dict[str, Any]) -> dict[str, Any]:
    entities = set((prov_export.get("entity") or {}).keys())
    activities = set((prov_export.get("activity") or {}).keys())
    agents = set((prov_export.get("agent") or {}).keys())
    audit = prov_export.get("audit") or {}
    retrieval_evaluation = prov_export.get("retrieval_evaluation") or {}
    summary = prov_export.get("prov_summary") or {}

    was_generated_by = prov_export.get("wasGeneratedBy") or {}
    used = prov_export.get("used") or {}
    was_derived_from = prov_export.get("wasDerivedFrom") or {}
    was_associated_with = prov_export.get("wasAssociatedWith") or {}
    was_attributed_to = prov_export.get("wasAttributedTo") or {}

    missing_generated_entities = _prov_missing_relation_references(
        was_generated_by,
        relation_type="wasGeneratedBy",
        reference_field="prov:entity",
        declared_ids=entities,
    )
    missing_generation_activities = _prov_missing_relation_references(
        was_generated_by,
        relation_type="wasGeneratedBy",
        reference_field="prov:activity",
        declared_ids=activities,
    )
    missing_used_activities = _prov_missing_relation_references(
        used,
        relation_type="used",
        reference_field="prov:activity",
        declared_ids=activities,
    )
    missing_used_entities = _prov_missing_relation_references(
        used,
        relation_type="used",
        reference_field="prov:entity",
        declared_ids=entities,
    )
    missing_derived_generated_entities = _prov_missing_relation_references(
        was_derived_from,
        relation_type="wasDerivedFrom",
        reference_field="prov:generatedEntity",
        declared_ids=entities,
    )
    missing_derived_used_entities = _prov_missing_relation_references(
        was_derived_from,
        relation_type="wasDerivedFrom",
        reference_field="prov:usedEntity",
        declared_ids=entities,
    )
    missing_association_activities = _prov_missing_relation_references(
        was_associated_with,
        relation_type="wasAssociatedWith",
        reference_field="prov:activity",
        declared_ids=activities,
    )
    missing_association_agents = _prov_missing_relation_references(
        was_associated_with,
        relation_type="wasAssociatedWith",
        reference_field="prov:agent",
        declared_ids=agents,
    )
    missing_attribution_entities = _prov_missing_relation_references(
        was_attributed_to,
        relation_type="wasAttributedTo",
        reference_field="prov:entity",
        declared_ids=entities,
    )
    missing_attribution_agents = _prov_missing_relation_references(
        was_attributed_to,
        relation_type="wasAttributedTo",
        reference_field="prov:agent",
        declared_ids=agents,
    )
    missing_relation_references = [
        *missing_generated_entities,
        *missing_generation_activities,
        *missing_used_activities,
        *missing_used_entities,
        *missing_derived_generated_entities,
        *missing_derived_used_entities,
        *missing_association_activities,
        *missing_association_agents,
        *missing_attribution_entities,
        *missing_attribution_agents,
    ]

    hash_basis = _clean_mapping(prov_export, drop_fields=_PROV_INTEGRITY_EXCLUDED_FIELDS)
    manifest_integrity_complete = bool((audit.get("manifest_integrity") or {}).get("complete"))
    trace_integrity_complete = bool((audit.get("trace_integrity") or {}).get("complete"))
    retrieval_evaluation_complete = bool(retrieval_evaluation.get("complete"))
    has_required_prov_surface = bool(entities and activities and was_derived_from)
    relation_references_complete = not missing_relation_references

    return {
        "hash_policy": "sha256 over canonical JSON excluding frozen_export and prov_integrity",
        "hash_basis_schema": "technical_report_prov_export_without_integrity_v1",
        "hash_basis_fields": sorted(hash_basis.keys()),
        "hash_excluded_fields": sorted(_PROV_INTEGRITY_EXCLUDED_FIELDS),
        "prov_sha256": payload_sha256(hash_basis),
        "manifest_integrity_complete": manifest_integrity_complete,
        "trace_integrity_complete": trace_integrity_complete,
        "retrieval_evaluation_complete": retrieval_evaluation_complete,
        "has_required_prov_surface": has_required_prov_surface,
        "all_generated_entities_declared": not missing_generated_entities,
        "all_generation_activities_declared": not missing_generation_activities,
        "all_used_activities_declared": not missing_used_activities,
        "all_used_entities_declared": not missing_used_entities,
        "all_derived_generated_entities_declared": not missing_derived_generated_entities,
        "all_derived_used_entities_declared": not missing_derived_used_entities,
        "all_association_activities_declared": not missing_association_activities,
        "all_association_agents_declared": not missing_association_agents,
        "all_attribution_entities_declared": not missing_attribution_entities,
        "all_attribution_agents_declared": not missing_attribution_agents,
        "all_relation_references_declared": relation_references_complete,
        "missing_relation_reference_count": len(missing_relation_references),
        "missing_relation_references": missing_relation_references,
        "relation_count": int(summary.get("relation_count") or 0),
        "complete": bool(
            manifest_integrity_complete
            and trace_integrity_complete
            and retrieval_evaluation_complete
            and has_required_prov_surface
            and relation_references_complete
        ),
    }


def _build_agent_task_provenance_export(session: Session, task_id: UUID) -> dict[str, Any]:
    manifest = get_agent_task_evidence_manifest(session, task_id)
    trace = get_agent_task_evidence_trace(session, task_id)
    retrieval_evaluation = dict(
        (manifest.get("retrieval_trace") or {}).get("source_evidence_closure") or {}
    )

    entities: dict[str, dict[str, Any]] = {}
    activities: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {
        "docling:agent/docling-system": {
            "prov:type": "prov:SoftwareAgent",
            "prov:label": "Docling System",
        },
        "docling:agent/technical-report-gate": {
            "prov:type": "prov:SoftwareAgent",
            "prov:label": "Technical report verification gate",
        },
    }
    was_generated_by: dict[str, dict[str, Any]] = {}
    used: dict[str, dict[str, Any]] = {}
    was_derived_from: dict[str, dict[str, Any]] = {}
    was_associated_with: dict[str, dict[str, Any]] = {}
    was_attributed_to: dict[str, dict[str, Any]] = {}

    manifest_entity_id = _prov_identifier(
        "evidence_manifests",
        manifest.get("evidence_manifest_id"),
    )
    _prov_entity(
        entities,
        manifest_entity_id,
        label="Technical report evidence manifest",
        entity_type="docling:TechnicalReportEvidenceManifest",
        **{
            "docling:manifest_sha256": manifest.get("manifest_sha256"),
            "docling:trace_sha256": manifest.get("trace_sha256"),
            "docling:manifest_kind": manifest.get("manifest_kind"),
        },
    )
    trace_entity_id = _prov_identifier("evidence_traces", manifest.get("evidence_manifest_id"))
    _prov_entity(
        entities,
        trace_entity_id,
        label="Technical report evidence trace",
        entity_type="docling:TechnicalReportEvidenceTrace",
        **{"docling:trace_sha256": trace.get("trace_sha256")},
    )

    for task_key in ("task", "draft_task", "verification_task"):
        task = manifest.get(task_key) or {}
        task_id_value = task.get("task_id")
        activity_id = _prov_identifier("agent_tasks", task_id_value)
        _prov_activity(
            activities,
            activity_id,
            label=str(task.get("task_type") or task_key),
            activity_type="docling:AgentTask",
            started_at=task.get("created_at"),
            ended_at=task.get("completed_at") or task.get("updated_at"),
            **{
                "docling:task_type": task.get("task_type"),
                "docling:status": task.get("status"),
                "docling:workflow_version": task.get("workflow_version"),
            },
        )
        _prov_relation(
            was_associated_with,
            "was-associated-with",
            sequence=len(was_associated_with) + 1,
            **{"prov:activity": activity_id, "prov:agent": "docling:agent/docling-system"},
        )

    verification_activity_id = _prov_identifier(
        "agent_tasks",
        (manifest.get("verification_task") or {}).get("task_id"),
    )
    _prov_relation(
        was_generated_by,
        "was-generated-by",
        sequence=len(was_generated_by) + 1,
        **{"prov:entity": manifest_entity_id, "prov:activity": verification_activity_id},
    )
    _prov_relation(
        was_generated_by,
        "was-generated-by",
        sequence=len(was_generated_by) + 1,
        **{"prov:entity": trace_entity_id, "prov:activity": verification_activity_id},
    )
    _prov_relation(
        was_associated_with,
        "was-associated-with",
        sequence=len(was_associated_with) + 1,
        **{
            "prov:activity": verification_activity_id,
            "prov:agent": "docling:agent/technical-report-gate",
        },
    )

    for document in manifest.get("source_documents") or []:
        entity_id = _prov_identifier("documents", document.get("id"))
        _prov_entity(
            entities,
            entity_id,
            label=str(document.get("source_filename") or "source document"),
            entity_type="docling:SourceDocument",
            **{
                "docling:sha256": document.get("sha256"),
                "docling:source_filename": document.get("source_filename"),
                "docling:title": document.get("title"),
            },
        )
        _prov_relation(
            was_attributed_to,
            "was-attributed-to",
            sequence=len(was_attributed_to) + 1,
            **{"prov:entity": entity_id, "prov:agent": "docling:agent/docling-system"},
        )

    for run in manifest.get("document_runs") or []:
        entity_id = _prov_identifier("document_runs", run.get("id"))
        _prov_entity(
            entities,
            entity_id,
            label="Document run",
            entity_type="docling:DocumentRun",
            **{
                "docling:document_id": run.get("document_id"),
                "docling:validation_status": run.get("validation_status"),
                "docling:docling_json_sha256": (run.get("artifact_hashes") or {}).get(
                    "docling_json_sha256"
                ),
                "docling:document_yaml_sha256": (run.get("artifact_hashes") or {}).get(
                    "document_yaml_sha256"
                ),
            },
        )

    for source_record in manifest.get("source_records") or []:
        entity_id = _prov_identifier(source_record.get("source_table"), source_record.get("id"))
        _prov_entity(
            entities,
            entity_id,
            label=str(source_record.get("source_type") or source_record.get("source_table")),
            entity_type="docling:SourceRecord",
            **{
                "docling:document_id": source_record.get("document_id"),
                "docling:run_id": source_record.get("run_id"),
                "docling:source_type": source_record.get("source_type"),
                "docling:source_snapshot_sha256": source_record.get(
                    "source_snapshot_sha256"
                ),
            },
        )

    report_trace = manifest.get("report_trace") or {}
    for export in report_trace.get("evidence_package_exports") or []:
        entity_id = _prov_identifier(
            "evidence_package_exports",
            export.get("evidence_package_export_id"),
        )
        _prov_entity(
            entities,
            entity_id,
            label=str(export.get("package_kind") or "evidence package export"),
            entity_type="docling:EvidencePackageExport",
            **{
                "docling:package_kind": export.get("package_kind"),
                "docling:package_sha256": export.get("package_sha256"),
                "docling:trace_sha256": export.get("trace_sha256"),
                "docling:search_request_id": export.get("search_request_id"),
            },
        )
        if export.get("search_request_id"):
            search_activity_id = _prov_identifier(
                "search_requests",
                export.get("search_request_id"),
            )
            _prov_activity(
                activities,
                search_activity_id,
                label="Search request",
                activity_type="docling:SearchRequest",
            )
            _prov_relation(
                was_generated_by,
                "was-generated-by",
                sequence=len(was_generated_by) + 1,
                **{"prov:entity": entity_id, "prov:activity": search_activity_id},
            )

    for card in report_trace.get("evidence_cards") or []:
        entity_id = _prov_identifier(
            "technical_report_evidence_cards",
            card.get("evidence_card_id"),
        )
        _prov_entity(
            entities,
            entity_id,
            label=str(card.get("evidence_card_id") or "evidence card"),
            entity_type="docling:TechnicalReportEvidenceCard",
            **{
                "docling:evidence_kind": card.get("evidence_kind"),
                "docling:source_type": card.get("source_type"),
                "docling:source_evidence_match_status": card.get(
                    "source_evidence_match_status"
                ),
            },
        )

    for claim in report_trace.get("claims") or []:
        entity_id = _prov_identifier("technical_report_claims", claim.get("claim_id"))
        _prov_entity(
            entities,
            entity_id,
            label=str(claim.get("claim_id") or "technical report claim"),
            entity_type="docling:TechnicalReportClaim",
            **{
                "docling:claim_text": claim.get("rendered_text"),
                "docling:source_evidence_match_status": claim.get(
                    "source_evidence_match_status"
                ),
            },
        )

    for derivation in report_trace.get("claim_derivations") or []:
        entity_id = _prov_identifier(
            "claim_evidence_derivations",
            derivation.get("claim_evidence_derivation_id"),
        )
        _prov_entity(
            entities,
            entity_id,
            label=str(derivation.get("claim_id") or "claim derivation"),
            entity_type="docling:ClaimEvidenceDerivation",
            **{"docling:derivation_sha256": derivation.get("derivation_sha256")},
        )

    for operator_run in report_trace.get("operator_runs") or []:
        activity_id = _prov_identifier(
            "knowledge_operator_runs",
            operator_run.get("operator_run_id"),
        )
        _prov_activity(
            activities,
            activity_id,
            label=str(operator_run.get("operator_name") or operator_run.get("operator_kind")),
            activity_type="docling:KnowledgeOperatorRun",
            started_at=operator_run.get("created_at"),
            **{
                "docling:operator_kind": operator_run.get("operator_kind"),
                "docling:operator_name": operator_run.get("operator_name"),
                "docling:operator_version": operator_run.get("operator_version"),
                "docling:status": operator_run.get("status"),
                "docling:config_sha256": operator_run.get("config_sha256"),
                "docling:input_sha256": operator_run.get("input_sha256"),
                "docling:output_sha256": operator_run.get("output_sha256"),
            },
        )
        _prov_relation(
            was_associated_with,
            "was-associated-with",
            sequence=len(was_associated_with) + 1,
            **{"prov:activity": activity_id, "prov:agent": "docling:agent/docling-system"},
        )

    for edge in manifest.get("provenance_edges") or []:
        from_ref = edge.get("from") or {}
        to_ref = edge.get("to") or {}
        from_id = _prov_identifier(
            from_ref.get("table"),
            from_ref.get("id") or from_ref.get("sha256"),
        )
        to_id = _prov_identifier(to_ref.get("table"), to_ref.get("id") or to_ref.get("sha256"))
        _prov_entity(
            entities,
            from_id,
            label=str(from_ref.get("table") or "provenance source"),
            entity_type="docling:ProvenanceEndpoint",
            **{"docling:table": from_ref.get("table")},
        )
        _prov_entity(
            entities,
            to_id,
            label=str(to_ref.get("table") or "provenance target"),
            entity_type="docling:ProvenanceEndpoint",
            **{"docling:table": to_ref.get("table")},
        )
        _prov_relation(
            was_derived_from,
            "was-derived-from",
            sequence=len(was_derived_from) + 1,
            **{
                "prov:generatedEntity": to_id,
                "prov:usedEntity": from_id,
                "docling:edge_type": edge.get("edge_type"),
            },
        )
        if verification_activity_id and from_id:
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": verification_activity_id, "prov:entity": from_id},
            )

    retrieval_complete = bool(retrieval_evaluation.get("complete"))
    relation_count = (
        len(was_generated_by)
        + len(used)
        + len(was_derived_from)
        + len(was_associated_with)
        + len(was_attributed_to)
    )
    prov_export = {
        "schema_name": "technical_report_prov_export",
        "schema_version": "1.0",
        "prov_compatibility": {
            "model": "W3C PROV-compatible JSON",
            "profile": "docling-system-technical-report-audit-v1",
        },
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://docling-system.local/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "entity": entities,
        "activity": activities,
        "agent": agents,
        "wasGeneratedBy": was_generated_by,
        "used": used,
        "wasDerivedFrom": was_derived_from,
        "wasAssociatedWith": was_associated_with,
        "wasAttributedTo": was_attributed_to,
        "retrieval_evaluation": retrieval_evaluation,
        "source_evidence_closure": retrieval_evaluation,
        "audit": {
            "manifest_sha256": manifest.get("manifest_sha256"),
            "trace_sha256": trace.get("trace_sha256"),
            "manifest_integrity": manifest.get("manifest_integrity"),
            "trace_integrity": trace.get("trace_integrity"),
            "audit_checklist": manifest.get("audit_checklist"),
        },
        "prov_summary": {
            "entity_count": len(entities),
            "activity_count": len(activities),
            "agent_count": len(agents),
            "was_generated_by_count": len(was_generated_by),
            "used_count": len(used),
            "was_derived_from_count": len(was_derived_from),
            "was_associated_with_count": len(was_associated_with),
            "was_attributed_to_count": len(was_attributed_to),
            "relation_count": relation_count,
            "retrieval_evaluation_complete": retrieval_complete,
            "source_record_recall": retrieval_evaluation.get("source_record_recall"),
        },
    }
    prov_export["prov_integrity"] = _prov_export_integrity_payload(prov_export)
    return _json_payload(prov_export)


def _existing_prov_export_artifact(
    session: Session,
    task_id: UUID,
) -> AgentTaskArtifact | None:
    return session.scalar(
        select(AgentTaskArtifact)
        .where(
            AgentTaskArtifact.task_id == task_id,
            AgentTaskArtifact.artifact_kind == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        )
        .order_by(AgentTaskArtifact.created_at.asc())
        .limit(1)
    )


def _prov_export_receipt_signature(receipt_sha256: str) -> dict[str, Any]:
    settings = get_settings()
    signing_key = getattr(settings, "audit_bundle_signing_key", None)
    if not signing_key:
        return {
            "signature_status": "unsigned",
            "signature": None,
            "signature_algorithm": PROV_EXPORT_RECEIPT_SIGNATURE_ALGORITHM,
            "signing_key_id": None,
        }
    signing_key_id = getattr(settings, "audit_bundle_signing_key_id", None) or "local"
    return {
        "signature_status": "signed",
        "signature": _prov_export_receipt_signature_value(receipt_sha256, str(signing_key)),
        "signature_algorithm": PROV_EXPORT_RECEIPT_SIGNATURE_ALGORITHM,
        "signing_key_id": str(signing_key_id),
    }


def _prov_export_receipt_signature_value(receipt_sha256: str, signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        receipt_sha256.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _prov_export_receipt(
    prov_export: dict[str, Any],
    *,
    artifact_id: UUID,
    task_id: UUID,
    created_at: Any,
    storage_path: str | None,
    export_payload_sha256: str | None,
    prov_hash_basis_sha256: str | None,
) -> dict[str, Any]:
    audit = prov_export.get("audit") or {}
    frozen_at = created_at.isoformat() if hasattr(created_at, "isoformat") else created_at
    receipt_core = {
        "schema_name": TECHNICAL_REPORT_PROV_EXPORT_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "artifact_id": str(artifact_id),
        "artifact_kind": TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        "task_id": str(task_id),
        "storage_path": storage_path,
        "frozen_at": frozen_at,
        "receipt_policy": (
            "Hash-chain receipt for the immutable technical-report PROV export. "
            "The receipt links the evidence manifest, evidence trace, PROV hash basis, "
            "and frozen export payload."
        ),
        "hash_chain": [
            {
                "position": 1,
                "name": "evidence_manifest",
                "sha256": audit.get("manifest_sha256"),
            },
            {
                "position": 2,
                "name": "evidence_trace",
                "sha256": audit.get("trace_sha256"),
            },
            {
                "position": 3,
                "name": "prov_hash_basis",
                "sha256": prov_hash_basis_sha256,
                "derived_from": ["evidence_manifest", "evidence_trace"],
            },
            {
                "position": 4,
                "name": "technical_report_prov_export",
                "sha256": export_payload_sha256,
                "derived_from": ["prov_hash_basis"],
            },
        ],
    }
    receipt_core["hash_chain_complete"] = all(
        bool(item.get("sha256")) for item in receipt_core["hash_chain"]
    )
    receipt_sha256 = str(payload_sha256(receipt_core))
    return {
        **receipt_core,
        "receipt_sha256": receipt_sha256,
        **_prov_export_receipt_signature(receipt_sha256),
    }


def _frozen_prov_export_payload(
    prov_export: dict[str, Any],
    *,
    artifact_id: UUID,
    task_id: UUID,
    created_at: Any,
    storage_path: str | None,
) -> dict[str, Any]:
    frozen_payload = _json_payload(prov_export)
    export_payload_sha256 = payload_sha256(prov_export)
    prov_hash_basis_sha256 = (prov_export.get("prov_integrity") or {}).get("prov_sha256")
    frozen_payload["frozen_export"] = {
        "schema_name": "technical_report_prov_export_freeze",
        "schema_version": "1.0",
        "artifact_id": str(artifact_id),
        "artifact_kind": TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        "task_id": str(task_id),
        "storage_path": storage_path,
        "frozen_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
        "freeze_policy": (
            "The first completed technical-report PROV export is persisted as an "
            "agent-task artifact and reused for subsequent reads."
        ),
        "export_payload_sha256": export_payload_sha256,
        "prov_hash_basis_sha256": prov_hash_basis_sha256,
        "export_receipt": _prov_export_receipt(
            prov_export,
            artifact_id=artifact_id,
            task_id=task_id,
            created_at=created_at,
            storage_path=storage_path,
            export_payload_sha256=export_payload_sha256,
            prov_hash_basis_sha256=prov_hash_basis_sha256,
        ),
    }
    return _json_payload(frozen_payload)


def _frozen_export_sha256(payload: dict[str, Any] | None) -> str | None:
    frozen_export = (payload or {}).get("frozen_export") or {}
    return frozen_export.get("export_payload_sha256")


def _frozen_export_receipt(payload: dict[str, Any] | None) -> dict[str, Any]:
    frozen_export = (payload or {}).get("frozen_export") or {}
    receipt = frozen_export.get("export_receipt")
    return receipt if isinstance(receipt, dict) else {}


def _receipt_hash_basis(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key
        not in {
            "receipt_sha256",
            "signature",
            "signature_algorithm",
            "signature_status",
            "signing_key_id",
        }
    }


def _receipt_hash_chain_sha256(receipt: dict[str, Any], name: str) -> str | None:
    for item in receipt.get("hash_chain") or []:
        if item.get("name") == name:
            return item.get("sha256")
    return None


def _prov_export_receipt_integrity(payload: dict[str, Any] | None) -> dict[str, Any]:
    frozen_payload = _json_payload(payload or {})
    frozen_export = frozen_payload.get("frozen_export") or {}
    receipt = _frozen_export_receipt(frozen_payload)
    receipt_hash_basis = _receipt_hash_basis(receipt)
    expected_receipt_sha256 = (
        str(payload_sha256(receipt_hash_basis)) if receipt_hash_basis else None
    )
    stored_receipt_sha256 = receipt.get("receipt_sha256")
    receipt_hash_matches = bool(
        expected_receipt_sha256 and expected_receipt_sha256 == stored_receipt_sha256
    )

    signature_status = receipt.get("signature_status") or "missing"
    signature_algorithm_matches = (
        receipt.get("signature_algorithm") == PROV_EXPORT_RECEIPT_SIGNATURE_ALGORITHM
    )
    signature_present = bool(receipt.get("signature")) and signature_status == "signed"
    signature_valid = False
    signature_verification_status = signature_status
    if signature_status == "signed" and stored_receipt_sha256 and signature_present:
        settings = get_settings()
        signing_key = getattr(settings, "audit_bundle_signing_key", None)
        if signing_key:
            signature_valid = hmac.compare_digest(
                str(receipt.get("signature")),
                _prov_export_receipt_signature_value(stored_receipt_sha256, str(signing_key)),
            )
            signature_verification_status = "verified" if signature_valid else "mismatch"
        else:
            signature_verification_status = "signing_key_missing"

    hash_chain_values = [
        item.get("sha256") for item in receipt.get("hash_chain") or []
    ]
    hash_chain_complete = bool(receipt.get("hash_chain_complete")) and all(hash_chain_values)
    export_payload_hash_matches = (
        _receipt_hash_chain_sha256(receipt, "technical_report_prov_export")
        == frozen_export.get("export_payload_sha256")
    )
    prov_hash_basis_matches = (
        _receipt_hash_chain_sha256(receipt, "prov_hash_basis")
        == frozen_export.get("prov_hash_basis_sha256")
    )
    checks = {
        "has_receipt": bool(receipt),
        "receipt_hash_matches": receipt_hash_matches,
        "expected_receipt_sha256": expected_receipt_sha256,
        "stored_receipt_sha256": stored_receipt_sha256,
        "hash_chain_complete": hash_chain_complete,
        "artifact_id_matches": receipt.get("artifact_id") == frozen_export.get("artifact_id"),
        "artifact_kind_matches": receipt.get("artifact_kind")
        == frozen_export.get("artifact_kind"),
        "task_id_matches": receipt.get("task_id") == frozen_export.get("task_id"),
        "storage_path_matches": receipt.get("storage_path") == frozen_export.get("storage_path"),
        "export_payload_hash_matches": export_payload_hash_matches,
        "prov_hash_basis_matches": prov_hash_basis_matches,
        "signature_status": signature_status,
        "signature_algorithm_matches": signature_algorithm_matches,
        "signature_present": signature_present,
        "signature_valid": signature_valid,
        "signature_verification_status": signature_verification_status,
    }
    checks["complete"] = all(
        bool(checks[key])
        for key in (
            "has_receipt",
            "receipt_hash_matches",
            "hash_chain_complete",
            "artifact_id_matches",
            "artifact_kind_matches",
            "task_id_matches",
            "storage_path_matches",
            "export_payload_hash_matches",
            "prov_hash_basis_matches",
            "signature_algorithm_matches",
            "signature_present",
            "signature_valid",
        )
    )
    return checks


def _record_prov_export_supersession_attempt(
    session: Session,
    *,
    existing: AgentTaskArtifact,
    attempted_prov_export: dict[str, Any],
) -> AgentTaskArtifactImmutabilityEvent | None:
    existing_payload = _json_payload(existing.payload_json or {})
    existing_sha256 = _frozen_export_sha256(existing_payload)
    attempted_sha256 = payload_sha256(attempted_prov_export)
    if existing_sha256 == attempted_sha256:
        return None

    duplicate = session.scalar(
        select(AgentTaskArtifactImmutabilityEvent)
        .where(
            AgentTaskArtifactImmutabilityEvent.artifact_id == existing.id,
            AgentTaskArtifactImmutabilityEvent.event_kind == "supersession_attempt",
            AgentTaskArtifactImmutabilityEvent.frozen_payload_sha256 == existing_sha256,
            AgentTaskArtifactImmutabilityEvent.attempted_payload_sha256 == attempted_sha256,
        )
        .limit(1)
    )
    if duplicate is not None:
        return duplicate

    existing_receipt = _frozen_export_receipt(existing_payload)
    event = AgentTaskArtifactImmutabilityEvent(
        artifact_id=existing.id,
        task_id=existing.task_id,
        event_kind="supersession_attempt",
        mutation_operation="FREEZE_REUSE",
        frozen_artifact_kind=existing.artifact_kind,
        attempted_artifact_kind=TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        frozen_storage_path=existing.storage_path,
        attempted_storage_path=existing.storage_path,
        frozen_payload_sha256=existing_sha256,
        attempted_payload_sha256=attempted_sha256,
        details_json={
            "reason": "A new PROV export was computed after the frozen artifact already existed.",
            "action": "kept_existing_frozen_artifact",
            "existing_receipt_sha256": existing_receipt.get("receipt_sha256"),
            "attempted_prov_hash_basis_sha256": (
                attempted_prov_export.get("prov_integrity") or {}
            ).get("prov_sha256"),
        },
        created_at=utcnow(),
    )
    session.add(event)
    session.flush()
    return event


def persist_agent_task_provenance_export(
    session: Session,
    *,
    task_id: UUID,
    storage_service: StorageService | None = None,
) -> AgentTaskArtifact:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    existing = _existing_prov_export_artifact(session, verification_task_id)
    if existing is not None:
        attempted_prov_export = _build_agent_task_provenance_export(session, verification_task_id)
        _record_prov_export_supersession_attempt(
            session,
            existing=existing,
            attempted_prov_export=attempted_prov_export,
        )
        record_technical_report_prov_export_governance_event(
            session,
            artifact=existing,
            evidence_manifest=_existing_evidence_manifest(session, verification_task_id),
        )
        return existing

    artifact_id = uuid.uuid4()
    created_at = utcnow()
    artifact_path = (
        storage_service.get_agent_task_dir(verification_task_id)
        / TECHNICAL_REPORT_PROV_EXPORT_FILENAME
        if storage_service is not None
        else None
    )
    storage_path = str(artifact_path) if artifact_path is not None else None
    prov_export = _build_agent_task_provenance_export(session, verification_task_id)
    frozen_payload = _frozen_prov_export_payload(
        prov_export,
        artifact_id=artifact_id,
        task_id=verification_task_id,
        created_at=created_at,
        storage_path=storage_path,
    )
    if artifact_path is not None:
        artifact_path.write_text(json.dumps(frozen_payload, indent=2, sort_keys=True))

    row = AgentTaskArtifact(
        id=artifact_id,
        task_id=verification_task_id,
        artifact_kind=TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        storage_path=storage_path,
        payload_json=frozen_payload,
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    record_technical_report_prov_export_governance_event(
        session,
        artifact=row,
        evidence_manifest=_existing_evidence_manifest(session, verification_task_id),
    )
    return row


def get_agent_task_provenance_export(
    session: Session,
    task_id: UUID,
    *,
    storage_service: StorageService | None = None,
) -> dict[str, Any]:
    artifact = persist_agent_task_provenance_export(
        session,
        task_id=task_id,
        storage_service=storage_service,
    )
    return _json_payload(artifact.payload_json or {})


def _draft_task_id_for_audit(task: AgentTask) -> UUID:
    if task.task_type == "draft_technical_report":
        return task.id
    if task.task_type == "verify_technical_report":
        payload = (task.result_json or {}).get("payload") or {}
        verification = payload.get("verification") or {}
        target_task_id = verification.get("target_task_id")
        if not target_task_id:
            target_task_id = (task.input_json or {}).get("target_task_id")
        if target_task_id:
            return UUID(str(target_task_id))
    raise ValueError("Audit bundles are currently supported for technical report tasks only.")


def _technical_report_upstream_task_ids(
    session: Session,
    draft_payload: dict[str, Any],
) -> list[UUID]:
    related_task_ids: list[UUID] = []
    harness_task_id = _uuid_or_none_safe(draft_payload.get("harness_task_id"))
    if harness_task_id is not None:
        related_task_ids.append(harness_task_id)
        harness_task = session.get(AgentTask, harness_task_id)
        harness_payload = (
            ((harness_task.result_json or {}).get("payload") or {}).get("harness", {})
            if harness_task is not None
            else {}
        )
        evidence_task_id = _uuid_or_none_safe(
            (harness_payload.get("workflow_state") or {}).get("evidence_task_id")
        )
        if evidence_task_id is not None:
            related_task_ids.append(evidence_task_id)
            evidence_task = session.get(AgentTask, evidence_task_id)
            evidence_payload = (
                ((evidence_task.result_json or {}).get("payload") or {}).get(
                    "evidence_bundle",
                    {},
                )
                if evidence_task is not None
                else {}
            )
            plan_task_id = _uuid_or_none_safe(evidence_payload.get("plan_task_id"))
            if plan_task_id is not None:
                related_task_ids.append(plan_task_id)
    return list(dict.fromkeys(related_task_ids))


def get_agent_task_audit_bundle(session: Session, task_id: UUID) -> dict:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    draft_task_id = _draft_task_id_for_audit(task)
    draft_task = session.get(AgentTask, draft_task_id)
    if draft_task is None:
        raise ValueError(f"Draft task '{draft_task_id}' was not found.")

    verification_task = task if task.task_type == "verify_technical_report" else None
    verification_row = None
    if verification_task is not None:
        verification_row = session.scalar(
            select(AgentTaskVerification).where(
                AgentTaskVerification.verification_task_id == verification_task.id
            )
        )

    draft_payload = ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
    related_task_ids = [
        draft_task.id,
        *_technical_report_upstream_task_ids(session, draft_payload),
    ]
    if verification_task is not None:
        related_task_ids.append(verification_task.id)
    related_task_ids = list(dict.fromkeys(related_task_ids))

    artifacts = list(
        session.scalars(
            select(AgentTaskArtifact)
            .where(AgentTaskArtifact.task_id.in_(related_task_ids))
            .order_by(AgentTaskArtifact.created_at.asc())
        )
    )
    prov_export_artifacts = [
        row
        for row in artifacts
        if row.artifact_kind == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND
    ]
    prov_export_artifact_ids = [row.id for row in prov_export_artifacts]
    prov_export_receipts = [
        _provenance_export_receipt_payload(row) for row in prov_export_artifacts
    ]
    prov_export_immutability_events = (
        list(
            session.scalars(
                select(AgentTaskArtifactImmutabilityEvent)
                .where(AgentTaskArtifactImmutabilityEvent.artifact_id.in_(prov_export_artifact_ids))
                .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
            )
        )
        if prov_export_artifact_ids
        else []
    )
    evidence_manifests = list(
        session.scalars(
            select(EvidenceManifest)
            .where(
                or_(
                    EvidenceManifest.agent_task_id.in_(related_task_ids),
                    EvidenceManifest.draft_task_id.in_(related_task_ids),
                    EvidenceManifest.verification_task_id.in_(related_task_ids),
                )
            )
            .order_by(EvidenceManifest.created_at.asc())
        )
    )
    semantic_governance_chain = semantic_governance_chain_for_audit(
        session,
        task_ids=related_task_ids,
        artifact_ids=prov_export_artifact_ids,
        evidence_manifest_ids=[row.id for row in evidence_manifests],
        receipt_sha256s=[
            (row.get("export_receipt") or {}).get("receipt_sha256")
            for row in prov_export_receipts
        ],
    )
    exports = list(
        session.scalars(
            select(EvidencePackageExport)
            .where(EvidencePackageExport.agent_task_id.in_(related_task_ids))
            .order_by(EvidencePackageExport.created_at.asc())
        )
    )
    report_exports = [row for row in exports if row.package_kind == "technical_report_claims"]
    search_exports = [row for row in exports if row.package_kind == "search_request"]
    report_export_ids = [row.id for row in report_exports]
    derivations: list[ClaimEvidenceDerivation] = []
    if report_export_ids:
        derivations = list(
            session.scalars(
                select(ClaimEvidenceDerivation)
                .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(report_export_ids))
                .order_by(ClaimEvidenceDerivation.claim_id.asc())
            )
        )
    operator_runs = list(
        session.scalars(
            select(KnowledgeOperatorRun)
            .where(KnowledgeOperatorRun.agent_task_id.in_(related_task_ids))
            .order_by(KnowledgeOperatorRun.created_at.asc())
        )
    )
    verification_payload = (
        ((verification_task.result_json or {}).get("payload") or {})
        if verification_task is not None
        else None
    )
    change_impact = _change_impact_payload(session, exports)
    integrity = _technical_report_integrity_payload(draft_payload, report_exports, derivations)
    source_evidence_closure = technical_report_search_evidence_closure_payload(
        session,
        draft_payload,
    )
    hash_integrity_verified = (
        integrity["draft_package_hash_matches"]
        and integrity["export_package_hash_matches"]
        and integrity["claim_derivation_count_matches"]
        and integrity["claim_derivation_hash_mismatch_count"] == 0
        and integrity["claim_package_hash_mismatch_count"] == 0
        and integrity["missing_claim_derivation_count"] == 0
    )
    source_evidence_trace_integrity_verified = source_evidence_closure["complete"]
    prov_export_receipts_integrity_verified = bool(prov_export_receipts) and all(
        (row.get("receipt_integrity") or {}).get("complete")
        for row in prov_export_receipts
    )
    prov_export_receipt_signature_verified = bool(prov_export_receipts) and all(
        (row.get("receipt_integrity") or {}).get("signature_verification_status")
        == "verified"
        for row in prov_export_receipts
    )
    audit_bundle = {
        "schema_name": "technical_report_audit_bundle",
        "schema_version": "1.0",
        "task": _task_payload(task),
        "draft_task": _task_payload(draft_task),
        "verification_task": _task_payload(verification_task),
        "draft": draft_payload,
        "verification": verification_payload,
        "verification_record": _verification_payload(verification_row),
        "artifacts": [_artifact_payload(row) for row in artifacts],
        "provenance_export_receipts": prov_export_receipts,
        "provenance_export_immutability_events": [
            _immutability_event_payload(row) for row in prov_export_immutability_events
        ],
        "semantic_governance_chain": semantic_governance_chain,
        "evidence_package_exports": [_evidence_export_payload(row) for row in exports],
        "search_evidence_package_traces": source_evidence_closure["trace_summaries"],
        "source_evidence_closure": source_evidence_closure,
        "claim_derivations": [_claim_derivation_payload(row) for row in derivations],
        "operator_runs": [_operator_run_summary(row) for row in operator_runs],
        "change_impact": change_impact,
        "integrity": integrity,
        "audit_checklist": {
            "has_frozen_evidence_package": bool(exports),
            "all_claims_have_derivations": len(derivations)
            == len(draft_payload.get("claims") or []),
            "hash_integrity_verified": hash_integrity_verified,
            "has_frozen_source_evidence_packages": bool(search_exports),
            "has_frozen_prov_export": bool(prov_export_artifacts),
            "has_prov_export_receipt": bool(prov_export_receipts)
            and all(
                (row.get("export_receipt") or {}).get("receipt_sha256")
                for row in prov_export_receipts
            ),
            "has_signed_prov_export_receipt": any(
                (row.get("export_receipt") or {}).get("signature_status") == "signed"
                for row in prov_export_receipts
            ),
            "prov_export_receipts_integrity_verified": (
                prov_export_receipts_integrity_verified
            ),
            "prov_export_receipt_signature_verified": (
                prov_export_receipt_signature_verified
            ),
            "no_prov_export_immutability_events": not prov_export_immutability_events,
            "has_semantic_governance_chain": semantic_governance_chain["integrity"][
                "has_events"
            ],
            "semantic_governance_chain_integrity_verified": semantic_governance_chain[
                "integrity"
            ]["complete"],
            "semantic_governance_chain_links_prov_receipt": semantic_governance_chain[
                "integrity"
            ]["links_requested_prov_receipt"],
            "source_evidence_trace_integrity_verified": (
                source_evidence_trace_integrity_verified
            ),
            "generation_evidence_closed": (
                hash_integrity_verified and source_evidence_trace_integrity_verified
            ),
            "has_generation_operator_run": any(
                row.operator_kind == "generate" for row in operator_runs
            ),
            "has_verification_operator_run": any(
                row.operator_kind == "verify" for row in operator_runs
            ),
            "verification_passed": (
                verification_row.outcome == "passed" if verification_row is not None else False
            ),
            "change_impact_clear": not change_impact["impacted"],
        },
    }
    audit_bundle["audit_checklist"]["complete"] = (
        audit_bundle["audit_checklist"]["generation_evidence_closed"]
        and audit_bundle["audit_checklist"]["has_generation_operator_run"]
        and audit_bundle["audit_checklist"]["has_verification_operator_run"]
        and audit_bundle["audit_checklist"]["has_frozen_prov_export"]
        and audit_bundle["audit_checklist"]["has_prov_export_receipt"]
        and audit_bundle["audit_checklist"]["has_signed_prov_export_receipt"]
        and audit_bundle["audit_checklist"]["prov_export_receipts_integrity_verified"]
        and audit_bundle["audit_checklist"]["prov_export_receipt_signature_verified"]
        and audit_bundle["audit_checklist"]["no_prov_export_immutability_events"]
        and audit_bundle["audit_checklist"]["has_semantic_governance_chain"]
        and audit_bundle["audit_checklist"]["semantic_governance_chain_integrity_verified"]
        and audit_bundle["audit_checklist"]["semantic_governance_chain_links_prov_receipt"]
        and audit_bundle["audit_checklist"]["verification_passed"]
        and audit_bundle["audit_checklist"]["change_impact_clear"]
    )
    audit_bundle["audit_bundle_sha256"] = payload_sha256(audit_bundle)
    return audit_bundle
