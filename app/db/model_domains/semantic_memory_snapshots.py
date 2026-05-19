from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SemanticOntologySnapshot(Base):
    __tablename__ = "semantic_ontology_snapshots"
    __table_args__ = (
        CheckConstraint(
            "source_kind IN ('upper_seed', 'ontology_extension_apply')",
            name="ck_semantic_ontology_snapshots_source_kind",
        ),
        UniqueConstraint(
            "ontology_version",
            name="uq_semantic_ontology_snapshots_ontology_version",
        ),
        Index("ix_semantic_ontology_snapshots_created_at", "created_at"),
        Index("ix_semantic_ontology_snapshots_upper_ontology_version", "upper_ontology_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ontology_name: Mapped[str] = mapped_column(Text, nullable=False)
    ontology_version: Mapped[str] = mapped_column(Text, nullable=False)
    upper_ontology_version: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    source_task_type: Mapped[str | None] = mapped_column(Text)
    parent_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkspaceSemanticState(Base):
    __tablename__ = "workspace_semantic_state"

    workspace_key: Mapped[str] = mapped_column(Text, primary_key=True)
    active_ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticGraphSnapshot(Base):
    __tablename__ = "semantic_graph_snapshots"
    __table_args__ = (
        CheckConstraint(
            "source_kind IN ('graph_promotion_apply')",
            name="ck_semantic_graph_snapshots_source_kind",
        ),
        UniqueConstraint(
            "graph_version",
            name="uq_semantic_graph_snapshots_graph_version",
        ),
        Index("ix_semantic_graph_snapshots_created_at", "created_at"),
        Index("ix_semantic_graph_snapshots_ontology_snapshot_id", "ontology_snapshot_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    graph_name: Mapped[str] = mapped_column(Text, nullable=False)
    graph_version: Mapped[str] = mapped_column(Text, nullable=False)
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    source_task_type: Mapped[str | None] = mapped_column(Text)
    parent_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_graph_snapshots.id", ondelete="SET NULL"),
    )
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkspaceSemanticGraphState(Base):
    __tablename__ = "workspace_semantic_graph_state"

    workspace_key: Mapped[str] = mapped_column(Text, primary_key=True)
    active_graph_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_graph_snapshots.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
