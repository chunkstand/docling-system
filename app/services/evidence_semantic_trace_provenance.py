# ruff: noqa: E501
from __future__ import annotations

from typing import Any

from app.services.evidence_constants import (
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
)
from app.services.evidence_release_readiness import (
    release_readiness_db_gate_trace_ref as _release_readiness_db_gate_trace_ref,
)


def _technical_report_provenance_edges(
    *,
    source_documents: list[dict[str, Any]],
    document_runs: list[dict[str, Any]],
    evidence_exports: list[dict[str, Any]],
    evidence_cards: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    claim_derivations: list[dict[str, Any]],
    claim_retrieval_feedback: list[dict[str, Any]],
    semantic_trace: dict[str, Any],
    context_pack_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    harness_task_id = context_pack_audit.get("harness_task_id")
    context_pack_artifacts = list(context_pack_audit.get("context_pack_artifacts") or [])
    evaluation_artifacts = list(context_pack_audit.get("evaluation_artifacts") or [])
    context_pack_verifications = list(context_pack_audit.get("verifications") or [])
    context_pack_operator_runs = list(context_pack_audit.get("operator_runs") or [])
    release_readiness_assessments = list(
        context_pack_audit.get("release_readiness_assessments") or []
    )
    release_readiness_db_gate = dict(context_pack_audit.get("release_readiness_db_gate") or {})
    release_readiness_db_gate_ref = _release_readiness_db_gate_trace_ref(context_pack_audit)
    for artifact in context_pack_artifacts:
        artifact_id = artifact.get("artifact_id")
        if harness_task_id and artifact_id:
            edges.append(
                {
                    "edge_type": "harness_task_to_context_pack_artifact",
                    "from": {"table": "agent_tasks", "id": harness_task_id},
                    "to": {"table": "agent_task_artifacts", "id": artifact_id},
                }
            )
    for verification in context_pack_verifications:
        verification_id = verification.get("verification_id")
        verification_task_id = verification.get("verification_task_id")
        if verification_task_id and verification_id:
            edges.append(
                {
                    "edge_type": "context_pack_eval_task_to_verifier_record",
                    "from": {"table": "agent_tasks", "id": verification_task_id},
                    "to": {"table": "agent_task_verifications", "id": verification_id},
                }
            )
        for artifact in context_pack_artifacts:
            artifact_id = artifact.get("artifact_id")
            if artifact_id and verification_id:
                edges.append(
                    {
                        "edge_type": "context_pack_artifact_to_verifier_record",
                        "from": {"table": "agent_task_artifacts", "id": artifact_id},
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                        "context_pack_sha256": verification.get("details", {}).get(
                            "context_pack_sha256"
                        ),
                    }
                )
        db_gate_verification_id = release_readiness_db_gate.get("verification_id")
        if (
            verification_id
            and db_gate_verification_id == str(verification_id)
            and release_readiness_db_gate_ref
        ):
            edges.append(
                {
                    "edge_type": "context_pack_verifier_record_to_release_readiness_db_gate",
                    "from": {"table": "agent_task_verifications", "id": verification_id},
                    "to": release_readiness_db_gate_ref,
                    "complete": release_readiness_db_gate.get("complete"),
                }
            )
    for artifact in evaluation_artifacts:
        artifact_id = artifact.get("artifact_id")
        task_id = artifact.get("task_id")
        if task_id and artifact_id:
            edges.append(
                {
                    "edge_type": "context_pack_eval_task_to_evaluation_artifact",
                    "from": {"table": "agent_tasks", "id": task_id},
                    "to": {"table": "agent_task_artifacts", "id": artifact_id},
                }
            )
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if verification_id and artifact_id:
                edges.append(
                    {
                        "edge_type": "context_pack_verifier_record_to_evaluation_artifact",
                        "from": {"table": "agent_task_verifications", "id": verification_id},
                        "to": {"table": "agent_task_artifacts", "id": artifact_id},
                    }
                )
    for operator_run in context_pack_operator_runs:
        operator_run_id = operator_run.get("operator_run_id")
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if operator_run_id and verification_id:
                edges.append(
                    {
                        "edge_type": "context_pack_eval_operator_to_verifier_record",
                        "from": {"table": "knowledge_operator_runs", "id": operator_run_id},
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                    }
                )
    for readiness_ref in release_readiness_assessments:
        assessment_id = readiness_ref.get("assessment_id")
        release_id = readiness_ref.get("search_harness_release_id")
        if release_id and assessment_id:
            edges.append(
                {
                    "edge_type": "search_harness_release_to_readiness_assessment",
                    "from": {"table": "search_harness_releases", "id": release_id},
                    "to": {
                        "table": "search_harness_release_readiness_assessments",
                        "id": assessment_id,
                    },
                }
            )
        for artifact in context_pack_artifacts:
            artifact_id = artifact.get("artifact_id")
            if assessment_id and artifact_id:
                edges.append(
                    {
                        "edge_type": "release_readiness_assessment_to_context_pack_artifact",
                        "from": {
                            "table": "search_harness_release_readiness_assessments",
                            "id": assessment_id,
                        },
                        "to": {"table": "agent_task_artifacts", "id": artifact_id},
                        "assessment_payload_sha256": readiness_ref.get("assessment_payload_sha256"),
                    }
                )
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if assessment_id and verification_id:
                edges.append(
                    {
                        "edge_type": "release_readiness_assessment_to_context_pack_verifier_record",
                        "from": {
                            "table": "search_harness_release_readiness_assessments",
                            "id": assessment_id,
                        },
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                    }
                )
        db_gate_verification_id = release_readiness_db_gate.get("verification_id")
        if assessment_id and db_gate_verification_id and release_readiness_db_gate_ref:
            edges.append(
                {
                    "edge_type": "release_readiness_assessment_to_release_readiness_db_gate",
                    "from": {
                        "table": "search_harness_release_readiness_assessments",
                        "id": assessment_id,
                    },
                    "to": release_readiness_db_gate_ref,
                    "assessment_payload_sha256": readiness_ref.get("assessment_payload_sha256"),
                }
            )
    for export in evidence_exports:
        if export.get("package_kind") == "search_request" and export.get("search_request_id"):
            edges.append(
                {
                    "edge_type": "search_request_to_evidence_package_export",
                    "from": {"table": "search_requests", "id": export.get("search_request_id")},
                    "to": {
                        "table": "evidence_package_exports",
                        "id": export.get("evidence_package_export_id"),
                    },
                }
            )
    for run in document_runs:
        if run.get("document_id"):
            edges.append(
                {
                    "edge_type": "source_document_to_document_run",
                    "from": {"table": "documents", "id": run.get("document_id")},
                    "to": {"table": "document_runs", "id": run.get("id")},
                }
            )
    for evidence in semantic_trace["assertion_evidence"]:
        target_id = evidence.get(f"{evidence.get('source_type')}_id")
        if target_id:
            edges.append(
                {
                    "edge_type": "document_run_to_source_record",
                    "from": {"table": "document_runs", "id": evidence.get("run_id")},
                    "to": {
                        "table": f"document_{evidence.get('source_type')}s",
                        "id": target_id,
                    },
                }
            )
    for card in evidence_cards:
        for export_id in card.get("source_evidence_package_export_ids") or []:
            edges.append(
                {
                    "edge_type": "search_evidence_export_to_report_card",
                    "from": {"table": "evidence_package_exports", "id": export_id},
                    "to": {
                        "table": "technical_report_evidence_cards",
                        "id": card.get("evidence_card_id"),
                    },
                }
            )
        for evidence_id in card.get("evidence_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_evidence_to_report_card",
                    "from": {"table": "semantic_assertion_evidence", "id": evidence_id},
                    "to": {
                        "table": "technical_report_evidence_cards",
                        "id": card.get("evidence_card_id"),
                    },
                }
            )
    for claim in claims:
        if claim.get("provenance_lock_sha256"):
            edges.append(
                {
                    "edge_type": "claim_to_provenance_lock",
                    "from": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "to": {
                        "table": "technical_report_claim_provenance_locks",
                        "id": claim.get("provenance_lock_sha256"),
                    },
                    "derivation_sha256": claim.get("derivation_sha256"),
                }
            )
        if claim.get("support_judgment_sha256"):
            edges.append(
                {
                    "edge_type": "claim_to_support_judgment",
                    "from": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "to": {
                        "table": "technical_report_claim_support_judgments",
                        "id": claim.get("support_judgment_sha256"),
                    },
                    "derivation_sha256": claim.get("derivation_sha256"),
                    "support_verdict": claim.get("support_verdict"),
                    "support_score": claim.get("support_score"),
                }
            )
        if claim.get("support_judge_run_id"):
            edges.append(
                {
                    "edge_type": "support_judge_run_to_claim",
                    "from": {
                        "table": "knowledge_operator_runs",
                        "id": claim.get("support_judge_run_id"),
                    },
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "support_judgment_sha256": claim.get("support_judgment_sha256"),
                }
            )
        for result_id in claim.get("source_search_request_result_ids") or []:
            edges.append(
                {
                    "edge_type": "search_result_to_claim",
                    "from": {"table": "search_request_results", "id": result_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for export_id in claim.get("source_evidence_package_export_ids") or []:
            edges.append(
                {
                    "edge_type": "search_evidence_export_to_claim",
                    "from": {"table": "evidence_package_exports", "id": export_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for snapshot_id in claim.get("semantic_ontology_snapshot_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_ontology_snapshot_to_claim",
                    "from": {"table": "semantic_ontology_snapshots", "id": snapshot_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for snapshot_id in claim.get("semantic_graph_snapshot_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_graph_snapshot_to_claim",
                    "from": {"table": "semantic_graph_snapshots", "id": snapshot_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for artifact_id in claim.get("retrieval_reranker_artifact_ids") or []:
            edges.append(
                {
                    "edge_type": "retrieval_reranker_artifact_to_claim",
                    "from": {"table": "retrieval_reranker_artifacts", "id": artifact_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for release_id in claim.get("search_harness_release_ids") or []:
            edges.append(
                {
                    "edge_type": "search_harness_release_to_claim",
                    "from": {"table": "search_harness_releases", "id": release_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for bundle_id in claim.get("release_audit_bundle_ids") or []:
            edges.append(
                {
                    "edge_type": "release_audit_bundle_to_claim",
                    "from": {"table": "audit_bundle_exports", "id": bundle_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for receipt_id in claim.get("release_validation_receipt_ids") or []:
            edges.append(
                {
                    "edge_type": "release_validation_receipt_to_claim",
                    "from": {"table": "audit_bundle_validation_receipts", "id": receipt_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for card_id in claim.get("evidence_card_ids") or []:
            edges.append(
                {
                    "edge_type": "report_card_to_claim",
                    "from": {"table": "technical_report_evidence_cards", "id": card_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
    for derivation in claim_derivations:
        edges.append(
            {
                "edge_type": "claim_to_derivation_hash",
                "from": {
                    "table": "technical_report_claims",
                    "id": derivation.get("claim_id"),
                },
                "to": {
                    "table": "claim_evidence_derivations",
                    "id": derivation.get("claim_evidence_derivation_id"),
                },
                "derivation_sha256": derivation.get("derivation_sha256"),
            }
        )
    for feedback in claim_retrieval_feedback:
        feedback_id = feedback.get("feedback_id")
        claim_id = feedback.get("claim_id")
        if feedback_id and claim_id:
            edges.append(
                {
                    "edge_type": "claim_to_retrieval_feedback",
                    "from": {"table": "technical_report_claims", "id": claim_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                    "feedback_payload_sha256": feedback.get("feedback_payload_sha256"),
                    "source_payload_sha256": feedback.get("source_payload_sha256"),
                }
            )
        gate_id = feedback.get("release_readiness_db_gate_id")
        if feedback_id and gate_id:
            edges.append(
                {
                    "edge_type": "release_readiness_db_gate_to_claim_retrieval_feedback",
                    "from": {
                        "table": TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
                        "id": gate_id,
                    },
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                    "feedback_payload_sha256": feedback.get("feedback_payload_sha256"),
                }
            )
        for request_id in feedback.get("source_search_request_ids") or []:
            edges.append(
                {
                    "edge_type": "search_request_to_claim_retrieval_feedback",
                    "from": {"table": "search_requests", "id": request_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                }
            )
        for result_id in feedback.get("source_search_request_result_ids") or []:
            edges.append(
                {
                    "edge_type": "search_result_to_claim_retrieval_feedback",
                    "from": {"table": "search_request_results", "id": result_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                }
            )
        for span_id in feedback.get("search_request_result_span_ids") or []:
            edges.append(
                {
                    "edge_type": "selected_span_to_claim_retrieval_feedback",
                    "from": {"table": "search_request_result_spans", "id": span_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                }
            )
        governance_event_id = feedback.get("semantic_governance_event_id")
        if feedback_id and governance_event_id:
            edges.append(
                {
                    "edge_type": "semantic_governance_event_to_claim_retrieval_feedback",
                    "from": {"table": "semantic_governance_events", "id": governance_event_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                }
            )
    for document in source_documents:
        edges.append(
            {
                "edge_type": "source_pdf_checksum",
                "from": {"table": "source_pdf", "sha256": document.get("sha256")},
                "to": {"table": "documents", "id": document.get("id")},
            }
        )
    return edges


technical_report_provenance_edges = _technical_report_provenance_edges
