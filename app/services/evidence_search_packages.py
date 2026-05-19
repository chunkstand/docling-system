from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    EvidencePackageExport,
)
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_search_package_build import build_search_evidence_package
from app.services.evidence_search_trace_store import (
    ensure_search_evidence_package_trace_graph,
    persist_search_evidence_package_trace_graph,
    search_evidence_package_export_response,
    search_evidence_package_trace_response,
    search_evidence_trace_rows,
)


def get_search_evidence_package(session: Session, search_request_id: UUID) -> dict:
    return build_search_evidence_package(session, search_request_id)


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
