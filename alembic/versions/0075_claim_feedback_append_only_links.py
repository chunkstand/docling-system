"""Make claim feedback late links append-only.

Revision ID: 0075_claim_feedback_append_links
Revises: 0074_claim_feedback_set_kind
Create Date: 2026-04-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0075_claim_feedback_append_links"
down_revision: str | Sequence[str] | None = "0074_claim_feedback_set_kind"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CREATE_APPEND_ONLY_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_tr_claim_feedback_core_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    late_link_changed boolean;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'technical_report_claim_retrieval_feedback rows are immutable'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF OLD.technical_report_verification_task_id IS DISTINCT FROM
       NEW.technical_report_verification_task_id
       OR OLD.claim_evidence_derivation_id IS DISTINCT FROM
          NEW.claim_evidence_derivation_id
       OR OLD.claim_id IS DISTINCT FROM NEW.claim_id
       OR OLD.claim_text IS DISTINCT FROM NEW.claim_text
       OR OLD.support_verdict IS DISTINCT FROM NEW.support_verdict
       OR OLD.support_score IS DISTINCT FROM NEW.support_score
       OR OLD.feedback_status IS DISTINCT FROM NEW.feedback_status
       OR OLD.learning_label IS DISTINCT FROM NEW.learning_label
       OR OLD.hard_negative_kind IS DISTINCT FROM NEW.hard_negative_kind
       OR OLD.source_search_request_id IS DISTINCT FROM NEW.source_search_request_id
       OR OLD.search_request_result_id IS DISTINCT FROM NEW.search_request_result_id
       OR OLD.source_search_request_ids IS DISTINCT FROM NEW.source_search_request_ids
       OR OLD.source_search_request_result_ids IS DISTINCT FROM
          NEW.source_search_request_result_ids
       OR OLD.search_request_result_span_ids IS DISTINCT FROM
          NEW.search_request_result_span_ids
       OR OLD.retrieval_evidence_span_ids IS DISTINCT FROM NEW.retrieval_evidence_span_ids
       OR OLD.semantic_ontology_snapshot_ids IS DISTINCT FROM
          NEW.semantic_ontology_snapshot_ids
       OR OLD.semantic_graph_snapshot_ids IS DISTINCT FROM NEW.semantic_graph_snapshot_ids
       OR OLD.retrieval_reranker_artifact_ids IS DISTINCT FROM
          NEW.retrieval_reranker_artifact_ids
       OR OLD.search_harness_release_ids IS DISTINCT FROM NEW.search_harness_release_ids
       OR OLD.release_audit_bundle_ids IS DISTINCT FROM NEW.release_audit_bundle_ids
       OR OLD.release_validation_receipt_ids IS DISTINCT FROM
          NEW.release_validation_receipt_ids
       OR OLD.evidence_refs IS DISTINCT FROM NEW.evidence_refs
       OR OLD.retrieval_context IS DISTINCT FROM NEW.retrieval_context
       OR OLD.feedback_payload IS DISTINCT FROM NEW.feedback_payload
       OR OLD.feedback_payload_sha256 IS DISTINCT FROM NEW.feedback_payload_sha256
       OR OLD.source_payload IS DISTINCT FROM NEW.source_payload
       OR OLD.source_payload_sha256 IS DISTINCT FROM NEW.source_payload_sha256
       OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION
            'technical_report_claim_retrieval_feedback core evidence fields are immutable'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF OLD.evidence_manifest_id IS NOT NULL
       AND OLD.evidence_manifest_id IS DISTINCT FROM NEW.evidence_manifest_id THEN
        RAISE EXCEPTION
            'technical_report_claim_retrieval_feedback evidence_manifest_id is append-only'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF OLD.prov_export_artifact_id IS NOT NULL
       AND OLD.prov_export_artifact_id IS DISTINCT FROM NEW.prov_export_artifact_id THEN
        RAISE EXCEPTION
            'technical_report_claim_retrieval_feedback prov_export_artifact_id is append-only'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF OLD.release_readiness_db_gate_id IS NOT NULL
       AND OLD.release_readiness_db_gate_id IS DISTINCT FROM
           NEW.release_readiness_db_gate_id THEN
        RAISE EXCEPTION
            'technical_report_claim_retrieval_feedback release_readiness_db_gate_id is append-only'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF OLD.semantic_governance_event_id IS NOT NULL
       AND OLD.semantic_governance_event_id IS DISTINCT FROM
           NEW.semantic_governance_event_id THEN
        RAISE EXCEPTION
            'technical_report_claim_retrieval_feedback semantic_governance_event_id is append-only'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    late_link_changed :=
        OLD.evidence_manifest_id IS DISTINCT FROM NEW.evidence_manifest_id
        OR OLD.prov_export_artifact_id IS DISTINCT FROM NEW.prov_export_artifact_id
        OR OLD.release_readiness_db_gate_id IS DISTINCT FROM
           NEW.release_readiness_db_gate_id
        OR OLD.semantic_governance_event_id IS DISTINCT FROM
           NEW.semantic_governance_event_id;

    IF OLD.updated_at IS DISTINCT FROM NEW.updated_at
       AND NOT late_link_changed THEN
        RAISE EXCEPTION
            'technical_report_claim_retrieval_feedback updated_at may only change with late links'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF NEW.updated_at < OLD.updated_at THEN
        RAISE EXCEPTION
            'technical_report_claim_retrieval_feedback updated_at cannot move backwards'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    RETURN NEW;
END;
$$;
"""


CREATE_LOOSE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_tr_claim_feedback_core_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'technical_report_claim_retrieval_feedback rows are immutable'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF OLD.technical_report_verification_task_id IS DISTINCT FROM
       NEW.technical_report_verification_task_id
       OR OLD.claim_evidence_derivation_id IS DISTINCT FROM
          NEW.claim_evidence_derivation_id
       OR OLD.claim_id IS DISTINCT FROM NEW.claim_id
       OR OLD.claim_text IS DISTINCT FROM NEW.claim_text
       OR OLD.support_verdict IS DISTINCT FROM NEW.support_verdict
       OR OLD.support_score IS DISTINCT FROM NEW.support_score
       OR OLD.feedback_status IS DISTINCT FROM NEW.feedback_status
       OR OLD.learning_label IS DISTINCT FROM NEW.learning_label
       OR OLD.hard_negative_kind IS DISTINCT FROM NEW.hard_negative_kind
       OR OLD.source_search_request_id IS DISTINCT FROM NEW.source_search_request_id
       OR OLD.search_request_result_id IS DISTINCT FROM NEW.search_request_result_id
       OR OLD.source_search_request_ids IS DISTINCT FROM NEW.source_search_request_ids
       OR OLD.source_search_request_result_ids IS DISTINCT FROM
          NEW.source_search_request_result_ids
       OR OLD.search_request_result_span_ids IS DISTINCT FROM
          NEW.search_request_result_span_ids
       OR OLD.retrieval_evidence_span_ids IS DISTINCT FROM NEW.retrieval_evidence_span_ids
       OR OLD.semantic_ontology_snapshot_ids IS DISTINCT FROM
          NEW.semantic_ontology_snapshot_ids
       OR OLD.semantic_graph_snapshot_ids IS DISTINCT FROM NEW.semantic_graph_snapshot_ids
       OR OLD.retrieval_reranker_artifact_ids IS DISTINCT FROM
          NEW.retrieval_reranker_artifact_ids
       OR OLD.search_harness_release_ids IS DISTINCT FROM NEW.search_harness_release_ids
       OR OLD.release_audit_bundle_ids IS DISTINCT FROM NEW.release_audit_bundle_ids
       OR OLD.release_validation_receipt_ids IS DISTINCT FROM
          NEW.release_validation_receipt_ids
       OR OLD.evidence_refs IS DISTINCT FROM NEW.evidence_refs
       OR OLD.retrieval_context IS DISTINCT FROM NEW.retrieval_context
       OR OLD.feedback_payload IS DISTINCT FROM NEW.feedback_payload
       OR OLD.feedback_payload_sha256 IS DISTINCT FROM NEW.feedback_payload_sha256
       OR OLD.source_payload IS DISTINCT FROM NEW.source_payload
       OR OLD.source_payload_sha256 IS DISTINCT FROM NEW.source_payload_sha256
       OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION
            'technical_report_claim_retrieval_feedback core evidence fields are immutable'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    op.execute(CREATE_APPEND_ONLY_FUNCTION_SQL)


def downgrade() -> None:
    op.execute(CREATE_LOOSE_FUNCTION_SQL)
