"""Allow claim feedback retrieval learning judgment set kind.

Revision ID: 0074_claim_feedback_set_kind
Revises: 0073_claim_feedback_ledger
Create Date: 2026-04-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0074_claim_feedback_set_kind"
down_revision: str | Sequence[str] | None = "0073_claim_feedback_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADED_SET_KIND_CHECK = (
    "set_kind IN ("
    "'feedback', "
    "'replay', "
    "'mixed', "
    "'training', "
    "'claim_support_replay_alert_corpus', "
    "'technical_report_claim_feedback'"
    ")"
)

DOWNGRADED_SET_KIND_CHECK = (
    "set_kind IN ("
    "'feedback', "
    "'replay', "
    "'mixed', "
    "'training', "
    "'claim_support_replay_alert_corpus'"
    ")"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_retrieval_judgment_sets_set_kind",
        "retrieval_judgment_sets",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_judgment_sets_set_kind",
        "retrieval_judgment_sets",
        UPGRADED_SET_KIND_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_retrieval_judgment_sets_set_kind",
        "retrieval_judgment_sets",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_judgment_sets_set_kind",
        "retrieval_judgment_sets",
        DOWNGRADED_SET_KIND_CHECK,
    )
