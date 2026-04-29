"""Allow claim feedback as a replay source.

Revision ID: 0076_claim_feedback_replay_src
Revises: 0075_claim_feedback_append_links
Create Date: 2026-04-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0076_claim_feedback_replay_src"
down_revision: str | Sequence[str] | None = "0075_claim_feedback_append_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADED_SOURCE_TYPE_CONSTRAINT = (
    "source_type IN ("
    "'evaluation_queries', "
    "'live_search_gaps', "
    "'feedback', "
    "'cross_document_prose_regressions', "
    "'technical_report_claim_feedback'"
    ")"
)

DOWNGRADED_SOURCE_TYPE_CONSTRAINT = (
    "source_type IN ("
    "'evaluation_queries', "
    "'live_search_gaps', "
    "'feedback', "
    "'cross_document_prose_regressions'"
    ")"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_search_replay_runs_source_type",
        "search_replay_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_search_replay_runs_source_type",
        "search_replay_runs",
        UPGRADED_SOURCE_TYPE_CONSTRAINT,
    )
    op.drop_constraint(
        "ck_search_harness_evaluation_sources_source_type",
        "search_harness_evaluation_sources",
        type_="check",
    )
    op.create_check_constraint(
        "ck_search_harness_evaluation_sources_source_type",
        "search_harness_evaluation_sources",
        UPGRADED_SOURCE_TYPE_CONSTRAINT,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_search_harness_evaluation_sources_source_type",
        "search_harness_evaluation_sources",
        type_="check",
    )
    op.execute(
        """
        DELETE FROM search_harness_evaluation_sources
        WHERE source_type = 'technical_report_claim_feedback'
        """
    )
    op.create_check_constraint(
        "ck_search_harness_evaluation_sources_source_type",
        "search_harness_evaluation_sources",
        DOWNGRADED_SOURCE_TYPE_CONSTRAINT,
    )
    op.drop_constraint(
        "ck_search_replay_runs_source_type",
        "search_replay_runs",
        type_="check",
    )
    op.execute(
        """
        UPDATE search_replay_runs
        SET source_type = 'feedback',
            summary = jsonb_set(
                COALESCE(summary, '{}'::jsonb),
                '{source_type}',
                to_jsonb('feedback'::text),
                true
            )
        WHERE source_type = 'technical_report_claim_feedback'
        """
    )
    op.create_check_constraint(
        "ck_search_replay_runs_source_type",
        "search_replay_runs",
        DOWNGRADED_SOURCE_TYPE_CONSTRAINT,
    )
