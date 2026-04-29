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
    AgentTaskDependency,
    AgentTaskVerification,
    AuditBundleExport,
    AuditBundleValidationReceipt,
    ClaimEvidenceDerivation,
    ClaimSupportPolicyChangeImpact,
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation,
    ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
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
    RetrievalRerankerArtifact,
    SearchHarnessRelease,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
    SemanticAssertion,
    SemanticAssertionEvidence,
    SemanticFact,
    SemanticFactEvidence,
    SemanticGovernanceEvent,
    SemanticGraphSnapshot,
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
DOCUMENT_GENERATION_CONTEXT_PACK_ARTIFACT_KIND = "document_generation_context_pack"
DOCUMENT_GENERATION_CONTEXT_PACK_EVALUATION_ARTIFACT_KIND = (
    "document_generation_context_pack_evaluation"
)
DOCUMENT_GENERATION_CONTEXT_PACK_GATE = "document_generation_context_pack_gate"
DOCUMENT_GENERATION_CONTEXT_PACK_EVALUATION_OPERATOR = "document_generation_context_pack_evaluation"
RELEASE_READINESS_DB_GATE_CHECK_KEY = "release_readiness_assessment_db_integrity"
_PROV_INTEGRITY_EXCLUDED_FIELDS = {"frozen_export", "prov_integrity"}
CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_CLOSED_EVENT_KIND = "claim_support_policy_impact_replay_closed"
CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND = (
    "claim_support_policy_impact_replay_escalated"
)
CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND = (
    "claim_support_policy_impact_fixture_promoted"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver_closed"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_coverage_waiver_closure"
)
CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot_activated"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_PAYLOAD_KEY = (
    "claim_support_replay_alert_fixture_corpus_snapshot"
)
CLAIM_SUPPORT_POLICY_IMPACT_OPEN_REPLAY_STATUSES = {
    "pending",
    "queued",
    "in_progress",
    "blocked",
}


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
        span for item in source_evidence for span in item.get("retrieval_evidence_spans", [])
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
                *(vector.get("span_vector_snapshot_sha256") for vector in late_interaction_vectors),
            ]
        ),
        "operator_run_ids": _string_values(run.get("operator_run_id") for run in operator_runs),
        "document_ids": _string_values(
            (item.get("document") or {}).get("id") for item in source_evidence
        ),
        "run_ids": _string_values((item.get("run") or {}).get("id") for item in source_evidence),
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
            source_record_keys.append(_source_record_key(source_type, source_payload.get("id")))
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
                span["key"]: span for span in source_page_spans if span and span.get("key")
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
        str(card_id) for claim in claims for card_id in (claim.get("evidence_card_ids") or [])
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
        if card.get("source_evidence_match_status") not in _ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES
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
        key for coverage in card_source_coverages for key in coverage["expected_source_record_keys"]
    }
    matched_source_record_keys = {
        key for coverage in card_source_coverages for key in coverage["matched_source_record_keys"]
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
        "claims_missing_source_evidence_package_export_count": len(claims_missing_source_exports),
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
        "reported_recomputed_match_mismatch_count": len(reported_recomputed_match_mismatches),
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

_CLAIM_PROVENANCE_LOCK_LIST_FIELDS = (
    "source_search_request_ids",
    "source_search_request_result_ids",
    "source_evidence_package_export_ids",
    "source_evidence_package_sha256s",
    "source_evidence_trace_sha256s",
    "semantic_ontology_snapshot_ids",
    "semantic_graph_snapshot_ids",
    "retrieval_reranker_artifact_ids",
    "search_harness_release_ids",
    "release_audit_bundle_ids",
    "release_validation_receipt_ids",
)


def _string_values(values: Iterable[Any]) -> list[str]:
    return [str(value) for value in dict.fromkeys(values) if value is not None and value != ""]


def _clean_mapping(value: dict[str, Any], *, drop_fields: set[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in drop_fields}


def _id_str_values(values: Iterable[Any]) -> list[str]:
    return _string_values(_uuid_values(values))


def _latest_passed_release_bindings_by_request(
    session: Session,
    request_rows_by_id: dict[str, SearchRequestRecord],
) -> tuple[dict[str, dict[str, Any]], dict[str, SearchHarnessRelease]]:
    harness_names = _string_values(row.harness_name for row in request_rows_by_id.values())
    if not harness_names:
        return {}, {}
    release_rows = list(
        session.scalars(
            select(SearchHarnessRelease)
            .where(
                SearchHarnessRelease.candidate_harness_name.in_(harness_names),
                SearchHarnessRelease.outcome == "passed",
            )
            .order_by(
                SearchHarnessRelease.candidate_harness_name.asc(),
                SearchHarnessRelease.created_at.desc(),
                SearchHarnessRelease.id.asc(),
            )
        )
    )
    release_rows_by_harness: dict[str, list[SearchHarnessRelease]] = {
        harness_name: [] for harness_name in harness_names
    }
    for row in release_rows:
        release_rows_by_harness.setdefault(row.candidate_harness_name, []).append(row)

    bindings_by_request_id: dict[str, dict[str, Any]] = {}
    releases_by_id: dict[str, SearchHarnessRelease] = {}
    for request_id, request_row in request_rows_by_id.items():
        selected_release = next(
            (
                row
                for row in release_rows_by_harness.get(request_row.harness_name, [])
                if row.created_at <= request_row.created_at
            ),
            None,
        )
        binding = {
            "search_request_id": request_id,
            "harness_name": request_row.harness_name,
            "search_request_created_at": request_row.created_at,
            "search_harness_release_id": (
                str(selected_release.id) if selected_release is not None else None
            ),
            "search_harness_release_created_at": (
                selected_release.created_at if selected_release is not None else None
            ),
            "selection_rule": "latest_passed_release_at_or_before_search_request",
            "selection_status": (
                "release_found_before_request"
                if selected_release is not None
                else "no_passed_release_before_request"
            ),
        }
        bindings_by_request_id[request_id] = _json_payload(binding)
        if selected_release is not None:
            releases_by_id[str(selected_release.id)] = selected_release
    return bindings_by_request_id, releases_by_id


def _latest_release_audit_bundles_by_release(
    session: Session,
    release_ids: Iterable[UUID],
) -> dict[UUID, AuditBundleExport]:
    ids = _uuid_values(release_ids)
    if not ids:
        return {}
    rows = list(
        session.scalars(
            select(AuditBundleExport)
            .where(
                AuditBundleExport.search_harness_release_id.in_(ids),
                AuditBundleExport.bundle_kind == "search_harness_release_provenance",
                AuditBundleExport.export_status == "completed",
            )
            .order_by(
                AuditBundleExport.search_harness_release_id.asc(),
                AuditBundleExport.created_at.desc(),
                AuditBundleExport.id.asc(),
            )
        )
    )
    latest_by_release: dict[UUID, AuditBundleExport] = {}
    for row in rows:
        if row.search_harness_release_id is not None:
            latest_by_release.setdefault(row.search_harness_release_id, row)
    return latest_by_release


def _latest_passed_receipts_by_bundle(
    session: Session,
    bundle_ids: Iterable[UUID],
) -> dict[UUID, AuditBundleValidationReceipt]:
    ids = _uuid_values(bundle_ids)
    if not ids:
        return {}
    rows = list(
        session.scalars(
            select(AuditBundleValidationReceipt)
            .where(
                AuditBundleValidationReceipt.audit_bundle_export_id.in_(ids),
                AuditBundleValidationReceipt.validation_status == "passed",
            )
            .order_by(
                AuditBundleValidationReceipt.audit_bundle_export_id.asc(),
                AuditBundleValidationReceipt.created_at.desc(),
                AuditBundleValidationReceipt.id.asc(),
            )
        )
    )
    latest_by_bundle: dict[UUID, AuditBundleValidationReceipt] = {}
    for row in rows:
        latest_by_bundle.setdefault(row.audit_bundle_export_id, row)
    return latest_by_bundle


def _claim_source_values(
    claim: dict[str, Any],
    *,
    cards_by_id: dict[str, dict[str, Any]],
    field_name: str,
) -> list[str]:
    return _string_values(
        [
            *(claim.get(field_name) or []),
            *[
                value
                for card_id in claim.get("evidence_card_ids") or []
                for value in (cards_by_id.get(str(card_id), {}).get(field_name) or [])
            ],
        ]
    )


def _claim_derivation_provenance_lock_contract_mismatches(
    row: ClaimEvidenceDerivation,
) -> list[str]:
    lock = dict(row.provenance_lock_json or {})
    if not lock:
        return ["provenance_lock"]
    mismatches: list[str] = []
    if lock.get("schema_name") != "technical_report_claim_provenance_lock":
        mismatches.append("schema_name")
    if lock.get("schema_version") != "1.0":
        mismatches.append("schema_version")
    if str(lock.get("claim_id") or "") != str(row.claim_id):
        mismatches.append("claim_id")
    row_values = {
        "source_search_request_ids": row.source_search_request_ids_json or [],
        "source_search_request_result_ids": row.source_search_request_result_ids_json or [],
        "source_evidence_package_export_ids": (row.source_evidence_package_export_ids_json or []),
        "source_evidence_package_sha256s": row.source_evidence_package_sha256s_json or [],
        "source_evidence_trace_sha256s": row.source_evidence_trace_sha256s_json or [],
        "semantic_ontology_snapshot_ids": row.semantic_ontology_snapshot_ids_json or [],
        "semantic_graph_snapshot_ids": row.semantic_graph_snapshot_ids_json or [],
        "retrieval_reranker_artifact_ids": row.retrieval_reranker_artifact_ids_json or [],
        "search_harness_release_ids": row.search_harness_release_ids_json or [],
        "release_audit_bundle_ids": row.release_audit_bundle_ids_json or [],
        "release_validation_receipt_ids": row.release_validation_receipt_ids_json or [],
    }
    for field_name in _CLAIM_PROVENANCE_LOCK_LIST_FIELDS:
        if _string_values(lock.get(field_name) or []) != _string_values(row_values[field_name]):
            mismatches.append(field_name)
    coverage = dict(lock.get("coverage") or {})
    coverage_fields = {
        "source_search_request_count": "source_search_request_ids",
        "source_search_request_result_count": "source_search_request_result_ids",
        "source_evidence_package_export_count": "source_evidence_package_export_ids",
        "semantic_ontology_snapshot_count": "semantic_ontology_snapshot_ids",
        "semantic_graph_snapshot_count": "semantic_graph_snapshot_ids",
        "retrieval_reranker_artifact_count": "retrieval_reranker_artifact_ids",
        "search_harness_release_count": "search_harness_release_ids",
        "release_audit_bundle_count": "release_audit_bundle_ids",
        "release_validation_receipt_count": "release_validation_receipt_ids",
    }
    for coverage_key, field_name in coverage_fields.items():
        if coverage.get(coverage_key) != len(_string_values(lock.get(field_name) or [])):
            mismatches.append(f"coverage.{coverage_key}")
    return mismatches


def _claim_derivation_support_judgment_contract_mismatches(
    row: ClaimEvidenceDerivation,
) -> list[str]:
    judgment = dict(row.support_judgment_json or {})
    if not judgment:
        return ["support_judgment"]
    mismatches: list[str] = []
    if judgment.get("schema_name") != "technical_report_claim_support_judgment":
        mismatches.append("schema_name")
    if judgment.get("schema_version") != "1.0":
        mismatches.append("schema_version")
    if judgment.get("judge_kind") != "deterministic_claim_support_v1":
        mismatches.append("judge_kind")
    if str(judgment.get("claim_id") or "") != str(row.claim_id):
        mismatches.append("claim_id")
    if judgment.get("verdict") != row.support_verdict:
        mismatches.append("verdict")
    try:
        judgment_score = float(judgment.get("support_score"))
    except (TypeError, ValueError):
        mismatches.append("support_score")
    else:
        if row.support_score is None or abs(judgment_score - row.support_score) > 0.0001:
            mismatches.append("support_score")
    if _string_values(judgment.get("source_search_request_result_ids") or []) != (
        row.source_search_request_result_ids_json or []
    ):
        mismatches.append("source_search_request_result_ids")
    if sorted(_string_values(judgment.get("evidence_card_ids") or [])) != sorted(
        row.evidence_card_ids_json or []
    ):
        mismatches.append("evidence_card_ids")
    if sorted(_string_values(judgment.get("graph_edge_ids") or [])) != sorted(
        row.graph_edge_ids_json or []
    ):
        mismatches.append("graph_edge_ids")
    return mismatches


def _apply_technical_report_claim_provenance_locks(
    session: Session,
    draft_payload: dict[str, Any],
) -> None:
    cards_by_id = {
        str(card.get("evidence_card_id")): dict(card)
        for card in draft_payload.get("evidence_cards", [])
        if card.get("evidence_card_id")
    }
    graph_snapshot_by_edge_id = {
        str(edge.get("edge_id")): edge.get("graph_snapshot_id")
        for edge in draft_payload.get("graph_context") or []
        if edge.get("edge_id") and edge.get("graph_snapshot_id")
    }
    all_fact_ids = _uuid_values(
        fact_id
        for claim in draft_payload.get("claims") or []
        for fact_id in (claim.get("fact_ids") or [])
    )
    fact_ontology_by_id: dict[str, str] = {}
    if all_fact_ids:
        facts = session.scalars(select(SemanticFact).where(SemanticFact.id.in_(all_fact_ids)))
        fact_ontology_by_id = {
            str(row.id): str(row.ontology_snapshot_id)
            for row in facts
            if row.ontology_snapshot_id is not None
        }

    all_graph_snapshot_ids = _uuid_values(graph_snapshot_by_edge_id.values())
    graph_snapshot_ontology_by_id: dict[str, str] = {}
    if all_graph_snapshot_ids:
        graph_snapshots = session.scalars(
            select(SemanticGraphSnapshot).where(
                SemanticGraphSnapshot.id.in_(all_graph_snapshot_ids)
            )
        )
        graph_snapshot_ontology_by_id = {
            str(row.id): str(row.ontology_snapshot_id)
            for row in graph_snapshots
            if row.ontology_snapshot_id is not None
        }

    all_search_request_ids = _uuid_values(
        request_id
        for claim in draft_payload.get("claims") or []
        for request_id in _claim_source_values(
            claim,
            cards_by_id=cards_by_id,
            field_name="source_search_request_ids",
        )
    )
    request_rows_by_id: dict[str, SearchRequestRecord] = {}
    if all_search_request_ids:
        requests = session.scalars(
            select(SearchRequestRecord).where(SearchRequestRecord.id.in_(all_search_request_ids))
        )
        request_rows_by_id = {str(row.id): row for row in requests}

    release_bindings_by_request_id, releases_by_id = _latest_passed_release_bindings_by_request(
        session,
        request_rows_by_id,
    )
    release_ids = _uuid_values(row.id for row in releases_by_id.values())
    reranker_artifacts_by_release: dict[str, list[RetrievalRerankerArtifact]] = {
        str(release_id): [] for release_id in release_ids
    }
    if release_ids:
        reranker_rows = session.scalars(
            select(RetrievalRerankerArtifact)
            .where(RetrievalRerankerArtifact.search_harness_release_id.in_(release_ids))
            .order_by(
                RetrievalRerankerArtifact.search_harness_release_id.asc(),
                RetrievalRerankerArtifact.created_at.desc(),
                RetrievalRerankerArtifact.id.asc(),
            )
        )
        for row in reranker_rows:
            if row.search_harness_release_id is not None:
                reranker_artifacts_by_release.setdefault(
                    str(row.search_harness_release_id), []
                ).append(row)
    audit_bundles_by_release = _latest_release_audit_bundles_by_release(session, release_ids)
    receipts_by_bundle = _latest_passed_receipts_by_bundle(
        session,
        (row.id for row in audit_bundles_by_release.values()),
    )

    all_lock_sha256s: list[str] = []
    all_ontology_snapshot_ids: list[str] = []
    all_graph_snapshot_ids_for_claims: list[str] = []
    all_reranker_artifact_ids: list[str] = []
    all_release_ids: list[str] = []
    all_audit_bundle_ids: list[str] = []
    all_receipt_ids: list[str] = []

    for claim in draft_payload.get("claims") or []:
        source_search_request_ids = _id_str_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_search_request_ids",
            )
        )
        source_search_request_result_ids = _id_str_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_search_request_result_ids",
            )
        )
        source_evidence_package_export_ids = _id_str_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_evidence_package_export_ids",
            )
        )
        source_evidence_package_sha256s = _string_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_evidence_package_sha256s",
            )
        )
        source_evidence_trace_sha256s = _string_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_evidence_trace_sha256s",
            )
        )
        semantic_graph_snapshot_ids = _id_str_values(
            graph_snapshot_by_edge_id.get(str(edge_id))
            for edge_id in claim.get("graph_edge_ids") or []
        )
        semantic_ontology_snapshot_ids = _id_str_values(
            [
                *[fact_ontology_by_id.get(str(fact_id)) for fact_id in claim.get("fact_ids") or []],
                *[
                    graph_snapshot_ontology_by_id.get(str(snapshot_id))
                    for snapshot_id in semantic_graph_snapshot_ids
                ],
            ]
        )
        source_search_request_release_bindings = [
            release_bindings_by_request_id[request_id]
            for request_id in source_search_request_ids
            if request_id in release_bindings_by_request_id
        ]
        claim_release_ids = _id_str_values(
            binding.get("search_harness_release_id")
            for binding in source_search_request_release_bindings
        )
        retrieval_reranker_artifact_ids = _id_str_values(
            row.id
            for release_id in claim_release_ids
            for row in reranker_artifacts_by_release.get(str(release_id), [])
        )
        release_audit_bundle_ids = _id_str_values(
            audit_bundles_by_release[UUID(str(release_id))].id
            for release_id in claim_release_ids
            if UUID(str(release_id)) in audit_bundles_by_release
        )
        release_validation_receipt_ids = _id_str_values(
            receipts_by_bundle[UUID(str(bundle_id))].id
            for bundle_id in release_audit_bundle_ids
            if UUID(str(bundle_id)) in receipts_by_bundle
        )
        provenance_lock = {
            "schema_name": "technical_report_claim_provenance_lock",
            "schema_version": "1.0",
            "claim_id": str(claim.get("claim_id") or ""),
            "source_search_request_ids": source_search_request_ids,
            "source_search_request_result_ids": source_search_request_result_ids,
            "source_evidence_package_export_ids": source_evidence_package_export_ids,
            "source_evidence_package_sha256s": source_evidence_package_sha256s,
            "source_evidence_trace_sha256s": source_evidence_trace_sha256s,
            "semantic_ontology_snapshot_ids": semantic_ontology_snapshot_ids,
            "semantic_graph_snapshot_ids": semantic_graph_snapshot_ids,
            "retrieval_reranker_artifact_ids": retrieval_reranker_artifact_ids,
            "search_harness_release_ids": claim_release_ids,
            "source_search_request_release_bindings": (source_search_request_release_bindings),
            "release_audit_bundle_ids": release_audit_bundle_ids,
            "release_validation_receipt_ids": release_validation_receipt_ids,
            "coverage": {
                "source_search_request_count": len(source_search_request_ids),
                "source_search_request_result_count": len(source_search_request_result_ids),
                "source_evidence_package_export_count": len(source_evidence_package_export_ids),
                "semantic_ontology_snapshot_count": len(semantic_ontology_snapshot_ids),
                "semantic_graph_snapshot_count": len(semantic_graph_snapshot_ids),
                "retrieval_reranker_artifact_count": len(retrieval_reranker_artifact_ids),
                "search_harness_release_count": len(claim_release_ids),
                "release_audit_bundle_count": len(release_audit_bundle_ids),
                "release_validation_receipt_count": len(release_validation_receipt_ids),
            },
        }
        provenance_lock_sha256 = str(payload_sha256(provenance_lock) or "")
        claim["source_search_request_ids"] = source_search_request_ids
        claim["source_search_request_result_ids"] = source_search_request_result_ids
        claim["source_evidence_package_export_ids"] = source_evidence_package_export_ids
        claim["source_evidence_package_sha256s"] = source_evidence_package_sha256s
        claim["source_evidence_trace_sha256s"] = source_evidence_trace_sha256s
        claim["semantic_ontology_snapshot_ids"] = semantic_ontology_snapshot_ids
        claim["semantic_graph_snapshot_ids"] = semantic_graph_snapshot_ids
        claim["retrieval_reranker_artifact_ids"] = retrieval_reranker_artifact_ids
        claim["search_harness_release_ids"] = claim_release_ids
        claim["release_audit_bundle_ids"] = release_audit_bundle_ids
        claim["release_validation_receipt_ids"] = release_validation_receipt_ids
        claim["provenance_lock"] = provenance_lock
        claim["provenance_lock_sha256"] = provenance_lock_sha256

        all_lock_sha256s.append(provenance_lock_sha256)
        all_ontology_snapshot_ids.extend(semantic_ontology_snapshot_ids)
        all_graph_snapshot_ids_for_claims.extend(semantic_graph_snapshot_ids)
        all_reranker_artifact_ids.extend(retrieval_reranker_artifact_ids)
        all_release_ids.extend(claim_release_ids)
        all_audit_bundle_ids.extend(release_audit_bundle_ids)
        all_receipt_ids.extend(release_validation_receipt_ids)

    draft_payload["semantic_ontology_snapshot_ids"] = _id_str_values(all_ontology_snapshot_ids)
    draft_payload["semantic_graph_snapshot_ids"] = _id_str_values(all_graph_snapshot_ids_for_claims)
    draft_payload["retrieval_reranker_artifact_ids"] = _id_str_values(all_reranker_artifact_ids)
    draft_payload["search_harness_release_ids"] = _id_str_values(all_release_ids)
    draft_payload["release_audit_bundle_ids"] = _id_str_values(all_audit_bundle_ids)
    draft_payload["release_validation_receipt_ids"] = _id_str_values(all_receipt_ids)
    draft_payload["provenance_lock_sha256s"] = _string_values(all_lock_sha256s)
    claim_count = len(draft_payload.get("claims") or [])
    draft_payload["provenance_lock_summary"] = {
        "schema_name": "technical_report_provenance_lock_summary",
        "schema_version": "1.0",
        "claim_count": claim_count,
        "claims_with_provenance_lock_count": len(
            [
                claim
                for claim in draft_payload.get("claims") or []
                if claim.get("provenance_lock_sha256")
            ]
        ),
        "source_search_request_result_id_count": len(
            _id_str_values(
                result_id
                for claim in draft_payload.get("claims") or []
                for result_id in (claim.get("source_search_request_result_ids") or [])
            )
        ),
        "semantic_ontology_snapshot_id_count": len(draft_payload["semantic_ontology_snapshot_ids"]),
        "semantic_graph_snapshot_id_count": len(draft_payload["semantic_graph_snapshot_ids"]),
        "retrieval_reranker_artifact_id_count": len(
            draft_payload["retrieval_reranker_artifact_ids"]
        ),
        "search_harness_release_id_count": len(draft_payload["search_harness_release_ids"]),
        "release_audit_bundle_id_count": len(draft_payload["release_audit_bundle_ids"]),
        "release_validation_receipt_id_count": len(draft_payload["release_validation_receipt_ids"]),
    }


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
                "source_search_request_ids": _string_values(
                    claim.get("source_search_request_ids") or []
                ),
                "source_search_request_result_ids": _string_values(
                    claim.get("source_search_request_result_ids") or []
                ),
                "source_evidence_package_export_ids": _string_values(
                    claim.get("source_evidence_package_export_ids") or []
                ),
                "source_evidence_package_sha256s": _string_values(
                    claim.get("source_evidence_package_sha256s") or []
                ),
                "source_evidence_trace_sha256s": _string_values(
                    claim.get("source_evidence_trace_sha256s") or []
                ),
                "semantic_ontology_snapshot_ids": _string_values(
                    claim.get("semantic_ontology_snapshot_ids") or []
                ),
                "semantic_graph_snapshot_ids": _string_values(
                    claim.get("semantic_graph_snapshot_ids") or []
                ),
                "retrieval_reranker_artifact_ids": _string_values(
                    claim.get("retrieval_reranker_artifact_ids") or []
                ),
                "search_harness_release_ids": _string_values(
                    claim.get("search_harness_release_ids") or []
                ),
                "release_audit_bundle_ids": _string_values(
                    claim.get("release_audit_bundle_ids") or []
                ),
                "release_validation_receipt_ids": _string_values(
                    claim.get("release_validation_receipt_ids") or []
                ),
                "provenance_lock": dict(claim.get("provenance_lock") or {}),
                "provenance_lock_sha256": claim.get("provenance_lock_sha256"),
                "support_verdict": claim.get("support_verdict"),
                "support_score": claim.get("support_score"),
                "support_judge_run_id": str(claim.get("support_judge_run_id") or "") or None,
                "support_judgment": dict(claim.get("support_judgment") or {}),
                "support_judgment_sha256": claim.get("support_judgment_sha256"),
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
    _apply_technical_report_claim_provenance_locks(session, draft_payload)
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
                source_search_request_ids_json=list(derivation["source_search_request_ids"]),
                source_search_request_result_ids_json=list(
                    derivation["source_search_request_result_ids"]
                ),
                source_evidence_package_export_ids_json=list(
                    derivation["source_evidence_package_export_ids"]
                ),
                source_evidence_package_sha256s_json=list(
                    derivation["source_evidence_package_sha256s"]
                ),
                source_evidence_trace_sha256s_json=list(
                    derivation["source_evidence_trace_sha256s"]
                ),
                semantic_ontology_snapshot_ids_json=list(
                    derivation["semantic_ontology_snapshot_ids"]
                ),
                semantic_graph_snapshot_ids_json=list(derivation["semantic_graph_snapshot_ids"]),
                retrieval_reranker_artifact_ids_json=list(
                    derivation["retrieval_reranker_artifact_ids"]
                ),
                search_harness_release_ids_json=list(derivation["search_harness_release_ids"]),
                release_audit_bundle_ids_json=list(derivation["release_audit_bundle_ids"]),
                release_validation_receipt_ids_json=list(
                    derivation["release_validation_receipt_ids"]
                ),
                provenance_lock_json=dict(derivation["provenance_lock"]),
                provenance_lock_sha256=derivation.get("provenance_lock_sha256"),
                support_verdict=derivation.get("support_verdict"),
                support_score=derivation.get("support_score"),
                support_judge_run_id=_uuid_or_none(derivation.get("support_judge_run_id")),
                support_judgment_json=dict(derivation.get("support_judgment") or {}),
                support_judgment_sha256=derivation.get("support_judgment_sha256"),
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
        "source_search_request_ids": row.source_search_request_ids_json or [],
        "source_search_request_result_ids": row.source_search_request_result_ids_json or [],
        "source_evidence_package_export_ids": (row.source_evidence_package_export_ids_json or []),
        "source_evidence_package_sha256s": row.source_evidence_package_sha256s_json or [],
        "source_evidence_trace_sha256s": row.source_evidence_trace_sha256s_json or [],
        "semantic_ontology_snapshot_ids": row.semantic_ontology_snapshot_ids_json or [],
        "semantic_graph_snapshot_ids": row.semantic_graph_snapshot_ids_json or [],
        "retrieval_reranker_artifact_ids": row.retrieval_reranker_artifact_ids_json or [],
        "search_harness_release_ids": row.search_harness_release_ids_json or [],
        "release_audit_bundle_ids": row.release_audit_bundle_ids_json or [],
        "release_validation_receipt_ids": row.release_validation_receipt_ids_json or [],
        "provenance_lock": row.provenance_lock_json or {},
        "provenance_lock_sha256": row.provenance_lock_sha256,
        "support_verdict": row.support_verdict,
        "support_score": row.support_score,
        "support_judge_run_id": row.support_judge_run_id,
        "support_judgment": row.support_judgment_json or {},
        "support_judgment_sha256": row.support_judgment_sha256,
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
        "payload_sha256": payload_sha256(row.payload_json or {}),
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


def _context_pack_eval_task_ids_for_harness(session: Session, harness_task_id: UUID) -> list[UUID]:
    task_ids = list(
        session.scalars(
            select(AgentTask.id)
            .join(AgentTaskDependency, AgentTaskDependency.task_id == AgentTask.id)
            .where(
                AgentTask.task_type == "evaluate_document_generation_context_pack",
                AgentTaskDependency.depends_on_task_id == harness_task_id,
                AgentTaskDependency.dependency_kind == "target_task",
            )
            .order_by(AgentTask.created_at.asc(), AgentTask.id.asc())
        )
    )
    verification_task_ids = list(
        session.scalars(
            select(AgentTaskVerification.verification_task_id)
            .where(
                AgentTaskVerification.target_task_id == harness_task_id,
                AgentTaskVerification.verifier_type == DOCUMENT_GENERATION_CONTEXT_PACK_GATE,
                AgentTaskVerification.verification_task_id.is_not(None),
            )
            .order_by(AgentTaskVerification.created_at.asc(), AgentTaskVerification.id.asc())
        )
    )
    return list(
        dict.fromkeys(
            [
                *task_ids,
                *[task_id for task_id in verification_task_ids if task_id],
            ]
        )
    )


def _context_pack_verification_rows(
    session: Session,
    *,
    harness_task_id: UUID | None,
    eval_task_ids: list[UUID],
) -> list[AgentTaskVerification]:
    filters = [AgentTaskVerification.verifier_type == DOCUMENT_GENERATION_CONTEXT_PACK_GATE]
    if harness_task_id is not None and eval_task_ids:
        filters.append(
            or_(
                AgentTaskVerification.target_task_id == harness_task_id,
                AgentTaskVerification.verification_task_id.in_(eval_task_ids),
            )
        )
    elif harness_task_id is not None:
        filters.append(AgentTaskVerification.target_task_id == harness_task_id)
    elif eval_task_ids:
        filters.append(AgentTaskVerification.verification_task_id.in_(eval_task_ids))
    else:
        return []
    return list(
        session.scalars(
            select(AgentTaskVerification)
            .where(*filters)
            .order_by(AgentTaskVerification.created_at.asc(), AgentTaskVerification.id.asc())
        )
    )


def _verification_check(row: AgentTaskVerification, check_key: str) -> dict[str, Any] | None:
    details = row.details_json or {}
    for check in details.get("checks") or []:
        if isinstance(check, dict) and check.get("check_key") == check_key:
            return dict(check)
    return None


def _verification_check_passed(row: AgentTaskVerification, check_key: str) -> bool:
    check = _verification_check(row, check_key)
    return check is not None and check.get("passed") is True


def _release_readiness_db_gate_payload(
    verification_rows: list[AgentTaskVerification],
) -> dict[str, Any]:
    for row in reversed(verification_rows):
        check = _verification_check(row, RELEASE_READINESS_DB_GATE_CHECK_KEY)
        if check is None:
            continue
        observed = check.get("observed")
        summary = dict(observed) if isinstance(observed, dict) else {}
        failure_count = _int_or_none(summary.get("failure_count")) or 0
        source_search_request_count = _int_or_none(summary.get("source_search_request_count")) or 0
        verified_request_count = _int_or_none(summary.get("verified_request_count")) or 0
        complete = (
            check.get("passed") is True
            and summary.get("complete") is True
            and failure_count == 0
            and (
                source_search_request_count == 0
                or verified_request_count == source_search_request_count
            )
        )
        return {
            "schema_name": "technical_report_release_readiness_db_gate",
            "schema_version": "1.0",
            "check_key": RELEASE_READINESS_DB_GATE_CHECK_KEY,
            "verification_id": str(row.id),
            "verification_task_id": (
                str(row.verification_task_id) if row.verification_task_id else None
            ),
            "passed": check.get("passed") is True,
            "required": check.get("required"),
            "source_search_request_count": source_search_request_count,
            "verified_request_count": verified_request_count,
            "failure_count": failure_count,
            "summary": summary,
            "complete": complete,
        }
    return {
        "schema_name": "technical_report_release_readiness_db_gate",
        "schema_version": "1.0",
        "check_key": RELEASE_READINESS_DB_GATE_CHECK_KEY,
        "verification_id": None,
        "verification_task_id": None,
        "passed": False,
        "required": None,
        "source_search_request_count": 0,
        "verified_request_count": 0,
        "failure_count": 0,
        "summary": {},
        "complete": False,
    }


def _context_pack_sha256s_from_artifacts(
    context_pack_artifacts: list[AgentTaskArtifact],
    evaluation_artifacts: list[AgentTaskArtifact],
    verification_rows: list[AgentTaskVerification],
) -> list[str]:
    values: list[Any] = []
    for artifact in context_pack_artifacts:
        values.append((artifact.payload_json or {}).get("context_pack_sha256"))
    for artifact in evaluation_artifacts:
        values.append((artifact.payload_json or {}).get("context_pack_sha256"))
    for row in verification_rows:
        values.append((row.details_json or {}).get("context_pack_sha256"))
    return _string_values(values)


def _context_pack_audit_refs(payload: dict[str, Any]) -> dict[str, Any]:
    audit_refs = payload.get("audit_refs") or {}
    return audit_refs if isinstance(audit_refs, dict) else {}


def _release_readiness_ref_key(ref: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(ref.get("search_request_id") or ""),
        str(ref.get("search_harness_release_id") or ""),
        str(ref.get("assessment_id") or ref.get("selection_status") or ""),
    )


def _release_readiness_assessment_ready(ref: dict[str, Any]) -> bool:
    integrity = ref.get("integrity") if isinstance(ref.get("integrity"), dict) else {}
    return (
        ref.get("selection_status") == "ready_integrity_complete"
        and ref.get("ready") is True
        and ref.get("readiness_status") == "ready"
        and bool(ref.get("assessment_id"))
        and bool(ref.get("assessment_payload_sha256"))
        and integrity.get("complete") is True
    )


def _release_readiness_refs_from_context_pack_artifacts(
    context_pack_artifacts: list[AgentTaskArtifact],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for artifact in context_pack_artifacts:
        payload = artifact.payload_json or {}
        for ref in _context_pack_audit_refs(payload).get("release_readiness_assessments") or []:
            if isinstance(ref, dict):
                refs.append(dict(ref))
    return list({_release_readiness_ref_key(ref): ref for ref in refs}.values())


def _source_search_request_ids_from_context_pack_artifacts(
    context_pack_artifacts: list[AgentTaskArtifact],
) -> list[str]:
    values: list[Any] = []
    for artifact in context_pack_artifacts:
        payload = artifact.payload_json or {}
        values.extend(_context_pack_audit_refs(payload).get("source_search_request_ids") or [])
    return _string_values(values)


def _release_readiness_audit_summary(
    *,
    source_search_request_ids: list[str],
    refs: list[dict[str, Any]],
) -> dict[str, Any]:
    refs_by_request_id = {
        str(ref.get("search_request_id")): ref for ref in refs if ref.get("search_request_id")
    }
    ready_request_ids = {
        request_id
        for request_id, ref in refs_by_request_id.items()
        if _release_readiness_assessment_ready(ref)
    }
    missing_source_search_request_ids = [
        request_id
        for request_id in source_search_request_ids
        if request_id not in ready_request_ids
    ]
    failed_refs = [
        ref
        for ref in refs
        if ref.get("search_request_id") in source_search_request_ids
        and not _release_readiness_assessment_ready(ref)
    ]
    failed_selection_status_counts: dict[str, int] = {}
    for ref in failed_refs:
        status = str(ref.get("selection_status") or "unknown")
        failed_selection_status_counts[status] = failed_selection_status_counts.get(status, 0) + 1
    return {
        "source_search_request_count": len(source_search_request_ids),
        "readiness_assessment_ref_count": len(refs),
        "ready_assessment_ref_count": len(ready_request_ids),
        "failed_ref_count": len(failed_refs),
        "missing_source_search_request_ids": missing_source_search_request_ids,
        "failed_selection_status_counts": failed_selection_status_counts,
    }


def _technical_report_context_pack_audit_payload(
    *,
    harness_task_id: UUID | None,
    eval_task_ids: list[UUID],
    artifacts: list[AgentTaskArtifact],
    verification_rows: list[AgentTaskVerification],
    operator_runs: list[KnowledgeOperatorRun],
) -> dict[str, Any]:
    eval_task_id_set = set(eval_task_ids)
    context_pack_artifacts = [
        row
        for row in artifacts
        if row.artifact_kind == DOCUMENT_GENERATION_CONTEXT_PACK_ARTIFACT_KIND
    ]
    evaluation_artifacts = [
        row
        for row in artifacts
        if row.artifact_kind == DOCUMENT_GENERATION_CONTEXT_PACK_EVALUATION_ARTIFACT_KIND
    ]
    context_pack_operator_runs = [
        row
        for row in operator_runs
        if row.operator_name == DOCUMENT_GENERATION_CONTEXT_PACK_EVALUATION_OPERATOR
        or (row.agent_task_id is not None and row.agent_task_id in eval_task_id_set)
    ]
    sha256s = _context_pack_sha256s_from_artifacts(
        context_pack_artifacts,
        evaluation_artifacts,
        verification_rows,
    )
    release_readiness_assessments = _release_readiness_refs_from_context_pack_artifacts(
        context_pack_artifacts
    )
    source_search_request_ids = _source_search_request_ids_from_context_pack_artifacts(
        context_pack_artifacts
    )
    release_readiness_summary = _release_readiness_audit_summary(
        source_search_request_ids=source_search_request_ids,
        refs=release_readiness_assessments,
    )
    release_readiness_db_gate = _release_readiness_db_gate_payload(verification_rows)
    release_readiness_db_summary = dict(release_readiness_db_gate.get("summary") or {})
    latest_verification = verification_rows[-1] if verification_rows else None
    integrity = {
        "has_context_pack_artifact": bool(context_pack_artifacts),
        "has_context_pack_evaluation_task": bool(eval_task_ids),
        "has_context_pack_evaluation_artifact": bool(evaluation_artifacts),
        "has_context_pack_verifier_record": bool(verification_rows),
        "has_context_pack_evaluation_operator_run": bool(context_pack_operator_runs),
        "latest_context_pack_evaluation_passed": (
            latest_verification.outcome == "passed" if latest_verification is not None else False
        ),
        "context_pack_hash_verified": any(
            _verification_check_passed(row, "context_pack_hash_integrity")
            for row in verification_rows
        ),
        "context_pack_sha256_consistent": bool(sha256s) and len(sha256s) == 1,
        "has_release_readiness_assessments": bool(release_readiness_assessments),
        "release_readiness_assessments_cover_source_requests": (
            not source_search_request_ids
            or not release_readiness_summary["missing_source_search_request_ids"]
        ),
        "release_readiness_assessments_ready": (
            release_readiness_summary["failed_ref_count"] == 0
            and (
                not source_search_request_ids
                or release_readiness_summary["ready_assessment_ref_count"]
                == len(source_search_request_ids)
            )
        ),
        "release_readiness_assessment_integrity_verified": any(
            _verification_check_passed(row, RELEASE_READINESS_DB_GATE_CHECK_KEY)
            for row in verification_rows
        ),
        "release_readiness_db_gate_verified": release_readiness_db_gate["passed"] is True,
        "release_readiness_db_gate_complete": release_readiness_db_gate["complete"] is True,
        "release_readiness_db_covers_source_requests": (
            release_readiness_db_gate["source_search_request_count"]
            == len(source_search_request_ids)
            and (
                not source_search_request_ids
                or release_readiness_db_gate["verified_request_count"]
                == len(source_search_request_ids)
            )
        ),
    }
    integrity["complete"] = all(integrity.values())
    return {
        "schema_name": "technical_report_context_pack_audit",
        "schema_version": "1.0",
        "harness_task_id": str(harness_task_id) if harness_task_id is not None else None,
        "evaluation_task_ids": _string_values(eval_task_ids),
        "context_pack_sha256s": sha256s,
        "context_pack_artifacts": [_artifact_payload(row) for row in context_pack_artifacts],
        "evaluation_artifacts": [_artifact_payload(row) for row in evaluation_artifacts],
        "verifications": [_verification_payload(row) for row in verification_rows],
        "operator_runs": [_operator_run_summary(row) for row in context_pack_operator_runs],
        "release_readiness_assessments": release_readiness_assessments,
        "release_readiness_summary": release_readiness_summary,
        "release_readiness_db_gate": release_readiness_db_gate,
        "release_readiness_db_summary": release_readiness_db_summary,
        "integrity": integrity,
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


def _empty_claim_support_policy_change_impact_summary() -> dict[str, Any]:
    waiver_lifecycle = {
        "related_waiver_count": 0,
        "unresolved_waiver_count": 0,
        "closed_waiver_count": 0,
        "invalid_waiver_closure_count": 0,
        "waiver_closure_integrity_verified": True,
        "clear": True,
    }
    replay_alert_fixture_corpus = {
        "related_snapshot_count": 0,
        "invalid_snapshot_governance_count": 0,
        "governance_integrity_verified": True,
        "trace_complete": True,
        "active_replay_alert_fixture_corpus_snapshot_id": None,
        "active_replay_alert_fixture_corpus_sha256": None,
        "invalid_snapshot_ids": [],
        "snapshots": [],
    }
    return {
        "related_count": 0,
        "open_count": 0,
        "closed_count": 0,
        "blocked_count": 0,
        "replay_status_counts": {},
        "waiver_lifecycle": waiver_lifecycle,
        "replay_alert_fixture_corpus": replay_alert_fixture_corpus,
        "clear": True,
        "impacts": [],
    }


def _claim_support_policy_change_impact_refs(
    session: Session,
    exports: list[EvidencePackageExport],
) -> dict[str, set[str]]:
    report_export_ids = [row.id for row in exports if row.package_kind == "technical_report_claims"]
    if not report_export_ids:
        return {
            "claim_derivation_ids": set(),
            "draft_task_ids": set(),
            "verification_task_ids": set(),
        }
    derivations = list(
        session.scalars(
            select(ClaimEvidenceDerivation)
            .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(report_export_ids))
            .order_by(ClaimEvidenceDerivation.created_at.asc())
        )
    )
    draft_task_ids = {
        str(row.agent_task_id) for row in derivations if row.agent_task_id is not None
    }
    draft_task_ids.update(
        str(row.agent_task_id)
        for row in exports
        if row.package_kind == "technical_report_claims" and row.agent_task_id is not None
    )
    verification_rows = (
        list(
            session.scalars(
                select(AgentTaskVerification)
                .where(
                    AgentTaskVerification.target_task_id.in_(_uuid_values(draft_task_ids)),
                    AgentTaskVerification.verifier_type == "technical_report_gate",
                )
                .order_by(AgentTaskVerification.created_at.asc())
            )
        )
        if draft_task_ids
        else []
    )
    return {
        "claim_derivation_ids": {str(row.id) for row in derivations},
        "draft_task_ids": draft_task_ids,
        "verification_task_ids": {
            str(row.verification_task_id)
            for row in verification_rows
            if row.verification_task_id is not None
        },
    }


def _claim_support_policy_change_impact_events_by_row(
    session: Session,
    rows: list[ClaimSupportPolicyChangeImpact],
    *,
    event_kind: str = CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_CLOSED_EVENT_KIND,
) -> dict[UUID, list[SemanticGovernanceEvent]]:
    row_ids = [row.id for row in rows]
    if not row_ids:
        return {}
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.subject_table == "claim_support_policy_change_impacts",
                SemanticGovernanceEvent.subject_id.in_(row_ids),
                SemanticGovernanceEvent.event_kind == event_kind,
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]] = {}
    for event in events:
        if event.subject_id is not None:
            events_by_row.setdefault(event.subject_id, []).append(event)
    return events_by_row


def _claim_support_policy_fixture_promotion_events_by_impact(
    session: Session,
    rows: list[ClaimSupportPolicyChangeImpact],
) -> dict[UUID, list[SemanticGovernanceEvent]]:
    row_ids = {str(row.id) for row in rows}
    if not row_ids:
        return {}
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]] = {}
    rows_by_id = {str(row.id): row for row in rows}
    for event in events:
        promotion_payload = (event.event_payload_json or {}).get(
            "claim_support_policy_impact_fixture_promotion"
        ) or {}
        source_change_impact_ids = {
            str(value) for value in promotion_payload.get("source_change_impact_ids") or [] if value
        }
        for row_id in sorted(source_change_impact_ids & row_ids):
            events_by_row.setdefault(rows_by_id[row_id].id, []).append(event)
    return events_by_row


def _fixture_promotion_event_payload(event: SemanticGovernanceEvent) -> dict[str, Any]:
    promotion_payload = (event.event_payload_json or {}).get(
        "claim_support_policy_impact_fixture_promotion"
    ) or {}
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "receipt_sha256": event.receipt_sha256,
        "agent_task_artifact_id": str(event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None,
        "payload_sha256": event.payload_sha256,
        "fixture_set_id": promotion_payload.get("fixture_set_id"),
        "fixture_set_name": promotion_payload.get("fixture_set_name"),
        "fixture_set_version": promotion_payload.get("fixture_set_version"),
        "fixture_set_sha256": promotion_payload.get("fixture_set_sha256"),
        "candidate_count": promotion_payload.get("candidate_count"),
        "source_escalation_event_ids": list(
            promotion_payload.get("source_escalation_event_ids") or []
        ),
    }


def _claim_support_replay_alert_waiver_closure_events_by_impact(
    session: Session,
    rows: list[ClaimSupportPolicyChangeImpact],
) -> dict[UUID, list[SemanticGovernanceEvent]]:
    row_ids = {str(row.id) for row in rows}
    if not row_ids:
        return {}
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]] = {}
    rows_by_id = {str(row.id): row for row in rows}
    for event in events:
        closure_payload = (event.event_payload_json or {}).get(
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        ) or {}
        source_change_impact_ids = {
            str(value) for value in closure_payload.get("source_change_impact_ids") or [] if value
        }
        for row_id in sorted(source_change_impact_ids & row_ids):
            events_by_row.setdefault(rows_by_id[row_id].id, []).append(event)
    return events_by_row


def _waiver_closure_event_integrity(
    session: Session,
    event: SemanticGovernanceEvent,
    closure_payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    receipt_sha256 = str(closure_payload.get("receipt_sha256") or "")
    receipt_basis = dict(closure_payload)
    receipt_basis.pop("receipt_sha256", None)
    if not receipt_sha256 or payload_sha256(receipt_basis) != receipt_sha256:
        failures.append("closure_receipt_hash_mismatch")
    if event.receipt_sha256 != receipt_sha256:
        failures.append("event_receipt_hash_mismatch")

    closure_artifact = (
        session.get(AgentTaskArtifact, event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None
    )
    if closure_artifact is None:
        failures.append("closure_artifact_missing")
    elif (
        closure_artifact.artifact_kind
        != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSURE_ARTIFACT_KIND
    ):
        failures.append("closure_artifact_kind_mismatch")
    elif closure_artifact.payload_json.get("receipt_sha256") != receipt_sha256:
        failures.append("closure_artifact_receipt_mismatch")

    waiver_artifact_id = closure_payload.get("waiver_artifact_id")
    try:
        waiver_artifact_uuid = UUID(str(waiver_artifact_id)) if waiver_artifact_id else None
    except (TypeError, ValueError):
        waiver_artifact_uuid = None
    waiver_artifact = (
        session.get(AgentTaskArtifact, waiver_artifact_uuid) if waiver_artifact_uuid else None
    )
    if waiver_artifact is None:
        failures.append("waiver_artifact_missing")
    elif (
        waiver_artifact.artifact_kind
        != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_ARTIFACT_KIND
    ):
        failures.append("waiver_artifact_kind_mismatch")
    elif waiver_artifact.payload_json.get("waiver_sha256") != closure_payload.get("waiver_sha256"):
        failures.append("waiver_artifact_hash_mismatch")

    promotion_artifact_id = closure_payload.get("promotion_artifact_id")
    try:
        promotion_artifact_uuid = (
            UUID(str(promotion_artifact_id)) if promotion_artifact_id else None
        )
    except (TypeError, ValueError):
        promotion_artifact_uuid = None
    promotion_event_id = closure_payload.get("promotion_event_id")
    try:
        promotion_event_uuid = UUID(str(promotion_event_id)) if promotion_event_id else None
    except (TypeError, ValueError):
        promotion_event_uuid = None
    promotion_artifact = (
        session.get(AgentTaskArtifact, promotion_artifact_uuid) if promotion_artifact_uuid else None
    )
    promotion_event = (
        session.get(SemanticGovernanceEvent, promotion_event_uuid) if promotion_event_uuid else None
    )
    if promotion_artifact is None:
        failures.append("promotion_artifact_missing")
    elif (
        promotion_artifact.artifact_kind
        != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND
    ):
        failures.append("promotion_artifact_kind_mismatch")
    elif promotion_artifact.payload_json.get("receipt_sha256") != closure_payload.get(
        "promotion_receipt_sha256"
    ):
        failures.append("promotion_artifact_receipt_mismatch")
    if promotion_event is None:
        failures.append("promotion_event_missing")
    elif promotion_event.event_kind != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND:
        failures.append("promotion_event_kind_mismatch")
    elif promotion_event.agent_task_artifact_id != promotion_artifact_uuid:
        failures.append("promotion_event_artifact_mismatch")
    elif promotion_event.receipt_sha256 != closure_payload.get("promotion_receipt_sha256"):
        failures.append("promotion_event_receipt_mismatch")

    waived_event_ids = set(_string_values(closure_payload.get("waived_escalation_event_ids") or []))
    covered_event_ids = set(
        _string_values(closure_payload.get("covered_escalation_event_ids") or [])
    )
    if not waived_event_ids:
        failures.append("waived_escalation_event_set_missing")
    if not covered_event_ids:
        failures.append("covered_escalation_event_set_missing")
    if waived_event_ids and not waived_event_ids.issubset(covered_event_ids):
        failures.append("covered_escalation_event_set_incomplete")

    raw_coverage_promotion_artifact_ids = set(
        _string_values(closure_payload.get("coverage_promotion_artifact_ids") or [])
    )
    coverage_promotion_artifact_ids = set(_uuid_values(raw_coverage_promotion_artifact_ids))
    if raw_coverage_promotion_artifact_ids and len(coverage_promotion_artifact_ids) != len(
        raw_coverage_promotion_artifact_ids
    ):
        failures.append("coverage_promotion_artifact_id_invalid")
    if promotion_artifact_uuid is not None:
        coverage_promotion_artifact_ids.add(promotion_artifact_uuid)
    promotion_source_escalation_event_ids: set[str] = set()
    actual_coverage_receipt_sha256s: set[str] = set()
    for coverage_artifact_id in sorted(coverage_promotion_artifact_ids, key=str):
        coverage_artifact = session.get(AgentTaskArtifact, coverage_artifact_id)
        if coverage_artifact is None:
            failures.append("coverage_promotion_artifact_missing")
            continue
        if (
            coverage_artifact.artifact_kind
            != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND
        ):
            failures.append("coverage_promotion_artifact_kind_mismatch")
            continue
        receipt_sha = str(coverage_artifact.payload_json.get("receipt_sha256") or "")
        if receipt_sha:
            actual_coverage_receipt_sha256s.add(receipt_sha)
        promotion_source_escalation_event_ids.update(
            _string_values(coverage_artifact.payload_json.get("source_escalation_event_ids") or [])
        )
    declared_coverage_receipt_sha256s = set(
        _string_values(closure_payload.get("coverage_promotion_receipt_sha256s") or [])
    )
    if (
        declared_coverage_receipt_sha256s
        and declared_coverage_receipt_sha256s != actual_coverage_receipt_sha256s
    ):
        failures.append("coverage_promotion_receipt_set_mismatch")
    if covered_event_ids and not covered_event_ids.issubset(promotion_source_escalation_event_ids):
        failures.append("covered_escalation_event_not_in_promotion")
    raw_coverage_promotion_event_ids = set(
        _string_values(closure_payload.get("coverage_promotion_event_ids") or [])
    )
    declared_coverage_event_ids = set(_uuid_values(raw_coverage_promotion_event_ids))
    if raw_coverage_promotion_event_ids and len(declared_coverage_event_ids) != len(
        raw_coverage_promotion_event_ids
    ):
        failures.append("coverage_promotion_event_id_invalid")
    if not declared_coverage_event_ids and promotion_event_uuid is not None:
        declared_coverage_event_ids.add(promotion_event_uuid)
    coverage_event_artifact_ids: set[UUID] = set()
    coverage_event_receipt_sha256s: set[str] = set()
    for coverage_event_id in sorted(declared_coverage_event_ids, key=str):
        coverage_event = session.get(SemanticGovernanceEvent, coverage_event_id)
        if coverage_event is None:
            failures.append("coverage_promotion_event_missing")
            continue
        if coverage_event.event_kind != CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND:
            failures.append("coverage_promotion_event_kind_mismatch")
            continue
        if coverage_event.agent_task_artifact_id is None:
            failures.append("coverage_promotion_event_artifact_missing")
            continue
        coverage_event_artifact_ids.add(coverage_event.agent_task_artifact_id)
        receipt_sha = str(coverage_event.receipt_sha256 or "")
        if receipt_sha:
            coverage_event_receipt_sha256s.add(receipt_sha)
        if receipt_sha and receipt_sha not in actual_coverage_receipt_sha256s:
            failures.append("coverage_promotion_event_receipt_mismatch")
    if (
        coverage_event_artifact_ids
        and coverage_event_artifact_ids != coverage_promotion_artifact_ids
    ):
        failures.append("coverage_promotion_event_artifact_set_mismatch")
    if (
        declared_coverage_receipt_sha256s
        and coverage_event_receipt_sha256s
        and declared_coverage_receipt_sha256s != coverage_event_receipt_sha256s
    ):
        failures.append("coverage_promotion_event_receipt_set_mismatch")
    return not failures, failures


def _waiver_closure_event_payload(
    session: Session,
    event: SemanticGovernanceEvent,
) -> dict[str, Any]:
    closure_payload = (event.event_payload_json or {}).get(
        "claim_support_replay_alert_fixture_coverage_waiver_closure"
    ) or {}
    integrity_verified, integrity_failures = _waiver_closure_event_integrity(
        session,
        event,
        closure_payload,
    )
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "receipt_sha256": event.receipt_sha256,
        "agent_task_artifact_id": str(event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None,
        "payload_sha256": event.payload_sha256,
        "waiver_artifact_id": closure_payload.get("waiver_artifact_id"),
        "waiver_sha256": closure_payload.get("waiver_sha256"),
        "closure_status": closure_payload.get("closure_status"),
        "promotion_event_id": closure_payload.get("promotion_event_id"),
        "promotion_receipt_sha256": closure_payload.get("promotion_receipt_sha256"),
        "promotion_artifact_id": closure_payload.get("promotion_artifact_id"),
        "coverage_promotion_event_ids": list(
            closure_payload.get("coverage_promotion_event_ids") or []
        ),
        "coverage_promotion_artifact_ids": list(
            closure_payload.get("coverage_promotion_artifact_ids") or []
        ),
        "coverage_promotion_receipt_sha256s": list(
            closure_payload.get("coverage_promotion_receipt_sha256s") or []
        ),
        "fixture_set_id": closure_payload.get("fixture_set_id"),
        "fixture_set_sha256": closure_payload.get("fixture_set_sha256"),
        "covered_escalation_event_ids": list(
            closure_payload.get("covered_escalation_event_ids") or []
        ),
        "integrity_verified": integrity_verified,
        "integrity_failures": integrity_failures,
    }


def _replay_alert_fixture_corpus_snapshot_governance_integrity(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> dict[str, Any]:
    failures: list[str] = []
    snapshot_payload = dict(snapshot.snapshot_payload_json or {})
    if payload_sha256(snapshot_payload) != snapshot.snapshot_sha256:
        failures.append("snapshot_payload_hash_mismatch")
    db_rows = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .order_by(
                ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc(),
                ClaimSupportReplayAlertFixtureCorpusRow.id.asc(),
            )
        )
    )
    declared_rows = [
        dict(row) for row in snapshot_payload.get("rows") or [] if isinstance(row, dict)
    ]
    db_row_payloads = [
        {
            "case_id": row.case_id,
            "case_identity_sha256": row.case_identity_sha256,
            "fixture_sha256": row.fixture_sha256,
            "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
            "promotion_event_id": (str(row.promotion_event_id) if row.promotion_event_id else None),
            "promotion_artifact_id": (
                str(row.promotion_artifact_id) if row.promotion_artifact_id else None
            ),
            "promotion_receipt_sha256": row.promotion_receipt_sha256,
            "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
            "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        }
        for row in db_rows
    ]
    if len(declared_rows) != snapshot.fixture_count:
        failures.append("snapshot_payload_row_count_mismatch")
    if len(db_rows) != snapshot.fixture_count:
        failures.append("snapshot_db_row_count_mismatch")
    if declared_rows != db_row_payloads:
        failures.append("snapshot_db_row_payload_mismatch")
    fixture_hash_mismatch_count = sum(
        1 for row in db_rows if payload_sha256(row.fixture_json or {}) != row.fixture_sha256
    )
    if fixture_hash_mismatch_count:
        failures.append("snapshot_db_fixture_hash_mismatch")
    event = (
        session.get(SemanticGovernanceEvent, snapshot.semantic_governance_event_id)
        if snapshot.semantic_governance_event_id is not None
        else None
    )
    artifact = (
        session.get(AgentTaskArtifact, snapshot.governance_artifact_id)
        if snapshot.governance_artifact_id is not None
        else None
    )
    if event is None:
        failures.append("snapshot_governance_event_missing")
    elif event.event_kind != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND:
        failures.append("snapshot_governance_event_kind_mismatch")
    elif (
        event.subject_table != "claim_support_replay_alert_fixture_corpus_snapshots"
        or event.subject_id != snapshot.id
    ):
        failures.append("snapshot_governance_event_subject_mismatch")
    if artifact is None:
        failures.append("snapshot_governance_artifact_missing")
    elif artifact.artifact_kind != CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND:
        failures.append("snapshot_governance_artifact_kind_mismatch")

    if event is not None:
        event_payload = dict(
            (event.event_payload_json or {}).get(
                CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_PAYLOAD_KEY
            )
            or {}
        )
        receipt_sha256 = str(event_payload.get("receipt_sha256") or "")
        event_basis = dict(event_payload)
        event_basis.pop("receipt_sha256", None)
        if event.receipt_sha256 != snapshot.governance_receipt_sha256:
            failures.append("snapshot_governance_event_receipt_mismatch")
        if event.receipt_sha256 != receipt_sha256:
            failures.append("snapshot_governance_event_payload_receipt_mismatch")
        if not receipt_sha256 or payload_sha256(event_basis) != receipt_sha256:
            failures.append("snapshot_governance_event_payload_hash_mismatch")
        if event_payload.get("snapshot_id") != str(snapshot.id):
            failures.append("snapshot_governance_event_snapshot_id_mismatch")
        if event_payload.get("snapshot_sha256") != snapshot.snapshot_sha256:
            failures.append("snapshot_governance_event_snapshot_hash_mismatch")
    if artifact is not None:
        artifact_payload = dict(artifact.payload_json or {})
        artifact_receipt_sha256 = str(artifact_payload.get("receipt_sha256") or "")
        artifact_basis = dict(artifact_payload)
        artifact_basis.pop("receipt_sha256", None)
        if artifact_receipt_sha256 != snapshot.governance_receipt_sha256:
            failures.append("snapshot_governance_artifact_receipt_mismatch")
        if not artifact_receipt_sha256 or payload_sha256(artifact_basis) != artifact_receipt_sha256:
            failures.append("snapshot_governance_artifact_hash_mismatch")
        if artifact_payload.get("snapshot_id") != str(snapshot.id):
            failures.append("snapshot_governance_artifact_snapshot_id_mismatch")
        if artifact_payload.get("snapshot_sha256") != snapshot.snapshot_sha256:
            failures.append("snapshot_governance_artifact_snapshot_hash_mismatch")
        if event is not None and event.agent_task_artifact_id != artifact.id:
            failures.append("snapshot_governance_event_artifact_mismatch")
    return {
        "complete": not failures,
        "failures": failures,
        "semantic_governance_event_id": (
            str(snapshot.semantic_governance_event_id)
            if snapshot.semantic_governance_event_id
            else None
        ),
        "governance_artifact_id": (
            str(snapshot.governance_artifact_id) if snapshot.governance_artifact_id else None
        ),
        "governance_receipt_sha256": snapshot.governance_receipt_sha256,
        "snapshot_payload_sha256": payload_sha256(snapshot_payload),
        "stored_snapshot_sha256": snapshot.snapshot_sha256,
        "declared_row_count": len(declared_rows),
        "db_row_count": len(db_rows),
        "fixture_hash_mismatch_count": fixture_hash_mismatch_count,
    }


def _replay_alert_fixture_corpus_row_payload(
    row: ClaimSupportReplayAlertFixtureCorpusRow,
) -> dict[str, Any]:
    return {
        "row_id": str(row.id),
        "snapshot_id": str(row.snapshot_id),
        "row_index": row.row_index,
        "case_id": row.case_id,
        "case_identity_sha256": row.case_identity_sha256,
        "fixture_sha256": row.fixture_sha256,
        "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
        "promotion_event_id": (str(row.promotion_event_id) if row.promotion_event_id else None),
        "promotion_artifact_id": (
            str(row.promotion_artifact_id) if row.promotion_artifact_id else None
        ),
        "promotion_receipt_sha256": row.promotion_receipt_sha256,
        "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
        "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        "replay_alert_source": dict(row.replay_alert_source_json or {}),
    }


def _replay_alert_fixture_corpus_snapshot_payload(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> dict[str, Any]:
    rows = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .order_by(
                ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc(),
                ClaimSupportReplayAlertFixtureCorpusRow.id.asc(),
            )
        )
    )
    governance_integrity = _replay_alert_fixture_corpus_snapshot_governance_integrity(
        session,
        snapshot,
    )
    return {
        "snapshot_id": str(snapshot.id),
        "snapshot_name": snapshot.snapshot_name,
        "status": snapshot.status,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "semantic_governance_event_id": (
            str(snapshot.semantic_governance_event_id)
            if snapshot.semantic_governance_event_id
            else None
        ),
        "governance_artifact_id": (
            str(snapshot.governance_artifact_id) if snapshot.governance_artifact_id else None
        ),
        "governance_receipt_sha256": snapshot.governance_receipt_sha256,
        "fixture_count": snapshot.fixture_count,
        "promotion_event_count": snapshot.promotion_event_count,
        "promotion_fixture_set_count": snapshot.promotion_fixture_set_count,
        "invalid_promotion_event_count": snapshot.invalid_promotion_event_count,
        "source_promotion_event_ids": list(snapshot.source_promotion_event_ids_json or []),
        "source_promotion_artifact_ids": list(snapshot.source_promotion_artifact_ids_json or []),
        "source_promotion_receipt_sha256s": list(
            snapshot.source_promotion_receipt_sha256s_json or []
        ),
        "source_fixture_set_ids": list(snapshot.source_fixture_set_ids_json or []),
        "source_fixture_set_sha256s": list(snapshot.source_fixture_set_sha256s_json or []),
        "source_escalation_event_ids": list(snapshot.source_escalation_event_ids_json or []),
        "invalid_promotion_event_ids": list(snapshot.invalid_promotion_event_ids_json or []),
        "invalid_promotion_events": list(
            (snapshot.snapshot_payload_json or {}).get("invalid_promotion_events") or []
        ),
        "rows": [_replay_alert_fixture_corpus_row_payload(row) for row in rows],
        "row_count": len(rows),
        "governance_integrity": governance_integrity,
        "trace_complete": bool(rows) and governance_integrity["complete"],
    }


def _claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event(
    session: Session,
    events: list[SemanticGovernanceEvent],
) -> dict[UUID, list[dict[str, Any]]]:
    event_ids = {event.id for event in events}
    if not event_ids:
        return {}
    snapshots = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusSnapshot).order_by(
                ClaimSupportReplayAlertFixtureCorpusSnapshot.created_at.asc(),
                ClaimSupportReplayAlertFixtureCorpusSnapshot.id.asc(),
            )
        )
    )
    by_event_id: dict[UUID, list[dict[str, Any]]] = {}
    for snapshot in snapshots:
        source_event_ids = {
            parsed
            for parsed in (
                _uuid_or_none_safe(value)
                for value in (snapshot.source_promotion_event_ids_json or [])
            )
            if parsed is not None
        }
        matching_event_ids = event_ids & source_event_ids
        if not matching_event_ids:
            continue
        payload = _replay_alert_fixture_corpus_snapshot_payload(session, snapshot)
        for event_id in sorted(matching_event_ids, key=str):
            by_event_id.setdefault(event_id, []).append(payload)
    return by_event_id


def _claim_support_replay_alert_waiver_lifecycle_summary(
    session: Session,
    matching_rows: list[ClaimSupportPolicyChangeImpact],
    waiver_closure_events_by_row: dict[UUID, list[SemanticGovernanceEvent]],
) -> dict[str, Any]:
    row_ids = {str(row.id) for row in matching_rows}
    row_uuids = [row.id for row in matching_rows]
    ledger_ids_from_escalations = set(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.ledger_id).where(
                ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.change_impact_id.in_(
                    row_uuids
                )
            )
        )
    )
    related_ledgers = [
        ledger
        for ledger in session.scalars(
            select(ClaimSupportReplayAlertFixtureCoverageWaiverLedger).order_by(
                ClaimSupportReplayAlertFixtureCoverageWaiverLedger.created_at.asc(),
                ClaimSupportReplayAlertFixtureCoverageWaiverLedger.id.asc(),
            )
        )
        if row_ids & {str(value) for value in (ledger.source_change_impact_ids_json or []) if value}
        or ledger.id in ledger_ids_from_escalations
    ]
    closure_events_by_id = {
        event.id: event for events in waiver_closure_events_by_row.values() for event in events
    }
    invalid_closure_event_ids: set[UUID] = set()
    for event in closure_events_by_id.values():
        closure_payload = (event.event_payload_json or {}).get(
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        ) or {}
        integrity_verified, _failures = _waiver_closure_event_integrity(
            session,
            event,
            closure_payload,
        )
        if not integrity_verified:
            invalid_closure_event_ids.add(event.id)

    for ledger in related_ledgers:
        if not ledger.coverage_complete:
            continue
        if ledger.closure_event_id is None:
            continue
        event = session.get(SemanticGovernanceEvent, ledger.closure_event_id)
        if event is None:
            invalid_closure_event_ids.add(ledger.closure_event_id)
            continue
        closure_payload = (event.event_payload_json or {}).get(
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        ) or {}
        integrity_verified, _failures = _waiver_closure_event_integrity(
            session,
            event,
            closure_payload,
        )
        if not integrity_verified:
            invalid_closure_event_ids.add(event.id)

    unresolved_ledgers = [
        ledger
        for ledger in related_ledgers
        if ledger.waived_escalation_event_count > 0 and not ledger.coverage_complete
    ]
    closed_ledgers = [
        ledger
        for ledger in related_ledgers
        if ledger.waived_escalation_event_count > 0 and ledger.coverage_complete
    ]
    invalid_closed_ledgers = [
        ledger
        for ledger in closed_ledgers
        if ledger.closure_event_id is None or ledger.closure_event_id in invalid_closure_event_ids
    ]
    invalid_waiver_closure_count = len(
        {
            *invalid_closure_event_ids,
            *[ledger.id for ledger in invalid_closed_ledgers if ledger.closure_event_id is None],
        }
    )
    waiver_closure_integrity_verified = invalid_waiver_closure_count == 0
    clear = not unresolved_ledgers and waiver_closure_integrity_verified
    return {
        "related_waiver_count": len(related_ledgers),
        "unresolved_waiver_count": len(unresolved_ledgers),
        "closed_waiver_count": len(closed_ledgers),
        "invalid_waiver_closure_count": invalid_waiver_closure_count,
        "waiver_closure_integrity_verified": waiver_closure_integrity_verified,
        "clear": clear,
        "related_waiver_ledger_ids": [str(ledger.id) for ledger in related_ledgers],
        "unresolved_waiver_ledger_ids": [str(ledger.id) for ledger in unresolved_ledgers],
        "closed_waiver_ledger_ids": [str(ledger.id) for ledger in closed_ledgers],
        "invalid_waiver_closure_event_ids": [
            str(event_id) for event_id in sorted(invalid_closure_event_ids, key=str)
        ],
    }


def _claim_support_policy_change_impact_summary(
    session: Session,
    exports: list[EvidencePackageExport],
) -> dict[str, Any]:
    refs = _claim_support_policy_change_impact_refs(session, exports)
    if not any(refs.values()):
        return _empty_claim_support_policy_change_impact_summary()
    rows = list(
        session.scalars(
            select(ClaimSupportPolicyChangeImpact).order_by(
                ClaimSupportPolicyChangeImpact.created_at.asc(),
                ClaimSupportPolicyChangeImpact.id.asc(),
            )
        )
    )
    matching_rows: list[ClaimSupportPolicyChangeImpact] = []
    for row in rows:
        if (
            set(str(value) for value in (row.impacted_claim_derivation_ids_json or []))
            & refs["claim_derivation_ids"]
            or set(str(value) for value in (row.impacted_task_ids_json or []))
            & refs["draft_task_ids"]
            or set(str(value) for value in (row.impacted_verification_task_ids_json or []))
            & refs["verification_task_ids"]
        ):
            matching_rows.append(row)

    if not matching_rows:
        return _empty_claim_support_policy_change_impact_summary()

    events_by_row = _claim_support_policy_change_impact_events_by_row(session, matching_rows)
    escalation_events_by_row = _claim_support_policy_change_impact_events_by_row(
        session,
        matching_rows,
        event_kind=CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
    )
    fixture_promotion_events_by_row = _claim_support_policy_fixture_promotion_events_by_impact(
        session, matching_rows
    )
    corpus_snapshots_by_promotion_event = (
        _claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event(
            session,
            [
                event
                for event_rows in fixture_promotion_events_by_row.values()
                for event in event_rows
            ],
        )
    )
    waiver_closure_events_by_row = _claim_support_replay_alert_waiver_closure_events_by_impact(
        session, matching_rows
    )
    waiver_lifecycle = _claim_support_replay_alert_waiver_lifecycle_summary(
        session,
        matching_rows,
        waiver_closure_events_by_row,
    )
    status_counts: dict[str, int] = {}
    impact_rows: list[dict[str, Any]] = []
    for row in matching_rows:
        status_value = str(row.replay_status)
        status_counts[status_value] = status_counts.get(status_value, 0) + 1
        closure_events = events_by_row.get(row.id, [])
        escalation_events = escalation_events_by_row.get(row.id, [])
        fixture_promotion_events = fixture_promotion_events_by_row.get(row.id, [])
        replay_alert_fixture_corpus_snapshots_by_id: dict[str, dict[str, Any]] = {}
        for event in fixture_promotion_events:
            for snapshot_payload in corpus_snapshots_by_promotion_event.get(event.id, []):
                replay_alert_fixture_corpus_snapshots_by_id[snapshot_payload["snapshot_id"]] = (
                    snapshot_payload
                )
        replay_alert_fixture_corpus_snapshots = [
            replay_alert_fixture_corpus_snapshots_by_id[snapshot_id]
            for snapshot_id in sorted(replay_alert_fixture_corpus_snapshots_by_id)
        ]
        waiver_closure_events = waiver_closure_events_by_row.get(row.id, [])
        waiver_closure_event_payloads = [
            _waiver_closure_event_payload(session, event) for event in waiver_closure_events
        ]
        impact_rows.append(
            {
                "change_impact_id": str(row.id),
                "policy_name": row.policy_name,
                "policy_version": row.policy_version,
                "impact_scope": row.impact_scope,
                "impact_payload_sha256": row.impact_payload_sha256,
                "replay_status": row.replay_status,
                "replay_recommended_count": row.replay_recommended_count,
                "replay_task_ids": list(row.replay_task_ids_json or []),
                "replay_closure_sha256": row.replay_closure_sha256,
                "replay_closed_at": row.replay_closed_at.isoformat()
                if row.replay_closed_at
                else None,
                "closure_governance_events": [
                    {
                        "event_id": str(event.id),
                        "event_hash": event.event_hash,
                        "receipt_sha256": event.receipt_sha256,
                        "agent_task_artifact_id": str(event.agent_task_artifact_id)
                        if event.agent_task_artifact_id
                        else None,
                        "payload_sha256": event.payload_sha256,
                    }
                    for event in closure_events
                ],
                "escalation_governance_events": [
                    {
                        "event_id": str(event.id),
                        "event_hash": event.event_hash,
                        "receipt_sha256": event.receipt_sha256,
                        "agent_task_artifact_id": str(event.agent_task_artifact_id)
                        if event.agent_task_artifact_id
                        else None,
                        "payload_sha256": event.payload_sha256,
                        "alert_kind": (
                            (
                                event.event_payload_json.get(
                                    "claim_support_policy_impact_replay_escalation"
                                )
                                or {}
                            ).get("alert_kind")
                            if event.event_payload_json
                            else None
                        ),
                    }
                    for event in escalation_events
                ],
                "fixture_promotion_governance_events": [
                    _fixture_promotion_event_payload(event) for event in fixture_promotion_events
                ],
                "replay_alert_fixture_corpus_snapshots": (replay_alert_fixture_corpus_snapshots),
                "waiver_closure_governance_events": waiver_closure_event_payloads,
            }
        )

    open_impacts = [
        row
        for row in impact_rows
        if row["replay_status"] in CLAIM_SUPPORT_POLICY_IMPACT_OPEN_REPLAY_STATUSES
    ]
    snapshots_by_id = {
        snapshot["snapshot_id"]: snapshot
        for row in impact_rows
        for snapshot in row.get("replay_alert_fixture_corpus_snapshots") or []
    }
    invalid_snapshot_ids = sorted(
        snapshot_id
        for snapshot_id, snapshot in snapshots_by_id.items()
        if not (snapshot.get("governance_integrity") or {}).get("complete")
    )
    trace_incomplete_snapshot_ids = sorted(
        snapshot_id
        for snapshot_id, snapshot in snapshots_by_id.items()
        if not snapshot.get("trace_complete")
    )
    active_snapshots = [
        snapshot for snapshot in snapshots_by_id.values() if snapshot.get("status") == "active"
    ]
    replay_alert_fixture_corpus = {
        "related_snapshot_count": len(snapshots_by_id),
        "invalid_snapshot_governance_count": len(invalid_snapshot_ids),
        "trace_incomplete_snapshot_count": len(trace_incomplete_snapshot_ids),
        "governance_integrity_verified": not invalid_snapshot_ids,
        "trace_complete": not trace_incomplete_snapshot_ids,
        "active_replay_alert_fixture_corpus_snapshot_id": (
            active_snapshots[-1]["snapshot_id"] if active_snapshots else None
        ),
        "active_replay_alert_fixture_corpus_sha256": (
            active_snapshots[-1]["snapshot_sha256"] if active_snapshots else None
        ),
        "active_replay_alert_fixture_corpus_governance_receipt_sha256": (
            active_snapshots[-1].get("governance_receipt_sha256") if active_snapshots else None
        ),
        "invalid_snapshot_ids": invalid_snapshot_ids,
        "trace_incomplete_snapshot_ids": trace_incomplete_snapshot_ids,
        "snapshots": [snapshots_by_id[snapshot_id] for snapshot_id in sorted(snapshots_by_id)],
    }
    return {
        "related_count": len(impact_rows),
        "open_count": len(open_impacts),
        "closed_count": sum(1 for row in impact_rows if row["replay_status"] == "closed"),
        "blocked_count": sum(1 for row in impact_rows if row["replay_status"] == "blocked"),
        "replay_status_counts": status_counts,
        "waiver_lifecycle": waiver_lifecycle,
        "replay_alert_fixture_corpus": replay_alert_fixture_corpus,
        "clear": (
            not open_impacts
            and waiver_lifecycle["clear"]
            and replay_alert_fixture_corpus["governance_integrity_verified"]
            and replay_alert_fixture_corpus["trace_complete"]
        ),
        "impacts": impact_rows,
    }


def _change_impact_payload(
    session: Session,
    exports: list[EvidencePackageExport],
) -> dict:
    impacts: list[dict[str, Any]] = []
    claim_support_policy_impacts = _claim_support_policy_change_impact_summary(
        session,
        exports,
    )
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
            "claim_support_policy_change_impacts": claim_support_policy_impacts,
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
    for impact in claim_support_policy_impacts["impacts"]:
        if impact["replay_status"] not in CLAIM_SUPPORT_POLICY_IMPACT_OPEN_REPLAY_STATUSES:
            continue
        impacts.append(
            {
                "impact_type": "claim_support_policy_change_replay_open",
                "change_impact_id": impact["change_impact_id"],
                "policy_name": impact["policy_name"],
                "policy_version": impact["policy_version"],
                "replay_status": impact["replay_status"],
                "replay_recommended_count": impact["replay_recommended_count"],
                "reason": (
                    "A claim-support calibration policy changed after this report's "
                    "support judgments were produced, and managed replay has not closed."
                ),
            }
        )
    waiver_lifecycle = claim_support_policy_impacts.get("waiver_lifecycle") or {}
    unresolved_waiver_count = int(waiver_lifecycle.get("unresolved_waiver_count") or 0)
    invalid_waiver_closure_count = int(waiver_lifecycle.get("invalid_waiver_closure_count") or 0)
    if unresolved_waiver_count:
        impacts.append(
            {
                "impact_type": "claim_support_replay_alert_fixture_coverage_waiver_unresolved",
                "unresolved_waiver_count": unresolved_waiver_count,
                "reason": (
                    "Replay-alert fixture coverage waivers related to this report still "
                    "lack complete promoted fixture coverage."
                ),
            }
        )
    if invalid_waiver_closure_count:
        impacts.append(
            {
                "impact_type": (
                    "claim_support_replay_alert_fixture_coverage_waiver_closure_invalid"
                ),
                "invalid_waiver_closure_count": invalid_waiver_closure_count,
                "reason": (
                    "Replay-alert fixture coverage waiver closure receipts related to "
                    "this report failed integrity checks."
                ),
            }
        )
    replay_alert_fixture_corpus = (
        claim_support_policy_impacts.get("replay_alert_fixture_corpus") or {}
    )
    invalid_corpus_snapshot_count = int(
        replay_alert_fixture_corpus.get("invalid_snapshot_governance_count") or 0
    )
    trace_incomplete_corpus_snapshot_count = int(
        replay_alert_fixture_corpus.get("trace_incomplete_snapshot_count") or 0
    )
    if invalid_corpus_snapshot_count:
        impacts.append(
            {
                "impact_type": (
                    "claim_support_replay_alert_fixture_corpus_snapshot_governance_invalid"
                ),
                "invalid_snapshot_governance_count": invalid_corpus_snapshot_count,
                "invalid_snapshot_ids": list(
                    replay_alert_fixture_corpus.get("invalid_snapshot_ids") or []
                ),
                "reason": (
                    "Replay-alert fixture corpus snapshots related to this report "
                    "failed governance receipt integrity checks."
                ),
            }
        )
    if trace_incomplete_corpus_snapshot_count:
        impacts.append(
            {
                "impact_type": (
                    "claim_support_replay_alert_fixture_corpus_snapshot_trace_incomplete"
                ),
                "trace_incomplete_snapshot_count": (trace_incomplete_corpus_snapshot_count),
                "trace_incomplete_snapshot_ids": list(
                    replay_alert_fixture_corpus.get("trace_incomplete_snapshot_ids") or []
                ),
                "reason": (
                    "Replay-alert fixture corpus snapshots related to this report "
                    "do not have complete row-to-promotion evidence trace coverage."
                ),
            }
        )
    return {
        "impacted": bool(impacts),
        "impact_count": len(impacts),
        "impacts": impacts,
        "claim_support_policy_change_impacts": claim_support_policy_impacts,
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
    provenance_lock_mismatched_claim_ids: list[str] = []
    provenance_lock_contract_mismatched_claim_ids: list[str] = []
    missing_provenance_lock_claim_ids: list[str] = []
    support_judgment_mismatched_claim_ids: list[str] = []
    support_judgment_contract_mismatched_claim_ids: list[str] = []
    missing_support_judgment_claim_ids: list[str] = []
    failed_support_judgment_claim_ids: list[str] = []
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
        expected_provenance_lock_sha256 = (
            str(expected_derivation.get("provenance_lock_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if not row.provenance_lock_json or not row.provenance_lock_sha256:
            missing_provenance_lock_claim_ids.append(str(row.claim_id))
        elif (
            row.provenance_lock_sha256 != payload_sha256(row.provenance_lock_json)
            or row.provenance_lock_sha256 != expected_provenance_lock_sha256
        ):
            provenance_lock_mismatched_claim_ids.append(str(row.claim_id))
        if _claim_derivation_provenance_lock_contract_mismatches(row):
            provenance_lock_contract_mismatched_claim_ids.append(str(row.claim_id))
        expected_support_judgment_sha256 = (
            str(expected_derivation.get("support_judgment_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if (
            not row.support_verdict
            or row.support_score is None
            or not row.support_judge_run_id
            or not row.support_judgment_json
            or not row.support_judgment_sha256
        ):
            missing_support_judgment_claim_ids.append(str(row.claim_id))
        elif (
            row.support_judgment_sha256 != payload_sha256(row.support_judgment_json)
            or row.support_judgment_sha256 != expected_support_judgment_sha256
        ):
            support_judgment_mismatched_claim_ids.append(str(row.claim_id))
        if _claim_derivation_support_judgment_contract_mismatches(row):
            support_judgment_contract_mismatched_claim_ids.append(str(row.claim_id))
        if row.support_verdict != "supported":
            failed_support_judgment_claim_ids.append(str(row.claim_id))

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
        "claim_provenance_lock_mismatch_count": len(provenance_lock_mismatched_claim_ids),
        "claim_provenance_lock_contract_mismatch_count": len(
            provenance_lock_contract_mismatched_claim_ids
        ),
        "missing_claim_provenance_lock_count": len(missing_provenance_lock_claim_ids),
        "claim_support_judgment_mismatch_count": len(support_judgment_mismatched_claim_ids),
        "claim_support_judgment_contract_mismatch_count": len(
            support_judgment_contract_mismatched_claim_ids
        ),
        "missing_claim_support_judgment_count": len(missing_support_judgment_claim_ids),
        "failed_claim_support_judgment_count": len(failed_support_judgment_claim_ids),
        "missing_claim_derivation_count": len(missing_claim_derivation_ids),
        "mismatched_claim_ids": sorted(mismatched_claim_ids),
        "package_mismatched_claim_ids": sorted(package_mismatched_claim_ids),
        "provenance_lock_mismatched_claim_ids": sorted(provenance_lock_mismatched_claim_ids),
        "provenance_lock_contract_mismatched_claim_ids": sorted(
            provenance_lock_contract_mismatched_claim_ids
        ),
        "missing_provenance_lock_claim_ids": sorted(missing_provenance_lock_claim_ids),
        "support_judgment_mismatched_claim_ids": sorted(support_judgment_mismatched_claim_ids),
        "support_judgment_contract_mismatched_claim_ids": sorted(
            support_judgment_contract_mismatched_claim_ids
        ),
        "missing_support_judgment_claim_ids": sorted(missing_support_judgment_claim_ids),
        "failed_support_judgment_claim_ids": sorted(failed_support_judgment_claim_ids),
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
    context_pack_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    harness_task_id = context_pack_audit.get("harness_task_id")
    context_pack_artifacts = list(context_pack_audit.get("context_pack_artifacts") or [])
    evaluation_artifacts = list(context_pack_audit.get("evaluation_artifacts") or [])
    context_pack_verifications = list(context_pack_audit.get("verifications") or [])
    context_pack_operator_runs = list(context_pack_audit.get("operator_runs") or [])
    release_readiness_assessments = list(
        context_pack_audit.get("release_readiness_assessments") or []
    )
    release_readiness_db_gate = dict(context_pack_audit.get("release_readiness_db_gate") or {})
    for artifact in context_pack_artifacts:
        artifact_id = artifact.get("artifact_id")
        if harness_task_id and artifact_id:
            edges.append(
                {
                    "edge_type": "harness_task_to_context_pack_artifact",
                    "from": {"table": "agent_tasks", "id": harness_task_id},
                    "to": {"table": "agent_task_artifacts", "id": artifact_id},
                }
            )
    for verification in context_pack_verifications:
        verification_id = verification.get("verification_id")
        verification_task_id = verification.get("verification_task_id")
        if verification_task_id and verification_id:
            edges.append(
                {
                    "edge_type": "context_pack_eval_task_to_verifier_record",
                    "from": {"table": "agent_tasks", "id": verification_task_id},
                    "to": {"table": "agent_task_verifications", "id": verification_id},
                }
            )
        for artifact in context_pack_artifacts:
            artifact_id = artifact.get("artifact_id")
            if artifact_id and verification_id:
                edges.append(
                    {
                        "edge_type": "context_pack_artifact_to_verifier_record",
                        "from": {"table": "agent_task_artifacts", "id": artifact_id},
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                        "context_pack_sha256": verification.get("details", {}).get(
                            "context_pack_sha256"
                        ),
                    }
                )
        db_gate_verification_id = release_readiness_db_gate.get("verification_id")
        if verification_id and db_gate_verification_id == str(verification_id):
            edges.append(
                {
                    "edge_type": "context_pack_verifier_record_to_release_readiness_db_gate",
                    "from": {"table": "agent_task_verifications", "id": verification_id},
                    "to": {
                        "table": "technical_report_release_readiness_db_gate",
                        "id": db_gate_verification_id,
                    },
                    "complete": release_readiness_db_gate.get("complete"),
                }
            )
    for artifact in evaluation_artifacts:
        artifact_id = artifact.get("artifact_id")
        task_id = artifact.get("task_id")
        if task_id and artifact_id:
            edges.append(
                {
                    "edge_type": "context_pack_eval_task_to_evaluation_artifact",
                    "from": {"table": "agent_tasks", "id": task_id},
                    "to": {"table": "agent_task_artifacts", "id": artifact_id},
                }
            )
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if verification_id and artifact_id:
                edges.append(
                    {
                        "edge_type": "context_pack_verifier_record_to_evaluation_artifact",
                        "from": {"table": "agent_task_verifications", "id": verification_id},
                        "to": {"table": "agent_task_artifacts", "id": artifact_id},
                    }
                )
    for operator_run in context_pack_operator_runs:
        operator_run_id = operator_run.get("operator_run_id")
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if operator_run_id and verification_id:
                edges.append(
                    {
                        "edge_type": "context_pack_eval_operator_to_verifier_record",
                        "from": {"table": "knowledge_operator_runs", "id": operator_run_id},
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                    }
                )
    for readiness_ref in release_readiness_assessments:
        assessment_id = readiness_ref.get("assessment_id")
        release_id = readiness_ref.get("search_harness_release_id")
        if release_id and assessment_id:
            edges.append(
                {
                    "edge_type": "search_harness_release_to_readiness_assessment",
                    "from": {"table": "search_harness_releases", "id": release_id},
                    "to": {
                        "table": "search_harness_release_readiness_assessments",
                        "id": assessment_id,
                    },
                }
            )
        for artifact in context_pack_artifacts:
            artifact_id = artifact.get("artifact_id")
            if assessment_id and artifact_id:
                edges.append(
                    {
                        "edge_type": "release_readiness_assessment_to_context_pack_artifact",
                        "from": {
                            "table": "search_harness_release_readiness_assessments",
                            "id": assessment_id,
                        },
                        "to": {"table": "agent_task_artifacts", "id": artifact_id},
                        "assessment_payload_sha256": readiness_ref.get("assessment_payload_sha256"),
                    }
                )
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if assessment_id and verification_id:
                edges.append(
                    {
                        "edge_type": "release_readiness_assessment_to_context_pack_verifier_record",
                        "from": {
                            "table": "search_harness_release_readiness_assessments",
                            "id": assessment_id,
                        },
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                    }
                )
        db_gate_verification_id = release_readiness_db_gate.get("verification_id")
        if assessment_id and db_gate_verification_id:
            edges.append(
                {
                    "edge_type": "release_readiness_assessment_to_release_readiness_db_gate",
                    "from": {
                        "table": "search_harness_release_readiness_assessments",
                        "id": assessment_id,
                    },
                    "to": {
                        "table": "technical_report_release_readiness_db_gate",
                        "id": db_gate_verification_id,
                    },
                    "assessment_payload_sha256": readiness_ref.get("assessment_payload_sha256"),
                }
            )
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
        if claim.get("provenance_lock_sha256"):
            edges.append(
                {
                    "edge_type": "claim_to_provenance_lock",
                    "from": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "to": {
                        "table": "technical_report_claim_provenance_locks",
                        "id": claim.get("provenance_lock_sha256"),
                    },
                    "derivation_sha256": claim.get("derivation_sha256"),
                }
            )
        if claim.get("support_judgment_sha256"):
            edges.append(
                {
                    "edge_type": "claim_to_support_judgment",
                    "from": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "to": {
                        "table": "technical_report_claim_support_judgments",
                        "id": claim.get("support_judgment_sha256"),
                    },
                    "derivation_sha256": claim.get("derivation_sha256"),
                    "support_verdict": claim.get("support_verdict"),
                    "support_score": claim.get("support_score"),
                }
            )
        if claim.get("support_judge_run_id"):
            edges.append(
                {
                    "edge_type": "support_judge_run_to_claim",
                    "from": {
                        "table": "knowledge_operator_runs",
                        "id": claim.get("support_judge_run_id"),
                    },
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "support_judgment_sha256": claim.get("support_judgment_sha256"),
                }
            )
        for result_id in claim.get("source_search_request_result_ids") or []:
            edges.append(
                {
                    "edge_type": "search_result_to_claim",
                    "from": {"table": "search_request_results", "id": result_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for export_id in claim.get("source_evidence_package_export_ids") or []:
            edges.append(
                {
                    "edge_type": "search_evidence_export_to_claim",
                    "from": {"table": "evidence_package_exports", "id": export_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for snapshot_id in claim.get("semantic_ontology_snapshot_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_ontology_snapshot_to_claim",
                    "from": {"table": "semantic_ontology_snapshots", "id": snapshot_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for snapshot_id in claim.get("semantic_graph_snapshot_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_graph_snapshot_to_claim",
                    "from": {"table": "semantic_graph_snapshots", "id": snapshot_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for artifact_id in claim.get("retrieval_reranker_artifact_ids") or []:
            edges.append(
                {
                    "edge_type": "retrieval_reranker_artifact_to_claim",
                    "from": {"table": "retrieval_reranker_artifacts", "id": artifact_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for release_id in claim.get("search_harness_release_ids") or []:
            edges.append(
                {
                    "edge_type": "search_harness_release_to_claim",
                    "from": {"table": "search_harness_releases", "id": release_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for bundle_id in claim.get("release_audit_bundle_ids") or []:
            edges.append(
                {
                    "edge_type": "release_audit_bundle_to_claim",
                    "from": {"table": "audit_bundle_exports", "id": bundle_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for receipt_id in claim.get("release_validation_receipt_ids") or []:
            edges.append(
                {
                    "edge_type": "release_validation_receipt_to_claim",
                    "from": {"table": "audit_bundle_validation_receipts", "id": receipt_id},
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
    context_pack_audit = dict(audit_bundle.get("context_pack_audit") or {})
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
        context_pack_audit=context_pack_audit,
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
        "has_claim_provenance_locks": bool(claims)
        and all(claim.get("provenance_lock_sha256") for claim in claims)
        and audit_bundle["audit_checklist"].get("all_claims_have_provenance_locks", False),
        "has_claim_support_judgments": bool(claims)
        and all(
            claim.get("support_verdict") == "supported"
            and claim.get("support_score") is not None
            and claim.get("support_judge_run_id")
            and claim.get("support_judgment_sha256")
            for claim in claims
        )
        and audit_bundle["audit_checklist"].get("all_claims_have_support_judgments", False)
        and audit_bundle["audit_checklist"].get(
            "claim_support_judgment_integrity_verified",
            False,
        ),
        "has_claim_source_search_results": bool(claims)
        and all(claim.get("source_search_request_result_ids") for claim in claims)
        and audit_bundle["audit_checklist"].get("all_claims_have_source_search_results", False),
        "has_semantic_trace": bool(
            semantic_trace["assertions"]
            or semantic_trace["facts"]
            or draft_payload.get("graph_context")
        ),
        "has_generation_operator_run": audit_bundle["audit_checklist"].get(
            "has_generation_operator_run",
            False,
        ),
        "has_support_judge_operator_run": audit_bundle["audit_checklist"].get(
            "has_support_judge_operator_run",
            False,
        ),
        "has_verification_operator_run": audit_bundle["audit_checklist"].get(
            "has_verification_operator_run",
            False,
        ),
        "has_context_pack_artifact": audit_bundle["audit_checklist"].get(
            "has_context_pack_artifact",
            False,
        ),
        "has_context_pack_evaluation_artifact": audit_bundle["audit_checklist"].get(
            "has_context_pack_evaluation_artifact",
            False,
        ),
        "has_context_pack_verifier_record": audit_bundle["audit_checklist"].get(
            "has_context_pack_verifier_record",
            False,
        ),
        "has_context_pack_evaluation_operator_run": audit_bundle["audit_checklist"].get(
            "has_context_pack_evaluation_operator_run",
            False,
        ),
        "context_pack_evaluation_passed": audit_bundle["audit_checklist"].get(
            "context_pack_evaluation_passed",
            False,
        ),
        "context_pack_hash_verified": audit_bundle["audit_checklist"].get(
            "context_pack_hash_verified",
            False,
        ),
        "has_release_readiness_assessments": audit_bundle["audit_checklist"].get(
            "has_release_readiness_assessments",
            False,
        ),
        "release_readiness_assessments_cover_source_requests": audit_bundle["audit_checklist"].get(
            "release_readiness_assessments_cover_source_requests", False
        ),
        "release_readiness_assessments_ready": audit_bundle["audit_checklist"].get(
            "release_readiness_assessments_ready",
            False,
        ),
        "release_readiness_assessment_integrity_verified": audit_bundle["audit_checklist"].get(
            "release_readiness_assessment_integrity_verified", False
        ),
        "release_readiness_db_gate_verified": audit_bundle["audit_checklist"].get(
            "release_readiness_db_gate_verified",
            False,
        ),
        "release_readiness_db_gate_complete": audit_bundle["audit_checklist"].get(
            "release_readiness_db_gate_complete",
            False,
        ),
        "release_readiness_db_covers_source_requests": audit_bundle["audit_checklist"].get(
            "release_readiness_db_covers_source_requests", False
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
        "replay_alert_waiver_closure_integrity_verified": audit_bundle["audit_checklist"].get(
            "replay_alert_waiver_closure_integrity_verified", False
        ),
        "replay_alert_waiver_lifecycle_clear": audit_bundle["audit_checklist"].get(
            "replay_alert_waiver_lifecycle_clear",
            False,
        ),
        "active_replay_alert_fixture_corpus_snapshot_id": audit_bundle["audit_checklist"].get(
            "active_replay_alert_fixture_corpus_snapshot_id"
        ),
        "active_replay_alert_fixture_corpus_sha256": audit_bundle["audit_checklist"].get(
            "active_replay_alert_fixture_corpus_sha256"
        ),
        "replay_alert_fixture_corpus_snapshot_governed": audit_bundle["audit_checklist"].get(
            "replay_alert_fixture_corpus_snapshot_governed", True
        ),
        "replay_alert_fixture_corpus_trace_complete": audit_bundle["audit_checklist"].get(
            "replay_alert_fixture_corpus_trace_complete", True
        ),
        "invalid_replay_alert_fixture_corpus_snapshot_governance_count": audit_bundle[
            "audit_checklist"
        ].get("invalid_replay_alert_fixture_corpus_snapshot_governance_count", 0),
        "incomplete_replay_alert_fixture_corpus_trace_count": audit_bundle["audit_checklist"].get(
            "incomplete_replay_alert_fixture_corpus_trace_count", 0
        ),
        "has_provenance_edges": bool(provenance_edges),
    }
    checklist["complete"] = all(value for value in checklist.values() if isinstance(value, bool))
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
            "context_pack_audit": context_pack_audit,
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
    "semantic_ontology_snapshots": "semantic_ontology_snapshot",
    "semantic_graph_snapshots": "semantic_graph_snapshot",
    "technical_report_evidence_cards": "evidence_card",
    "technical_report_claims": "technical_report_claim",
    "technical_report_claim_provenance_locks": "claim_provenance_lock",
    "technical_report_claim_support_judgments": "claim_support_judgment",
    "claim_support_policy_change_impacts": "claim_support_policy_change_impact",
    "claim_support_replay_alert_fixture_corpus_snapshots": (
        "claim_support_replay_alert_fixture_corpus_snapshot"
    ),
    "claim_support_replay_alert_fixture_corpus_rows": (
        "claim_support_replay_alert_fixture_corpus_row"
    ),
    "claim_evidence_derivations": "claim_derivation",
    "evidence_package_exports": "evidence_package_export",
    "audit_bundle_exports": "audit_bundle_export",
    "audit_bundle_validation_receipts": "audit_bundle_validation_receipt",
    "knowledge_operator_runs": "operator_run",
    "agent_tasks": "agent_task",
    "agent_task_artifacts": "agent_task_artifact",
    "agent_task_verifications": "verification_record",
    "search_requests": "search_request",
    "search_request_results": "search_result",
    "search_request_result_spans": "selected_retrieval_span",
    "retrieval_evidence_spans": "retrieval_evidence_span",
    "retrieval_evidence_span_multivectors": "retrieval_evidence_span_multivector",
    "retrieval_reranker_artifacts": "retrieval_reranker_artifact",
    "search_harness_releases": "search_harness_release",
    "search_harness_release_readiness_assessments": "release_readiness_assessment",
    "technical_report_release_readiness_db_gate": "release_readiness_db_gate",
    "evidence_manifests": "evidence_manifest",
    "semantic_governance_events": "semantic_governance_event",
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
    if any(edge.get("edge_key") == edge_key for edge in edges):
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
                    "retrieval_evidence_span_id": str(span.get("retrieval_evidence_span_id")),
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
    context_pack_audit = report_trace.get("context_pack_audit") or {}
    for eval_task_id in context_pack_audit.get("evaluation_task_ids") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="agent_tasks",
            source_id=eval_task_id,
            node_kind="context_pack_evaluation_task",
            payload={
                "task_id": str(eval_task_id),
                "task_type": "evaluate_document_generation_context_pack",
            },
        )
    for artifact in [
        *(context_pack_audit.get("context_pack_artifacts") or []),
        *(context_pack_audit.get("evaluation_artifacts") or []),
    ]:
        _put_trace_node_from_id(
            nodes,
            source_table="agent_task_artifacts",
            source_id=artifact.get("artifact_id"),
            payload=artifact,
        )
    for verification in context_pack_audit.get("verifications") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="agent_task_verifications",
            source_id=verification.get("verification_id"),
            payload=verification,
        )
    for readiness_ref in context_pack_audit.get("release_readiness_assessments") or []:
        _put_trace_node_from_id(
            nodes,
            source_table="search_harness_release_readiness_assessments",
            source_id=readiness_ref.get("assessment_id"),
            payload=readiness_ref,
        )
    release_readiness_db_gate = context_pack_audit.get("release_readiness_db_gate") or {}
    if release_readiness_db_gate.get("verification_id"):
        _put_trace_node_from_id(
            nodes,
            source_table="technical_report_release_readiness_db_gate",
            source_id=release_readiness_db_gate.get("verification_id"),
            payload=release_readiness_db_gate,
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

    change_impact = manifest_payload.get("change_impact") or {}
    policy_impacts = (change_impact.get("claim_support_policy_change_impacts") or {}).get(
        "impacts"
    ) or []
    for impact in policy_impacts:
        impact_node_key = _put_trace_node_from_id(
            nodes,
            source_table="claim_support_policy_change_impacts",
            source_id=impact.get("change_impact_id"),
            payload=impact,
        )
        for event_kind, event_rows in [
            ("replay_closure_event", impact.get("closure_governance_events") or []),
            ("replay_escalation_event", impact.get("escalation_governance_events") or []),
            (
                "replay_fixture_promotion_event",
                impact.get("fixture_promotion_governance_events") or [],
            ),
            (
                "replay_fixture_waiver_closure_event",
                impact.get("waiver_closure_governance_events") or [],
            ),
        ]:
            for event in event_rows:
                event_node_key = _put_trace_node_from_id(
                    nodes,
                    source_table="semantic_governance_events",
                    source_id=event.get("event_id"),
                    payload=event,
                )
                _put_trace_edge(
                    edges,
                    edge_key=(
                        f"claim-support-impact:{impact.get('change_impact_id')}:"
                        f"{event_kind}:{event.get('event_id')}"
                    ),
                    edge_kind=event_kind,
                    from_node_key=impact_node_key,
                    to_node_key=event_node_key,
                    payload={"source": "claim_support_policy_change_impact"},
                )
                artifact_id = event.get("agent_task_artifact_id")
                if artifact_id:
                    artifact_node_key = _put_trace_node_from_id(
                        nodes,
                        source_table="agent_task_artifacts",
                        source_id=artifact_id,
                        payload={
                            "artifact_id": artifact_id,
                            "receipt_sha256": event.get("receipt_sha256"),
                        },
                    )
                    _put_trace_edge(
                        edges,
                        edge_key=(
                            f"claim-support-impact:{impact.get('change_impact_id')}:"
                            f"{event_kind}-artifact:{artifact_id}"
                        ),
                        edge_kind=f"{event_kind}_artifact",
                        from_node_key=event_node_key,
                        to_node_key=artifact_node_key,
                        payload={"source": "claim_support_policy_change_impact"},
                    )

        for snapshot in impact.get("replay_alert_fixture_corpus_snapshots") or []:
            snapshot_id = snapshot.get("snapshot_id")
            snapshot_node_key = _put_trace_node_from_id(
                nodes,
                source_table="claim_support_replay_alert_fixture_corpus_snapshots",
                source_id=snapshot_id,
                payload=snapshot,
            )
            _put_trace_edge(
                edges,
                edge_key=(
                    f"claim-support-impact:{impact.get('change_impact_id')}:"
                    f"replay-fixture-corpus-snapshot:{snapshot_id}"
                ),
                edge_kind="replay_fixture_corpus_snapshot",
                from_node_key=impact_node_key,
                to_node_key=snapshot_node_key,
                payload={"source": "claim_support_policy_change_impact"},
            )
            _put_trace_edge(
                edges,
                edge_key=(
                    f"verification:{verification.get('verification_id')}:"
                    f"uses-replay-fixture-corpus-snapshot:{snapshot_id}"
                ),
                edge_kind="verification_uses_replay_fixture_corpus_snapshot",
                from_node_key=verification_record_node_key,
                to_node_key=snapshot_node_key,
                payload={"source": "claim_support_policy_change_impact"},
            )
            governance_event_id = snapshot.get("semantic_governance_event_id")
            governance_event_node_key = _put_trace_node_from_id(
                nodes,
                source_table="semantic_governance_events",
                source_id=governance_event_id,
                payload={
                    "event_id": governance_event_id,
                    "event_kind": (CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND),
                    "receipt_sha256": snapshot.get("governance_receipt_sha256"),
                    "governance_integrity": snapshot.get("governance_integrity"),
                },
            )
            _put_trace_edge(
                edges,
                edge_key=(
                    f"replay-fixture-corpus-snapshot:{snapshot_id}:"
                    f"governance-event:{governance_event_id}"
                ),
                edge_kind="replay_fixture_corpus_snapshot_governance_event",
                from_node_key=snapshot_node_key,
                to_node_key=governance_event_node_key,
                payload={"source": "claim_support_replay_alert_fixture_corpus"},
            )
            governance_artifact_id = snapshot.get("governance_artifact_id")
            governance_artifact_node_key = _put_trace_node_from_id(
                nodes,
                source_table="agent_task_artifacts",
                source_id=governance_artifact_id,
                payload={
                    "artifact_id": governance_artifact_id,
                    "artifact_kind": (
                        CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND
                    ),
                    "receipt_sha256": snapshot.get("governance_receipt_sha256"),
                },
            )
            _put_trace_edge(
                edges,
                edge_key=(
                    f"replay-fixture-corpus-snapshot:{snapshot_id}:"
                    f"governance-artifact:{governance_artifact_id}"
                ),
                edge_kind="replay_fixture_corpus_snapshot_governance_artifact",
                from_node_key=governance_event_node_key,
                to_node_key=governance_artifact_node_key,
                payload={"source": "claim_support_replay_alert_fixture_corpus"},
            )
            for row in snapshot.get("rows") or []:
                row_id = row.get("row_id")
                row_node_key = _put_trace_node_from_id(
                    nodes,
                    source_table="claim_support_replay_alert_fixture_corpus_rows",
                    source_id=row_id,
                    payload=row,
                )
                _put_trace_edge(
                    edges,
                    edge_key=(f"replay-fixture-corpus-snapshot:{snapshot_id}:row:{row_id}"),
                    edge_kind="replay_fixture_corpus_row",
                    from_node_key=snapshot_node_key,
                    to_node_key=row_node_key,
                    payload={"source": "claim_support_replay_alert_fixture_corpus"},
                )
                promotion_event_id = row.get("promotion_event_id")
                promotion_event_node_key = _put_trace_node_from_id(
                    nodes,
                    source_table="semantic_governance_events",
                    source_id=promotion_event_id,
                    payload={
                        "event_id": promotion_event_id,
                        "event_kind": CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND,
                        "receipt_sha256": row.get("promotion_receipt_sha256"),
                    },
                )
                _put_trace_edge(
                    edges,
                    edge_key=(
                        f"replay-fixture-corpus-row:{row_id}:promotion-event:{promotion_event_id}"
                    ),
                    edge_kind="replay_fixture_corpus_row_promotion_event",
                    from_node_key=row_node_key,
                    to_node_key=promotion_event_node_key,
                    payload={"source": "claim_support_replay_alert_fixture_corpus"},
                )
                promotion_artifact_id = row.get("promotion_artifact_id")
                promotion_artifact_node_key = _put_trace_node_from_id(
                    nodes,
                    source_table="agent_task_artifacts",
                    source_id=promotion_artifact_id,
                    payload={
                        "artifact_id": promotion_artifact_id,
                        "artifact_kind": (
                            CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND
                        ),
                        "receipt_sha256": row.get("promotion_receipt_sha256"),
                    },
                )
                _put_trace_edge(
                    edges,
                    edge_key=(
                        f"replay-fixture-corpus-row:{row_id}:"
                        f"promotion-artifact:{promotion_artifact_id}"
                    ),
                    edge_kind="replay_fixture_corpus_row_promotion_artifact",
                    from_node_key=row_node_key,
                    to_node_key=promotion_artifact_node_key,
                    payload={"source": "claim_support_replay_alert_fixture_corpus"},
                )
                for escalation_event_id in row.get("source_escalation_event_ids") or []:
                    escalation_event_node_key = _put_trace_node_from_id(
                        nodes,
                        source_table="semantic_governance_events",
                        source_id=escalation_event_id,
                        payload={
                            "event_id": escalation_event_id,
                            "event_kind": (CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND),
                        },
                    )
                    _put_trace_edge(
                        edges,
                        edge_key=(
                            f"replay-fixture-corpus-row:{row_id}:"
                            f"source-escalation-event:{escalation_event_id}"
                        ),
                        edge_kind="replay_fixture_corpus_row_source_escalation_event",
                        from_node_key=row_node_key,
                        to_node_key=escalation_event_node_key,
                        payload={"source": "claim_support_replay_alert_fixture_corpus"},
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
    return (
        node_specs,
        edge_specs,
        str(graph.get("trace_sha256") or _search_trace_graph_sha256(node_specs, edge_specs)),
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
        "docling:agent/context-pack-gate": {
            "prov:type": "prov:SoftwareAgent",
            "prov:label": "Document generation context-pack gate",
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

    report_trace = manifest.get("report_trace") or {}
    context_pack_audit = report_trace.get("context_pack_audit") or {}
    release_readiness_db_gate = dict(context_pack_audit.get("release_readiness_db_gate") or {})
    release_readiness_db_gate_entity_id = _prov_identifier(
        "technical_report_release_readiness_db_gate",
        release_readiness_db_gate.get("verification_id"),
    )
    harness_activity_id = _prov_identifier(
        "agent_tasks",
        context_pack_audit.get("harness_task_id"),
    )
    if harness_activity_id:
        _prov_activity(
            activities,
            harness_activity_id,
            label="prepare_report_agent_harness",
            activity_type="docling:AgentTask",
            **{"docling:task_type": "prepare_report_agent_harness"},
        )
        _prov_relation(
            was_associated_with,
            "was-associated-with",
            sequence=len(was_associated_with) + 1,
            **{"prov:activity": harness_activity_id, "prov:agent": "docling:agent/docling-system"},
        )
    for eval_task_id in context_pack_audit.get("evaluation_task_ids") or []:
        activity_id = _prov_identifier("agent_tasks", eval_task_id)
        _prov_activity(
            activities,
            activity_id,
            label="evaluate_document_generation_context_pack",
            activity_type="docling:ContextPackEvaluationTask",
            **{"docling:task_type": "evaluate_document_generation_context_pack"},
        )
        _prov_relation(
            was_associated_with,
            "was-associated-with",
            sequence=len(was_associated_with) + 1,
            **{"prov:activity": activity_id, "prov:agent": "docling:agent/context-pack-gate"},
        )
    for artifact in context_pack_audit.get("context_pack_artifacts") or []:
        entity_id = _prov_identifier("agent_task_artifacts", artifact.get("artifact_id"))
        _prov_entity(
            entities,
            entity_id,
            label="Document generation context pack",
            entity_type="docling:DocumentGenerationContextPack",
            **{
                "docling:artifact_kind": artifact.get("artifact_kind"),
                "docling:payload_sha256": artifact.get("payload_sha256"),
                "docling:context_pack_sha256": (
                    context_pack_audit.get("context_pack_sha256s") or [None]
                )[0],
            },
        )
        _prov_relation(
            was_generated_by,
            "was-generated-by",
            sequence=len(was_generated_by) + 1,
            **{"prov:entity": entity_id, "prov:activity": harness_activity_id},
        )
    for artifact in context_pack_audit.get("evaluation_artifacts") or []:
        entity_id = _prov_identifier("agent_task_artifacts", artifact.get("artifact_id"))
        eval_activity_id = _prov_identifier("agent_tasks", artifact.get("task_id"))
        _prov_entity(
            entities,
            entity_id,
            label="Document generation context-pack evaluation",
            entity_type="docling:DocumentGenerationContextPackEvaluation",
            **{
                "docling:artifact_kind": artifact.get("artifact_kind"),
                "docling:payload_sha256": artifact.get("payload_sha256"),
            },
        )
        _prov_relation(
            was_generated_by,
            "was-generated-by",
            sequence=len(was_generated_by) + 1,
            **{"prov:entity": entity_id, "prov:activity": eval_activity_id},
        )
    for verification in context_pack_audit.get("verifications") or []:
        entity_id = _prov_identifier(
            "agent_task_verifications",
            verification.get("verification_id"),
        )
        eval_activity_id = _prov_identifier("agent_tasks", verification.get("verification_task_id"))
        _prov_entity(
            entities,
            entity_id,
            label="Document generation context-pack verifier record",
            entity_type="docling:ContextPackVerificationRecord",
            **{
                "docling:outcome": verification.get("outcome"),
                "docling:context_pack_sha256": (verification.get("details") or {}).get(
                    "context_pack_sha256"
                ),
            },
        )
        _prov_relation(
            was_generated_by,
            "was-generated-by",
            sequence=len(was_generated_by) + 1,
            **{"prov:entity": entity_id, "prov:activity": eval_activity_id},
        )
        for artifact in context_pack_audit.get("context_pack_artifacts") or []:
            context_entity_id = _prov_identifier(
                "agent_task_artifacts",
                artifact.get("artifact_id"),
            )
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": eval_activity_id, "prov:entity": context_entity_id},
            )
    if release_readiness_db_gate_entity_id:
        db_gate_verification_id = release_readiness_db_gate.get("verification_id")
        db_gate_eval_activity_id = _prov_identifier(
            "agent_tasks",
            release_readiness_db_gate.get("verification_task_id"),
        )
        _prov_entity(
            entities,
            release_readiness_db_gate_entity_id,
            label="Release readiness DB gate summary",
            entity_type="docling:ReleaseReadinessDbGate",
            **{
                "docling:check_key": release_readiness_db_gate.get("check_key"),
                "docling:passed": release_readiness_db_gate.get("passed"),
                "docling:required": release_readiness_db_gate.get("required"),
                "docling:complete": release_readiness_db_gate.get("complete"),
                "docling:failure_count": release_readiness_db_gate.get("failure_count"),
                "docling:source_search_request_count": release_readiness_db_gate.get(
                    "source_search_request_count"
                ),
                "docling:verified_request_count": release_readiness_db_gate.get(
                    "verified_request_count"
                ),
            },
        )
        if db_gate_eval_activity_id:
            _prov_relation(
                was_generated_by,
                "was-generated-by",
                sequence=len(was_generated_by) + 1,
                **{
                    "prov:entity": release_readiness_db_gate_entity_id,
                    "prov:activity": db_gate_eval_activity_id,
                },
            )
        for verification in context_pack_audit.get("verifications") or []:
            verification_id = verification.get("verification_id")
            if str(verification_id) != str(db_gate_verification_id):
                continue
            verification_entity_id = _prov_identifier(
                "agent_task_verifications",
                verification_id,
            )
            if verification_entity_id:
                _prov_relation(
                    was_derived_from,
                    "was-derived-from",
                    sequence=len(was_derived_from) + 1,
                    **{
                        "prov:generatedEntity": release_readiness_db_gate_entity_id,
                        "prov:usedEntity": verification_entity_id,
                        "docling:edge_type": (
                            "context_pack_verifier_record_to_release_readiness_db_gate"
                        ),
                    },
                )
    for readiness_ref in context_pack_audit.get("release_readiness_assessments") or []:
        entity_id = _prov_identifier(
            "search_harness_release_readiness_assessments",
            readiness_ref.get("assessment_id"),
        )
        if entity_id is None:
            continue
        _prov_entity(
            entities,
            entity_id,
            label="Search harness release readiness assessment",
            entity_type="docling:SearchHarnessReleaseReadinessAssessment",
            **{
                "docling:search_harness_release_id": readiness_ref.get("search_harness_release_id"),
                "docling:harness_name": readiness_ref.get("harness_name"),
                "docling:readiness_status": readiness_ref.get("readiness_status"),
                "docling:ready": readiness_ref.get("ready"),
                "docling:selection_status": readiness_ref.get("selection_status"),
                "docling:assessment_payload_sha256": readiness_ref.get("assessment_payload_sha256"),
            },
        )
        if harness_activity_id:
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": harness_activity_id, "prov:entity": entity_id},
            )
        for eval_task_id in context_pack_audit.get("evaluation_task_ids") or []:
            eval_activity_id = _prov_identifier("agent_tasks", eval_task_id)
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": eval_activity_id, "prov:entity": entity_id},
            )
        if release_readiness_db_gate_entity_id:
            _prov_relation(
                was_derived_from,
                "was-derived-from",
                sequence=len(was_derived_from) + 1,
                **{
                    "prov:generatedEntity": release_readiness_db_gate_entity_id,
                    "prov:usedEntity": entity_id,
                    "docling:edge_type": (
                        "release_readiness_assessment_to_release_readiness_db_gate"
                    ),
                },
            )

    verification_activity_id = _prov_identifier(
        "agent_tasks",
        (manifest.get("verification_task") or {}).get("task_id"),
    )
    if verification_activity_id and release_readiness_db_gate_entity_id:
        _prov_relation(
            used,
            "used",
            sequence=len(used) + 1,
            **{
                "prov:activity": verification_activity_id,
                "prov:entity": release_readiness_db_gate_entity_id,
            },
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
                "docling:source_snapshot_sha256": source_record.get("source_snapshot_sha256"),
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
                "docling:source_evidence_match_status": card.get("source_evidence_match_status"),
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
                "docling:source_evidence_match_status": claim.get("source_evidence_match_status"),
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
        if from_id not in entities:
            _prov_entity(
                entities,
                from_id,
                label=str(from_ref.get("table") or "provenance source"),
                entity_type="docling:ProvenanceEndpoint",
                **{"docling:table": from_ref.get("table")},
            )
        if to_id not in entities:
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
            "release_readiness_db_gate": release_readiness_db_gate,
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
            "release_readiness_db_gate_complete": release_readiness_db_gate.get("complete") is True,
            "release_readiness_db_gate_failure_count": release_readiness_db_gate.get(
                "failure_count"
            ),
            "release_readiness_db_verified_request_count": release_readiness_db_gate.get(
                "verified_request_count"
            ),
            "release_readiness_db_source_search_request_count": release_readiness_db_gate.get(
                "source_search_request_count"
            ),
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

    hash_chain_values = [item.get("sha256") for item in receipt.get("hash_chain") or []]
    hash_chain_complete = bool(receipt.get("hash_chain_complete")) and all(hash_chain_values)
    export_payload_hash_matches = _receipt_hash_chain_sha256(
        receipt, "technical_report_prov_export"
    ) == frozen_export.get("export_payload_sha256")
    prov_hash_basis_matches = _receipt_hash_chain_sha256(
        receipt, "prov_hash_basis"
    ) == frozen_export.get("prov_hash_basis_sha256")
    checks = {
        "has_receipt": bool(receipt),
        "receipt_hash_matches": receipt_hash_matches,
        "expected_receipt_sha256": expected_receipt_sha256,
        "stored_receipt_sha256": stored_receipt_sha256,
        "hash_chain_complete": hash_chain_complete,
        "artifact_id_matches": receipt.get("artifact_id") == frozen_export.get("artifact_id"),
        "artifact_kind_matches": receipt.get("artifact_kind") == frozen_export.get("artifact_kind"),
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


def _technical_report_change_impact_for_governance(
    session: Session,
    verification_task_id: UUID,
) -> dict[str, Any]:
    verification_task = session.get(AgentTask, verification_task_id)
    if verification_task is None:
        return {
            "impacted": True,
            "impact_count": 1,
            "impacts": [
                {
                    "impact_type": "verification_task_missing",
                    "verification_task_id": str(verification_task_id),
                }
            ],
        }
    draft_task_id = _draft_task_id_for_audit(verification_task)
    draft_task = session.get(AgentTask, draft_task_id)
    draft_payload = (
        ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
        if draft_task is not None
        else {}
    )
    related_task_ids = [
        draft_task_id,
        *_technical_report_upstream_task_ids(session, draft_payload),
        verification_task_id,
    ]
    related_task_ids = list(dict.fromkeys(related_task_ids))
    exports = list(
        session.scalars(
            select(EvidencePackageExport)
            .where(EvidencePackageExport.agent_task_id.in_(related_task_ids))
            .order_by(EvidencePackageExport.created_at.asc())
        )
    )
    return _change_impact_payload(session, exports)


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
    governance_change_impact = _technical_report_change_impact_for_governance(
        session,
        verification_task_id,
    )
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
            change_impact=governance_change_impact,
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
        change_impact=governance_change_impact,
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
        related_task_ids.extend(_context_pack_eval_task_ids_for_harness(session, harness_task_id))
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
        row for row in artifacts if row.artifact_kind == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND
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
            (row.get("export_receipt") or {}).get("receipt_sha256") for row in prov_export_receipts
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
    harness_task_id = _uuid_or_none_safe(draft_payload.get("harness_task_id"))
    context_pack_eval_task_ids = (
        _context_pack_eval_task_ids_for_harness(session, harness_task_id)
        if harness_task_id is not None
        else []
    )
    context_pack_verifications = _context_pack_verification_rows(
        session,
        harness_task_id=harness_task_id,
        eval_task_ids=context_pack_eval_task_ids,
    )
    context_pack_audit = _technical_report_context_pack_audit_payload(
        harness_task_id=harness_task_id,
        eval_task_ids=context_pack_eval_task_ids,
        artifacts=artifacts,
        verification_rows=context_pack_verifications,
        operator_runs=operator_runs,
    )
    verification_payload = (
        ((verification_task.result_json or {}).get("payload") or {})
        if verification_task is not None
        else None
    )
    change_impact = _change_impact_payload(session, exports)
    claim_support_change_impacts = change_impact.get("claim_support_policy_change_impacts") or {}
    waiver_lifecycle = claim_support_change_impacts.get("waiver_lifecycle") or {}
    replay_alert_fixture_corpus = (
        claim_support_change_impacts.get("replay_alert_fixture_corpus") or {}
    )
    unresolved_waiver_count = int(waiver_lifecycle.get("unresolved_waiver_count") or 0)
    invalid_waiver_closure_count = int(waiver_lifecycle.get("invalid_waiver_closure_count") or 0)
    replay_alert_waiver_closure_integrity_verified = bool(
        waiver_lifecycle.get("waiver_closure_integrity_verified", True)
    )
    replay_alert_waiver_lifecycle_clear = (
        unresolved_waiver_count == 0
        and invalid_waiver_closure_count == 0
        and replay_alert_waiver_closure_integrity_verified
    )
    invalid_replay_alert_fixture_corpus_snapshot_count = int(
        replay_alert_fixture_corpus.get("invalid_snapshot_governance_count") or 0
    )
    incomplete_replay_alert_fixture_corpus_trace_count = int(
        replay_alert_fixture_corpus.get("trace_incomplete_snapshot_count") or 0
    )
    replay_alert_fixture_corpus_snapshot_governed = bool(
        replay_alert_fixture_corpus.get("governance_integrity_verified", True)
    )
    replay_alert_fixture_corpus_trace_complete = bool(
        replay_alert_fixture_corpus.get("trace_complete", True)
    )
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
        and integrity["claim_provenance_lock_mismatch_count"] == 0
        and integrity["claim_provenance_lock_contract_mismatch_count"] == 0
        and integrity["missing_claim_provenance_lock_count"] == 0
        and integrity["claim_support_judgment_mismatch_count"] == 0
        and integrity["claim_support_judgment_contract_mismatch_count"] == 0
        and integrity["missing_claim_support_judgment_count"] == 0
        and integrity["failed_claim_support_judgment_count"] == 0
        and integrity["missing_claim_derivation_count"] == 0
    )
    source_evidence_trace_integrity_verified = source_evidence_closure["complete"]
    prov_export_receipts_integrity_verified = bool(prov_export_receipts) and all(
        (row.get("receipt_integrity") or {}).get("complete") for row in prov_export_receipts
    )
    prov_export_receipt_signature_verified = bool(prov_export_receipts) and all(
        (row.get("receipt_integrity") or {}).get("signature_verification_status") == "verified"
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
        "context_pack_audit": context_pack_audit,
        "change_impact": change_impact,
        "integrity": integrity,
        "audit_checklist": {
            "has_frozen_evidence_package": bool(exports),
            "all_claims_have_derivations": len(derivations)
            == len(draft_payload.get("claims") or []),
            "all_claims_have_provenance_locks": bool(draft_payload.get("claims"))
            and all(
                claim.get("provenance_lock") and claim.get("provenance_lock_sha256")
                for claim in draft_payload.get("claims") or []
            )
            and integrity["missing_claim_provenance_lock_count"] == 0
            and integrity["claim_provenance_lock_mismatch_count"] == 0,
            "all_claim_provenance_locks_match_claim_fields": (
                integrity["claim_provenance_lock_contract_mismatch_count"] == 0
            ),
            "all_claims_have_support_judgments": bool(draft_payload.get("claims"))
            and all(
                claim.get("support_verdict") == "supported"
                and claim.get("support_score") is not None
                and claim.get("support_judge_run_id")
                and claim.get("support_judgment")
                and claim.get("support_judgment_sha256")
                for claim in draft_payload.get("claims") or []
            )
            and integrity["missing_claim_support_judgment_count"] == 0
            and integrity["failed_claim_support_judgment_count"] == 0,
            "all_claim_support_judgments_match_claim_fields": (
                integrity["claim_support_judgment_contract_mismatch_count"] == 0
            ),
            "claim_support_judgment_integrity_verified": (
                integrity["claim_support_judgment_mismatch_count"] == 0
            ),
            "all_claims_have_source_search_results": bool(draft_payload.get("claims"))
            and all(
                claim.get("source_search_request_result_ids")
                for claim in draft_payload.get("claims") or []
            ),
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
            "prov_export_receipts_integrity_verified": (prov_export_receipts_integrity_verified),
            "prov_export_receipt_signature_verified": (prov_export_receipt_signature_verified),
            "no_prov_export_immutability_events": not prov_export_immutability_events,
            "has_semantic_governance_chain": semantic_governance_chain["integrity"]["has_events"],
            "semantic_governance_chain_integrity_verified": semantic_governance_chain["integrity"][
                "complete"
            ],
            "semantic_governance_chain_links_prov_receipt": semantic_governance_chain["integrity"][
                "links_requested_prov_receipt"
            ],
            "semantic_governance_chain_change_impact_evaluated": (
                semantic_governance_chain["integrity"]["change_impact_evaluated"]
            ),
            "source_evidence_trace_integrity_verified": (source_evidence_trace_integrity_verified),
            "generation_evidence_closed": (
                hash_integrity_verified and source_evidence_trace_integrity_verified
            ),
            "has_generation_operator_run": any(
                row.operator_kind == "generate" for row in operator_runs
            ),
            "has_support_judge_operator_run": any(
                row.operator_kind == "judge"
                and row.operator_name == "technical_report_claim_support_judge"
                for row in operator_runs
            ),
            "has_verification_operator_run": any(
                row.operator_kind == "verify" for row in operator_runs
            ),
            "has_context_pack_artifact": context_pack_audit["integrity"][
                "has_context_pack_artifact"
            ],
            "has_context_pack_evaluation_artifact": context_pack_audit["integrity"][
                "has_context_pack_evaluation_artifact"
            ],
            "has_context_pack_verifier_record": context_pack_audit["integrity"][
                "has_context_pack_verifier_record"
            ],
            "has_context_pack_evaluation_operator_run": context_pack_audit["integrity"][
                "has_context_pack_evaluation_operator_run"
            ],
            "context_pack_evaluation_passed": context_pack_audit["integrity"][
                "latest_context_pack_evaluation_passed"
            ],
            "context_pack_hash_verified": context_pack_audit["integrity"][
                "context_pack_hash_verified"
            ],
            "has_release_readiness_assessments": context_pack_audit["integrity"][
                "has_release_readiness_assessments"
            ],
            "release_readiness_assessments_cover_source_requests": context_pack_audit["integrity"][
                "release_readiness_assessments_cover_source_requests"
            ],
            "release_readiness_assessments_ready": context_pack_audit["integrity"][
                "release_readiness_assessments_ready"
            ],
            "release_readiness_assessment_integrity_verified": context_pack_audit["integrity"][
                "release_readiness_assessment_integrity_verified"
            ],
            "release_readiness_db_gate_verified": context_pack_audit["integrity"][
                "release_readiness_db_gate_verified"
            ],
            "release_readiness_db_gate_complete": context_pack_audit["integrity"][
                "release_readiness_db_gate_complete"
            ],
            "release_readiness_db_covers_source_requests": context_pack_audit["integrity"][
                "release_readiness_db_covers_source_requests"
            ],
            "context_pack_audit_complete": context_pack_audit["integrity"]["complete"],
            "verification_passed": (
                verification_row.outcome == "passed" if verification_row is not None else False
            ),
            "change_impact_clear": not change_impact["impacted"],
            "replay_alert_waiver_closure_integrity_verified": (
                replay_alert_waiver_closure_integrity_verified
            ),
            "unresolved_replay_alert_fixture_coverage_waiver_count": (unresolved_waiver_count),
            "invalid_replay_alert_fixture_coverage_waiver_closure_count": (
                invalid_waiver_closure_count
            ),
            "replay_alert_waiver_lifecycle_clear": (replay_alert_waiver_lifecycle_clear),
            "active_replay_alert_fixture_corpus_snapshot_id": (
                replay_alert_fixture_corpus.get("active_replay_alert_fixture_corpus_snapshot_id")
            ),
            "active_replay_alert_fixture_corpus_sha256": (
                replay_alert_fixture_corpus.get("active_replay_alert_fixture_corpus_sha256")
            ),
            "replay_alert_fixture_corpus_snapshot_governed": (
                replay_alert_fixture_corpus_snapshot_governed
            ),
            "replay_alert_fixture_corpus_trace_complete": (
                replay_alert_fixture_corpus_trace_complete
            ),
            "invalid_replay_alert_fixture_corpus_snapshot_governance_count": (
                invalid_replay_alert_fixture_corpus_snapshot_count
            ),
            "incomplete_replay_alert_fixture_corpus_trace_count": (
                incomplete_replay_alert_fixture_corpus_trace_count
            ),
        },
    }
    audit_bundle["audit_checklist"]["complete"] = (
        audit_bundle["audit_checklist"]["generation_evidence_closed"]
        and audit_bundle["audit_checklist"]["all_claims_have_provenance_locks"]
        and audit_bundle["audit_checklist"]["all_claim_provenance_locks_match_claim_fields"]
        and audit_bundle["audit_checklist"]["all_claims_have_support_judgments"]
        and audit_bundle["audit_checklist"]["all_claim_support_judgments_match_claim_fields"]
        and audit_bundle["audit_checklist"]["claim_support_judgment_integrity_verified"]
        and audit_bundle["audit_checklist"]["all_claims_have_source_search_results"]
        and audit_bundle["audit_checklist"]["has_generation_operator_run"]
        and audit_bundle["audit_checklist"]["has_support_judge_operator_run"]
        and audit_bundle["audit_checklist"]["has_verification_operator_run"]
        and audit_bundle["audit_checklist"]["context_pack_audit_complete"]
        and audit_bundle["audit_checklist"]["has_release_readiness_assessments"]
        and audit_bundle["audit_checklist"]["release_readiness_assessments_cover_source_requests"]
        and audit_bundle["audit_checklist"]["release_readiness_assessments_ready"]
        and audit_bundle["audit_checklist"]["release_readiness_assessment_integrity_verified"]
        and audit_bundle["audit_checklist"]["release_readiness_db_gate_verified"]
        and audit_bundle["audit_checklist"]["release_readiness_db_gate_complete"]
        and audit_bundle["audit_checklist"]["release_readiness_db_covers_source_requests"]
        and audit_bundle["audit_checklist"]["has_frozen_prov_export"]
        and audit_bundle["audit_checklist"]["has_prov_export_receipt"]
        and audit_bundle["audit_checklist"]["has_signed_prov_export_receipt"]
        and audit_bundle["audit_checklist"]["prov_export_receipts_integrity_verified"]
        and audit_bundle["audit_checklist"]["prov_export_receipt_signature_verified"]
        and audit_bundle["audit_checklist"]["no_prov_export_immutability_events"]
        and audit_bundle["audit_checklist"]["has_semantic_governance_chain"]
        and audit_bundle["audit_checklist"]["semantic_governance_chain_integrity_verified"]
        and audit_bundle["audit_checklist"]["semantic_governance_chain_links_prov_receipt"]
        and audit_bundle["audit_checklist"]["semantic_governance_chain_change_impact_evaluated"]
        and audit_bundle["audit_checklist"]["verification_passed"]
        and audit_bundle["audit_checklist"]["change_impact_clear"]
        and audit_bundle["audit_checklist"]["replay_alert_waiver_closure_integrity_verified"]
        and audit_bundle["audit_checklist"]["replay_alert_waiver_lifecycle_clear"]
        and audit_bundle["audit_checklist"]["replay_alert_fixture_corpus_snapshot_governed"]
        and audit_bundle["audit_checklist"]["replay_alert_fixture_corpus_trace_complete"]
    )
    audit_bundle["audit_bundle_sha256"] = payload_sha256(audit_bundle)
    return audit_bundle
