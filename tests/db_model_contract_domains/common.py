"""Shared DB model contract exports."""

from __future__ import annotations

DB_MODELS_ENUM_SUPPORT_MODULE = "app.db._model_enums"

INGEST_ENUM_SYMBOLS = ("RunStatus",)

AGENT_TASK_ENUM_SYMBOLS = (
    "AgentTaskStatus",
    "AgentTaskSideEffectLevel",
    "AgentTaskDependencyKind",
    "AgentTaskAttemptStatus",
    "AgentTaskVerificationOutcome",
    "AgentTaskOutcomeLabel",
    "KnowledgeOperatorKind",
    "KnowledgeOperatorStatus",
)

RETRIEVAL_ENUM_SYMBOLS = (
    "RetrievalJudgmentKind",
    "RetrievalHardNegativeKind",
    "RetrievalTrainingRunStatus",
    "RetrievalLearningCandidateStatus",
)

AUDIT_AND_EVIDENCE_ENUM_SYMBOLS = (
    "TechnicalReportClaimRetrievalFeedbackStatus",
    "TechnicalReportClaimRetrievalLearningLabel",
)

SEMANTIC_MEMORY_ENUM_SYMBOLS = (
    "SemanticPassStatus",
    "SemanticEvaluationStatus",
    "SemanticGovernanceEventKind",
    "SemanticTermKind",
    "SemanticAssertionKind",
    "SemanticEvidenceSourceType",
    "SemanticReviewStatus",
    "SemanticEpistemicStatus",
    "SemanticContextScope",
    "SemanticBindingOrigin",
    "SemanticCategoryBindingType",
    "SemanticOntologySourceKind",
    "SemanticGraphSourceKind",
    "SemanticEntityType",
)

ENUM_SYMBOLS = (
    "RunStatus",
    "AgentTaskStatus",
    "AgentTaskSideEffectLevel",
    "AgentTaskDependencyKind",
    "AgentTaskAttemptStatus",
    "AgentTaskVerificationOutcome",
    "AgentTaskOutcomeLabel",
    "KnowledgeOperatorKind",
    "KnowledgeOperatorStatus",
    "SemanticPassStatus",
    "SemanticEvaluationStatus",
    "SemanticGovernanceEventKind",
    "RetrievalJudgmentKind",
    "RetrievalHardNegativeKind",
    "RetrievalTrainingRunStatus",
    "TechnicalReportClaimRetrievalFeedbackStatus",
    "TechnicalReportClaimRetrievalLearningLabel",
    "RetrievalLearningCandidateStatus",
    "SemanticTermKind",
    "SemanticAssertionKind",
    "SemanticEvidenceSourceType",
    "SemanticReviewStatus",
    "SemanticEpistemicStatus",
    "SemanticContextScope",
    "SemanticBindingOrigin",
    "SemanticCategoryBindingType",
    "SemanticOntologySourceKind",
    "SemanticGraphSourceKind",
    "SemanticEntityType",
)

FACADE_CONSTANT_SYMBOLS = ("DOCUMENT_METADATA_NORMALIZE_SQL", "DOCUMENT_METADATA_TEXTSEARCH_SQL")

ALLOWED_DB_MODELS_SUPPORT_SYMBOLS = ("annotations",)
