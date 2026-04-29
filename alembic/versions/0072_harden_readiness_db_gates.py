"""harden technical report readiness DB gates

Revision ID: 0072_tr_gate_harden
Revises: 0071_tr_readiness_gate
Create Date: 2026-04-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0072_tr_gate_harden"
down_revision: str | Sequence[str] | None = "0071_tr_readiness_gate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CREATE_CORE_IMMUTABILITY_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_tr_readiness_db_gate_core_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'technical_report_release_readiness_db_gates rows are immutable'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF OLD.technical_report_verification_task_id IS DISTINCT FROM
       NEW.technical_report_verification_task_id
       OR OLD.source_verification_id IS DISTINCT FROM NEW.source_verification_id
       OR OLD.source_verification_task_id IS DISTINCT FROM NEW.source_verification_task_id
       OR OLD.harness_task_id IS DISTINCT FROM NEW.harness_task_id
       OR OLD.check_key IS DISTINCT FROM NEW.check_key
       OR OLD.passed IS DISTINCT FROM NEW.passed
       OR OLD.required IS DISTINCT FROM NEW.required
       OR OLD.coverage_complete IS DISTINCT FROM NEW.coverage_complete
       OR OLD.complete IS DISTINCT FROM NEW.complete
       OR OLD.source_search_request_count IS DISTINCT FROM NEW.source_search_request_count
       OR OLD.verified_request_count IS DISTINCT FROM NEW.verified_request_count
       OR OLD.failure_count IS DISTINCT FROM NEW.failure_count
       OR OLD.source_search_request_ids IS DISTINCT FROM NEW.source_search_request_ids
       OR OLD.verified_request_ids IS DISTINCT FROM NEW.verified_request_ids
       OR OLD.missing_expected_request_ids IS DISTINCT FROM NEW.missing_expected_request_ids
       OR OLD.unexpected_verified_request_ids IS DISTINCT FROM NEW.unexpected_verified_request_ids
       OR OLD.summary IS DISTINCT FROM NEW.summary
       OR OLD.gate_payload IS DISTINCT FROM NEW.gate_payload
       OR OLD.gate_payload_sha256 IS DISTINCT FROM NEW.gate_payload_sha256
       OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION
            'technical_report_release_readiness_db_gates core evidence fields are immutable'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    RETURN NEW;
END;
$$;
"""

CREATE_CORE_IMMUTABILITY_TRIGGER_SQL = """
CREATE TRIGGER trg_tr_readiness_db_gates_prevent_core_mutation
BEFORE UPDATE OR DELETE ON technical_report_release_readiness_db_gates
FOR EACH ROW
EXECUTE FUNCTION prevent_tr_readiness_db_gate_core_mutation();
"""


def upgrade() -> None:
    op.create_check_constraint(
        "ck_tr_readiness_db_gates_payload_sha_length",
        "technical_report_release_readiness_db_gates",
        "char_length(gate_payload_sha256) = 64",
    )
    op.create_check_constraint(
        "ck_tr_readiness_db_gates_request_count_consistency",
        "technical_report_release_readiness_db_gates",
        "source_search_request_count = jsonb_array_length(source_search_request_ids) "
        "AND verified_request_count = jsonb_array_length(verified_request_ids)",
    )
    op.create_check_constraint(
        "ck_tr_readiness_db_gates_complete_consistency",
        "technical_report_release_readiness_db_gates",
        "NOT complete OR ("
        "passed "
        "AND coverage_complete "
        "AND failure_count = 0 "
        "AND missing_expected_request_ids = '[]'::jsonb "
        "AND unexpected_verified_request_ids = '[]'::jsonb"
        ")",
    )
    op.execute(CREATE_CORE_IMMUTABILITY_FUNCTION_SQL)
    op.execute(CREATE_CORE_IMMUTABILITY_TRIGGER_SQL)


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_tr_readiness_db_gates_prevent_core_mutation
        ON technical_report_release_readiness_db_gates;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_tr_readiness_db_gate_core_mutation();")
    op.drop_constraint(
        "ck_tr_readiness_db_gates_complete_consistency",
        "technical_report_release_readiness_db_gates",
        type_="check",
    )
    op.drop_constraint(
        "ck_tr_readiness_db_gates_request_count_consistency",
        "technical_report_release_readiness_db_gates",
        type_="check",
    )
    op.drop_constraint(
        "ck_tr_readiness_db_gates_payload_sha_length",
        "technical_report_release_readiness_db_gates",
        type_="check",
    )
