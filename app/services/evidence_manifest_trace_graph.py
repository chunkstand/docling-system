from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from app.core.json_utils import json_object_payload as _json_payload
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import trace_node_key as _trace_node_key
from app.services.evidence_common import trace_payload_sha256 as _trace_payload_sha256
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe

TRACE_NODE_KIND_BY_TABLE = {
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
    "technical_report_claim_retrieval_feedback": "claim_retrieval_feedback",
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
    "technical_report_release_readiness_db_gates": "release_readiness_db_gate",
    "evidence_manifests": "evidence_manifest",
    "semantic_governance_events": "semantic_governance_event",
}


def put_trace_node(
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
        "node_kind": node_kind or TRACE_NODE_KIND_BY_TABLE.get(source_table, source_table),
        "source_table": source_table,
        "source_id": source_id,
        "source_ref": normalized_source_ref,
        "content_sha256": _trace_payload_sha256(node_payload),
        "payload": node_payload,
    }
    return key


def put_trace_node_from_id(
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
    return put_trace_node(
        nodes,
        source_table=source_table,
        source_ref=parsed_source_id,
        source_id=parsed_source_id,
        node_kind=node_kind,
        payload=payload,
    )


def put_trace_node_from_ref(
    nodes: dict[str, dict[str, Any]],
    ref: dict[str, Any],
) -> str:
    source_table = str(ref.get("table") or "unknown")
    source_ref = ref.get("id") or ref.get("sha256") or ref.get("ref") or "unknown"
    source_id = _uuid_or_none_safe(ref.get("id"))
    return put_trace_node(
        nodes,
        source_table=source_table,
        source_ref=source_ref,
        source_id=source_id,
        payload={"placeholder": True, "ref": ref},
    )


def put_trace_edge(
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


def trace_graph_canonical_payload(
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


def trace_graph_sha256(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> str:
    return str(payload_sha256(trace_graph_canonical_payload(nodes, edges)))
