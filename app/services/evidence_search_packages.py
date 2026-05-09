from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    EvidencePackageExport,
    KnowledgeOperatorInput,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
    SearchRequestRecord,
    SearchRequestResult,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_records import (
    late_interaction_matches as _late_interaction_matches,
)
from app.services.evidence_records import (
    operator_run_payload as _operator_run_payload,
)
from app.services.evidence_records import (
    result_payload as _result_payload,
)
from app.services.evidence_records import (
    source_evidence_payloads as _source_evidence_payloads,
)
from app.services.evidence_search_trace_graph import (
    build_search_evidence_trace_graph,
    search_evidence_provenance_edges,
)
from app.services.evidence_search_trace_store import (
    ensure_search_evidence_package_trace_graph,
    persist_search_evidence_package_trace_graph,
    search_evidence_package_export_response,
    search_evidence_package_trace_response,
    search_evidence_trace_rows,
)


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
    provenance_edges = search_evidence_provenance_edges(
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
    package["trace_graph"] = build_search_evidence_trace_graph(package)
    package["package_sha256"] = payload_sha256(package)
    return package


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
    persist_search_evidence_package_trace_graph(
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
    nodes, edges = search_evidence_trace_rows(session, export.id)
    return search_evidence_package_export_response(session, export, nodes, edges)


def get_search_evidence_package_export_trace(
    session: Session,
    evidence_package_export_id: UUID,
) -> dict[str, Any]:
    export = session.get(EvidencePackageExport, evidence_package_export_id)
    if export is None or export.package_kind != "search_request":
        raise ValueError(
            f"Search evidence package export '{evidence_package_export_id}' was not found."
        )
    ensure_search_evidence_package_trace_graph(session, export)
    nodes, edges = search_evidence_trace_rows(session, export.id)
    return search_evidence_package_trace_response(session, export, nodes, edges)


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
