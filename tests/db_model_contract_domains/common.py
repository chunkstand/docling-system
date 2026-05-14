"""Shared DB model contract exports."""

from __future__ import annotations

DB_MODELS_ENUM_SUPPORT_MODULE = "app.db._model_enums"

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
