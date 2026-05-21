from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.public.audit_and_evidence import EvidenceManifest, EvidenceTraceEdge, EvidenceTraceNode
from app.services.evidence_common import (
    trace_edge_spec_from_row as _trace_edge_spec_from_row,
)
from app.services.evidence_common import (
    trace_node_spec_from_row as _trace_node_spec_from_row,
)
from app.services.evidence_common import (
    trace_payload_sha256 as _trace_payload_sha256,
)
from app.services.evidence_manifest_trace_assembly import (
    build_manifest_trace_graph_specs as _build_manifest_trace_graph_specs,
)
from app.services.evidence_manifest_trace_graph import (
    trace_graph_sha256 as _trace_graph_sha256,
)


def build_evidence_trace_graph_specs(
    *,
    manifest_row: EvidenceManifest,
    manifest_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    return _build_manifest_trace_graph_specs(
        manifest_row=manifest_row,
        manifest_payload=manifest_payload,
    )


def persist_evidence_trace_graph(
    session: Session,
    *,
    manifest_row: EvidenceManifest,
    manifest_payload: dict[str, Any],
) -> None:
    node_specs, edge_specs, trace_sha256 = build_evidence_trace_graph_specs(
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


def evidence_trace_rows(
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


def evidence_trace_integrity_payload(
    session: Session,
    row: EvidenceManifest,
    nodes: list[EvidenceTraceNode],
    edges: list[EvidenceTraceEdge],
    *,
    build_manifest_payload: Callable[[Session, UUID], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if build_manifest_payload is None:
        from app.services import evidence as _evidence

        build_manifest_payload = _evidence.build_technical_report_evidence_manifest_payload
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
        recomputed_manifest_payload = build_manifest_payload(session, row.verification_task_id)
        recomputed_nodes, recomputed_edges, recomputed_trace_sha256 = (
            build_evidence_trace_graph_specs(
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
