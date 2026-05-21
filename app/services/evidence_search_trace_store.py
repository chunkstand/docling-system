from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.public.audit_and_evidence import (
    EvidencePackageExport,
    EvidenceTraceEdge,
    EvidenceTraceNode,
)
from app.services.evidence_common import clean_mapping as _clean_mapping
from app.services.evidence_common import payload_sha256, trace_payload_sha256
from app.services.evidence_common import trace_edge_row_payload as _trace_edge_row_payload
from app.services.evidence_common import trace_edge_spec_from_row as _trace_edge_spec_from_row
from app.services.evidence_common import trace_node_row_payload as _trace_node_row_payload
from app.services.evidence_common import trace_node_spec_from_row as _trace_node_spec_from_row
from app.services.evidence_records import evidence_export_payload as _evidence_export_payload
from app.services.evidence_search_package_build import build_search_evidence_package
from app.services.evidence_search_trace_graph import (
    search_trace_graph_sha256,
    search_trace_specs_from_package,
)


def persist_search_evidence_package_trace_graph(
    session: Session,
    *,
    export_row: EvidencePackageExport,
    package_payload: dict[str, Any],
) -> None:
    node_specs, edge_specs, trace_sha256 = search_trace_specs_from_package(package_payload)
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


def search_evidence_trace_rows(
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


def search_evidence_trace_integrity_payload(
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
    persisted_trace_sha256 = search_trace_graph_sha256(
        (_trace_node_spec_from_row(node) for node in nodes),
        (_trace_edge_spec_from_row(edge) for edge in edges),
    )
    node_payload_hash_mismatch_count = sum(
        1 for node in nodes if trace_payload_sha256(node.payload_json or {}) != node.content_sha256
    )
    edge_payload_hash_mismatch_count = sum(
        1 for edge in edges if trace_payload_sha256(edge.payload_json or {}) != edge.content_sha256
    )
    recomputed_package_sha256 = None
    recomputed_trace_sha256 = None
    recomputation_error = None
    recomputed_nodes: list[dict[str, Any]] = []
    recomputed_edges: list[dict[str, Any]] = []
    try:
        if row.search_request_id is None:
            raise ValueError("Search evidence package export is missing search_request_id.")
        recomputed_package = build_search_evidence_package(session, row.search_request_id)
        recomputed_package_sha256 = str(recomputed_package["package_sha256"])
        recomputed_nodes, recomputed_edges, recomputed_trace_sha256 = (
            search_trace_specs_from_package(recomputed_package)
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


def ensure_search_evidence_package_trace_graph(
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
    persist_search_evidence_package_trace_graph(
        session,
        export_row=row,
        package_payload=row.package_payload_json or {},
    )
    session.flush()
    return row


def search_evidence_package_export_response(
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
        "trace_integrity": search_evidence_trace_integrity_payload(
            session,
            row,
            nodes,
            edges,
        ),
    }


def search_evidence_package_trace_response(
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
        "trace_integrity": search_evidence_trace_integrity_payload(
            session,
            row,
            nodes,
            edges,
        ),
    }
