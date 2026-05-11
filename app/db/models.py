from __future__ import annotations

import importlib as _importlib
from enum import StrEnum as _StrEnum

from app.db.model_domains import agent_tasks as _agent_tasks_domain
from app.db.model_domains import claim_support as _claim_support_domain
from app.db.model_domains import evaluation_feedback as _evaluation_feedback_domain
from app.db.model_domains import retrieval_interactions as _retrieval_interactions_domain
from app.db.model_domains import (
    retrieval_learning_artifacts as _retrieval_learning_artifacts_domain,
)
from app.db.model_domains import (
    retrieval_learning_examples as _retrieval_learning_examples_domain,
)
from app.db.model_domains import (
    retrieval_replay_governance as _retrieval_replay_governance_domain,
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
_audit_and_evidence_domain = _importlib.import_module("app.db.model_domains.audit_and_evidence")
_semantic_memory_domain = _importlib.import_module("app.db.model_domains.semantic_memory")

AgentTask = _agent_tasks_domain.AgentTask
AgentTaskArtifact = _agent_tasks_domain.AgentTaskArtifact
AgentTaskArtifactImmutabilityEvent = _agent_tasks_domain.AgentTaskArtifactImmutabilityEvent
AgentTaskAttempt = _agent_tasks_domain.AgentTaskAttempt
AgentTaskDependency = _agent_tasks_domain.AgentTaskDependency
AgentTaskOutcome = _agent_tasks_domain.AgentTaskOutcome
AgentTaskVerification = _agent_tasks_domain.AgentTaskVerification
AuditBundleExport = _audit_and_evidence_domain.AuditBundleExport
AuditBundleValidationReceipt = _audit_and_evidence_domain.AuditBundleValidationReceipt
ClaimEvidenceDerivation = _audit_and_evidence_domain.ClaimEvidenceDerivation
ClaimSupportCalibrationPolicy = _claim_support_domain.ClaimSupportCalibrationPolicy
ClaimSupportEvaluation = _claim_support_domain.ClaimSupportEvaluation
ClaimSupportEvaluationCase = _claim_support_domain.ClaimSupportEvaluationCase
ClaimSupportFixtureSet = _claim_support_domain.ClaimSupportFixtureSet
ClaimSupportPolicyChangeImpact = _claim_support_domain.ClaimSupportPolicyChangeImpact
ClaimSupportReplayAlertFixtureCorpusRow = (
    _claim_support_domain.ClaimSupportReplayAlertFixtureCorpusRow
)
ClaimSupportReplayAlertFixtureCorpusSnapshot = (
    _claim_support_domain.ClaimSupportReplayAlertFixtureCorpusSnapshot
)
ClaimSupportReplayAlertFixtureCoverageWaiverEscalation = (
    _claim_support_domain.ClaimSupportReplayAlertFixtureCoverageWaiverEscalation
)
ClaimSupportReplayAlertFixtureCoverageWaiverLedger = (
    _claim_support_domain.ClaimSupportReplayAlertFixtureCoverageWaiverLedger
)
ChatAnswerFeedback = _retrieval_interactions_domain.ChatAnswerFeedback
ChatAnswerRecord = _retrieval_interactions_domain.ChatAnswerRecord
DocumentRunSemanticPass = _semantic_memory_domain.DocumentRunSemanticPass
DocumentSemanticCategoryReview = _semantic_memory_domain.DocumentSemanticCategoryReview
DocumentSemanticConceptReview = _semantic_memory_domain.DocumentSemanticConceptReview
EvidenceManifest = _audit_and_evidence_domain.EvidenceManifest
EvidencePackageExport = _audit_and_evidence_domain.EvidencePackageExport
EvidenceTraceEdge = _audit_and_evidence_domain.EvidenceTraceEdge
EvidenceTraceNode = _audit_and_evidence_domain.EvidenceTraceNode
EvalFailureCase = _evaluation_feedback_domain.EvalFailureCase
EvalObservation = _evaluation_feedback_domain.EvalObservation
KnowledgeOperatorInput = _agent_tasks_domain.KnowledgeOperatorInput
KnowledgeOperatorOutput = _agent_tasks_domain.KnowledgeOperatorOutput
KnowledgeOperatorRun = _agent_tasks_domain.KnowledgeOperatorRun
RetrievalEvidenceSpan = _retrieval_interactions_domain.RetrievalEvidenceSpan
RetrievalEvidenceSpanMultiVector = _retrieval_interactions_domain.RetrievalEvidenceSpanMultiVector
RetrievalHardNegative = _retrieval_learning_examples_domain.RetrievalHardNegative
RetrievalJudgment = _retrieval_learning_examples_domain.RetrievalJudgment
RetrievalJudgmentSet = _retrieval_learning_examples_domain.RetrievalJudgmentSet
RetrievalLearningCandidateEvaluation = (
    _retrieval_learning_artifacts_domain.RetrievalLearningCandidateEvaluation
)
RetrievalRerankerArtifact = _retrieval_learning_artifacts_domain.RetrievalRerankerArtifact
RetrievalTrainingRun = _retrieval_learning_artifacts_domain.RetrievalTrainingRun
SearchFeedback = _retrieval_interactions_domain.SearchFeedback
SearchHarnessEvaluation = _retrieval_replay_governance_domain.SearchHarnessEvaluation
SearchHarnessEvaluationSource = _retrieval_replay_governance_domain.SearchHarnessEvaluationSource
SearchHarnessRelease = _retrieval_replay_governance_domain.SearchHarnessRelease
SearchHarnessReleaseReadinessAssessment = (
    _retrieval_replay_governance_domain.SearchHarnessReleaseReadinessAssessment
)
SearchReplayQuery = _retrieval_replay_governance_domain.SearchReplayQuery
SearchReplayRun = _retrieval_replay_governance_domain.SearchReplayRun
SearchRequestRecord = _retrieval_interactions_domain.SearchRequestRecord
SearchRequestResult = _retrieval_interactions_domain.SearchRequestResult
SearchRequestResultSpan = _retrieval_interactions_domain.SearchRequestResultSpan
SemanticAssertion = _semantic_memory_domain.SemanticAssertion
SemanticAssertionCategoryBinding = _semantic_memory_domain.SemanticAssertionCategoryBinding
SemanticAssertionEvidence = _semantic_memory_domain.SemanticAssertionEvidence
SemanticCategory = _semantic_memory_domain.SemanticCategory
SemanticConcept = _semantic_memory_domain.SemanticConcept
SemanticConceptCategoryBinding = _semantic_memory_domain.SemanticConceptCategoryBinding
SemanticConceptTerm = _semantic_memory_domain.SemanticConceptTerm
SemanticEntity = _semantic_memory_domain.SemanticEntity
SemanticFact = _semantic_memory_domain.SemanticFact
SemanticFactEvidence = _semantic_memory_domain.SemanticFactEvidence
SemanticGovernanceEvent = _semantic_memory_domain.SemanticGovernanceEvent
SemanticGraphSnapshot = _semantic_memory_domain.SemanticGraphSnapshot
SemanticOntologySnapshot = _semantic_memory_domain.SemanticOntologySnapshot
SemanticTerm = _semantic_memory_domain.SemanticTerm
TechnicalReportClaimRetrievalFeedback = (
    _audit_and_evidence_domain.TechnicalReportClaimRetrievalFeedback
)
TechnicalReportReleaseReadinessDbGate = (
    _audit_and_evidence_domain.TechnicalReportReleaseReadinessDbGate
)
WorkspaceSemanticGraphState = _semantic_memory_domain.WorkspaceSemanticGraphState
WorkspaceSemanticState = _semantic_memory_domain.WorkspaceSemanticState


class RunStatus(_StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    VALIDATING = "validating"
    RETRY_WAIT = "retry_wait"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTaskStatus(_StrEnum):
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRY_WAIT = "retry_wait"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTaskSideEffectLevel(_StrEnum):
    READ_ONLY = "read_only"
    DRAFT_CHANGE = "draft_change"
    PROMOTABLE = "promotable"


class AgentTaskDependencyKind(_StrEnum):
    EXPLICIT = "explicit"
    TARGET_TASK = "target_task"
    SOURCE_TASK = "source_task"
    DRAFT_TASK = "draft_task"
    VERIFICATION_TASK = "verification_task"


class AgentTaskAttemptStatus(_StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class AgentTaskVerificationOutcome(_StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class AgentTaskOutcomeLabel(_StrEnum):
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    CORRECT = "correct"
    INCORRECT = "incorrect"


class KnowledgeOperatorKind(_StrEnum):
    PARSE = "parse"
    EMBED = "embed"
    RETRIEVE = "retrieve"
    RERANK = "rerank"
    JUDGE = "judge"
    GENERATE = "generate"
    VERIFY = "verify"
    EXPORT = "export"
    ORCHESTRATE = "orchestrate"


class KnowledgeOperatorStatus(_StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SemanticPassStatus(_StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SemanticEvaluationStatus(_StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SemanticGovernanceEventKind(_StrEnum):
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


class RetrievalJudgmentKind(_StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MISSING = "missing"


class RetrievalHardNegativeKind(_StrEnum):
    EXPLICIT_IRRELEVANT = "explicit_irrelevant"
    MISSING_EXPECTED = "missing_expected"
    FAILED_REPLAY_TOP_RESULT = "failed_replay_top_result"
    WRONG_RESULT_TYPE = "wrong_result_type"
    NO_ANSWER_RETURNED = "no_answer_returned"


class RetrievalTrainingRunStatus(_StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class TechnicalReportClaimRetrievalFeedbackStatus(_StrEnum):
    SUPPORTED = "supported"
    WEAK = "weak"
    MISSING = "missing"
    CONTRADICTED = "contradicted"
    REJECTED = "rejected"


class TechnicalReportClaimRetrievalLearningLabel(_StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MISSING = "missing"


class RetrievalLearningCandidateStatus(_StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class SemanticTermKind(_StrEnum):
    PREFERRED_LABEL = "preferred_label"
    ALIAS = "alias"


class SemanticAssertionKind(_StrEnum):
    CONCEPT_MENTION = "concept_mention"


class SemanticEvidenceSourceType(_StrEnum):
    CHUNK = "chunk"
    TABLE = "table"
    FIGURE = "figure"


class SemanticReviewStatus(_StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"


class SemanticEpistemicStatus(_StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    CURATED = "curated"


class SemanticContextScope(_StrEnum):
    DOCUMENT_RUN = "document_run"
    DOCUMENT = "document"
    REGISTRY = "registry"


class SemanticBindingOrigin(_StrEnum):
    REGISTRY = "registry"
    DERIVED = "derived"


class SemanticCategoryBindingType(_StrEnum):
    CONCEPT_CATEGORY = "concept_category"
    ASSERTION_CATEGORY = "assertion_category"


class SemanticOntologySourceKind(_StrEnum):
    UPPER_SEED = "upper_seed"
    ONTOLOGY_EXTENSION_APPLY = "ontology_extension_apply"


class SemanticGraphSourceKind(_StrEnum):
    GRAPH_PROMOTION_APPLY = "graph_promotion_apply"


class SemanticEntityType(_StrEnum):
    DOCUMENT = "document"
    CONCEPT = "concept"
    LITERAL = "literal"
