from __future__ import annotations

from typing import Any

from app.db.models import EvidenceManifest
from app.services.evidence_common import trace_node_key as _trace_node_key
from app.services.evidence_constants import (
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
)
from app.services.evidence_manifest_trace_graph import (
    put_trace_edge,
    put_trace_node,
    put_trace_node_from_id,
    put_trace_node_from_ref,
    trace_graph_sha256,
)
from app.services.evidence_manifest_trace_replay import add_claim_support_replay_trace


def add_manifest_root_node(
    nodes: dict[str, dict[str, Any]],
    *,
    manifest_row: EvidenceManifest,
) -> str:
    return put_trace_node(
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


def add_task_nodes(
    nodes: dict[str, dict[str, Any]],
    *,
    manifest_payload: dict[str, Any],
) -> dict[str, str]:
    task_node_keys: dict[str, str] = {}
    for payload_key, node_kind in (
        ("task", "agent_task"),
        ("draft_task", "draft_task"),
        ("verification_task", "verification_task"),
    ):
        task_payload = manifest_payload.get(payload_key) or {}
        task_node_key = put_trace_node_from_id(
            nodes,
            source_table="agent_tasks",
            source_id=task_payload.get("task_id"),
            node_kind=node_kind,
            payload=task_payload,
        )
        if task_node_key:
            task_node_keys[payload_key] = task_node_key
    return task_node_keys


def add_source_document_nodes(
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    manifest_payload: dict[str, Any],
) -> None:
    for document in manifest_payload.get("source_documents") or []:
        document_node_key = put_trace_node_from_id(
            nodes,
            source_table="documents",
            source_id=document.get("id"),
            payload=document,
        )
        if document.get("sha256"):
            source_pdf_node_key = put_trace_node(
                nodes,
                source_table="source_pdf",
                source_ref=document["sha256"],
                payload={
                    "sha256": document["sha256"],
                    "source_filename": document.get("source_filename"),
                    "document_id": document.get("id"),
                },
            )
            put_trace_edge(
                edges,
                edge_key=f"materialized:source_pdf_checksum:{document['sha256']}",
                edge_kind="source_pdf_checksum",
                from_node_key=source_pdf_node_key,
                to_node_key=document_node_key,
                payload={"source": "materialized_trace", "document_id": document.get("id")},
            )

    for run in manifest_payload.get("document_runs") or []:
        put_trace_node_from_id(
            nodes,
            source_table="document_runs",
            source_id=run.get("id"),
            payload=run,
        )


def add_source_record_nodes(
    nodes: dict[str, dict[str, Any]],
    *,
    manifest_payload: dict[str, Any],
) -> None:
    for record in manifest_payload.get("source_records") or []:
        if record.get("record_kind") == "technical_report_evidence_card":
            put_trace_node(
                nodes,
                source_table="technical_report_evidence_cards",
                source_ref=record.get("evidence_card_id"),
                payload=record,
            )
        if record.get("evidence_id"):
            put_trace_node_from_id(
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
                put_trace_node_from_id(
                    nodes,
                    source_table=source_table,
                    source_id=source_payload.get("id"),
                    payload=source_payload,
                )


def add_semantic_trace_nodes(
    nodes: dict[str, dict[str, Any]],
    *,
    manifest_payload: dict[str, Any],
) -> None:
    semantic_trace = manifest_payload.get("semantic_trace") or {}
    for assertion in semantic_trace.get("assertions") or []:
        put_trace_node_from_id(
            nodes,
            source_table="semantic_assertions",
            source_id=assertion.get("assertion_id"),
            payload=assertion,
        )
    for evidence in semantic_trace.get("assertion_evidence") or []:
        put_trace_node_from_id(
            nodes,
            source_table="semantic_assertion_evidence",
            source_id=evidence.get("evidence_id"),
            payload=evidence,
        )
    for fact in semantic_trace.get("facts") or []:
        put_trace_node_from_id(
            nodes,
            source_table="semantic_facts",
            source_id=fact.get("fact_id"),
            payload=fact,
        )
    for evidence in semantic_trace.get("fact_evidence") or []:
        put_trace_node_from_id(
            nodes,
            source_table="semantic_fact_evidence",
            source_id=evidence.get("fact_evidence_id"),
            payload=evidence,
        )


def add_report_trace_nodes(
    nodes: dict[str, dict[str, Any]],
    *,
    manifest_payload: dict[str, Any],
) -> tuple[dict[str, Any], Any, str | None]:
    report_trace = manifest_payload.get("report_trace") or {}
    for card in report_trace.get("evidence_cards") or []:
        put_trace_node(
            nodes,
            source_table="technical_report_evidence_cards",
            source_ref=card.get("evidence_card_id"),
            payload=card,
        )
    for claim in report_trace.get("claims") or []:
        put_trace_node(
            nodes,
            source_table="technical_report_claims",
            source_ref=claim.get("claim_id"),
            payload=claim,
        )
    for derivation in report_trace.get("claim_derivations") or []:
        derivation_id = derivation.get("claim_evidence_derivation_id")
        if derivation_id:
            put_trace_node_from_id(
                nodes,
                source_table="claim_evidence_derivations",
                source_id=derivation_id,
                payload=derivation,
            )
        else:
            put_trace_node(
                nodes,
                source_table="claim_evidence_derivations",
                source_ref=f"claim:{derivation.get('claim_id')}",
                payload=derivation,
            )
    for feedback in report_trace.get("claim_retrieval_feedback") or []:
        put_trace_node_from_id(
            nodes,
            source_table=TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
            source_id=feedback.get("feedback_id"),
            payload=feedback,
        )
    for export in report_trace.get("evidence_package_exports") or []:
        put_trace_node_from_id(
            nodes,
            source_table="evidence_package_exports",
            source_id=export.get("evidence_package_export_id"),
            payload=export,
        )
    context_pack_audit = report_trace.get("context_pack_audit") or {}
    for eval_task_id in context_pack_audit.get("evaluation_task_ids") or []:
        put_trace_node_from_id(
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
        put_trace_node_from_id(
            nodes,
            source_table="agent_task_artifacts",
            source_id=artifact.get("artifact_id"),
            payload=artifact,
        )
    for verification in context_pack_audit.get("verifications") or []:
        put_trace_node_from_id(
            nodes,
            source_table="agent_task_verifications",
            source_id=verification.get("verification_id"),
            payload=verification,
        )
    for readiness_ref in context_pack_audit.get("release_readiness_assessments") or []:
        put_trace_node_from_id(
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
        put_trace_node_from_id(
            nodes,
            source_table=TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
            source_id=release_readiness_db_gate_record.get("gate_id"),
            payload={
                "record": release_readiness_db_gate_record,
                "gate": release_readiness_db_gate,
            },
        )
    elif release_readiness_db_gate.get("verification_id"):
        put_trace_node_from_id(
            nodes,
            source_table=TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
            source_id=release_readiness_db_gate.get("verification_id"),
            payload=release_readiness_db_gate,
        )
    for operator_run in report_trace.get("operator_runs") or []:
        put_trace_node_from_id(
            nodes,
            source_table="knowledge_operator_runs",
            source_id=operator_run.get("operator_run_id"),
            payload=operator_run,
        )
    verification = report_trace.get("verification") or {}
    verification_record_node_key = put_trace_node_from_id(
        nodes,
        source_table="agent_task_verifications",
        source_id=verification.get("verification_id"),
        payload=verification,
    )
    return report_trace, verification.get("verification_id"), verification_record_node_key


def add_search_request_nodes(
    nodes: dict[str, dict[str, Any]],
    *,
    manifest_payload: dict[str, Any],
) -> None:
    for search_request_id in manifest_payload.get("search_request_ids") or []:
        put_trace_node_from_id(
            nodes,
            source_table="search_requests",
            source_id=search_request_id,
            payload={"search_request_id": str(search_request_id)},
        )


def add_manifest_provenance_edges(
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    manifest_payload: dict[str, Any],
) -> None:
    for index, provenance_edge in enumerate(manifest_payload.get("provenance_edges") or []):
        from_node_key = put_trace_node_from_ref(nodes, provenance_edge.get("from") or {})
        to_node_key = put_trace_node_from_ref(nodes, provenance_edge.get("to") or {})
        put_trace_edge(
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


def add_manifest_lifecycle_edges(
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    report_trace: dict[str, Any],
    task_node_keys: dict[str, str],
    manifest_node_key: str,
    verification_record_node_key: str | None,
) -> None:
    draft_node_key = task_node_keys.get("draft_task")
    verification_task_node_key = task_node_keys.get("verification_task")
    put_trace_edge(
        edges,
        edge_key="lifecycle:draft_task_to_verification_task",
        edge_kind="draft_task_to_verification_task",
        from_node_key=draft_node_key,
        to_node_key=verification_task_node_key,
        payload={"source": "materialized_trace"},
    )
    put_trace_edge(
        edges,
        edge_key="lifecycle:verification_task_to_manifest",
        edge_kind="verification_task_to_manifest",
        from_node_key=verification_task_node_key,
        to_node_key=manifest_node_key,
        payload={"source": "materialized_trace"},
    )
    put_trace_edge(
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
        put_trace_edge(
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
        put_trace_edge(
            edges,
            edge_key=f"manifest_contains:operator_run:{operator_node_key}",
            edge_kind="operator_run_to_manifest",
            from_node_key=operator_node_key,
            to_node_key=manifest_node_key,
            payload={"source": "materialized_trace"},
        )
        parent_operator_id = operator_run.get("parent_operator_run_id")
        if parent_operator_id:
            parent_node_key = put_trace_node_from_id(
                nodes,
                source_table="knowledge_operator_runs",
                source_id=parent_operator_id,
                payload={"operator_run_id": str(parent_operator_id), "placeholder": True},
            )
            put_trace_edge(
                edges,
                edge_key=f"operator_parent:{parent_node_key}->{operator_node_key}",
                edge_kind="operator_run_parent_child",
                from_node_key=parent_node_key,
                to_node_key=operator_node_key,
                payload={"source": "materialized_trace"},
            )


def build_manifest_trace_graph_specs(
    *,
    manifest_row: EvidenceManifest,
    manifest_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    manifest_node_key = add_manifest_root_node(nodes, manifest_row=manifest_row)
    task_node_keys = add_task_nodes(nodes, manifest_payload=manifest_payload)
    add_source_document_nodes(nodes, edges, manifest_payload=manifest_payload)
    add_source_record_nodes(nodes, manifest_payload=manifest_payload)
    add_semantic_trace_nodes(nodes, manifest_payload=manifest_payload)
    report_trace, verification_id, verification_record_node_key = add_report_trace_nodes(
        nodes,
        manifest_payload=manifest_payload,
    )
    add_search_request_nodes(nodes, manifest_payload=manifest_payload)
    change_impact = manifest_payload.get("change_impact") or {}
    policy_impacts = (change_impact.get("claim_support_policy_change_impacts") or {}).get(
        "impacts"
    ) or []
    add_claim_support_replay_trace(
        nodes,
        edges,
        policy_impacts=policy_impacts,
        verification_id=verification_id,
        verification_record_node_key=verification_record_node_key,
    )
    add_manifest_provenance_edges(nodes, edges, manifest_payload=manifest_payload)
    add_manifest_lifecycle_edges(
        nodes,
        edges,
        report_trace=report_trace,
        task_node_keys=task_node_keys,
        manifest_node_key=manifest_node_key,
        verification_record_node_key=verification_record_node_key,
    )

    node_specs = sorted(nodes.values(), key=lambda item: item["node_key"])
    edge_specs = sorted(edges, key=lambda item: item["edge_key"])
    return node_specs, edge_specs, trace_graph_sha256(node_specs, edge_specs)
