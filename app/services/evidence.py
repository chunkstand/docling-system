from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentRun,
    DocumentTable,
    DocumentTableSegment,
    KnowledgeOperatorInput,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
    SearchRequestRecord,
    SearchRequestResult,
)


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
    return {
        row.id: row
        for row in session.scalars(select(model).where(model.id.in_(unique_ids)))
    }


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


def _result_payload(
    row: SearchRequestResult,
    *,
    source_snapshot_sha256: str | None,
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
    }


def _source_evidence_payloads(
    session: Session,
    result_rows: list[SearchRequestResult],
) -> list[dict]:
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
    operator_rows = list(
        session.scalars(
            select(KnowledgeOperatorRun)
            .where(KnowledgeOperatorRun.search_request_id == search_request_id)
            .order_by(KnowledgeOperatorRun.created_at.asc(), KnowledgeOperatorRun.id.asc())
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

    source_evidence = _source_evidence_payloads(session, result_rows)
    source_evidence_by_result_id = {
        str(row["search_request_result_id"]): row for row in source_evidence
    }
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
            )
            for row in result_rows
        ],
        "source_evidence": source_evidence,
        "audit_checklist": {
            "has_retrieve_run": any(row.operator_kind == "retrieve" for row in operator_rows),
            "has_rerank_run": any(row.operator_kind == "rerank" for row in operator_rows),
            "has_judge_run": any(row.operator_kind == "judge" for row in operator_rows),
            "has_config_hashes": all(
                row.config_sha256
                for row in operator_rows
                if row.operator_kind in {"retrieve", "rerank"}
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
                item.get("run") is not None
                and item["run"].get("validation_status") == "passed"
                for item in source_evidence
            ),
            "all_source_snapshots_hashed": all(
                bool(item.get("source_snapshot_sha256")) for item in source_evidence
            ),
        },
    }
    package["package_sha256"] = payload_sha256(package)
    return package
