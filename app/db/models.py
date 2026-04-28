from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RunStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    VALIDATING = "validating"
    RETRY_WAIT = "retry_wait"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTaskStatus(StrEnum):
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRY_WAIT = "retry_wait"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTaskSideEffectLevel(StrEnum):
    READ_ONLY = "read_only"
    DRAFT_CHANGE = "draft_change"
    PROMOTABLE = "promotable"


class AgentTaskDependencyKind(StrEnum):
    EXPLICIT = "explicit"
    TARGET_TASK = "target_task"
    SOURCE_TASK = "source_task"
    DRAFT_TASK = "draft_task"
    VERIFICATION_TASK = "verification_task"


class AgentTaskAttemptStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class AgentTaskVerificationOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class AgentTaskOutcomeLabel(StrEnum):
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    CORRECT = "correct"
    INCORRECT = "incorrect"


class KnowledgeOperatorKind(StrEnum):
    PARSE = "parse"
    EMBED = "embed"
    RETRIEVE = "retrieve"
    RERANK = "rerank"
    JUDGE = "judge"
    GENERATE = "generate"
    VERIFY = "verify"
    EXPORT = "export"
    ORCHESTRATE = "orchestrate"


class KnowledgeOperatorStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SemanticPassStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SemanticEvaluationStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SemanticGovernanceEventKind(StrEnum):
    ONTOLOGY_SNAPSHOT_RECORDED = "ontology_snapshot_recorded"
    ONTOLOGY_SNAPSHOT_ACTIVATED = "ontology_snapshot_activated"
    SEMANTIC_GRAPH_SNAPSHOT_RECORDED = "semantic_graph_snapshot_recorded"
    SEMANTIC_GRAPH_SNAPSHOT_ACTIVATED = "semantic_graph_snapshot_activated"
    SEARCH_HARNESS_RELEASE_RECORDED = "search_harness_release_recorded"
    TECHNICAL_REPORT_PROV_EXPORT_FROZEN = "technical_report_prov_export_frozen"
    RETRIEVAL_TRAINING_RUN_MATERIALIZED = "retrieval_training_run_materialized"
    RETRIEVAL_LEARNING_CANDIDATE_EVALUATED = "retrieval_learning_candidate_evaluated"
    RETRIEVAL_RERANKER_ARTIFACT_MATERIALIZED = "retrieval_reranker_artifact_materialized"
    CLAIM_SUPPORT_POLICY_ACTIVATED = "claim_support_policy_activated"
    CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_CLOSED = (
        "claim_support_policy_impact_replay_closed"
    )
    CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED = (
        "claim_support_policy_impact_replay_escalated"
    )
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED = (
        "claim_support_policy_impact_fixture_promoted"
    )
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_COVERAGE_WAIVER_CLOSED = (
        "claim_support_replay_alert_fixture_coverage_waiver_closed"
    )
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ACTIVATED = (
        "claim_support_replay_alert_fixture_corpus_snapshot_activated"
    )


class RetrievalJudgmentKind(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MISSING = "missing"


class RetrievalHardNegativeKind(StrEnum):
    EXPLICIT_IRRELEVANT = "explicit_irrelevant"
    MISSING_EXPECTED = "missing_expected"
    FAILED_REPLAY_TOP_RESULT = "failed_replay_top_result"
    WRONG_RESULT_TYPE = "wrong_result_type"
    NO_ANSWER_RETURNED = "no_answer_returned"


class RetrievalTrainingRunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class RetrievalLearningCandidateStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class SemanticTermKind(StrEnum):
    PREFERRED_LABEL = "preferred_label"
    ALIAS = "alias"


class SemanticAssertionKind(StrEnum):
    CONCEPT_MENTION = "concept_mention"


class SemanticEvidenceSourceType(StrEnum):
    CHUNK = "chunk"
    TABLE = "table"
    FIGURE = "figure"


class SemanticReviewStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"


class SemanticEpistemicStatus(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    CURATED = "curated"


class SemanticContextScope(StrEnum):
    DOCUMENT_RUN = "document_run"
    DOCUMENT = "document"
    REGISTRY = "registry"


class SemanticBindingOrigin(StrEnum):
    REGISTRY = "registry"
    DERIVED = "derived"


class SemanticCategoryBindingType(StrEnum):
    CONCEPT_CATEGORY = "concept_category"
    ASSERTION_CATEGORY = "assertion_category"


class SemanticOntologySourceKind(StrEnum):
    UPPER_SEED = "upper_seed"
    ONTOLOGY_EXTENSION_APPLY = "ontology_extension_apply"


class SemanticGraphSourceKind(StrEnum):
    GRAPH_PROMOTION_APPLY = "graph_promotion_apply"


class SemanticEntityType(StrEnum):
    DOCUMENT = "document"
    CONCEPT = "concept"
    LITERAL = "literal"


class IngestBatch(Base):
    __tablename__ = "ingest_batches"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('local_directory', 'zip_upload')",
            name="ck_ingest_batches_source_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_errors', 'failed')",
            name="ck_ingest_batches_status",
        ),
        Index("ix_ingest_batches_created_at", "created_at"),
        Index("ix_ingest_batches_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    root_path: Mapped[str | None] = mapped_column(Text)
    recursive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    file_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    queued_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    recovery_queued_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    duplicate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestBatchItem(Base):
    __tablename__ = "ingest_batch_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'queued_recovery', 'duplicate', 'failed')",
            name="ck_ingest_batch_items_status",
        ),
        UniqueConstraint(
            "batch_id",
            "relative_path",
            name="uq_ingest_batch_items_batch_relative_path",
        ),
        Index("ix_ingest_batch_items_batch_id", "batch_id"),
        Index("ix_ingest_batch_items_document_id", "document_id"),
        Index("ix_ingest_batch_items_run_id", "run_id"),
        Index("ix_ingest_batch_items_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingest_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL"),
    )
    duplicate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    recovery_run: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApiIdempotencyKey(Base):
    __tablename__ = "api_idempotency_keys"
    __table_args__ = (
        UniqueConstraint("scope", "idempotency_key", name="uq_api_idempotency_keys_scope_key"),
        Index("ix_api_idempotency_keys_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_json: Mapped[dict] = mapped_column(
        "response",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


DOCUMENT_METADATA_NORMALIZE_SQL = """
trim(
    regexp_replace(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        coalesce(title, '') || ' ' ||
                        regexp_replace(coalesce(source_filename, ''), '\\.[^.]+$', '', 'g'),
                        '([A-Z]+)([A-Z][a-z])', '\\1 \\2', 'g'
                    ),
                    '([a-z0-9])([A-Z])', '\\1 \\2', 'g'
                ),
                '([A-Za-z])([0-9])', '\\1 \\2', 'g'
            ),
            '([0-9])([A-Za-z])', '\\1 \\2', 'g'
        ),
        '[^A-Za-z0-9]+', ' ', 'g'
    )
)
""".strip()
DOCUMENT_METADATA_TEXTSEARCH_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    f"setweight(to_tsvector('simple', {DOCUMENT_METADATA_NORMALIZE_SQL}), 'A')"
)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_updated_at", "updated_at"),
        Index("ix_documents_metadata_textsearch", "metadata_textsearch", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    metadata_textsearch: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(DOCUMENT_METADATA_TEXTSEARCH_SQL, persisted=True),
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    active_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "document_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_documents_active_run_id",
        ),
    )
    latest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "document_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_documents_latest_run_id",
        ),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentRun(Base):
    __tablename__ = "document_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'validating', 'retry_wait', 'completed', 'failed')",
            name="ck_document_runs_status",
        ),
        UniqueConstraint("document_id", "run_number", name="uq_document_runs_doc_run_number"),
        Index("ix_document_runs_status_next_attempt_at", "status", "next_attempt_at"),
        Index("ix_document_runs_locked_at", "locked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Text)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    failure_stage: Mapped[str | None] = mapped_column(Text)
    failure_artifact_path: Mapped[str | None] = mapped_column(Text)
    docling_json_path: Mapped[str | None] = mapped_column(Text)
    yaml_path: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int | None] = mapped_column(Integer)
    table_count: Mapped[int | None] = mapped_column(Integer)
    figure_count: Mapped[int | None] = mapped_column(Integer)
    embedding_model: Mapped[str | None] = mapped_column(Text)
    embedding_dim: Mapped[int | None] = mapped_column(Integer)
    validation_status: Mapped[str | None] = mapped_column(Text)
    validation_results_json: Mapped[dict] = mapped_column(
        "validation_results",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentRunEvaluation(Base):
    __tablename__ = "document_run_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'skipped')",
            name="ck_document_run_evaluations_status",
        ),
        UniqueConstraint(
            "run_id",
            "corpus_name",
            "eval_version",
            name="uq_document_run_evaluations_run_corpus_version",
        ),
        Index("ix_document_run_evaluations_run_id", "run_id"),
        Index("ix_document_run_evaluations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    corpus_name: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_name: Mapped[str | None] = mapped_column(Text)
    eval_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=sql_text("1")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", server_default=sql_text("'pending'")
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentRunEvaluationQuery(Base):
    __tablename__ = "document_run_evaluation_queries"
    __table_args__ = (
        Index("ix_document_run_evaluation_queries_evaluation_id", "evaluation_id"),
        Index("ix_document_run_evaluation_queries_query_text", "query_text"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    expected_result_type: Mapped[str | None] = mapped_column(Text)
    expected_top_n: Mapped[int | None] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=sql_text("false")
    )
    candidate_rank: Mapped[int | None] = mapped_column(Integer)
    baseline_rank: Mapped[int | None] = mapped_column(Integer)
    rank_delta: Mapped[int | None] = mapped_column(Integer)
    candidate_score: Mapped[float | None] = mapped_column(Float)
    baseline_score: Mapped[float | None] = mapped_column(Float)
    candidate_result_type: Mapped[str | None] = mapped_column(Text)
    baseline_result_type: Mapped[str | None] = mapped_column(Text)
    candidate_label: Mapped[str | None] = mapped_column(Text)
    baseline_label: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


class SemanticConcept(Base):
    __tablename__ = "semantic_concepts"
    __table_args__ = (
        UniqueConstraint(
            "concept_key",
            "registry_version",
            name="uq_semantic_concepts_key_registry_version",
        ),
        Index("ix_semantic_concepts_concept_key", "concept_key"),
        Index("ix_semantic_concepts_registry_version", "registry_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_key: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_label: Mapped[str] = mapped_column(Text, nullable=False)
    scope_note: Mapped[str | None] = mapped_column(Text)
    registry_version: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticCategory(Base):
    __tablename__ = "semantic_categories"
    __table_args__ = (
        UniqueConstraint(
            "category_key",
            "registry_version",
            name="uq_semantic_categories_key_registry_version",
        ),
        Index("ix_semantic_categories_category_key", "category_key"),
        Index("ix_semantic_categories_registry_version", "registry_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_key: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_label: Mapped[str] = mapped_column(Text, nullable=False)
    scope_note: Mapped[str | None] = mapped_column(Text)
    registry_version: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticTerm(Base):
    __tablename__ = "semantic_terms"
    __table_args__ = (
        CheckConstraint(
            "term_kind IN ('preferred_label', 'alias')",
            name="ck_semantic_terms_term_kind",
        ),
        UniqueConstraint(
            "registry_version",
            "normalized_text",
            name="uq_semantic_terms_registry_version_normalized_text",
        ),
        Index("ix_semantic_terms_registry_version", "registry_version"),
        Index("ix_semantic_terms_normalized_text", "normalized_text"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_version: Mapped[str] = mapped_column(Text, nullable=False)
    term_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    term_kind: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticConceptTerm(Base):
    __tablename__ = "semantic_concept_terms"
    __table_args__ = (
        CheckConstraint(
            "mapping_kind IN ('preferred_label', 'alias')",
            name="ck_semantic_concept_terms_mapping_kind",
        ),
        CheckConstraint(
            "created_from IN ('registry', 'derived')",
            name="ck_semantic_concept_terms_created_from",
        ),
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_concept_terms_review_status",
        ),
        UniqueConstraint(
            "concept_id",
            "term_id",
            name="uq_semantic_concept_terms_concept_term",
        ),
        Index("ix_semantic_concept_terms_concept_id", "concept_id"),
        Index("ix_semantic_concept_terms_term_id", "term_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_terms.id", ondelete="CASCADE"),
        nullable=False,
    )
    mapping_kind: Mapped[str] = mapped_column(Text, nullable=False)
    created_from: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticBindingOrigin.REGISTRY.value,
        server_default=sql_text("'registry'"),
    )
    review_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticReviewStatus.APPROVED.value,
        server_default=sql_text("'approved'"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticConceptCategoryBinding(Base):
    __tablename__ = "semantic_concept_category_bindings"
    __table_args__ = (
        CheckConstraint(
            "binding_type IN ('concept_category')",
            name="ck_semantic_concept_category_bindings_binding_type",
        ),
        CheckConstraint(
            "created_from IN ('registry', 'derived')",
            name="ck_semantic_concept_category_bindings_created_from",
        ),
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_concept_category_bindings_review_status",
        ),
        UniqueConstraint(
            "concept_id",
            "category_id",
            name="uq_semantic_concept_category_bindings_concept_category",
        ),
        Index("ix_semantic_concept_category_bindings_concept_id", "concept_id"),
        Index("ix_semantic_concept_category_bindings_category_id", "category_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    binding_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_from: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticBindingOrigin.REGISTRY.value,
        server_default=sql_text("'registry'"),
    )
    review_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticReviewStatus.APPROVED.value,
        server_default=sql_text("'approved'"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentSemanticConceptReview(Base):
    __tablename__ = "document_semantic_concept_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_document_semantic_concept_reviews_review_status",
        ),
        Index("ix_document_semantic_concept_reviews_document_id", "document_id"),
        Index("ix_document_semantic_concept_reviews_concept_id", "concept_id"),
        Index(
            "ix_doc_sem_concept_reviews_doc_concept_created_at",
            "document_id",
            "concept_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentSemanticCategoryReview(Base):
    __tablename__ = "document_semantic_category_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_document_semantic_category_reviews_review_status",
        ),
        Index("ix_document_semantic_category_reviews_document_id", "document_id"),
        Index("ix_document_semantic_category_reviews_concept_id", "concept_id"),
        Index("ix_document_semantic_category_reviews_category_id", "category_id"),
        Index(
            "ix_doc_sem_category_reviews_doc_binding_created_at",
            "document_id",
            "concept_id",
            "category_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentRunSemanticPass(Base):
    __tablename__ = "document_run_semantic_passes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_document_run_semantic_passes_status",
        ),
        CheckConstraint(
            "evaluation_status IN ('pending', 'completed', 'failed', 'skipped')",
            name="ck_document_run_semantic_passes_evaluation_status",
        ),
        UniqueConstraint(
            "run_id",
            "registry_version",
            "extractor_version",
            "artifact_schema_version",
            name="uq_document_run_semantic_passes_run_version_tuple",
        ),
        Index("ix_document_run_semantic_passes_document_id", "document_id"),
        Index("ix_document_run_semantic_passes_run_id", "run_id"),
        Index("ix_document_run_semantic_passes_baseline_run_id", "baseline_run_id"),
        Index("ix_document_run_semantic_passes_ontology_snapshot_id", "ontology_snapshot_id"),
        Index("ix_document_run_semantic_passes_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    baseline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL"),
    )
    baseline_semantic_pass_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_semantic_passes.id", ondelete="SET NULL"),
    )
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    upper_ontology_version: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", server_default=sql_text("'pending'")
    )
    registry_version: Mapped[str] = mapped_column(Text, nullable=False)
    registry_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    extractor_version: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evaluation_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default=sql_text("'pending'"),
    )
    evaluation_fixture_name: Mapped[str | None] = mapped_column(Text)
    evaluation_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=sql_text("1"),
    )
    evaluation_summary_json: Mapped[dict] = mapped_column(
        "evaluation_summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    continuity_summary_json: Mapped[dict] = mapped_column(
        "continuity_summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    artifact_json_path: Mapped[str | None] = mapped_column(Text)
    artifact_yaml_path: Mapped[str | None] = mapped_column(Text)
    artifact_json_sha256: Mapped[str | None] = mapped_column(Text)
    artifact_yaml_sha256: Mapped[str | None] = mapped_column(Text)
    assertion_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SemanticAssertion(Base):
    __tablename__ = "semantic_assertions"
    __table_args__ = (
        CheckConstraint(
            "assertion_kind IN ('concept_mention')",
            name="ck_semantic_assertions_assertion_kind",
        ),
        CheckConstraint(
            "epistemic_status IN ('observed', 'inferred', 'curated')",
            name="ck_semantic_assertions_epistemic_status",
        ),
        CheckConstraint(
            "context_scope IN ('document_run', 'document', 'registry')",
            name="ck_semantic_assertions_context_scope",
        ),
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_assertions_review_status",
        ),
        UniqueConstraint(
            "semantic_pass_id",
            "concept_id",
            "assertion_kind",
            name="uq_semantic_assertions_pass_concept_kind",
        ),
        Index("ix_semantic_assertions_semantic_pass_id", "semantic_pass_id"),
        Index("ix_semantic_assertions_concept_id", "concept_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    semantic_pass_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_semantic_passes.id", ondelete="CASCADE"),
        nullable=False,
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    assertion_kind: Mapped[str] = mapped_column(Text, nullable=False)
    epistemic_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticEpistemicStatus.OBSERVED.value,
        server_default=sql_text("'observed'"),
    )
    context_scope: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticContextScope.DOCUMENT_RUN.value,
        server_default=sql_text("'document_run'"),
    )
    review_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticReviewStatus.CANDIDATE.value,
        server_default=sql_text("'candidate'"),
    )
    matched_terms_json: Mapped[list] = mapped_column(
        "matched_terms",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    confidence: Mapped[float | None] = mapped_column(Float)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticAssertionCategoryBinding(Base):
    __tablename__ = "semantic_assertion_category_bindings"
    __table_args__ = (
        CheckConstraint(
            "binding_type IN ('assertion_category')",
            name="ck_semantic_assertion_category_bindings_binding_type",
        ),
        CheckConstraint(
            "created_from IN ('registry', 'derived')",
            name="ck_semantic_assertion_category_bindings_created_from",
        ),
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_assertion_category_bindings_review_status",
        ),
        UniqueConstraint(
            "assertion_id",
            "category_id",
            name="uq_semantic_assertion_category_bindings_assertion_category",
        ),
        Index("ix_semantic_assertion_category_bindings_assertion_id", "assertion_id"),
        Index("ix_semantic_assertion_category_bindings_category_id", "category_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assertion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertions.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    concept_category_binding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concept_category_bindings.id", ondelete="SET NULL"),
    )
    binding_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_from: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticBindingOrigin.DERIVED.value,
        server_default=sql_text("'derived'"),
    )
    review_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SemanticReviewStatus.CANDIDATE.value,
        server_default=sql_text("'candidate'"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticAssertionEvidence(Base):
    __tablename__ = "semantic_assertion_evidence"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('chunk', 'table', 'figure')",
            name="ck_semantic_assertion_evidence_source_type",
        ),
        UniqueConstraint(
            "assertion_id",
            "source_type",
            "source_locator",
            name="uq_semantic_assertion_evidence_assertion_source",
        ),
        Index("ix_semantic_assertion_evidence_assertion_id", "assertion_id"),
        Index("ix_semantic_assertion_evidence_run_id", "run_id"),
        Index("ix_semantic_assertion_evidence_source_type", "source_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assertion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertions.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_tables.id", ondelete="SET NULL"),
    )
    figure_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_figures.id", ondelete="SET NULL"),
    )
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    matched_terms_json: Mapped[list] = mapped_column(
        "matched_terms",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    excerpt: Mapped[str | None] = mapped_column(Text)
    source_label: Mapped[str | None] = mapped_column(Text)
    source_artifact_path: Mapped[str | None] = mapped_column(Text)
    source_artifact_sha256: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticEntity(Base):
    __tablename__ = "semantic_entities"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('document', 'concept', 'literal')",
            name="ck_semantic_entities_entity_type",
        ),
        UniqueConstraint("entity_key", name="uq_semantic_entities_entity_key"),
        Index("ix_semantic_entities_document_id", "document_id"),
        Index("ix_semantic_entities_concept_id", "concept_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_key: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_label: Mapped[str] = mapped_column(Text, nullable=False)
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_concepts.id", ondelete="SET NULL"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticFact(Base):
    __tablename__ = "semantic_facts"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('candidate', 'approved', 'rejected')",
            name="ck_semantic_facts_review_status",
        ),
        Index("ix_semantic_facts_document_id", "document_id"),
        Index("ix_semantic_facts_run_id", "run_id"),
        Index("ix_semantic_facts_semantic_pass_id", "semantic_pass_id"),
        Index("ix_semantic_facts_relation_key", "relation_key"),
        Index("ix_semantic_facts_subject_entity_id", "subject_entity_id"),
        Index("ix_semantic_facts_object_entity_id", "object_entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    semantic_pass_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_semantic_passes.id", ondelete="CASCADE"),
        nullable=False,
    )
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    subject_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_key: Mapped[str] = mapped_column(Text, nullable=False)
    relation_label: Mapped[str] = mapped_column(Text, nullable=False)
    object_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_entities.id", ondelete="SET NULL"),
    )
    object_value_text: Mapped[str | None] = mapped_column(Text)
    source_assertion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertions.id", ondelete="SET NULL"),
    )
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticFactEvidence(Base):
    __tablename__ = "semantic_fact_evidence"
    __table_args__ = (
        Index("ix_semantic_fact_evidence_fact_id", "fact_id"),
        Index("ix_semantic_fact_evidence_assertion_id", "assertion_id"),
        Index("ix_semantic_fact_evidence_evidence_id", "assertion_evidence_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_facts.id", ondelete="CASCADE"),
        nullable=False,
    )
    assertion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertions.id", ondelete="SET NULL"),
    )
    assertion_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_assertion_evidence.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchRequestRecord(Base):
    __tablename__ = "search_requests"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('keyword', 'semantic', 'hybrid')",
            name="ck_search_requests_mode",
        ),
        Index("ix_search_requests_created_at", "created_at"),
        Index("ix_search_requests_origin_created_at", "origin", "created_at"),
        Index("ix_search_requests_evaluation_id", "evaluation_id"),
        Index("ix_search_requests_parent_request_id", "parent_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluations.id", ondelete="SET NULL"),
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL"),
    )
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    tabular_query: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    harness_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    reranker_name: Mapped[str] = mapped_column(Text, nullable=False)
    reranker_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="v1",
        server_default=sql_text("'v1'"),
    )
    retrieval_profile_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    harness_config_json: Mapped[dict] = mapped_column(
        "harness_config",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    embedding_status: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_error: Mapped[str | None] = mapped_column(Text)
    candidate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchRequestResult(Base):
    __tablename__ = "search_request_results"
    __table_args__ = (
        CheckConstraint(
            "result_type IN ('chunk', 'table')",
            name="ck_search_request_results_result_type",
        ),
        UniqueConstraint(
            "search_request_id",
            "rank",
            name="uq_search_request_results_request_rank",
        ),
        Index("ix_search_request_results_search_request_id", "search_request_id"),
        Index("ix_search_request_results_result_type", "result_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    base_rank: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    table_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    score: Mapped[float] = mapped_column(Float, nullable=False)
    keyword_score: Mapped[float | None] = mapped_column(Float)
    semantic_score: Mapped[float | None] = mapped_column(Float)
    hybrid_score: Mapped[float | None] = mapped_column(Float)
    rerank_features_json: Mapped[dict] = mapped_column(
        "rerank_features",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    preview_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalEvidenceSpan(Base):
    __tablename__ = "retrieval_evidence_spans"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_retrieval_evidence_spans_source_type",
        ),
        CheckConstraint(
            "("
            "source_type = 'chunk' AND chunk_id IS NOT NULL AND table_id IS NULL"
            ") OR ("
            "source_type = 'table' AND table_id IS NOT NULL AND chunk_id IS NULL"
            ")",
            name="ck_retrieval_evidence_spans_source_ref",
        ),
        UniqueConstraint(
            "run_id",
            "source_type",
            "source_id",
            "span_index",
            name="uq_retrieval_evidence_spans_run_source_span",
        ),
        Index("ix_retrieval_evidence_spans_document_id", "document_id"),
        Index("ix_retrieval_evidence_spans_run_id", "run_id"),
        Index("ix_retrieval_evidence_spans_source", "source_type", "source_id"),
        Index("ix_retrieval_evidence_spans_chunk_id", "chunk_id"),
        Index("ix_retrieval_evidence_spans_table_id", "table_id"),
        Index("ix_retrieval_evidence_spans_page_from", "page_from"),
        Index("ix_retrieval_evidence_spans_page_to", "page_to"),
        Index("ix_retrieval_evidence_spans_content_sha256", "content_sha256"),
        Index(
            "ix_retrieval_evidence_spans_textsearch",
            "textsearch",
            postgresql_using="gin",
        ),
        Index(
            "ix_retrieval_evidence_spans_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE")
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_tables.id", ondelete="CASCADE")
    )
    span_index: Mapped[int] = mapped_column(Integer, nullable=False)
    span_text: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    textsearch: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(heading, '')), 'A') || "
            "to_tsvector('english', coalesce(span_text, ''))",
            persisted=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalEvidenceSpanMultiVector(Base):
    __tablename__ = "retrieval_evidence_span_multivectors"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_retrieval_span_multivectors_source_type",
        ),
        CheckConstraint(
            "token_start >= 0 AND token_end > token_start",
            name="ck_retrieval_span_multivectors_token_range",
        ),
        CheckConstraint(
            "embedding_dim = 1536",
            name="ck_retrieval_span_multivectors_embedding_dim",
        ),
        UniqueConstraint(
            "retrieval_evidence_span_id",
            "vector_index",
            name="uq_retrieval_span_multivectors_span_vector",
        ),
        Index(
            "ix_retrieval_span_multivectors_span_id",
            "retrieval_evidence_span_id",
        ),
        Index("ix_retrieval_span_multivectors_document_id", "document_id"),
        Index("ix_retrieval_span_multivectors_run_id", "run_id"),
        Index(
            "ix_retrieval_span_multivectors_source",
            "source_type",
            "source_id",
        ),
        Index(
            "ix_retrieval_span_multivectors_model",
            "embedding_model",
        ),
        Index(
            "ix_retrieval_span_multivectors_content_sha256",
            "content_sha256",
        ),
        Index(
            "ix_retrieval_span_multivectors_embedding_sha256",
            "embedding_sha256",
        ),
        Index(
            "ix_retrieval_span_multivectors_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_evidence_span_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_evidence_spans.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    vector_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_start: Mapped[int] = mapped_column(Integer, nullable=False)
    token_end: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchRequestResultSpan(Base):
    __tablename__ = "search_request_result_spans"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('chunk', 'table')",
            name="ck_search_request_result_spans_source_type",
        ),
        UniqueConstraint(
            "search_request_result_id",
            "span_rank",
            name="uq_search_request_result_spans_result_rank",
        ),
        Index("ix_search_request_result_spans_request_id", "search_request_id"),
        Index("ix_search_request_result_spans_result_id", "search_request_result_id"),
        Index("ix_search_request_result_spans_span_id", "retrieval_evidence_span_id"),
        Index("ix_search_request_result_spans_source", "source_type", "source_id"),
        Index("ix_search_request_result_spans_content_sha256", "content_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    search_request_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    retrieval_evidence_span_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_evidence_spans.id", ondelete="SET NULL"),
    )
    span_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score_kind: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    span_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    text_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot_sha256: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchFeedback(Base):
    __tablename__ = "search_feedback"
    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('relevant', 'irrelevant', 'missing_table', "
            "'missing_chunk', 'no_answer')",
            name="ck_search_feedback_type",
        ),
        Index("ix_search_feedback_search_request_id", "search_request_id"),
        Index("ix_search_feedback_search_request_result_id", "search_request_result_id"),
        Index("ix_search_feedback_feedback_type", "feedback_type"),
        Index("ix_search_feedback_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    search_request_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="SET NULL"),
    )
    result_rank: Mapped[int | None] = mapped_column(Integer)
    feedback_type: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchReplayRun(Base):
    __tablename__ = "search_replay_runs"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ("
            "'evaluation_queries', "
            "'live_search_gaps', "
            "'feedback', "
            "'cross_document_prose_regressions'"
            ")",
            name="ck_search_replay_runs_source_type",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_search_replay_runs_status",
        ),
        Index("ix_search_replay_runs_created_at", "created_at"),
        Index("ix_search_replay_runs_source_type_created_at", "source_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    harness_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    reranker_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="linear_feature_reranker",
        server_default=sql_text("'linear_feature_reranker'"),
    )
    reranker_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="v1",
        server_default=sql_text("'v1'"),
    )
    retrieval_profile_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    harness_config_json: Mapped[dict] = mapped_column(
        "harness_config",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    passed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    zero_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    top_result_changes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    max_rank_shift: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SearchReplayQuery(Base):
    __tablename__ = "search_replay_queries"
    __table_args__ = (
        Index("ix_search_replay_queries_replay_run_id", "replay_run_id"),
        Index("ix_search_replay_queries_source_search_request_id", "source_search_request_id"),
        Index("ix_search_replay_queries_replay_search_request_id", "replay_search_request_id"),
        Index("ix_search_replay_queries_feedback_id", "feedback_id"),
        Index("ix_search_replay_queries_evaluation_query_id", "evaluation_query_id"),
        Index("ix_search_replay_queries_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    replay_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    replay_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_feedback.id", ondelete="SET NULL"),
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL"),
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    expected_result_type: Mapped[str | None] = mapped_column(Text)
    expected_top_n: Mapped[int | None] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    overlap_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    added_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    removed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    top_result_changed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    max_rank_shift: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchHarnessEvaluation(Base):
    __tablename__ = "search_harness_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_search_harness_evaluations_status",
        ),
        Index("ix_search_harness_evaluations_created_at", "created_at"),
        Index(
            "ix_search_harness_evaluations_candidate_created_at",
            "candidate_harness_name",
            "created_at",
        ),
        Index(
            "ix_search_harness_evaluations_baseline_candidate",
            "baseline_harness_name",
            "candidate_harness_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    harness_overrides_json: Mapped[dict] = mapped_column(
        "harness_overrides",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    total_shared_query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    total_improved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    total_regressed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    total_unchanged_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SearchHarnessEvaluationSource(Base):
    __tablename__ = "search_harness_evaluation_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ("
            "'evaluation_queries', "
            "'live_search_gaps', "
            "'feedback', "
            "'cross_document_prose_regressions'"
            ")",
            name="ck_search_harness_evaluation_sources_source_type",
        ),
        UniqueConstraint(
            "search_harness_evaluation_id",
            "source_type",
            name="uq_search_harness_evaluation_sources_eval_source",
        ),
        Index(
            "ix_search_harness_evaluation_sources_eval_id",
            "search_harness_evaluation_id",
        ),
        Index(
            "ix_search_harness_evaluation_sources_baseline_replay",
            "baseline_replay_run_id",
        ),
        Index(
            "ix_search_harness_evaluation_sources_candidate_replay",
            "candidate_replay_run_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_harness_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_replay_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_replay_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    baseline_status: Mapped[str | None] = mapped_column(Text)
    candidate_status: Mapped[str | None] = mapped_column(Text)
    baseline_query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_passed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_passed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_zero_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_zero_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_table_hit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_top_result_changes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_top_result_changes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_mrr: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=sql_text("0")
    )
    candidate_mrr: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=sql_text("0")
    )
    baseline_foreign_top_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    candidate_foreign_top_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    acceptance_checks_json: Mapped[dict] = mapped_column(
        "acceptance_checks",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    shared_query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    improved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    regressed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    unchanged_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchHarnessRelease(Base):
    __tablename__ = "search_harness_releases"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('passed', 'failed', 'error')",
            name="ck_search_harness_releases_outcome",
        ),
        Index("ix_search_harness_releases_created_at", "created_at"),
        Index(
            "ix_search_harness_releases_candidate_created_at",
            "candidate_harness_name",
            "created_at",
        ),
        Index(
            "ix_search_harness_releases_evaluation_id",
            "search_harness_evaluation_id",
        ),
        Index(
            "ix_search_harness_releases_outcome_created_at",
            "outcome",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_harness_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    reasons_json: Mapped[list] = mapped_column(
        "reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evaluation_snapshot_json: Mapped[dict] = mapped_column(
        "evaluation_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    release_package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalJudgmentSet(Base):
    __tablename__ = "retrieval_judgment_sets"
    __table_args__ = (
        CheckConstraint(
            "set_kind IN ("
            "'feedback', "
            "'replay', "
            "'mixed', "
            "'training', "
            "'claim_support_replay_alert_corpus'"
            ")",
            name="ck_retrieval_judgment_sets_set_kind",
        ),
        UniqueConstraint("set_name", name="uq_retrieval_judgment_sets_set_name"),
        Index("ix_retrieval_judgment_sets_created_at", "created_at"),
        Index("ix_retrieval_judgment_sets_set_kind_created", "set_kind", "created_at"),
        Index("ix_retrieval_judgment_sets_payload_sha", "payload_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    set_name: Mapped[str] = mapped_column(Text, nullable=False)
    set_kind: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="mixed",
        server_default=sql_text("'mixed'"),
    )
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    criteria_json: Mapped[dict] = mapped_column(
        "criteria",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    judgment_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    positive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    missing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    hard_negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalJudgment(Base):
    __tablename__ = "retrieval_judgments"
    __table_args__ = (
        CheckConstraint(
            "judgment_kind IN ('positive', 'negative', 'missing')",
            name="ck_retrieval_judgments_kind",
        ),
        CheckConstraint(
            "source_type IN ('feedback', 'replay', 'claim_support_replay_alert_corpus')",
            name="ck_retrieval_judgments_source_type",
        ),
        CheckConstraint(
            "result_type IS NULL OR result_type IN ('chunk', 'table')",
            name="ck_retrieval_judgments_result_type",
        ),
        UniqueConstraint(
            "deduplication_key",
            name="uq_retrieval_judgments_dedup_key",
        ),
        Index("ix_retrieval_judgments_set_kind", "judgment_set_id", "judgment_kind"),
        Index("ix_retrieval_judgments_source", "source_type", "source_ref_id"),
        Index("ix_retrieval_judgments_search_request", "search_request_id"),
        Index("ix_retrieval_judgments_source_request", "source_search_request_id"),
        Index("ix_retrieval_judgments_search_result", "search_request_result_id"),
        Index("ix_retrieval_judgments_feedback", "search_feedback_id"),
        Index("ix_retrieval_judgments_replay_query", "search_replay_query_id"),
        Index("ix_retrieval_judgments_result", "result_type", "result_id"),
        Index("ix_retrieval_judgments_source_payload_sha", "source_payload_sha256"),
        Index("ix_retrieval_judgments_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    judgment_kind: Mapped[str] = mapped_column(Text, nullable=False)
    judgment_label: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    search_feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_feedback.id", ondelete="SET NULL"),
    )
    search_replay_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_queries.id", ondelete="SET NULL"),
    )
    search_replay_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="SET NULL"),
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL"),
    )
    source_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="SET NULL"),
    )
    result_rank: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str | None] = mapped_column(Text)
    result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    score: Mapped[float | None] = mapped_column(Float)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    expected_result_type: Mapped[str | None] = mapped_column(Text)
    expected_top_n: Mapped[int | None] = mapped_column(Integer)
    harness_name: Mapped[str | None] = mapped_column(Text)
    reranker_name: Mapped[str | None] = mapped_column(Text)
    reranker_version: Mapped[str | None] = mapped_column(Text)
    retrieval_profile_name: Mapped[str | None] = mapped_column(Text)
    rerank_features_json: Mapped[dict] = mapped_column(
        "rerank_features",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    rationale: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_payload_sha256: Mapped[str | None] = mapped_column(Text)
    deduplication_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalHardNegative(Base):
    __tablename__ = "retrieval_hard_negatives"
    __table_args__ = (
        CheckConstraint(
            "hard_negative_kind IN ("
            "'explicit_irrelevant', "
            "'missing_expected', "
            "'failed_replay_top_result', "
            "'wrong_result_type', "
            "'no_answer_returned'"
            ")",
            name="ck_retrieval_hard_negatives_kind",
        ),
        CheckConstraint(
            "source_type IN ('feedback', 'replay', 'claim_support_replay_alert_corpus')",
            name="ck_retrieval_hard_negatives_source_type",
        ),
        CheckConstraint(
            "result_type IS NULL OR result_type IN ('chunk', 'table')",
            name="ck_retrieval_hard_negatives_result_type",
        ),
        UniqueConstraint(
            "deduplication_key",
            name="uq_retrieval_hard_negatives_dedup_key",
        ),
        Index("ix_retrieval_hard_negatives_set_kind", "judgment_set_id", "hard_negative_kind"),
        Index("ix_retrieval_hard_negatives_judgment", "judgment_id"),
        Index("ix_retrieval_hard_negatives_positive_judgment", "positive_judgment_id"),
        Index("ix_retrieval_hard_negatives_source", "source_type", "source_ref_id"),
        Index("ix_retrieval_hard_negatives_feedback", "search_feedback_id"),
        Index("ix_retrieval_hard_negatives_replay_query", "search_replay_query_id"),
        Index("ix_retrieval_hard_negatives_source_request", "source_search_request_id"),
        Index("ix_retrieval_hard_negatives_request", "search_request_id"),
        Index("ix_retrieval_hard_negatives_search_result", "search_request_result_id"),
        Index("ix_retrieval_hard_negatives_result", "result_type", "result_id"),
        Index("ix_retrieval_hard_negatives_source_payload_sha", "source_payload_sha256"),
        Index("ix_retrieval_hard_negatives_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    judgment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgments.id", ondelete="CASCADE"),
        nullable=False,
    )
    positive_judgment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgments.id", ondelete="SET NULL"),
    )
    hard_negative_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    search_feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_feedback.id", ondelete="SET NULL"),
    )
    search_replay_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_queries.id", ondelete="SET NULL"),
    )
    search_replay_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_replay_runs.id", ondelete="SET NULL"),
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL"),
    )
    source_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="SET NULL"),
    )
    result_rank: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str | None] = mapped_column(Text)
    result_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    score: Mapped[float | None] = mapped_column(Float)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict] = mapped_column(
        "filters",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    rerank_features_json: Mapped[dict] = mapped_column(
        "rerank_features",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    expected_result_type: Mapped[str | None] = mapped_column(Text)
    expected_top_n: Mapped[int | None] = mapped_column(Integer)
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_payload_sha256: Mapped[str | None] = mapped_column(Text)
    deduplication_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalTrainingRun(Base):
    __tablename__ = "retrieval_training_runs"
    __table_args__ = (
        CheckConstraint(
            "run_kind IN ('materialized_training_dataset')",
            name="ck_retrieval_training_runs_run_kind",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_retrieval_training_runs_status",
        ),
        Index("ix_retrieval_training_runs_judgment_set", "judgment_set_id"),
        Index("ix_retrieval_training_runs_release", "search_harness_release_id"),
        Index("ix_retrieval_training_runs_governance", "semantic_governance_event_id"),
        Index("ix_retrieval_training_runs_dataset_sha", "training_dataset_sha256"),
        Index("ix_retrieval_training_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_kind: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="materialized_training_dataset",
        server_default=sql_text("'materialized_training_dataset'"),
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    search_harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="SET NULL"),
    )
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    training_dataset_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    training_payload_json: Mapped[dict] = mapped_column(
        "training_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    example_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    positive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    missing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    hard_negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalLearningCandidateEvaluation(Base):
    __tablename__ = "retrieval_learning_candidate_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_retrieval_learning_candidate_evaluations_status",
        ),
        CheckConstraint(
            "gate_outcome IS NULL OR gate_outcome IN ('passed', 'failed', 'error')",
            name="ck_retrieval_learning_candidate_evaluations_gate_outcome",
        ),
        UniqueConstraint(
            "retrieval_training_run_id",
            "search_harness_evaluation_id",
            name="uq_retrieval_learning_candidate_training_eval",
        ),
        Index(
            "ix_retrieval_learning_candidate_training",
            "retrieval_training_run_id",
            "created_at",
        ),
        Index(
            "ix_retrieval_learning_candidate_judgment_set",
            "judgment_set_id",
            "created_at",
        ),
        Index(
            "ix_retrieval_learning_candidate_evaluation",
            "search_harness_evaluation_id",
        ),
        Index(
            "ix_retrieval_learning_candidate_release",
            "search_harness_release_id",
        ),
        Index(
            "ix_retrieval_learning_candidate_governance",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_retrieval_learning_candidate_dataset_sha",
            "training_dataset_sha256",
        ),
        Index(
            "ix_retrieval_learning_candidate_harness_created",
            "candidate_harness_name",
            "created_at",
        ),
        Index(
            "ix_retrieval_learning_candidate_outcome_created",
            "gate_outcome",
            "created_at",
        ),
        Index(
            "ix_retrieval_learning_candidate_package_sha",
            "learning_package_sha256",
        ),
        Index("ix_retrieval_learning_candidate_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_training_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    search_harness_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    training_dataset_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    training_example_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    positive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    missing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    hard_negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    baseline_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    gate_outcome: Mapped[str | None] = mapped_column(Text)
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    reasons_json: Mapped[list] = mapped_column(
        "reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    evaluation_snapshot_json: Mapped[dict] = mapped_column(
        "evaluation_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    release_snapshot_json: Mapped[dict] = mapped_column(
        "release_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    learning_package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalRerankerArtifact(Base):
    __tablename__ = "retrieval_reranker_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_kind IN ('linear_feature_weight_candidate')",
            name="ck_retrieval_reranker_artifacts_kind",
        ),
        CheckConstraint(
            "status IN ('evaluated', 'failed')",
            name="ck_retrieval_reranker_artifacts_status",
        ),
        CheckConstraint(
            "gate_outcome IS NULL OR gate_outcome IN ('passed', 'failed', 'error')",
            name="ck_retrieval_reranker_artifacts_gate_outcome",
        ),
        UniqueConstraint(
            "retrieval_learning_candidate_evaluation_id",
            name="uq_retrieval_reranker_artifacts_candidate_eval",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_training_created",
            "retrieval_training_run_id",
            "created_at",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_candidate_eval",
            "retrieval_learning_candidate_evaluation_id",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_evaluation",
            "search_harness_evaluation_id",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_release",
            "search_harness_release_id",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_governance",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_candidate_created",
            "candidate_harness_name",
            "created_at",
        ),
        Index(
            "ix_retrieval_reranker_artifacts_gate_created",
            "gate_outcome",
            "created_at",
        ),
        Index("ix_retrieval_reranker_artifacts_artifact_sha", "artifact_sha256"),
        Index(
            "ix_retrieval_reranker_artifacts_impact_sha",
            "change_impact_sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retrieval_training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_training_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    judgment_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_judgment_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retrieval_learning_candidate_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_learning_candidate_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    search_harness_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    artifact_kind: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_name: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    gate_outcome: Mapped[str | None] = mapped_column(Text)
    baseline_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_harness_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_types_json: Mapped[list] = mapped_column(
        "source_types",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    training_dataset_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    training_example_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    positive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    missing_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    hard_negative_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    reasons_json: Mapped[list] = mapped_column(
        "reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    feature_weights_json: Mapped[dict] = mapped_column(
        "feature_weights",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    harness_overrides_json: Mapped[dict] = mapped_column(
        "harness_overrides",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    artifact_payload_json: Mapped[dict] = mapped_column(
        "artifact_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evaluation_snapshot_json: Mapped[dict] = mapped_column(
        "evaluation_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    release_snapshot_json: Mapped[dict] = mapped_column(
        "release_snapshot",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    change_impact_report_json: Mapped[dict] = mapped_column(
        "change_impact_report",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    artifact_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    change_impact_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditBundleExport(Base):
    __tablename__ = "audit_bundle_exports"
    __table_args__ = (
        CheckConstraint(
            "bundle_kind IN ("
            "'search_harness_release_provenance', "
            "'retrieval_training_run_provenance'"
            ")",
            name="ck_audit_bundle_exports_bundle_kind",
        ),
        CheckConstraint(
            "source_table IN ('search_harness_releases', 'retrieval_training_runs')",
            name="ck_audit_bundle_exports_source_table",
        ),
        CheckConstraint(
            "export_status IN ('completed', 'failed')",
            name="ck_audit_bundle_exports_status",
        ),
        CheckConstraint(
            "("
            "bundle_kind = 'search_harness_release_provenance' "
            "AND source_table = 'search_harness_releases' "
            "AND search_harness_release_id IS NOT NULL "
            "AND search_harness_release_id = source_id "
            "AND retrieval_training_run_id IS NULL"
            ") OR ("
            "bundle_kind = 'retrieval_training_run_provenance' "
            "AND source_table = 'retrieval_training_runs' "
            "AND retrieval_training_run_id IS NOT NULL "
            "AND retrieval_training_run_id = source_id"
            ")",
            name="ck_audit_bundle_exports_source_consistency",
        ),
        Index("ix_audit_bundle_exports_bundle_kind_created_at", "bundle_kind", "created_at"),
        Index("ix_audit_bundle_exports_source", "source_table", "source_id"),
        Index(
            "ix_audit_bundle_exports_release_created_at",
            "search_harness_release_id",
            "created_at",
        ),
        Index(
            "ix_audit_bundle_exports_training_run_created_at",
            "retrieval_training_run_id",
            "created_at",
        ),
        Index("ix_audit_bundle_exports_payload_sha256", "payload_sha256"),
        Index("ix_audit_bundle_exports_bundle_sha256", "bundle_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="RESTRICT"),
    )
    retrieval_training_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_training_runs.id", ondelete="RESTRICT"),
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    signing_key_id: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_payload_json: Mapped[dict] = mapped_column(
        "bundle_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    integrity_json: Mapped[dict] = mapped_column(
        "integrity",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_by: Mapped[str | None] = mapped_column(Text)
    export_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditBundleValidationReceipt(Base):
    __tablename__ = "audit_bundle_validation_receipts"
    __table_args__ = (
        CheckConstraint(
            "bundle_kind IN ("
            "'search_harness_release_provenance', "
            "'retrieval_training_run_provenance'"
            ")",
            name="ck_audit_bundle_validation_receipts_bundle_kind",
        ),
        CheckConstraint(
            "source_table IN ('search_harness_releases', 'retrieval_training_runs')",
            name="ck_audit_bundle_validation_receipts_source_table",
        ),
        CheckConstraint(
            "validation_status IN ('passed', 'failed')",
            name="ck_audit_bundle_validation_receipts_status",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_bundle_created",
            "audit_bundle_export_id",
            "created_at",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_source",
            "source_table",
            "source_id",
            "created_at",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_receipt_sha",
            "receipt_sha256",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_prov_jsonld_sha",
            "prov_jsonld_sha256",
        ),
        Index(
            "ix_audit_bundle_validation_receipts_status_created",
            "validation_status",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_bundle_export_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_bundle_exports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bundle_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    validation_profile: Mapped[str] = mapped_column(Text, nullable=False)
    validation_status: Mapped[str] = mapped_column(Text, nullable=False)
    payload_schema_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prov_graph_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    bundle_integrity_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_integrity_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    semantic_governance_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    receipt_storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    prov_jsonld_storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    prov_jsonld_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(Text, nullable=False)
    signing_key_id: Mapped[str] = mapped_column(Text, nullable=False)
    validation_errors_json: Mapped[list] = mapped_column(
        "validation_errors",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    receipt_payload_json: Mapped[dict] = mapped_column(
        "receipt_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    prov_jsonld_json: Mapped[dict] = mapped_column(
        "prov_jsonld",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatAnswerRecord(Base):
    __tablename__ = "chat_answer_records"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('keyword', 'semantic', 'hybrid')",
            name="ck_chat_answer_records_mode",
        ),
        Index("ix_chat_answer_records_search_request_id", "search_request_id"),
        Index("ix_chat_answer_records_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    used_fallback: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    warning: Mapped[str | None] = mapped_column(Text)
    citations_json: Mapped[list] = mapped_column(
        "citations",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    harness_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    reranker_name: Mapped[str] = mapped_column(Text, nullable=False)
    reranker_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="v1",
        server_default=sql_text("'v1'"),
    )
    retrieval_profile_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="default_v1",
        server_default=sql_text("'default_v1'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatAnswerFeedback(Base):
    __tablename__ = "chat_answer_feedback"
    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('helpful', 'unhelpful', 'unsupported', 'incomplete')",
            name="ck_chat_answer_feedback_type",
        ),
        Index("ix_chat_answer_feedback_answer_id", "chat_answer_id"),
        Index("ix_chat_answer_feedback_feedback_type", "feedback_type"),
        Index("ix_chat_answer_feedback_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_answer_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvalObservation(Base):
    __tablename__ = "eval_observations"
    __table_args__ = (
        CheckConstraint(
            "surface IN ("
            "'document_evaluation', "
            "'search_request', "
            "'chat_answer', "
            "'search_replay', "
            "'harness_evaluation', "
            "'agent_task'"
            ")",
            name="ck_eval_observations_surface",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_eval_observations_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'resolved', 'suppressed')",
            name="ck_eval_observations_status",
        ),
        UniqueConstraint("observation_key", name="uq_eval_observations_observation_key"),
        Index("ix_eval_observations_surface_last_seen", "surface", "last_seen_at"),
        Index("ix_eval_observations_status_last_seen", "status", "last_seen_at"),
        Index("ix_eval_observations_document_id", "document_id"),
        Index("ix_eval_observations_search_request_id", "search_request_id"),
        Index("ix_eval_observations_evaluation_id", "evaluation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_key: Mapped[str] = mapped_column(Text, nullable=False)
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    subject_kind: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active", server_default=sql_text("'active'")
    )
    severity: Mapped[str] = mapped_column(
        Text, nullable=False, default="medium", server_default=sql_text("'medium'")
    )
    failure_classification: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="SET NULL")
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluations.id", ondelete="SET NULL")
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL")
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_requests.id", ondelete="SET NULL")
    )
    replay_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_replay_runs.id", ondelete="SET NULL")
    )
    harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_harness_evaluations.id", ondelete="SET NULL")
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvalFailureCase(Base):
    __tablename__ = "eval_failure_cases"
    __table_args__ = (
        CheckConstraint(
            "surface IN ("
            "'document_evaluation', "
            "'search_request', "
            "'chat_answer', "
            "'search_replay', "
            "'harness_evaluation', "
            "'agent_task'"
            ")",
            name="ck_eval_failure_cases_surface",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_eval_failure_cases_severity",
        ),
        CheckConstraint(
            "status IN ("
            "'open', 'triaged', 'drafted', 'verified', 'awaiting_approval', "
            "'applied', 'rejected', 'resolved', 'suppressed'"
            ")",
            name="ck_eval_failure_cases_status",
        ),
        UniqueConstraint("case_key", name="uq_eval_failure_cases_case_key"),
        Index("ix_eval_failure_cases_status_updated", "status", "updated_at"),
        Index("ix_eval_failure_cases_surface_status", "surface", "status"),
        Index("ix_eval_failure_cases_document_id", "document_id"),
        Index("ix_eval_failure_cases_search_request_id", "search_request_id"),
        Index("ix_eval_failure_cases_evaluation_id", "evaluation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="open", server_default=sql_text("'open'")
    )
    severity: Mapped[str] = mapped_column(
        Text, nullable=False, default="medium", server_default=sql_text("'medium'")
    )
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    failure_classification: Mapped[str] = mapped_column(Text, nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    observed_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    source_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_observations.id", ondelete="SET NULL")
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="SET NULL")
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluations.id", ondelete="SET NULL")
    )
    evaluation_query_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_run_evaluation_queries.id", ondelete="SET NULL")
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_requests.id", ondelete="SET NULL")
    )
    replay_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_replay_runs.id", ondelete="SET NULL")
    )
    harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_harness_evaluations.id", ondelete="SET NULL")
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    recommended_next_actions_json: Mapped[list] = mapped_column(
        "recommended_next_actions",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    allowed_repair_surfaces_json: Mapped[list] = mapped_column(
        "allowed_repair_surfaces",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    blocked_repair_surfaces_json: Mapped[list] = mapped_column(
        "blocked_repair_surfaces",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    verification_requirements_json: Mapped[dict] = mapped_column(
        "verification_requirements",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    agent_task_payloads_json: Mapped[dict] = mapped_column(
        "agent_task_payloads",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'blocked', 'awaiting_approval', 'rejected', 'queued', 'processing', "
            "'retry_wait', 'completed', 'failed'"
            ")",
            name="ck_agent_tasks_status",
        ),
        CheckConstraint(
            "side_effect_level IN ('read_only', 'draft_change', 'promotable')",
            name="ck_agent_tasks_side_effect_level",
        ),
        Index(
            "ix_agent_tasks_status_priority_next_attempt_at",
            "status",
            "priority",
            "next_attempt_at",
        ),
        Index("ix_agent_tasks_locked_at", "locked_at"),
        Index("ix_agent_tasks_parent_task_id", "parent_task_id"),
        Index("ix_agent_tasks_task_type_created_at", "task_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default=sql_text("100")
    )
    side_effect_level: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=AgentTaskSideEffectLevel.READ_ONLY.value,
        server_default=sql_text("'read_only'"),
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    input_json: Mapped[dict] = mapped_column(
        "input",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    result_json: Mapped[dict] = mapped_column(
        "result",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    failure_artifact_path: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sql_text("0")
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Text)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    workflow_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="v1", server_default=sql_text("'v1'")
    )
    tool_version: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    model_settings_json: Mapped[dict] = mapped_column(
        "model_settings",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(Text)
    approval_note: Mapped[str | None] = mapped_column(Text)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by: Mapped[str | None] = mapped_column(Text)
    rejection_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentTaskDependency(Base):
    __tablename__ = "agent_task_dependencies"
    __table_args__ = (
        CheckConstraint(
            "task_id <> depends_on_task_id",
            name="ck_agent_task_dependencies_not_self",
        ),
        CheckConstraint(
            "dependency_kind IN ("
            "'explicit', 'target_task', 'source_task', 'draft_task', 'verification_task'"
            ")",
            name="ck_agent_task_dependencies_dependency_kind",
        ),
        UniqueConstraint(
            "task_id",
            "depends_on_task_id",
            name="uq_agent_task_dependencies_task_depends_on",
        ),
        Index("ix_agent_task_dependencies_depends_on_task_id", "depends_on_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    dependency_kind: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=AgentTaskDependencyKind.EXPLICIT.value,
        server_default=sql_text("'explicit'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskAttempt(Base):
    __tablename__ = "agent_task_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed', 'abandoned')",
            name="ck_agent_task_attempts_status",
        ),
        UniqueConstraint("task_id", "attempt_number", name="uq_agent_task_attempts_task_attempt"),
        Index("ix_agent_task_attempts_task_id", "task_id"),
        Index("ix_agent_task_attempts_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(Text)
    input_json: Mapped[dict] = mapped_column(
        "input",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    result_json: Mapped[dict] = mapped_column(
        "result",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    cost_json: Mapped[dict] = mapped_column(
        "cost",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    performance_json: Mapped[dict] = mapped_column(
        "performance",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentTaskArtifact(Base):
    __tablename__ = "agent_task_artifacts"
    __table_args__ = (
        Index("ix_agent_task_artifacts_task_id", "task_id"),
        Index("ix_agent_task_artifacts_attempt_id", "attempt_id"),
        Index("ix_agent_task_artifacts_artifact_kind", "artifact_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_attempts.id", ondelete="SET NULL"),
    )
    artifact_kind: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskArtifactImmutabilityEvent(Base):
    __tablename__ = "agent_task_artifact_immutability_events"
    __table_args__ = (
        CheckConstraint(
            "event_kind IN ('mutation_blocked', 'supersession_attempt')",
            name="ck_agent_artifact_immut_events_event_kind",
        ),
        CheckConstraint(
            "mutation_operation IN ('UPDATE', 'DELETE', 'FREEZE_REUSE')",
            name="ck_agent_artifact_immut_events_mutation_op",
        ),
        Index(
            "ix_agent_artifact_immut_events_artifact_created",
            "artifact_id",
            "created_at",
        ),
        Index("ix_agent_artifact_immut_events_task_created", "task_id", "created_at"),
        Index("ix_agent_artifact_immut_events_kind", "event_kind"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_kind: Mapped[str] = mapped_column(Text, nullable=False)
    mutation_operation: Mapped[str] = mapped_column(Text, nullable=False)
    frozen_artifact_kind: Mapped[str | None] = mapped_column(Text)
    attempted_artifact_kind: Mapped[str | None] = mapped_column(Text)
    frozen_storage_path: Mapped[str | None] = mapped_column(Text)
    attempted_storage_path: Mapped[str | None] = mapped_column(Text)
    frozen_payload_sha256: Mapped[str | None] = mapped_column(Text)
    attempted_payload_sha256: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SemanticGovernanceEvent(Base):
    __tablename__ = "semantic_governance_events"
    __table_args__ = (
        CheckConstraint(
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
            "'claim_support_policy_activated', "
            "'claim_support_policy_impact_replay_closed', "
            "'claim_support_policy_impact_replay_escalated', "
            "'claim_support_policy_impact_fixture_promoted', "
            "'claim_support_replay_alert_fixture_coverage_waiver_closed', "
            "'claim_support_replay_alert_fixture_corpus_snapshot_activated'"
            ")",
            name="ck_semantic_governance_events_event_kind",
        ),
        UniqueConstraint(
            "deduplication_key",
            name="uq_semantic_governance_events_dedup_key",
        ),
        UniqueConstraint(
            "event_sequence",
            name="uq_semantic_governance_events_sequence",
        ),
        Index(
            "ix_semantic_governance_events_scope_created",
            "governance_scope",
            "created_at",
        ),
        Index("ix_semantic_governance_events_kind_created", "event_kind", "created_at"),
        Index(
            "ix_semantic_governance_events_subject",
            "subject_table",
            "subject_id",
        ),
        Index("ix_semantic_governance_events_task_created", "task_id", "created_at"),
        Index(
            "ix_semantic_governance_events_ontology",
            "ontology_snapshot_id",
            "created_at",
        ),
        Index(
            "ix_semantic_governance_events_graph",
            "semantic_graph_snapshot_id",
            "created_at",
        ),
        Index(
            "ix_semantic_governance_events_release",
            "search_harness_release_id",
            "created_at",
        ),
        Index(
            "ix_semantic_governance_events_manifest",
            "evidence_manifest_id",
            "created_at",
        ),
        Index(
            "ix_semantic_governance_events_artifact",
            "agent_task_artifact_id",
            "created_at",
        ),
        Index("ix_semantic_governance_events_receipt_sha", "receipt_sha256"),
        Index("ix_semantic_governance_events_payload_sha", "payload_sha256"),
        Index("ix_semantic_governance_events_event_hash", "event_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_sequence: Mapped[int] = mapped_column(Integer, Identity(), nullable=False)
    event_kind: Mapped[str] = mapped_column(Text, nullable=False)
    governance_scope: Mapped[str] = mapped_column(Text, nullable=False)
    subject_table: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    ontology_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_ontology_snapshots.id", ondelete="SET NULL"),
    )
    semantic_graph_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_graph_snapshots.id", ondelete="SET NULL"),
    )
    search_harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="SET NULL"),
    )
    search_harness_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_releases.id", ondelete="SET NULL"),
    )
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="SET NULL"),
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="SET NULL"),
    )
    agent_task_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    previous_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="RESTRICT"),
    )
    previous_event_hash: Mapped[str | None] = mapped_column(Text)
    receipt_sha256: Mapped[str | None] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    event_hash: Mapped[str] = mapped_column(Text, nullable=False)
    deduplication_key: Mapped[str] = mapped_column(Text, nullable=False)
    event_payload_json: Mapped[dict] = mapped_column(
        "event_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimSupportReplayAlertFixtureCoverageWaiverLedger(Base):
    __tablename__ = "claim_support_replay_alert_fixture_coverage_waiver_ledgers"
    __table_args__ = (
        CheckConstraint(
            "coverage_status IN ('open', 'partially_covered', 'closed', 'no_action_required')",
            name="ck_cs_waiver_ledgers_status",
        ),
        UniqueConstraint(
            "waiver_artifact_id",
            "waiver_sha256",
            name="uq_cs_waiver_ledgers_artifact_sha",
        ),
        Index("ix_cs_waiver_ledgers_artifact", "waiver_artifact_id"),
        Index("ix_cs_waiver_ledgers_task", "verification_task_id"),
        Index("ix_cs_waiver_ledgers_status", "coverage_status", "created_at"),
        Index("ix_cs_waiver_ledgers_closure", "closure_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waiver_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    target_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL")
    )
    fixture_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claim_support_fixture_sets.id", ondelete="SET NULL")
    )
    waiver_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    waiver_severity: Mapped[str | None] = mapped_column(Text)
    waived_by: Mapped[str | None] = mapped_column(Text)
    waiver_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waiver_review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waiver_remediation_owner: Mapped[str | None] = mapped_column(Text)
    waived_escalation_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    covered_escalation_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    coverage_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    coverage_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="open",
        server_default=sql_text("'open'"),
    )
    waived_escalation_set_sha256: Mapped[str | None] = mapped_column(Text)
    covered_escalation_set_sha256: Mapped[str | None] = mapped_column(Text)
    source_change_impact_ids_json: Mapped[list] = mapped_column(
        "source_change_impact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_verification_task_ids_json: Mapped[list] = mapped_column(
        "source_verification_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    closure_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_governance_events.id", ondelete="SET NULL")
    )
    closure_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_task_artifacts.id", ondelete="SET NULL")
    )
    closure_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    promotion_event_ids_json: Mapped[list] = mapped_column(
        "promotion_event_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    promotion_artifact_ids_json: Mapped[list] = mapped_column(
        "promotion_artifact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    promotion_receipt_sha256s_json: Mapped[list] = mapped_column(
        "promotion_receipt_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    ledger_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimSupportReplayAlertFixtureCoverageWaiverEscalation(Base):
    __tablename__ = "claim_support_replay_alert_fixture_coverage_waiver_escalations"
    __table_args__ = (
        UniqueConstraint(
            "ledger_id",
            "escalation_event_id",
            name="uq_cs_waiver_escalations_ledger_event",
        ),
        Index("ix_cs_waiver_escalations_ledger", "ledger_id"),
        Index("ix_cs_waiver_escalations_event", "escalation_event_id"),
        Index("ix_cs_waiver_escalations_covered", "ledger_id", "covered"),
        Index("ix_cs_waiver_escalations_impact", "change_impact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "claim_support_replay_alert_fixture_coverage_waiver_ledgers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    waiver_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    escalation_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    change_impact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_policy_change_impacts.id", ondelete="SET NULL"),
    )
    escalation_event_hash: Mapped[str | None] = mapped_column(Text)
    escalation_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    alert_kind: Mapped[str | None] = mapped_column(Text)
    replay_status: Mapped[str | None] = mapped_column(Text)
    covered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    covered_by_promotion_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_governance_events.id", ondelete="SET NULL")
    )
    covered_by_promotion_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_task_artifacts.id", ondelete="SET NULL")
    )
    covered_by_promotion_receipt_sha256: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    covered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentTaskOutcome(Base):
    __tablename__ = "agent_task_outcomes"
    __table_args__ = (
        CheckConstraint(
            "outcome_label IN ('useful', 'not_useful', 'correct', 'incorrect')",
            name="ck_agent_task_outcomes_outcome_label",
        ),
        UniqueConstraint(
            "task_id",
            "outcome_label",
            "created_by",
            name="uq_agent_task_outcomes_task_label_actor",
        ),
        Index("ix_agent_task_outcomes_task_id", "task_id"),
        Index("ix_agent_task_outcomes_outcome_label", "outcome_label"),
        Index("ix_agent_task_outcomes_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    outcome_label: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentTaskVerification(Base):
    __tablename__ = "agent_task_verifications"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('passed', 'failed', 'error')",
            name="ck_agent_task_verifications_outcome",
        ),
        Index("ix_agent_task_verifications_target_task_id", "target_task_id"),
        Index("ix_agent_task_verifications_verification_task_id", "verification_task_id"),
        Index("ix_agent_task_verifications_verifier_type", "verifier_type"),
        Index("ix_agent_task_verifications_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    verification_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    verifier_type: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    reasons_json: Mapped[list] = mapped_column(
        "reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    details_json: Mapped[dict] = mapped_column(
        "details",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KnowledgeOperatorRun(Base):
    __tablename__ = "knowledge_operator_runs"
    __table_args__ = (
        CheckConstraint(
            "operator_kind IN ("
            "'parse', 'embed', 'retrieve', 'rerank', 'judge', "
            "'generate', 'verify', 'export', 'orchestrate'"
            ")",
            name="ck_knowledge_operator_runs_operator_kind",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed', 'skipped')",
            name="ck_knowledge_operator_runs_status",
        ),
        Index("ix_knowledge_operator_runs_created_at", "created_at"),
        Index("ix_knowledge_operator_runs_search_request_id", "search_request_id"),
        Index("ix_knowledge_operator_runs_agent_task_id", "agent_task_id"),
        Index("ix_knowledge_operator_runs_parent_id", "parent_operator_run_id"),
        Index("ix_knowledge_operator_runs_kind_created_at", "operator_kind", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_operator_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="SET NULL"),
    )
    operator_kind: Mapped[str] = mapped_column(Text, nullable=False)
    operator_name: Mapped[str] = mapped_column(Text, nullable=False)
    operator_version: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=KnowledgeOperatorStatus.COMPLETED.value,
        server_default=sql_text("'completed'"),
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_runs.id", ondelete="SET NULL"),
    )
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_harness_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_harness_evaluations.id", ondelete="SET NULL"),
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    agent_task_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_attempts.id", ondelete="SET NULL"),
    )
    model_name: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(Text)
    prompt_sha256: Mapped[str | None] = mapped_column(Text)
    config_sha256: Mapped[str | None] = mapped_column(Text)
    input_sha256: Mapped[str | None] = mapped_column(Text)
    output_sha256: Mapped[str | None] = mapped_column(Text)
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeOperatorInput(Base):
    __tablename__ = "knowledge_operator_inputs"
    __table_args__ = (
        Index("ix_knowledge_operator_inputs_operator_run_id", "operator_run_id"),
        Index("ix_knowledge_operator_inputs_source", "source_table", "source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    input_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    artifact_path: Mapped[str | None] = mapped_column(Text)
    artifact_sha256: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeOperatorOutput(Base):
    __tablename__ = "knowledge_operator_outputs"
    __table_args__ = (
        Index("ix_knowledge_operator_outputs_operator_run_id", "operator_run_id"),
        Index("ix_knowledge_operator_outputs_target", "target_table", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    output_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    output_kind: Mapped[str] = mapped_column(Text, nullable=False)
    target_table: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    artifact_path: Mapped[str | None] = mapped_column(Text)
    artifact_sha256: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidencePackageExport(Base):
    __tablename__ = "evidence_package_exports"
    __table_args__ = (
        CheckConstraint(
            "package_kind IN ('search_request', 'technical_report_claims')",
            name="ck_evidence_package_exports_package_kind",
        ),
        CheckConstraint(
            "export_status IN ('completed', 'failed')",
            name="ck_evidence_package_exports_export_status",
        ),
        Index("ix_evidence_package_exports_created_at", "created_at"),
        Index("ix_evidence_package_exports_search_request_id", "search_request_id"),
        Index("ix_evidence_package_exports_agent_task_id", "agent_task_id"),
        Index("ix_evidence_package_exports_package_sha256", "package_sha256"),
        Index("ix_evidence_package_exports_trace_sha256", "trace_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_kind: Mapped[str] = mapped_column(Text, nullable=False)
    search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    agent_task_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    trace_sha256: Mapped[str | None] = mapped_column(Text)
    package_payload_json: Mapped[dict] = mapped_column(
        "package_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_snapshot_sha256s_json: Mapped[list] = mapped_column(
        "source_snapshot_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    operator_run_ids_json: Mapped[list] = mapped_column(
        "operator_run_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    document_ids_json: Mapped[list] = mapped_column(
        "document_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    run_ids_json: Mapped[list] = mapped_column(
        "run_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    claim_ids_json: Mapped[list] = mapped_column(
        "claim_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    export_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceManifest(Base):
    __tablename__ = "evidence_manifests"
    __table_args__ = (
        CheckConstraint(
            "manifest_kind IN ('technical_report_court_evidence')",
            name="ck_evidence_manifests_manifest_kind",
        ),
        CheckConstraint(
            "manifest_status IN ('completed', 'failed')",
            name="ck_evidence_manifests_manifest_status",
        ),
        UniqueConstraint(
            "verification_task_id",
            "manifest_kind",
            name="uq_evidence_manifests_verification_task_kind",
        ),
        Index("ix_evidence_manifests_agent_task_id", "agent_task_id"),
        Index("ix_evidence_manifests_draft_task_id", "draft_task_id"),
        Index("ix_evidence_manifests_verification_task_id", "verification_task_id"),
        Index("ix_evidence_manifests_export_id", "evidence_package_export_id"),
        Index("ix_evidence_manifests_manifest_sha256", "manifest_sha256"),
        Index("ix_evidence_manifests_trace_sha256", "trace_sha256"),
        Index("ix_evidence_manifests_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manifest_kind: Mapped[str] = mapped_column(Text, nullable=False)
    agent_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    draft_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="SET NULL"),
    )
    manifest_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    trace_sha256: Mapped[str | None] = mapped_column(Text)
    manifest_payload_json: Mapped[dict] = mapped_column(
        "manifest_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_snapshot_sha256s_json: Mapped[list] = mapped_column(
        "source_snapshot_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    document_ids_json: Mapped[list] = mapped_column(
        "document_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    run_ids_json: Mapped[list] = mapped_column(
        "run_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    claim_ids_json: Mapped[list] = mapped_column(
        "claim_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    search_request_ids_json: Mapped[list] = mapped_column(
        "search_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    operator_run_ids_json: Mapped[list] = mapped_column(
        "operator_run_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    manifest_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="completed",
        server_default=sql_text("'completed'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceTraceNode(Base):
    __tablename__ = "evidence_trace_nodes"
    __table_args__ = (
        CheckConstraint(
            "(evidence_manifest_id IS NOT NULL AND evidence_package_export_id IS NULL) "
            "OR (evidence_manifest_id IS NULL AND evidence_package_export_id IS NOT NULL)",
            name="ck_evidence_trace_nodes_single_owner",
        ),
        UniqueConstraint(
            "evidence_manifest_id",
            "node_key",
            name="uq_evidence_trace_nodes_manifest_node_key",
        ),
        UniqueConstraint(
            "evidence_package_export_id",
            "node_key",
            name="uq_evidence_trace_nodes_export_node_key",
        ),
        Index("ix_evidence_trace_nodes_manifest_id", "evidence_manifest_id"),
        Index("ix_evidence_trace_nodes_export_id", "evidence_package_export_id"),
        Index("ix_evidence_trace_nodes_node_kind", "node_kind"),
        Index("ix_evidence_trace_nodes_source", "source_table", "source_id"),
        Index("ix_evidence_trace_nodes_source_ref", "source_table", "source_ref"),
        Index("ix_evidence_trace_nodes_content_sha256", "content_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="CASCADE"),
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
    )
    node_key: Mapped[str] = mapped_column(Text, nullable=False)
    node_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_table: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_ref: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceTraceEdge(Base):
    __tablename__ = "evidence_trace_edges"
    __table_args__ = (
        CheckConstraint(
            "(evidence_manifest_id IS NOT NULL AND evidence_package_export_id IS NULL) "
            "OR (evidence_manifest_id IS NULL AND evidence_package_export_id IS NOT NULL)",
            name="ck_evidence_trace_edges_single_owner",
        ),
        UniqueConstraint(
            "evidence_manifest_id",
            "edge_key",
            name="uq_evidence_trace_edges_manifest_edge_key",
        ),
        UniqueConstraint(
            "evidence_package_export_id",
            "edge_key",
            name="uq_evidence_trace_edges_export_edge_key",
        ),
        Index("ix_evidence_trace_edges_manifest_id", "evidence_manifest_id"),
        Index("ix_evidence_trace_edges_export_id", "evidence_package_export_id"),
        Index("ix_evidence_trace_edges_edge_kind", "edge_kind"),
        Index("ix_evidence_trace_edges_from_node_id", "from_node_id"),
        Index("ix_evidence_trace_edges_to_node_id", "to_node_id"),
        Index("ix_evidence_trace_edges_derivation_sha256", "derivation_sha256"),
        Index("ix_evidence_trace_edges_content_sha256", "content_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="CASCADE"),
    )
    evidence_package_export_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
    )
    edge_key: Mapped[str] = mapped_column(Text, nullable=False)
    edge_kind: Mapped[str] = mapped_column(Text, nullable=False)
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_trace_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_trace_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_node_key: Mapped[str] = mapped_column(Text, nullable=False)
    to_node_key: Mapped[str] = mapped_column(Text, nullable=False)
    derivation_sha256: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        "payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimEvidenceDerivation(Base):
    __tablename__ = "claim_evidence_derivations"
    __table_args__ = (
        CheckConstraint(
            "support_verdict IS NULL OR support_verdict IN "
            "('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_evidence_derivations_support_verdict",
        ),
        Index("ix_claim_evidence_derivations_export_id", "evidence_package_export_id"),
        Index("ix_claim_evidence_derivations_agent_task_id", "agent_task_id"),
        Index("ix_claim_evidence_derivations_claim_id", "claim_id"),
        Index("ix_claim_evidence_derivations_derivation_sha256", "derivation_sha256"),
        Index("ix_claim_evidence_derivations_support_verdict", "support_verdict"),
        Index("ix_claim_evidence_derivations_support_judge_run_id", "support_judge_run_id"),
        Index(
            "ix_claim_evidence_derivations_provenance_lock_sha",
            "provenance_lock_sha256",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_package_export_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_package_exports.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    claim_id: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str | None] = mapped_column(Text)
    derivation_rule: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_card_ids_json: Mapped[list] = mapped_column(
        "evidence_card_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    graph_edge_ids_json: Mapped[list] = mapped_column(
        "graph_edge_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    fact_ids_json: Mapped[list] = mapped_column(
        "fact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    assertion_ids_json: Mapped[list] = mapped_column(
        "assertion_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_document_ids_json: Mapped[list] = mapped_column(
        "source_document_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_snapshot_sha256s_json: Mapped[list] = mapped_column(
        "source_snapshot_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_search_request_ids_json: Mapped[list] = mapped_column(
        "source_search_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_search_request_result_ids_json: Mapped[list] = mapped_column(
        "source_search_request_result_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_evidence_package_export_ids_json: Mapped[list] = mapped_column(
        "source_evidence_package_export_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_evidence_package_sha256s_json: Mapped[list] = mapped_column(
        "source_evidence_package_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    source_evidence_trace_sha256s_json: Mapped[list] = mapped_column(
        "source_evidence_trace_sha256s",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    semantic_ontology_snapshot_ids_json: Mapped[list] = mapped_column(
        "semantic_ontology_snapshot_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    semantic_graph_snapshot_ids_json: Mapped[list] = mapped_column(
        "semantic_graph_snapshot_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    retrieval_reranker_artifact_ids_json: Mapped[list] = mapped_column(
        "retrieval_reranker_artifact_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    search_harness_release_ids_json: Mapped[list] = mapped_column(
        "search_harness_release_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    release_audit_bundle_ids_json: Mapped[list] = mapped_column(
        "release_audit_bundle_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    release_validation_receipt_ids_json: Mapped[list] = mapped_column(
        "release_validation_receipt_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    provenance_lock_json: Mapped[dict] = mapped_column(
        "provenance_lock",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    provenance_lock_sha256: Mapped[str | None] = mapped_column(Text)
    support_verdict: Mapped[str | None] = mapped_column(Text)
    support_score: Mapped[float | None] = mapped_column(Float)
    support_judge_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="SET NULL"),
    )
    support_judgment_json: Mapped[dict] = mapped_column(
        "support_judgment",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    support_judgment_sha256: Mapped[str | None] = mapped_column(Text)
    evidence_package_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    derivation_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


class ClaimSupportCalibrationPolicy(Base):
    __tablename__ = "claim_support_calibration_policies"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'retired')",
            name="ck_claim_support_calibration_policies_status",
        ),
        UniqueConstraint(
            "policy_name",
            "policy_version",
            "policy_sha256",
            name="uq_claim_support_calibration_policies_identity",
        ),
        Index(
            "ix_claim_support_calibration_policies_name_version",
            "policy_name",
            "policy_version",
        ),
        Index(
            "uq_claim_support_calibration_policies_active_name",
            "policy_name",
            unique=True,
            postgresql_where=sql_text("status = 'active'"),
        ),
        Index("ix_claim_support_calibration_policies_status", "status"),
        Index("ix_claim_support_calibration_policies_sha", "policy_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_name: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    policy_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    min_hard_case_kind_count: Mapped[int] = mapped_column(Integer, nullable=False)
    required_hard_case_kinds_json: Mapped[list] = mapped_column(
        "required_hard_case_kinds",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    required_verdicts_json: Mapped[list] = mapped_column(
        "required_verdicts",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    policy_payload_json: Mapped[dict] = mapped_column(
        "policy_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimSupportEvaluation(Base):
    __tablename__ = "claim_support_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_claim_support_evaluations_status",
        ),
        CheckConstraint(
            "gate_outcome IN ('passed', 'failed')",
            name="ck_claim_support_evaluations_gate_outcome",
        ),
        Index("ix_claim_support_evaluations_agent_task_id", "agent_task_id"),
        Index("ix_claim_support_evaluations_operator_run_id", "operator_run_id"),
        Index("ix_claim_support_evaluations_created_at", "created_at"),
        Index("ix_claim_support_evaluations_gate_created", "gate_outcome", "created_at"),
        Index("ix_claim_support_evaluations_fixture_sha", "fixture_set_sha256"),
        Index("ix_claim_support_evaluations_fixture_set_id", "fixture_set_id"),
        Index("ix_claim_support_evaluations_policy_id", "policy_id"),
        Index("ix_claim_support_evaluations_policy_sha", "policy_sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    operator_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_operator_runs.id", ondelete="SET NULL"),
    )
    fixture_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_fixture_sets.id", ondelete="SET NULL"),
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    evaluation_name: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_set_name: Mapped[str] = mapped_column(Text, nullable=False)
    fixture_set_version: Mapped[str | None] = mapped_column(Text)
    fixture_set_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    policy_name: Mapped[str | None] = mapped_column(Text)
    policy_version: Mapped[str | None] = mapped_column(Text)
    policy_sha256: Mapped[str | None] = mapped_column(Text)
    judge_name: Mapped[str] = mapped_column(Text, nullable=False)
    judge_version: Mapped[str] = mapped_column(Text, nullable=False)
    min_support_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    gate_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    thresholds_json: Mapped[dict] = mapped_column(
        "thresholds",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    metrics_json: Mapped[dict] = mapped_column(
        "metrics",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    reasons_json: Mapped[list] = mapped_column(
        "reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    evaluation_payload_json: Mapped[dict] = mapped_column(
        "evaluation_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    evaluation_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimSupportEvaluationCase(Base):
    __tablename__ = "claim_support_evaluation_cases"
    __table_args__ = (
        CheckConstraint(
            "expected_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_support_evaluation_cases_expected_verdict",
        ),
        CheckConstraint(
            "predicted_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_claim_support_evaluation_cases_predicted_verdict",
        ),
        UniqueConstraint(
            "evaluation_id",
            "case_id",
            name="uq_claim_support_evaluation_cases_eval_case",
        ),
        Index("ix_claim_support_evaluation_cases_eval_id", "evaluation_id"),
        Index("ix_claim_support_evaluation_cases_case_id", "case_id"),
        Index("ix_claim_support_evaluation_cases_expected", "expected_verdict"),
        Index("ix_claim_support_evaluation_cases_predicted", "predicted_verdict"),
        Index("ix_claim_support_evaluation_cases_passed", "passed"),
        Index("ix_claim_support_evaluation_cases_hard_kind", "hard_case_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    case_index: Mapped[int] = mapped_column(Integer, nullable=False)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    hard_case_kind: Mapped[str | None] = mapped_column(Text)
    expected_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    support_score: Mapped[float | None] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    claim_payload_json: Mapped[dict] = mapped_column(
        "claim_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    support_judgment_json: Mapped[dict] = mapped_column(
        "support_judgment",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    failure_reasons_json: Mapped[list] = mapped_column(
        "failure_reasons",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClaimSupportPolicyChangeImpact(Base):
    __tablename__ = "claim_support_policy_change_impacts"
    __table_args__ = (
        CheckConstraint(
            "affected_support_judgment_count >= 0",
            name="ck_claim_support_policy_change_impacts_support_count",
        ),
        CheckConstraint(
            "affected_generated_document_count >= 0",
            name="ck_claim_support_policy_change_impacts_document_count",
        ),
        CheckConstraint(
            "affected_verification_count >= 0",
            name="ck_claim_support_policy_change_impacts_verification_count",
        ),
        CheckConstraint(
            "replay_recommended_count >= 0",
            name="ck_claim_support_policy_change_impacts_replay_count",
        ),
        CheckConstraint(
            "replay_status IN "
            "('no_action_required', 'pending', 'queued', 'in_progress', 'blocked', 'closed')",
            name="ck_claim_support_policy_change_impacts_replay_status",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_activation_task",
            "activation_task_id",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_policy",
            "activated_policy_id",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_governance_event",
            "semantic_governance_event_id",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_governance_artifact",
            "governance_artifact_id",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_scope_created",
            "impact_scope",
            "created_at",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_payload_sha",
            "impact_payload_sha256",
        ),
        Index(
            "ix_claim_support_policy_change_impacts_replay_status",
            "replay_status",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activation_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    activated_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    previous_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_support_calibration_policies.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    governance_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    impact_scope: Mapped[str] = mapped_column(Text, nullable=False)
    policy_name: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    activated_policy_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    previous_policy_sha256: Mapped[str | None] = mapped_column(Text)
    affected_support_judgment_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    affected_generated_document_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    affected_verification_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    replay_recommended_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    replay_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default=sql_text("'pending'"),
    )
    impacted_claim_derivation_ids_json: Mapped[list] = mapped_column(
        "impacted_claim_derivation_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impacted_task_ids_json: Mapped[list] = mapped_column(
        "impacted_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impacted_verification_task_ids_json: Mapped[list] = mapped_column(
        "impacted_verification_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    impact_payload_json: Mapped[dict] = mapped_column(
        "impact_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    impact_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    replay_task_ids_json: Mapped[list] = mapped_column(
        "replay_task_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    replay_task_plan_json: Mapped[dict] = mapped_column(
        "replay_task_plan",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    replay_closure_json: Mapped[dict] = mapped_column(
        "replay_closure",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    replay_closure_sha256: Mapped[str | None] = mapped_column(Text)
    replay_status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replay_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("run_id", "chunk_index", name="uq_document_chunks_run_chunk_index"),
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_page_from", "page_from"),
        Index("ix_document_chunks_page_to", "page_to"),
        Index("ix_document_chunks_textsearch", "textsearch", postgresql_using="gin"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    textsearch: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(heading, '')), 'A') || "
            "to_tsvector('english', coalesce(text, ''))",
            persisted=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentTable(Base):
    __tablename__ = "document_tables"
    __table_args__ = (
        UniqueConstraint("run_id", "table_index", name="uq_document_tables_run_table_index"),
        Index("ix_document_tables_document_id", "document_id"),
        Index("ix_document_tables_page_from", "page_from"),
        Index("ix_document_tables_page_to", "page_to"),
        Index("ix_document_tables_textsearch", "textsearch", postgresql_using="gin"),
        Index(
            "ix_document_tables_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    table_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    logical_table_key: Mapped[str | None] = mapped_column(Text)
    table_version: Mapped[int | None] = mapped_column(Integer)
    supersedes_table_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lineage_group: Mapped[str | None] = mapped_column(Text)
    heading: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    row_count: Mapped[int | None] = mapped_column(Integer)
    col_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="persisted", server_default=sql_text("'persisted'")
    )
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    preview_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    json_path: Mapped[str | None] = mapped_column(Text)
    yaml_path: Mapped[str | None] = mapped_column(Text)
    textsearch: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(heading, '')), 'B') || "
            "to_tsvector('english', coalesce(search_text, ''))",
            persisted=True,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentTableSegment(Base):
    __tablename__ = "document_table_segments"
    __table_args__ = (
        UniqueConstraint(
            "table_id", "segment_index", name="uq_document_table_segments_table_segment_index"
        ),
        Index("ix_document_table_segments_run_id", "run_id"),
        Index("ix_document_table_segments_page_from", "page_from"),
        Index("ix_document_table_segments_page_to", "page_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_tables.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_table_ref: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    segment_order: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentFigure(Base):
    __tablename__ = "document_figures"
    __table_args__ = (
        UniqueConstraint("run_id", "figure_index", name="uq_document_figures_run_figure_index"),
        Index("ix_document_figures_document_id", "document_id"),
        Index("ix_document_figures_run_id", "run_id"),
        Index("ix_document_figures_page_from", "page_from"),
        Index("ix_document_figures_page_to", "page_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False
    )
    figure_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_figure_ref: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    heading: Mapped[str | None] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="persisted", server_default=sql_text("'persisted'")
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    json_path: Mapped[str | None] = mapped_column(Text)
    yaml_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
