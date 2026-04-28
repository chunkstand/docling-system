"""Add claim support policy activation governance events.

Revision ID: 0059_claim_policy_governance
Revises: 0058_claim_policy_activation
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0059_claim_policy_governance"
down_revision: str | Sequence[str] | None = "0058_claim_policy_activation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'technical_report_prov_export_frozen', "
    "'retrieval_training_run_materialized', "
    "'retrieval_learning_candidate_evaluated', "
    "'retrieval_reranker_artifact_materialized', "
    "'claim_support_policy_activated'"
    ")"
)

LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL = (
    "event_kind IN ("
    "'ontology_snapshot_recorded', "
    "'ontology_snapshot_activated', "
    "'semantic_graph_snapshot_recorded', "
    "'semantic_graph_snapshot_activated', "
    "'search_harness_release_recorded', "
    "'technical_report_prov_export_frozen', "
    "'retrieval_training_run_materialized', "
    "'retrieval_learning_candidate_evaluated', "
    "'retrieval_reranker_artifact_materialized'"
    ")"
)

PROTECTED_ARTIFACT_MUTATION_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_frozen_agent_task_artifact_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND (
           OLD.artifact_kind IN (
               'technical_report_prov_export',
               'claim_support_policy_activation_governance'
           )
           OR NEW.artifact_kind IN (
               'technical_report_prov_export',
               'claim_support_policy_activation_governance'
           )
       )
    THEN
        INSERT INTO agent_task_artifact_immutability_events (
            artifact_id,
            task_id,
            event_kind,
            mutation_operation,
            frozen_artifact_kind,
            attempted_artifact_kind,
            frozen_storage_path,
            attempted_storage_path,
            frozen_payload_sha256,
            attempted_payload_sha256,
            details,
            created_at
        )
        VALUES (
            OLD.id,
            OLD.task_id,
            'mutation_blocked',
            TG_OP,
            OLD.artifact_kind,
            NEW.artifact_kind,
            OLD.storage_path,
            NEW.storage_path,
            COALESCE(
                OLD.payload #>> '{frozen_export,export_payload_sha256}',
                OLD.payload #>> '{activation_governance_receipt,signed_payload_sha256}',
                OLD.payload #>> '{activation_governance_payload_sha256}'
            ),
            COALESCE(
                NEW.payload #>> '{frozen_export,export_payload_sha256}',
                NEW.payload #>> '{activation_governance_receipt,signed_payload_sha256}',
                NEW.payload #>> '{activation_governance_payload_sha256}'
            ),
            jsonb_build_object(
                'reason', 'frozen governance artifacts are immutable',
                'protected_artifact_kinds', jsonb_build_array(
                    'technical_report_prov_export',
                    'claim_support_policy_activation_governance'
                )
            ),
            now()
        );
        RETURN OLD;
    END IF;

    IF TG_OP = 'DELETE'
       AND OLD.artifact_kind IN (
           'technical_report_prov_export',
           'claim_support_policy_activation_governance'
       )
    THEN
        INSERT INTO agent_task_artifact_immutability_events (
            artifact_id,
            task_id,
            event_kind,
            mutation_operation,
            frozen_artifact_kind,
            attempted_artifact_kind,
            frozen_storage_path,
            attempted_storage_path,
            frozen_payload_sha256,
            attempted_payload_sha256,
            details,
            created_at
        )
        VALUES (
            OLD.id,
            OLD.task_id,
            'mutation_blocked',
            TG_OP,
            OLD.artifact_kind,
            NULL,
            OLD.storage_path,
            NULL,
            COALESCE(
                OLD.payload #>> '{frozen_export,export_payload_sha256}',
                OLD.payload #>> '{activation_governance_receipt,signed_payload_sha256}',
                OLD.payload #>> '{activation_governance_payload_sha256}'
            ),
            NULL,
            jsonb_build_object(
                'reason', 'frozen governance artifacts are immutable',
                'protected_artifact_kinds', jsonb_build_array(
                    'technical_report_prov_export',
                    'claim_support_policy_activation_governance'
                )
            ),
            now()
        );
        RETURN NULL;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
"""

LEGACY_PROTECTED_ARTIFACT_MUTATION_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_frozen_agent_task_artifact_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND (
           OLD.artifact_kind = 'technical_report_prov_export'
           OR NEW.artifact_kind = 'technical_report_prov_export'
       )
    THEN
        INSERT INTO agent_task_artifact_immutability_events (
            artifact_id,
            task_id,
            event_kind,
            mutation_operation,
            frozen_artifact_kind,
            attempted_artifact_kind,
            frozen_storage_path,
            attempted_storage_path,
            frozen_payload_sha256,
            attempted_payload_sha256,
            details,
            created_at
        )
        VALUES (
            OLD.id,
            OLD.task_id,
            'mutation_blocked',
            TG_OP,
            OLD.artifact_kind,
            NEW.artifact_kind,
            OLD.storage_path,
            NEW.storage_path,
            OLD.payload #>> '{frozen_export,export_payload_sha256}',
            NEW.payload #>> '{frozen_export,export_payload_sha256}',
            jsonb_build_object(
                'reason', 'technical_report_prov_export artifacts are immutable',
                'protected_artifact_kind', 'technical_report_prov_export'
            ),
            now()
        );
        RETURN OLD;
    END IF;

    IF TG_OP = 'DELETE'
       AND OLD.artifact_kind = 'technical_report_prov_export'
    THEN
        INSERT INTO agent_task_artifact_immutability_events (
            artifact_id,
            task_id,
            event_kind,
            mutation_operation,
            frozen_artifact_kind,
            attempted_artifact_kind,
            frozen_storage_path,
            attempted_storage_path,
            frozen_payload_sha256,
            attempted_payload_sha256,
            details,
            created_at
        )
        VALUES (
            OLD.id,
            OLD.task_id,
            'mutation_blocked',
            TG_OP,
            OLD.artifact_kind,
            NULL,
            OLD.storage_path,
            NULL,
            OLD.payload #>> '{frozen_export,export_payload_sha256}',
            NULL,
            jsonb_build_object(
                'reason', 'technical_report_prov_export artifacts are immutable',
                'protected_artifact_kind', 'technical_report_prov_export'
            ),
            now()
        );
        RETURN NULL;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
"""


def _replace_semantic_governance_event_kind_constraint(sql_text: str) -> None:
    op.drop_constraint(
        "ck_semantic_governance_events_event_kind",
        "semantic_governance_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_semantic_governance_events_event_kind",
        "semantic_governance_events",
        sql_text,
    )


def upgrade() -> None:
    _replace_semantic_governance_event_kind_constraint(
        SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL
    )
    op.execute(PROTECTED_ARTIFACT_MUTATION_FUNCTION_SQL)


def downgrade() -> None:
    _replace_semantic_governance_event_kind_constraint(
        LEGACY_SEMANTIC_GOVERNANCE_EVENT_KIND_CHECK_SQL
    )
    op.execute(LEGACY_PROTECTED_ARTIFACT_MUTATION_FUNCTION_SQL)
