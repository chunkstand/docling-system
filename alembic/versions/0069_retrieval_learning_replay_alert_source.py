"""add replay alert corpus retrieval learning source

Revision ID: 0069_replay_alert_learning
Revises: 0068_claim_replay_fixture_corpus_gov
Create Date: 2026-04-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0069_replay_alert_learning"
down_revision: str | Sequence[str] | None = "0068_claim_replay_corpus_gov"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADED_SET_KIND = (
    "set_kind IN ("
    "'feedback', "
    "'replay', "
    "'mixed', "
    "'training', "
    "'claim_support_replay_alert_corpus'"
    ")"
)

DOWNGRADED_SET_KIND = "set_kind IN ('feedback', 'replay', 'mixed', 'training')"

UPGRADED_SOURCE_TYPE = (
    "source_type IN ('feedback', 'replay', 'claim_support_replay_alert_corpus')"
)

DOWNGRADED_SOURCE_TYPE = "source_type IN ('feedback', 'replay')"


def upgrade() -> None:
    op.drop_constraint(
        "ck_retrieval_judgment_sets_set_kind",
        "retrieval_judgment_sets",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_judgment_sets_set_kind",
        "retrieval_judgment_sets",
        UPGRADED_SET_KIND,
    )
    op.drop_constraint(
        "ck_retrieval_judgments_source_type",
        "retrieval_judgments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_judgments_source_type",
        "retrieval_judgments",
        UPGRADED_SOURCE_TYPE,
    )
    op.drop_constraint(
        "ck_retrieval_hard_negatives_source_type",
        "retrieval_hard_negatives",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_hard_negatives_source_type",
        "retrieval_hard_negatives",
        UPGRADED_SOURCE_TYPE,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_retrieval_hard_negatives_source_type",
        "retrieval_hard_negatives",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_hard_negatives_source_type",
        "retrieval_hard_negatives",
        DOWNGRADED_SOURCE_TYPE,
    )
    op.drop_constraint(
        "ck_retrieval_judgments_source_type",
        "retrieval_judgments",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_judgments_source_type",
        "retrieval_judgments",
        DOWNGRADED_SOURCE_TYPE,
    )
    op.drop_constraint(
        "ck_retrieval_judgment_sets_set_kind",
        "retrieval_judgment_sets",
        type_="check",
    )
    op.create_check_constraint(
        "ck_retrieval_judgment_sets_set_kind",
        "retrieval_judgment_sets",
        DOWNGRADED_SET_KIND,
    )
