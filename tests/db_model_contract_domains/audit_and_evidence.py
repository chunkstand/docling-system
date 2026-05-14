"""DB model contract fragment for audit and evidence."""

from __future__ import annotations

MODEL_SYMBOLS = (
    "AuditBundleExport",
    "AuditBundleValidationReceipt",
    "EvidencePackageExport",
    "EvidenceManifest",
    "TechnicalReportReleaseReadinessDbGate",
    "TechnicalReportClaimRetrievalFeedback",
    "EvidenceTraceNode",
    "EvidenceTraceEdge",
    "ClaimEvidenceDerivation",
)

AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS = {
    "audit_bundle_exports": frozenset(
        {
            "bundle_kind",
            "bundle_payload",
            "bundle_sha256",
            "created_at",
            "created_by",
            "export_status",
            "id",
            "integrity",
            "payload_sha256",
            "retrieval_training_run_id",
            "search_harness_release_id",
            "signature",
            "signature_algorithm",
            "signing_key_id",
            "source_id",
            "source_table",
            "storage_path",
        }
    ),
    "audit_bundle_validation_receipts": frozenset(
        {
            "audit_bundle_export_id",
            "bundle_integrity_valid",
            "bundle_kind",
            "created_at",
            "created_by",
            "id",
            "payload_schema_valid",
            "prov_graph_valid",
            "prov_jsonld",
            "prov_jsonld_sha256",
            "prov_jsonld_storage_path",
            "receipt_payload",
            "receipt_sha256",
            "receipt_storage_path",
            "semantic_governance_valid",
            "signature",
            "signature_algorithm",
            "signing_key_id",
            "source_id",
            "source_integrity_valid",
            "source_table",
            "validation_errors",
            "validation_profile",
            "validation_status",
        }
    ),
    "evidence_package_exports": frozenset(
        {
            "agent_task_artifact_id",
            "agent_task_id",
            "claim_ids",
            "created_at",
            "document_ids",
            "export_status",
            "id",
            "operator_run_ids",
            "package_kind",
            "package_payload",
            "package_sha256",
            "run_ids",
            "search_request_id",
            "source_snapshot_sha256s",
            "trace_sha256",
        }
    ),
    "evidence_manifests": frozenset(
        {
            "agent_task_id",
            "claim_ids",
            "created_at",
            "document_ids",
            "draft_task_id",
            "evidence_package_export_id",
            "id",
            "manifest_kind",
            "manifest_payload",
            "manifest_sha256",
            "manifest_status",
            "operator_run_ids",
            "run_ids",
            "search_request_ids",
            "source_snapshot_sha256s",
            "trace_sha256",
            "verification_task_id",
        }
    ),
    "technical_report_release_readiness_db_gates": frozenset(
        {
            "check_key",
            "complete",
            "coverage_complete",
            "created_at",
            "evidence_manifest_id",
            "failure_count",
            "gate_payload",
            "gate_payload_sha256",
            "harness_task_id",
            "id",
            "missing_expected_request_ids",
            "passed",
            "prov_export_artifact_id",
            "required",
            "semantic_governance_event_id",
            "source_search_request_count",
            "source_search_request_ids",
            "source_verification_id",
            "source_verification_task_id",
            "summary",
            "technical_report_verification_task_id",
            "unexpected_verified_request_ids",
            "updated_at",
            "verified_request_count",
            "verified_request_ids",
        }
    ),
    "technical_report_claim_retrieval_feedback": frozenset(
        {
            "claim_evidence_derivation_id",
            "claim_id",
            "claim_text",
            "created_at",
            "evidence_manifest_id",
            "evidence_refs",
            "feedback_payload",
            "feedback_payload_sha256",
            "feedback_status",
            "hard_negative_kind",
            "id",
            "learning_label",
            "prov_export_artifact_id",
            "release_audit_bundle_ids",
            "release_readiness_db_gate_id",
            "release_validation_receipt_ids",
            "retrieval_context",
            "retrieval_evidence_span_ids",
            "retrieval_reranker_artifact_ids",
            "search_harness_release_ids",
            "search_request_result_id",
            "search_request_result_span_ids",
            "semantic_governance_event_id",
            "semantic_graph_snapshot_ids",
            "semantic_ontology_snapshot_ids",
            "source_payload",
            "source_payload_sha256",
            "source_search_request_id",
            "source_search_request_ids",
            "source_search_request_result_ids",
            "support_score",
            "support_verdict",
            "technical_report_verification_task_id",
            "updated_at",
        }
    ),
    "evidence_trace_nodes": frozenset(
        {
            "content_sha256",
            "created_at",
            "evidence_manifest_id",
            "evidence_package_export_id",
            "id",
            "node_key",
            "node_kind",
            "payload",
            "source_id",
            "source_ref",
            "source_table",
        }
    ),
    "evidence_trace_edges": frozenset(
        {
            "content_sha256",
            "created_at",
            "derivation_sha256",
            "edge_key",
            "edge_kind",
            "evidence_manifest_id",
            "evidence_package_export_id",
            "from_node_id",
            "from_node_key",
            "id",
            "payload",
            "to_node_id",
            "to_node_key",
        }
    ),
    "claim_evidence_derivations": frozenset(
        {
            "agent_task_id",
            "assertion_ids",
            "claim_id",
            "claim_text",
            "created_at",
            "derivation_rule",
            "derivation_sha256",
            "evidence_card_ids",
            "evidence_package_export_id",
            "evidence_package_sha256",
            "fact_ids",
            "graph_edge_ids",
            "id",
            "provenance_lock",
            "provenance_lock_sha256",
            "release_audit_bundle_ids",
            "release_validation_receipt_ids",
            "retrieval_reranker_artifact_ids",
            "search_harness_release_ids",
            "semantic_graph_snapshot_ids",
            "semantic_ontology_snapshot_ids",
            "source_document_ids",
            "source_evidence_package_export_ids",
            "source_evidence_package_sha256s",
            "source_evidence_trace_sha256s",
            "source_search_request_ids",
            "source_search_request_result_ids",
            "source_snapshot_sha256s",
            "support_judge_run_id",
            "support_judgment",
            "support_judgment_sha256",
            "support_score",
            "support_verdict",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "audit_bundle_exports": frozenset(
        {
            "ix_audit_bundle_exports_bundle_kind_created_at",
            "ix_audit_bundle_exports_bundle_sha256",
            "ix_audit_bundle_exports_payload_sha256",
            "ix_audit_bundle_exports_release_created_at",
            "ix_audit_bundle_exports_source",
            "ix_audit_bundle_exports_training_run_created_at",
        }
    ),
    "audit_bundle_validation_receipts": frozenset(
        {
            "ix_audit_bundle_validation_receipts_bundle_created",
            "ix_audit_bundle_validation_receipts_prov_jsonld_sha",
            "ix_audit_bundle_validation_receipts_receipt_sha",
            "ix_audit_bundle_validation_receipts_source",
            "ix_audit_bundle_validation_receipts_status_created",
        }
    ),
    "evidence_package_exports": frozenset(
        {
            "ix_evidence_package_exports_agent_task_id",
            "ix_evidence_package_exports_created_at",
            "ix_evidence_package_exports_package_sha256",
            "ix_evidence_package_exports_search_request_id",
            "ix_evidence_package_exports_trace_sha256",
        }
    ),
    "evidence_manifests": frozenset(
        {
            "ix_evidence_manifests_agent_task_id",
            "ix_evidence_manifests_created_at",
            "ix_evidence_manifests_draft_task_id",
            "ix_evidence_manifests_export_id",
            "ix_evidence_manifests_manifest_sha256",
            "ix_evidence_manifests_trace_sha256",
            "ix_evidence_manifests_verification_task_id",
        }
    ),
    "technical_report_release_readiness_db_gates": frozenset(
        {
            "ix_tr_readiness_db_gates_created",
            "ix_tr_readiness_db_gates_governance",
            "ix_tr_readiness_db_gates_harness_task",
            "ix_tr_readiness_db_gates_manifest",
            "ix_tr_readiness_db_gates_payload_sha",
            "ix_tr_readiness_db_gates_prov_artifact",
            "ix_tr_readiness_db_gates_source_verification",
            "ix_tr_readiness_db_gates_verification_task",
        }
    ),
    "technical_report_claim_retrieval_feedback": frozenset(
        {
            "ix_tr_claim_feedback_claim",
            "ix_tr_claim_feedback_created",
            "ix_tr_claim_feedback_derivation",
            "ix_tr_claim_feedback_governance",
            "ix_tr_claim_feedback_manifest",
            "ix_tr_claim_feedback_payload_sha",
            "ix_tr_claim_feedback_prov_artifact",
            "ix_tr_claim_feedback_release_gate",
            "ix_tr_claim_feedback_search_result",
            "ix_tr_claim_feedback_source_request",
            "ix_tr_claim_feedback_status_label",
            "ix_tr_claim_feedback_verification_task",
        }
    ),
    "evidence_trace_nodes": frozenset(
        {
            "ix_evidence_trace_nodes_content_sha256",
            "ix_evidence_trace_nodes_export_id",
            "ix_evidence_trace_nodes_manifest_id",
            "ix_evidence_trace_nodes_node_kind",
            "ix_evidence_trace_nodes_source",
            "ix_evidence_trace_nodes_source_ref",
        }
    ),
    "evidence_trace_edges": frozenset(
        {
            "ix_evidence_trace_edges_content_sha256",
            "ix_evidence_trace_edges_derivation_sha256",
            "ix_evidence_trace_edges_edge_kind",
            "ix_evidence_trace_edges_export_id",
            "ix_evidence_trace_edges_from_node_id",
            "ix_evidence_trace_edges_manifest_id",
            "ix_evidence_trace_edges_to_node_id",
        }
    ),
    "claim_evidence_derivations": frozenset(
        {
            "ix_claim_evidence_derivations_agent_task_id",
            "ix_claim_evidence_derivations_claim_id",
            "ix_claim_evidence_derivations_derivation_sha256",
            "ix_claim_evidence_derivations_export_id",
            "ix_claim_evidence_derivations_provenance_lock_sha",
            "ix_claim_evidence_derivations_support_judge_run_id",
            "ix_claim_evidence_derivations_support_verdict",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
    "audit_bundle_exports": {
        "ix_audit_bundle_exports_bundle_kind_created_at": ("bundle_kind", "created_at"),
        "ix_audit_bundle_exports_source": ("source_table", "source_id"),
        "ix_audit_bundle_exports_release_created_at": ("search_harness_release_id", "created_at"),
        "ix_audit_bundle_exports_training_run_created_at": (
            "retrieval_training_run_id",
            "created_at",
        ),
        "ix_audit_bundle_exports_payload_sha256": ("payload_sha256",),
        "ix_audit_bundle_exports_bundle_sha256": ("bundle_sha256",),
    },
    "audit_bundle_validation_receipts": {
        "ix_audit_bundle_validation_receipts_bundle_created": (
            "audit_bundle_export_id",
            "created_at",
        ),
        "ix_audit_bundle_validation_receipts_source": ("source_table", "source_id", "created_at"),
        "ix_audit_bundle_validation_receipts_receipt_sha": ("receipt_sha256",),
        "ix_audit_bundle_validation_receipts_prov_jsonld_sha": ("prov_jsonld_sha256",),
        "ix_audit_bundle_validation_receipts_status_created": ("validation_status", "created_at"),
    },
    "evidence_package_exports": {
        "ix_evidence_package_exports_created_at": ("created_at",),
        "ix_evidence_package_exports_search_request_id": ("search_request_id",),
        "ix_evidence_package_exports_agent_task_id": ("agent_task_id",),
        "ix_evidence_package_exports_package_sha256": ("package_sha256",),
        "ix_evidence_package_exports_trace_sha256": ("trace_sha256",),
    },
    "evidence_manifests": {
        "ix_evidence_manifests_agent_task_id": ("agent_task_id",),
        "ix_evidence_manifests_draft_task_id": ("draft_task_id",),
        "ix_evidence_manifests_verification_task_id": ("verification_task_id",),
        "ix_evidence_manifests_export_id": ("evidence_package_export_id",),
        "ix_evidence_manifests_manifest_sha256": ("manifest_sha256",),
        "ix_evidence_manifests_trace_sha256": ("trace_sha256",),
        "ix_evidence_manifests_created_at": ("created_at",),
    },
    "technical_report_release_readiness_db_gates": {
        "ix_tr_readiness_db_gates_verification_task": ("technical_report_verification_task_id",),
        "ix_tr_readiness_db_gates_source_verification": ("source_verification_id",),
        "ix_tr_readiness_db_gates_harness_task": ("harness_task_id",),
        "ix_tr_readiness_db_gates_manifest": ("evidence_manifest_id",),
        "ix_tr_readiness_db_gates_prov_artifact": ("prov_export_artifact_id",),
        "ix_tr_readiness_db_gates_governance": ("semantic_governance_event_id",),
        "ix_tr_readiness_db_gates_payload_sha": ("gate_payload_sha256",),
        "ix_tr_readiness_db_gates_created": ("created_at",),
    },
    "technical_report_claim_retrieval_feedback": {
        "ix_tr_claim_feedback_verification_task": ("technical_report_verification_task_id",),
        "ix_tr_claim_feedback_claim": ("claim_id",),
        "ix_tr_claim_feedback_derivation": ("claim_evidence_derivation_id",),
        "ix_tr_claim_feedback_manifest": ("evidence_manifest_id",),
        "ix_tr_claim_feedback_prov_artifact": ("prov_export_artifact_id",),
        "ix_tr_claim_feedback_release_gate": ("release_readiness_db_gate_id",),
        "ix_tr_claim_feedback_governance": ("semantic_governance_event_id",),
        "ix_tr_claim_feedback_source_request": ("source_search_request_id",),
        "ix_tr_claim_feedback_search_result": ("search_request_result_id",),
        "ix_tr_claim_feedback_status_label": ("feedback_status", "learning_label"),
        "ix_tr_claim_feedback_payload_sha": ("feedback_payload_sha256",),
        "ix_tr_claim_feedback_created": ("created_at",),
    },
    "evidence_trace_nodes": {
        "ix_evidence_trace_nodes_manifest_id": ("evidence_manifest_id",),
        "ix_evidence_trace_nodes_export_id": ("evidence_package_export_id",),
        "ix_evidence_trace_nodes_node_kind": ("node_kind",),
        "ix_evidence_trace_nodes_source": ("source_table", "source_id"),
        "ix_evidence_trace_nodes_source_ref": ("source_table", "source_ref"),
        "ix_evidence_trace_nodes_content_sha256": ("content_sha256",),
    },
    "evidence_trace_edges": {
        "ix_evidence_trace_edges_manifest_id": ("evidence_manifest_id",),
        "ix_evidence_trace_edges_export_id": ("evidence_package_export_id",),
        "ix_evidence_trace_edges_edge_kind": ("edge_kind",),
        "ix_evidence_trace_edges_from_node_id": ("from_node_id",),
        "ix_evidence_trace_edges_to_node_id": ("to_node_id",),
        "ix_evidence_trace_edges_derivation_sha256": ("derivation_sha256",),
        "ix_evidence_trace_edges_content_sha256": ("content_sha256",),
    },
    "claim_evidence_derivations": {
        "ix_claim_evidence_derivations_export_id": ("evidence_package_export_id",),
        "ix_claim_evidence_derivations_agent_task_id": ("agent_task_id",),
        "ix_claim_evidence_derivations_claim_id": ("claim_id",),
        "ix_claim_evidence_derivations_derivation_sha256": ("derivation_sha256",),
        "ix_claim_evidence_derivations_support_verdict": ("support_verdict",),
        "ix_claim_evidence_derivations_support_judge_run_id": ("support_judge_run_id",),
        "ix_claim_evidence_derivations_provenance_lock_sha": ("provenance_lock_sha256",),
    },
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "evidence_manifests": frozenset({"uq_evidence_manifests_verification_task_kind"}),
    "technical_report_release_readiness_db_gates": frozenset(
        {"uq_tr_readiness_db_gates_verification_task"}
    ),
    "technical_report_claim_retrieval_feedback": frozenset(
        {"uq_tr_claim_feedback_verification_claim"}
    ),
    "evidence_trace_nodes": frozenset(
        {"uq_evidence_trace_nodes_export_node_key", "uq_evidence_trace_nodes_manifest_node_key"}
    ),
    "evidence_trace_edges": frozenset(
        {"uq_evidence_trace_edges_export_edge_key", "uq_evidence_trace_edges_manifest_edge_key"}
    ),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "evidence_manifests": {
        "uq_evidence_manifests_verification_task_kind": ("verification_task_id", "manifest_kind")
    },
    "technical_report_release_readiness_db_gates": {
        "uq_tr_readiness_db_gates_verification_task": ("technical_report_verification_task_id",)
    },
    "technical_report_claim_retrieval_feedback": {
        "uq_tr_claim_feedback_verification_claim": (
            "technical_report_verification_task_id",
            "claim_id",
        )
    },
    "evidence_trace_nodes": {
        "uq_evidence_trace_nodes_manifest_node_key": ("evidence_manifest_id", "node_key"),
        "uq_evidence_trace_nodes_export_node_key": ("evidence_package_export_id", "node_key"),
    },
    "evidence_trace_edges": {
        "uq_evidence_trace_edges_manifest_edge_key": ("evidence_manifest_id", "edge_key"),
        "uq_evidence_trace_edges_export_edge_key": ("evidence_package_export_id", "edge_key"),
    },
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
