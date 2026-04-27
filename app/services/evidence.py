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
    AgentTask,
    AgentTaskArtifact,
    AgentTaskVerification,
    ClaimEvidenceDerivation,
    Document,
    DocumentChunk,
    DocumentRun,
    DocumentTable,
    DocumentTableSegment,
    EvidencePackageExport,
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
        _evidence_card_snapshot(dict(card))
        for card in draft_payload.get("evidence_cards", [])
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


def _draft_task_id_for_audit(task: AgentTask) -> UUID:
    if task.task_type == "draft_technical_report":
        return task.id
    if task.task_type == "verify_technical_report":
        payload = (task.result_json or {}).get("payload") or {}
        verification = payload.get("verification") or {}
        target_task_id = verification.get("target_task_id")
        if target_task_id:
            return UUID(str(target_task_id))
    raise ValueError("Audit bundles are currently supported for technical report tasks only.")


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

    related_task_ids = [draft_task.id]
    if verification_task is not None:
        related_task_ids.append(verification_task.id)

    artifacts = list(
        session.scalars(
            select(AgentTaskArtifact)
            .where(AgentTaskArtifact.task_id.in_(related_task_ids))
            .order_by(AgentTaskArtifact.created_at.asc())
        )
    )
    exports = list(
        session.scalars(
            select(EvidencePackageExport)
            .where(EvidencePackageExport.agent_task_id == draft_task.id)
            .order_by(EvidencePackageExport.created_at.asc())
        )
    )
    export_ids = [row.id for row in exports]
    derivations: list[ClaimEvidenceDerivation] = []
    if export_ids:
        derivations = list(
            session.scalars(
                select(ClaimEvidenceDerivation)
                .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(export_ids))
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
    draft_payload = ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
    verification_payload = (
        ((verification_task.result_json or {}).get("payload") or {})
        if verification_task is not None
        else None
    )
    change_impact = _change_impact_payload(session, exports)
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
        "evidence_package_exports": [_evidence_export_payload(row) for row in exports],
        "claim_derivations": [_claim_derivation_payload(row) for row in derivations],
        "operator_runs": [_operator_run_summary(row) for row in operator_runs],
        "change_impact": change_impact,
        "audit_checklist": {
            "has_frozen_evidence_package": bool(exports),
            "all_claims_have_derivations": len(derivations)
            == len(draft_payload.get("claims") or []),
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
    audit_bundle["audit_bundle_sha256"] = payload_sha256(audit_bundle)
    return audit_bundle
