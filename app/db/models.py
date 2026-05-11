from __future__ import annotations

import importlib
from enum import StrEnum

from app.db.model_domains import agent_tasks as agent_tasks_domain
from app.db.model_domains import claim_support as claim_support_domain
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

# Delay these imports until their FK target tables are registered.
audit_and_evidence_domain = importlib.import_module("app.db.model_domains.audit_and_evidence")
semantic_memory_domain = importlib.import_module("app.db.model_domains.semantic_memory")

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
ClaimSupportCalibrationPolicy = claim_support_domain.ClaimSupportCalibrationPolicy
ClaimSupportEvaluation = claim_support_domain.ClaimSupportEvaluation
ClaimSupportEvaluationCase = claim_support_domain.ClaimSupportEvaluationCase
ClaimSupportFixtureSet = claim_support_domain.ClaimSupportFixtureSet
ClaimSupportPolicyChangeImpact = claim_support_domain.ClaimSupportPolicyChangeImpact
ClaimSupportReplayAlertFixtureCorpusRow = (
    claim_support_domain.ClaimSupportReplayAlertFixtureCorpusRow
)
ClaimSupportReplayAlertFixtureCorpusSnapshot = (
    claim_support_domain.ClaimSupportReplayAlertFixtureCorpusSnapshot
)
ClaimSupportReplayAlertFixtureCoverageWaiverEscalation = (
    claim_support_domain.ClaimSupportReplayAlertFixtureCoverageWaiverEscalation
)
ClaimSupportReplayAlertFixtureCoverageWaiverLedger = (
    claim_support_domain.ClaimSupportReplayAlertFixtureCoverageWaiverLedger
)
ChatAnswerFeedback = retrieval_interactions_domain.ChatAnswerFeedback
ChatAnswerRecord = retrieval_interactions_domain.ChatAnswerRecord
DocumentRunSemanticPass = semantic_memory_domain.DocumentRunSemanticPass
DocumentSemanticCategoryReview = semantic_memory_domain.DocumentSemanticCategoryReview
DocumentSemanticConceptReview = semantic_memory_domain.DocumentSemanticConceptReview
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
SemanticAssertion = semantic_memory_domain.SemanticAssertion
SemanticAssertionCategoryBinding = semantic_memory_domain.SemanticAssertionCategoryBinding
SemanticAssertionEvidence = semantic_memory_domain.SemanticAssertionEvidence
SemanticCategory = semantic_memory_domain.SemanticCategory
SemanticConcept = semantic_memory_domain.SemanticConcept
SemanticConceptCategoryBinding = semantic_memory_domain.SemanticConceptCategoryBinding
SemanticConceptTerm = semantic_memory_domain.SemanticConceptTerm
SemanticEntity = semantic_memory_domain.SemanticEntity
SemanticFact = semantic_memory_domain.SemanticFact
SemanticFactEvidence = semantic_memory_domain.SemanticFactEvidence
SemanticGovernanceEvent = semantic_memory_domain.SemanticGovernanceEvent
SemanticGraphSnapshot = semantic_memory_domain.SemanticGraphSnapshot
SemanticOntologySnapshot = semantic_memory_domain.SemanticOntologySnapshot
SemanticTerm = semantic_memory_domain.SemanticTerm
TechnicalReportClaimRetrievalFeedback = (
    audit_and_evidence_domain.TechnicalReportClaimRetrievalFeedback
)
TechnicalReportReleaseReadinessDbGate = (
    audit_and_evidence_domain.TechnicalReportReleaseReadinessDbGate
)
WorkspaceSemanticGraphState = semantic_memory_domain.WorkspaceSemanticGraphState
WorkspaceSemanticState = semantic_memory_domain.WorkspaceSemanticState


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
