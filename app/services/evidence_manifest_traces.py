from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    EvidenceManifest,
    EvidenceTraceEdge,
    EvidenceTraceNode,
)
from app.services.evidence_common import (
    payload_sha256,
)
from app.services.evidence_common import (
    trace_edge_spec_from_row as _trace_edge_spec_from_row,
)
from app.services.evidence_common import (
    trace_node_key as _trace_node_key,
)
from app.services.evidence_common import (
    trace_node_spec_from_row as _trace_node_spec_from_row,
)
from app.services.evidence_common import (
    trace_payload_sha256 as _trace_payload_sha256,
)
from app.services.evidence_common import (
    uuid_or_none_safe as _uuid_or_none_safe,
)

TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE = "technical_report_claim_retrieval_feedback"
TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA = "technical_report_release_readiness_db_gate"
TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE = "technical_report_release_readiness_db_gates"
CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND = (
    "claim_support_policy_impact_replay_escalated"
)
CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND = (
    "claim_support_policy_impact_fixture_promoted"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot_activated"
)
CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot"
)

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


def build_evidence_trace_graph_specs(
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
    for feedback in report_trace.get("claim_retrieval_feedback") or []:
        _put_trace_node_from_id(
            nodes,
            source_table=TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
            source_id=feedback.get("feedback_id"),
            payload=feedback,
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
    release_readiness_db_gate_record = (
        context_pack_audit.get("release_readiness_db_gate_record") or {}
    )
    if release_readiness_db_gate_record.get("gate_id"):
        _put_trace_node_from_id(
            nodes,
            source_table=TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
            source_id=release_readiness_db_gate_record.get("gate_id"),
            payload={
                "record": release_readiness_db_gate_record,
                "gate": release_readiness_db_gate,
            },
        )
    elif release_readiness_db_gate.get("verification_id"):
        _put_trace_node_from_id(
            nodes,
            source_table=TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
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
                    "event_kind": CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND,
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
                    edge_key=f"replay-fixture-corpus-snapshot:{snapshot_id}:row:{row_id}",
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
                            "event_kind": CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
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
                edge_key=f"operator_parent:{parent_node_key}->{operator_node_key}",
                edge_kind="operator_run_parent_child",
                from_node_key=parent_node_key,
                to_node_key=operator_node_key,
                payload={"source": "materialized_trace"},
            )

    node_specs = sorted(nodes.values(), key=lambda item: item["node_key"])
    edge_specs = sorted(edges, key=lambda item: item["edge_key"])
    return node_specs, edge_specs, _trace_graph_sha256(node_specs, edge_specs)


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
