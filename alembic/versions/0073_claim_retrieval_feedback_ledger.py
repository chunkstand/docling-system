"""Add technical report claim retrieval feedback ledger.

Revision ID: 0073_claim_feedback_ledger
Revises: 0072_tr_gate_harden
Create Date: 2026-04-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0073_claim_feedback_ledger"
down_revision: str | Sequence[str] | None = "0072_tr_gate_harden"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADED_GOVERNANCE_EVENT_KIND_CHECK = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'search_harness_release_readiness_assessed', "
    "'technical_report_prov_export_frozen', "
    "'technical_report_readiness_db_gate_recorded', "
    "'technical_report_claim_retrieval_feedback_recorded', "
    "'retrieval_training_run_materialized', "
    "'retrieval_learning_candidate_evaluated', "
    "'retrieval_reranker_artifact_materialized', "
    "'claim_support_policy_activated', "
    "'claim_support_policy_impact_replay_closed', "
    "'claim_support_policy_impact_replay_escalated', "
    "'claim_support_policy_impact_fixture_promoted', "
    "'claim_support_replay_alert_fixture_coverage_waiver_closed', "
    "'claim_support_replay_alert_fixture_corpus_snapshot_activated'"
    ")"
)

DOWNGRADED_GOVERNANCE_EVENT_KIND_CHECK = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'search_harness_release_readiness_assessed', "
    "'technical_report_prov_export_frozen', "
    "'technical_report_readiness_db_gate_recorded', "
    "'retrieval_training_run_materialized', "
    "'retrieval_learning_candidate_evaluated', "
    "'retrieval_reranker_artifact_materialized', "
    "'claim_support_policy_activated', "
    "'claim_support_policy_impact_replay_closed', "
    "'claim_support_policy_impact_replay_escalated', "
    "'claim_support_policy_impact_fixture_promoted', "
    "'claim_support_replay_alert_fixture_coverage_waiver_closed', "
    "'claim_support_replay_alert_fixture_corpus_snapshot_activated'"
    ")"
)

UPGRADED_RETRIEVAL_SOURCE_TYPE_CHECK = (
    "source_type IN ("
    "'feedback', "
    "'replay', "
    "'claim_support_replay_alert_corpus', "
    "'technical_report_claim_feedback'"
    ")"
)

DOWNGRADED_RETRIEVAL_SOURCE_TYPE_CHECK = (
    "source_type IN ('feedback', 'replay', 'claim_support_replay_alert_corpus')"
)

CREATE_CORE_IMMUTABILITY_FUNCTION_SQL = """
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

CREATE_CORE_IMMUTABILITY_TRIGGER_SQL = """
CREATE TRIGGER trg_tr_claim_feedback_prevent_core_mutation
BEFORE UPDATE OR DELETE ON technical_report_claim_retrieval_feedback
FOR EACH ROW
EXECUTE FUNCTION prevent_tr_claim_feedback_core_mutation();
"""


def _upgrade_check_constraints() -> None:
    op.drop_constraint(
        "ck_semantic_governance_events_event_kind",
        "semantic_governance_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_semantic_governance_events_event_kind",
        "semantic_governance_events",
        UPGRADED_GOVERNANCE_EVENT_KIND_CHECK,
    )
    op.drop_constraint(
        "ck_retrieval_judgments_source_type",
        "retrieval_judgments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_judgments_source_type",
        "retrieval_judgments",
        UPGRADED_RETRIEVAL_SOURCE_TYPE_CHECK,
    )
    op.drop_constraint(
        "ck_retrieval_hard_negatives_source_type",
        "retrieval_hard_negatives",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_hard_negatives_source_type",
        "retrieval_hard_negatives",
        UPGRADED_RETRIEVAL_SOURCE_TYPE_CHECK,
    )


def _downgrade_check_constraints() -> None:
    op.drop_constraint(
        "ck_retrieval_hard_negatives_source_type",
        "retrieval_hard_negatives",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_hard_negatives_source_type",
        "retrieval_hard_negatives",
        DOWNGRADED_RETRIEVAL_SOURCE_TYPE_CHECK,
    )
    op.drop_constraint(
        "ck_retrieval_judgments_source_type",
        "retrieval_judgments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_judgments_source_type",
        "retrieval_judgments",
        DOWNGRADED_RETRIEVAL_SOURCE_TYPE_CHECK,
    )
    op.execute(
        """
        DELETE FROM semantic_governance_events
        WHERE event_kind = 'technical_report_claim_retrieval_feedback_recorded';
        """
    )
    op.drop_constraint(
        "ck_semantic_governance_events_event_kind",
        "semantic_governance_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_semantic_governance_events_event_kind",
        "semantic_governance_events",
        DOWNGRADED_GOVERNANCE_EVENT_KIND_CHECK,
    )


def upgrade() -> None:
    _upgrade_check_constraints()
    op.create_table(
        "technical_report_claim_retrieval_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "technical_report_verification_task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("claim_evidence_derivation_id", postgresql.UUID(as_uuid=True)),
        sa.Column("evidence_manifest_id", postgresql.UUID(as_uuid=True)),
        sa.Column("prov_export_artifact_id", postgresql.UUID(as_uuid=True)),
        sa.Column("release_readiness_db_gate_id", postgresql.UUID(as_uuid=True)),
        sa.Column("semantic_governance_event_id", postgresql.UUID(as_uuid=True)),
        sa.Column("claim_id", sa.Text(), nullable=False),
        sa.Column("claim_text", sa.Text()),
        sa.Column("support_verdict", sa.Text(), nullable=False),
        sa.Column("support_score", sa.Float()),
        sa.Column("feedback_status", sa.Text(), nullable=False),
        sa.Column("learning_label", sa.Text(), nullable=False),
        sa.Column("hard_negative_kind", sa.Text()),
        sa.Column("source_search_request_id", postgresql.UUID(as_uuid=True)),
        sa.Column("search_request_result_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "source_search_request_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_search_request_result_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "search_request_result_span_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "retrieval_evidence_span_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "semantic_ontology_snapshot_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "semantic_graph_snapshot_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "retrieval_reranker_artifact_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "search_harness_release_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "release_audit_bundle_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "release_validation_receipt_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "retrieval_context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "feedback_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("feedback_payload_sha256", sa.Text(), nullable=False),
        sa.Column(
            "source_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("source_payload_sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["technical_report_verification_task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["claim_evidence_derivation_id"],
            ["claim_evidence_derivations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_manifest_id"],
            ["evidence_manifests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["prov_export_artifact_id"],
            ["agent_task_artifacts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["release_readiness_db_gate_id"],
            ["technical_report_release_readiness_db_gates.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_governance_event_id"],
            ["semantic_governance_events.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_search_request_id"],
            ["search_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_request_result_id"],
            ["search_request_results.id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "support_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_tr_claim_feedback_support_verdict",
        ),
        sa.CheckConstraint(
            "feedback_status IN ('supported', 'weak', 'missing', 'contradicted', 'rejected')",
            name="ck_tr_claim_feedback_status",
        ),
        sa.CheckConstraint(
            "learning_label IN ('positive', 'negative', 'missing')",
            name="ck_tr_claim_feedback_learning_label",
        ),
        sa.CheckConstraint(
            "hard_negative_kind IS NULL OR hard_negative_kind IN ("
            "'explicit_irrelevant', "
            "'missing_expected', "
            "'failed_replay_top_result', "
            "'wrong_result_type', "
            "'no_answer_returned'"
            ")",
            name="ck_tr_claim_feedback_hard_negative_kind",
        ),
        sa.CheckConstraint(
            "char_length(feedback_payload_sha256) = 64",
            name="ck_tr_claim_feedback_payload_sha_length",
        ),
        sa.CheckConstraint(
            "char_length(source_payload_sha256) = 64",
            name="ck_tr_claim_feedback_source_sha_length",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "technical_report_verification_task_id",
            "claim_id",
            name="uq_tr_claim_feedback_verification_claim",
        ),
    )
    op.create_index(
        "ix_tr_claim_feedback_verification_task",
        "technical_report_claim_retrieval_feedback",
        ["technical_report_verification_task_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_claim",
        "technical_report_claim_retrieval_feedback",
        ["claim_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_derivation",
        "technical_report_claim_retrieval_feedback",
        ["claim_evidence_derivation_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_manifest",
        "technical_report_claim_retrieval_feedback",
        ["evidence_manifest_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_prov_artifact",
        "technical_report_claim_retrieval_feedback",
        ["prov_export_artifact_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_release_gate",
        "technical_report_claim_retrieval_feedback",
        ["release_readiness_db_gate_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_governance",
        "technical_report_claim_retrieval_feedback",
        ["semantic_governance_event_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_source_request",
        "technical_report_claim_retrieval_feedback",
        ["source_search_request_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_search_result",
        "technical_report_claim_retrieval_feedback",
        ["search_request_result_id"],
    )
    op.create_index(
        "ix_tr_claim_feedback_status_label",
        "technical_report_claim_retrieval_feedback",
        ["feedback_status", "learning_label"],
    )
    op.create_index(
        "ix_tr_claim_feedback_payload_sha",
        "technical_report_claim_retrieval_feedback",
        ["feedback_payload_sha256"],
    )
    op.create_index(
        "ix_tr_claim_feedback_created",
        "technical_report_claim_retrieval_feedback",
        ["created_at"],
    )
    op.execute(CREATE_CORE_IMMUTABILITY_FUNCTION_SQL)
    op.execute(CREATE_CORE_IMMUTABILITY_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_tr_claim_feedback_prevent_core_mutation
        ON technical_report_claim_retrieval_feedback;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_tr_claim_feedback_core_mutation();")
    for index_name in [
        "ix_tr_claim_feedback_created",
        "ix_tr_claim_feedback_payload_sha",
        "ix_tr_claim_feedback_status_label",
        "ix_tr_claim_feedback_search_result",
        "ix_tr_claim_feedback_source_request",
        "ix_tr_claim_feedback_governance",
        "ix_tr_claim_feedback_release_gate",
        "ix_tr_claim_feedback_prov_artifact",
        "ix_tr_claim_feedback_manifest",
        "ix_tr_claim_feedback_derivation",
        "ix_tr_claim_feedback_claim",
        "ix_tr_claim_feedback_verification_task",
    ]:
        op.drop_index(index_name, table_name="technical_report_claim_retrieval_feedback")
    op.drop_table("technical_report_claim_retrieval_feedback")
    _downgrade_check_constraints()
