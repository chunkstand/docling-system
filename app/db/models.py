from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.model_domains import evaluation_feedback as evaluation_feedback_domain
from app.db.model_domains import retrieval_interactions as retrieval_interactions_domain
from app.db.model_domains import (
    retrieval_learning_artifacts as retrieval_learning_artifacts_domain,
)
from app.db.model_domains import (
    retrieval_learning_examples as retrieval_learning_examples_domain,
)
from app.db.model_domains import (
    retrieval_replay_governance as retrieval_replay_governance_domain,
)
from app.db.model_domains.document_artifacts import DocumentChunk as DocumentChunk
from app.db.model_domains.document_artifacts import DocumentFigure as DocumentFigure
from app.db.model_domains.document_artifacts import DocumentRunEvaluation as DocumentRunEvaluation
from app.db.model_domains.document_artifacts import (
    DocumentRunEvaluationQuery as DocumentRunEvaluationQuery,
)
from app.db.model_domains.document_artifacts import DocumentTable as DocumentTable
from app.db.model_domains.document_artifacts import DocumentTableSegment as DocumentTableSegment
from app.db.model_domains.ingest import (
    DOCUMENT_METADATA_NORMALIZE_SQL as DOCUMENT_METADATA_NORMALIZE_SQL,
)
from app.db.model_domains.ingest import (
    DOCUMENT_METADATA_TEXTSEARCH_SQL as DOCUMENT_METADATA_TEXTSEARCH_SQL,
)
from app.db.model_domains.ingest import Document as Document
from app.db.model_domains.ingest import DocumentRun as DocumentRun
from app.db.model_domains.ingest import IngestBatch as IngestBatch
from app.db.model_domains.ingest import IngestBatchItem as IngestBatchItem
from app.db.model_domains.platform import ApiIdempotencyKey as ApiIdempotencyKey

ChatAnswerFeedback = retrieval_interactions_domain.ChatAnswerFeedback
ChatAnswerRecord = retrieval_interactions_domain.ChatAnswerRecord
EvalFailureCase = evaluation_feedback_domain.EvalFailureCase
EvalObservation = evaluation_feedback_domain.EvalObservation
RetrievalEvidenceSpan = retrieval_interactions_domain.RetrievalEvidenceSpan
RetrievalEvidenceSpanMultiVector = retrieval_interactions_domain.RetrievalEvidenceSpanMultiVector
RetrievalHardNegative = retrieval_learning_examples_domain.RetrievalHardNegative
RetrievalJudgment = retrieval_learning_examples_domain.RetrievalJudgment
RetrievalJudgmentSet = retrieval_learning_examples_domain.RetrievalJudgmentSet
RetrievalLearningCandidateEvaluation = (
    retrieval_learning_artifacts_domain.RetrievalLearningCandidateEvaluation
)
RetrievalRerankerArtifact = retrieval_learning_artifacts_domain.RetrievalRerankerArtifact
RetrievalTrainingRun = retrieval_learning_artifacts_domain.RetrievalTrainingRun
SearchFeedback = retrieval_interactions_domain.SearchFeedback
SearchHarnessEvaluation = retrieval_replay_governance_domain.SearchHarnessEvaluation
SearchHarnessEvaluationSource = retrieval_replay_governance_domain.SearchHarnessEvaluationSource
SearchHarnessRelease = retrieval_replay_governance_domain.SearchHarnessRelease
SearchHarnessReleaseReadinessAssessment = (
    retrieval_replay_governance_domain.SearchHarnessReleaseReadinessAssessment
)
SearchReplayQuery = retrieval_replay_governance_domain.SearchReplayQuery
SearchReplayRun = retrieval_replay_governance_domain.SearchReplayRun
SearchRequestRecord = retrieval_interactions_domain.SearchRequestRecord
SearchRequestResult = retrieval_interactions_domain.SearchRequestResult
SearchRequestResultSpan = retrieval_interactions_domain.SearchRequestResultSpan


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
    SEARCH_HARNESS_RELEASE_READINESS_ASSESSED = (
        "search_harness_release_readiness_assessed"
    )
    TECHNICAL_REPORT_PROV_EXPORT_FROZEN = "technical_report_prov_export_frozen"
    TECHNICAL_REPORT_READINESS_DB_GATE_RECORDED = (
        "technical_report_readiness_db_gate_recorded"
    )
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_RECORDED = (
        "technical_report_claim_retrieval_feedback_recorded"
    )
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


class TechnicalReportClaimRetrievalFeedbackStatus(StrEnum):
    SUPPORTED = "supported"
    WEAK = "weak"
    MISSING = "missing"
    CONTRADICTED = "contradicted"
    REJECTED = "rejected"


class TechnicalReportClaimRetrievalLearningLabel(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MISSING = "missing"


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


class TechnicalReportReleaseReadinessDbGate(Base):
    __tablename__ = "technical_report_release_readiness_db_gates"
    __table_args__ = (
        CheckConstraint(
            "check_key = 'release_readiness_assessment_db_integrity'",
            name="ck_tr_readiness_db_gates_check_key",
        ),
        CheckConstraint(
            "source_search_request_count >= 0 "
            "AND verified_request_count >= 0 "
            "AND failure_count >= 0",
            name="ck_tr_readiness_db_gates_nonnegative_counts",
        ),
        CheckConstraint(
            "char_length(gate_payload_sha256) = 64",
            name="ck_tr_readiness_db_gates_payload_sha_length",
        ),
        CheckConstraint(
            "source_search_request_count = jsonb_array_length(source_search_request_ids) "
            "AND verified_request_count = jsonb_array_length(verified_request_ids)",
            name="ck_tr_readiness_db_gates_request_count_consistency",
        ),
        CheckConstraint(
            "NOT complete OR ("
            "passed "
            "AND coverage_complete "
            "AND failure_count = 0 "
            "AND missing_expected_request_ids = '[]'::jsonb "
            "AND unexpected_verified_request_ids = '[]'::jsonb"
            ")",
            name="ck_tr_readiness_db_gates_complete_consistency",
        ),
        UniqueConstraint(
            "technical_report_verification_task_id",
            name="uq_tr_readiness_db_gates_verification_task",
        ),
        Index(
            "ix_tr_readiness_db_gates_verification_task",
            "technical_report_verification_task_id",
        ),
        Index(
            "ix_tr_readiness_db_gates_source_verification",
            "source_verification_id",
        ),
        Index("ix_tr_readiness_db_gates_harness_task", "harness_task_id"),
        Index("ix_tr_readiness_db_gates_manifest", "evidence_manifest_id"),
        Index("ix_tr_readiness_db_gates_prov_artifact", "prov_export_artifact_id"),
        Index("ix_tr_readiness_db_gates_governance", "semantic_governance_event_id"),
        Index("ix_tr_readiness_db_gates_payload_sha", "gate_payload_sha256"),
        Index("ix_tr_readiness_db_gates_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    technical_report_verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_verification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_verifications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_verification_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    harness_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
    )
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="SET NULL"),
    )
    prov_export_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    check_key: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    required: Mapped[bool | None] = mapped_column(Boolean)
    coverage_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_search_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    verified_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    source_search_request_ids_json: Mapped[list] = mapped_column(
        "source_search_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    verified_request_ids_json: Mapped[list] = mapped_column(
        "verified_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    missing_expected_request_ids_json: Mapped[list] = mapped_column(
        "missing_expected_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    unexpected_verified_request_ids_json: Mapped[list] = mapped_column(
        "unexpected_verified_request_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    summary_json: Mapped[dict] = mapped_column(
        "summary",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    gate_payload_json: Mapped[dict] = mapped_column(
        "gate_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    gate_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TechnicalReportClaimRetrievalFeedback(Base):
    __tablename__ = "technical_report_claim_retrieval_feedback"
    __table_args__ = (
        CheckConstraint(
            "support_verdict IN ('supported', 'unsupported', 'insufficient_evidence')",
            name="ck_tr_claim_feedback_support_verdict",
        ),
        CheckConstraint(
            "feedback_status IN ('supported', 'weak', 'missing', 'contradicted', 'rejected')",
            name="ck_tr_claim_feedback_status",
        ),
        CheckConstraint(
            "learning_label IN ('positive', 'negative', 'missing')",
            name="ck_tr_claim_feedback_learning_label",
        ),
        CheckConstraint(
            "hard_negative_kind IS NULL OR hard_negative_kind IN ("
            "'explicit_irrelevant', "
            "'missing_expected', "
            "'failed_replay_top_result', "
            "'wrong_result_type', "
            "'no_answer_returned'"
            ")",
            name="ck_tr_claim_feedback_hard_negative_kind",
        ),
        CheckConstraint(
            "char_length(feedback_payload_sha256) = 64",
            name="ck_tr_claim_feedback_payload_sha_length",
        ),
        CheckConstraint(
            "char_length(source_payload_sha256) = 64",
            name="ck_tr_claim_feedback_source_sha_length",
        ),
        UniqueConstraint(
            "technical_report_verification_task_id",
            "claim_id",
            name="uq_tr_claim_feedback_verification_claim",
        ),
        Index(
            "ix_tr_claim_feedback_verification_task",
            "technical_report_verification_task_id",
        ),
        Index("ix_tr_claim_feedback_claim", "claim_id"),
        Index("ix_tr_claim_feedback_derivation", "claim_evidence_derivation_id"),
        Index("ix_tr_claim_feedback_manifest", "evidence_manifest_id"),
        Index("ix_tr_claim_feedback_prov_artifact", "prov_export_artifact_id"),
        Index("ix_tr_claim_feedback_release_gate", "release_readiness_db_gate_id"),
        Index("ix_tr_claim_feedback_governance", "semantic_governance_event_id"),
        Index("ix_tr_claim_feedback_source_request", "source_search_request_id"),
        Index("ix_tr_claim_feedback_search_result", "search_request_result_id"),
        Index("ix_tr_claim_feedback_status_label", "feedback_status", "learning_label"),
        Index("ix_tr_claim_feedback_payload_sha", "feedback_payload_sha256"),
        Index("ix_tr_claim_feedback_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    technical_report_verification_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_evidence_derivation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_evidence_derivations.id", ondelete="SET NULL"),
    )
    evidence_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_manifests.id", ondelete="SET NULL"),
    )
    prov_export_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_task_artifacts.id", ondelete="SET NULL"),
    )
    release_readiness_db_gate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technical_report_release_readiness_db_gates.id", ondelete="SET NULL"),
    )
    semantic_governance_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_governance_events.id", ondelete="SET NULL"),
    )
    claim_id: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str | None] = mapped_column(Text)
    support_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    support_score: Mapped[float | None] = mapped_column(Float)
    feedback_status: Mapped[str] = mapped_column(Text, nullable=False)
    learning_label: Mapped[str] = mapped_column(Text, nullable=False)
    hard_negative_kind: Mapped[str | None] = mapped_column(Text)
    source_search_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_requests.id", ondelete="SET NULL"),
    )
    search_request_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_request_results.id", ondelete="SET NULL"),
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
    search_request_result_span_ids_json: Mapped[list] = mapped_column(
        "search_request_result_span_ids",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    retrieval_evidence_span_ids_json: Mapped[list] = mapped_column(
        "retrieval_evidence_span_ids",
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
    evidence_refs_json: Mapped[list] = mapped_column(
        "evidence_refs",
        JSONB,
        nullable=False,
        default=list,
        server_default=sql_text("'[]'::jsonb"),
    )
    retrieval_context_json: Mapped[dict] = mapped_column(
        "retrieval_context",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    feedback_payload_json: Mapped[dict] = mapped_column(
        "feedback_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    feedback_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload_json: Mapped[dict] = mapped_column(
        "source_payload",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sql_text("'{}'::jsonb"),
    )
    source_payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
