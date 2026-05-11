from __future__ import annotations

from enum import StrEnum


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
