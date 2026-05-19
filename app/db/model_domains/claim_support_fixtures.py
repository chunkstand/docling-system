from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClaimSupportFixtureSet(Base):
    __tablename__ = "claim_support_fixture_sets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'retired')",
            name="ck_claim_support_fixture_sets_status",
        ),
        UniqueConstraint(
            "fixture_set_name",
            "fixture_set_version",
            "fixture_set_sha256",
            name="uq_claim_support_fixture_sets_identity",
        ),
        Index(
            "ix_claim_support_fixture_sets_name_version",
            "fixture_set_name",
            "fixture_set_version",
        ),
        Index("ix_claim_support_fixture_sets_status", "status"),
        Index("ix_claim_support_fixture_sets_sha", "fixture_set_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fixture_set_name: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_set_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_set_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hard_case_kinds_json: Mapped[list] = mapped_column(
        "hard_case_kinds",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    verdicts_json: Mapped[list] = mapped_column(
        "verdicts",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    fixtures_json: Mapped[list] = mapped_column(
        "fixtures",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimSupportReplayAlertFixtureCorpusSnapshot(Base):
    __tablename__ = "claim_support_replay_alert_fixture_corpus_snapshots"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'superseded')",
            name="ck_cs_replay_fixture_corpus_snapshots_status",
        ),
        UniqueConstraint(
            "snapshot_sha256",
            name="uq_cs_replay_fixture_corpus_snapshots_sha",
        ),
        Index(
            "ix_cs_replay_fixture_corpus_snapshots_status_created",
            "status",
            "created_at",
        ),
        Index("ix_cs_replay_fixture_corpus_snapshots_sha", "snapshot_sha256"),
        Index(
            "ix_cs_replay_fixture_corpus_snapshots_governance_event",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_cs_replay_fixture_corpus_snapshots_governance_artifact",
            "governance_artifact_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="active",
        server_default=sql_text("'active'"),
    )
    snapshot_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_count: Mapped[int] = mapped_column(Integer, nullable=False)
    promotion_event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    promotion_fixture_set_count: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid_promotion_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    source_promotion_event_ids_json: Mapped[list] = mapped_column(
        "source_promotion_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_promotion_artifact_ids_json: Mapped[list] = mapped_column(
        "source_promotion_artifact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_promotion_receipt_sha256s_json: Mapped[list] = mapped_column(
        "source_promotion_receipt_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_fixture_set_ids_json: Mapped[list] = mapped_column(
        "source_fixture_set_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_fixture_set_sha256s_json: Mapped[list] = mapped_column(
        "source_fixture_set_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_escalation_event_ids_json: Mapped[list] = mapped_column(
        "source_escalation_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    invalid_promotion_event_ids_json: Mapped[list] = mapped_column(
        "invalid_promotion_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    snapshot_payload_json: Mapped[dict] = mapped_column(
        "snapshot_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    governance_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    governance_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimSupportReplayAlertFixtureCorpusRow(Base):
    __tablename__ = "claim_support_replay_alert_fixture_corpus_rows"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "case_identity_sha256",
            name="uq_cs_replay_fixture_corpus_rows_snapshot_identity",
        ),
        UniqueConstraint(
            "snapshot_id",
            "row_index",
            name="uq_cs_replay_fixture_corpus_rows_snapshot_index",
        ),
        Index("ix_cs_replay_fixture_corpus_rows_snapshot", "snapshot_id"),
        Index("ix_cs_replay_fixture_corpus_rows_case", "case_id"),
        Index("ix_cs_replay_fixture_corpus_rows_fixture_sha", "fixture_sha256"),
        Index("ix_cs_replay_fixture_corpus_rows_promotion", "promotion_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_replay_alert_fixture_corpus_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    case_identity_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_json: Mapped[dict] = mapped_column(
        "fixture",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    fixture_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claim_support_fixture_sets.id", ondelete="SET NULL")
    )
    promotion_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_governance_events.id", ondelete="SET NULL")
    )
    promotion_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_task_artifacts.id", ondelete="SET NULL")
    )
    promotion_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    source_change_impact_ids_json: Mapped[list] = mapped_column(
        "source_change_impact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_escalation_event_ids_json: Mapped[list] = mapped_column(
        "source_escalation_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    replay_alert_source_json: Mapped[dict] = mapped_column(
        "replay_alert_source",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
