from __future__ import annotations

import importlib
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
from app.db.model_domains import agent_tasks as agent_tasks_domain
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

# Delay this import until its FK target tables are registered.
audit_and_evidence_domain = importlib.import_module("app.db.model_domains.audit_and_evidence")

AgentTask = agent_tasks_domain.AgentTask
AgentTaskArtifact = agent_tasks_domain.AgentTaskArtifact
AgentTaskArtifactImmutabilityEvent = agent_tasks_domain.AgentTaskArtifactImmutabilityEvent
AgentTaskAttempt = agent_tasks_domain.AgentTaskAttempt
AgentTaskDependency = agent_tasks_domain.AgentTaskDependency
AgentTaskOutcome = agent_tasks_domain.AgentTaskOutcome
AgentTaskVerification = agent_tasks_domain.AgentTaskVerification
AuditBundleExport = audit_and_evidence_domain.AuditBundleExport
AuditBundleValidationReceipt = audit_and_evidence_domain.AuditBundleValidationReceipt
ClaimEvidenceDerivation = audit_and_evidence_domain.ClaimEvidenceDerivation
ChatAnswerFeedback = retrieval_interactions_domain.ChatAnswerFeedback
ChatAnswerRecord = retrieval_interactions_domain.ChatAnswerRecord
EvidenceManifest = audit_and_evidence_domain.EvidenceManifest
EvidencePackageExport = audit_and_evidence_domain.EvidencePackageExport
EvidenceTraceEdge = audit_and_evidence_domain.EvidenceTraceEdge
EvidenceTraceNode = audit_and_evidence_domain.EvidenceTraceNode
EvalFailureCase = evaluation_feedback_domain.EvalFailureCase
EvalObservation = evaluation_feedback_domain.EvalObservation
KnowledgeOperatorInput = agent_tasks_domain.KnowledgeOperatorInput
KnowledgeOperatorOutput = agent_tasks_domain.KnowledgeOperatorOutput
KnowledgeOperatorRun = agent_tasks_domain.KnowledgeOperatorRun
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
TechnicalReportClaimRetrievalFeedback = (
    audit_and_evidence_domain.TechnicalReportClaimRetrievalFeedback
)
TechnicalReportReleaseReadinessDbGate = (
    audit_and_evidence_domain.TechnicalReportReleaseReadinessDbGate
)


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
