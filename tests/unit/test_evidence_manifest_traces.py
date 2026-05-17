from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import app.services.evidence_manifest_trace_graph as trace_graph_owner
import app.services.evidence_manifest_traces as evidence_manifest_traces


def _manifest_row(
    *,
    verification_task_id: UUID | str | None = None,
    manifest_status: str = "completed",
    trace_sha256: str | None = None,
) -> SimpleNamespace:
    verification_task_uuid = (
        UUID(str(verification_task_id)) if verification_task_id is not None else uuid4()
    )
    return SimpleNamespace(
        id=uuid4(),
        manifest_kind="technical_report",
        manifest_sha256="manifest-sha",
        manifest_status=manifest_status,
        verification_task_id=verification_task_uuid,
        trace_sha256=trace_sha256,
    )


def _trace_node_row(spec: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        node_key=spec["node_key"],
        node_kind=spec["node_kind"],
        source_table=spec.get("source_table"),
        source_id=spec.get("source_id"),
        source_ref=spec.get("source_ref"),
        content_sha256=spec["content_sha256"],
        payload_json=spec["payload"],
    )


def _trace_edge_row(spec: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        edge_key=spec["edge_key"],
        edge_kind=spec["edge_kind"],
        from_node_key=spec["from_node_key"],
        to_node_key=spec["to_node_key"],
        derivation_sha256=spec.get("derivation_sha256"),
        content_sha256=spec["content_sha256"],
        payload_json=spec["payload"],
    )


def test_build_evidence_trace_graph_specs_preserves_materialized_nodes() -> None:
    document_id = str(uuid4())
    manifest_row = _manifest_row()
    manifest_payload = {
        "source_documents": [
            {
                "id": document_id,
                "sha256": "document-sha",
                "source_filename": "report.pdf",
            }
        ],
        "provenance_edges": [
            {
                "from": {"table": "documents", "id": document_id},
                "to": {"table": "source_pdf", "sha256": "document-sha"},
                "edge_type": "document_has_pdf",
            },
            {
                "from": {"table": "documents", "id": document_id},
                "to": {"table": "external_records", "ref": "record-1"},
                "edge_type": "document_to_external_record",
            },
        ],
    }

    node_specs, edge_specs, _ = evidence_manifest_traces.build_evidence_trace_graph_specs(
        manifest_row=manifest_row,
        manifest_payload=manifest_payload,
    )

    nodes_by_key = {node["node_key"]: node for node in node_specs}
    source_pdf_node = nodes_by_key["source_pdf:document-sha"]
    external_record_node = nodes_by_key["external_records:record-1"]

    assert source_pdf_node["payload"]["sha256"] == "document-sha"
    assert source_pdf_node["payload"].get("placeholder") is None
    assert external_record_node["payload"]["placeholder"] is True
    assert external_record_node["payload"]["ref"] == {
        "table": "external_records",
        "ref": "record-1",
    }
    assert {edge["edge_kind"] for edge in edge_specs} >= {
        "source_pdf_checksum",
        "document_has_pdf",
        "document_to_external_record",
    }


def test_trace_graph_owner_replaces_placeholder_with_materialized_node() -> None:
    nodes: dict[str, dict[str, Any]] = {}

    placeholder_key = trace_graph_owner.put_trace_node_from_ref(
        nodes,
        {"table": "documents", "id": "doc-1"},
    )
    materialized_key = trace_graph_owner.put_trace_node(
        nodes,
        source_table="documents",
        source_ref="doc-1",
        payload={"title": "Materialized"},
    )

    assert placeholder_key == materialized_key
    assert nodes[materialized_key]["payload"] == {
        "source_table": "documents",
        "source_ref": "doc-1",
        "title": "Materialized",
    }


def test_trace_graph_owner_dedupes_edges_by_edge_key() -> None:
    edges: list[dict[str, Any]] = []

    trace_graph_owner.put_trace_edge(
        edges,
        edge_key="edge-1",
        edge_kind="supports",
        from_node_key="from",
        to_node_key="to",
        payload={"source": "first"},
    )
    trace_graph_owner.put_trace_edge(
        edges,
        edge_key="edge-1",
        edge_kind="supports",
        from_node_key="from",
        to_node_key="to",
        payload={"source": "second"},
    )

    assert len(edges) == 1
    assert edges[0]["payload"]["source"] == "first"


def test_build_evidence_trace_graph_specs_adds_replay_fixture_lineage_edges() -> None:
    verification_id = str(uuid4())
    impact_id = str(uuid4())
    closure_event_id = str(uuid4())
    snapshot_id = str(uuid4())
    governance_event_id = str(uuid4())
    governance_artifact_id = str(uuid4())
    row_id = str(uuid4())
    promotion_event_id = str(uuid4())
    promotion_artifact_id = str(uuid4())
    escalation_event_id = str(uuid4())
    manifest_row = _manifest_row()
    manifest_payload = {
        "report_trace": {"verification": {"verification_id": verification_id}},
        "change_impact": {
            "claim_support_policy_change_impacts": {
                "impacts": [
                    {
                        "change_impact_id": impact_id,
                        "closure_governance_events": [{"event_id": closure_event_id}],
                        "replay_alert_fixture_corpus_snapshots": [
                            {
                                "snapshot_id": snapshot_id,
                                "semantic_governance_event_id": governance_event_id,
                                "governance_artifact_id": governance_artifact_id,
                                "governance_receipt_sha256": "governance-receipt-sha",
                                "governance_integrity": {"complete": True},
                                "rows": [
                                    {
                                        "row_id": row_id,
                                        "promotion_event_id": promotion_event_id,
                                        "promotion_artifact_id": promotion_artifact_id,
                                        "promotion_receipt_sha256": "promotion-receipt-sha",
                                        "source_escalation_event_ids": [escalation_event_id],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        },
    }

    _, edge_specs, _ = evidence_manifest_traces.build_evidence_trace_graph_specs(
        manifest_row=manifest_row,
        manifest_payload=manifest_payload,
    )

    assert {edge["edge_kind"] for edge in edge_specs} >= {
        "replay_closure_event",
        "replay_fixture_corpus_snapshot",
        "verification_uses_replay_fixture_corpus_snapshot",
        "replay_fixture_corpus_snapshot_governance_event",
        "replay_fixture_corpus_snapshot_governance_artifact",
        "replay_fixture_corpus_row",
        "replay_fixture_corpus_row_promotion_event",
        "replay_fixture_corpus_row_promotion_artifact",
        "replay_fixture_corpus_row_source_escalation_event",
    }


def test_evidence_trace_integrity_payload_reports_complete_trace() -> None:
    verification_task_id = str(uuid4())
    manifest_row = _manifest_row(verification_task_id=verification_task_id)
    manifest_payload = {
        "verification_task": {
            "task_id": verification_task_id,
            "task_type": "verify_technical_report",
        },
        "report_trace": {"verification": {"verification_id": verification_task_id}},
    }
    node_specs, edge_specs, trace_sha256 = (
        evidence_manifest_traces.build_evidence_trace_graph_specs(
            manifest_row=manifest_row,
            manifest_payload=manifest_payload,
        )
    )
    manifest_row.trace_sha256 = trace_sha256
    nodes = [_trace_node_row(spec) for spec in node_specs]
    edges = [_trace_edge_row(spec) for spec in edge_specs]

    payload = evidence_manifest_traces.evidence_trace_integrity_payload(
        None,
        manifest_row,
        nodes,
        edges,
        build_manifest_payload=lambda _session, _task_id: manifest_payload,
    )

    assert payload["stored_trace_sha256"] == trace_sha256
    assert payload["persisted_trace_hash_matches"] is True
    assert payload["recomputed_trace_hash_matches"] is True
    assert payload["persisted_trace_matches_recomputed"] is True
    assert payload["node_count_matches_recomputed"] is True
    assert payload["edge_count_matches_recomputed"] is True
    assert payload["complete"] is True


def test_evidence_trace_integrity_payload_reports_hash_mismatch_and_recompute_error() -> None:
    verification_task_id = str(uuid4())
    manifest_row = _manifest_row(
        verification_task_id=verification_task_id,
        trace_sha256="stored-trace-sha",
    )
    manifest_payload = {
        "verification_task": {
            "task_id": verification_task_id,
            "task_type": "verify_technical_report",
        },
        "report_trace": {"verification": {"verification_id": verification_task_id}},
    }
    node_specs, edge_specs, _ = evidence_manifest_traces.build_evidence_trace_graph_specs(
        manifest_row=manifest_row,
        manifest_payload=manifest_payload,
    )
    broken_node_spec = deepcopy(node_specs[0])
    broken_node_spec["content_sha256"] = "broken-node-sha"
    nodes = [_trace_node_row(broken_node_spec), *[_trace_node_row(spec) for spec in node_specs[1:]]]
    edges = [_trace_edge_row(spec) for spec in edge_specs]

    def _raise_value_error(_session: Any, _task_id: UUID) -> dict[str, Any]:
        raise ValueError("missing recomputation payload")

    payload = evidence_manifest_traces.evidence_trace_integrity_payload(
        None,
        manifest_row,
        nodes,
        edges,
        build_manifest_payload=_raise_value_error,
    )

    assert payload["node_payload_hash_mismatch_count"] == 1
    assert payload["edge_payload_hash_mismatch_count"] == 0
    assert payload["persisted_trace_hash_matches"] is False
    assert payload["recomputed_trace_hash_matches"] is False
    assert payload["persisted_trace_matches_recomputed"] is False
    assert payload["recomputation_error"] == "missing recomputation payload"
    assert payload["complete"] is False


def test_evidence_manifest_traces_facade_stays_within_budget() -> None:
    with open(evidence_manifest_traces.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 600
