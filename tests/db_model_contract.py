"""Expected public ORM model contract for data-model boundary work."""

from __future__ import annotations

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

MODEL_DOMAIN_SYMBOLS = {
    "ingest": (
        "IngestBatch",
        "IngestBatchItem",
        "Document",
        "DocumentRun",
    ),
    "document_artifacts": (
        "DocumentRunEvaluation",
        "DocumentRunEvaluationQuery",
        "DocumentChunk",
        "DocumentTable",
        "DocumentTableSegment",
        "DocumentFigure",
    ),
    "retrieval": (
        "SearchRequestRecord",
        "SearchRequestResult",
        "RetrievalEvidenceSpan",
        "RetrievalEvidenceSpanMultiVector",
        "SearchRequestResultSpan",
        "SearchFeedback",
        "SearchReplayRun",
        "SearchReplayQuery",
        "SearchHarnessEvaluation",
        "SearchHarnessEvaluationSource",
        "SearchHarnessRelease",
        "SearchHarnessReleaseReadinessAssessment",
        "RetrievalJudgmentSet",
        "RetrievalJudgment",
        "RetrievalHardNegative",
        "RetrievalTrainingRun",
        "RetrievalLearningCandidateEvaluation",
        "RetrievalRerankerArtifact",
        "ChatAnswerRecord",
        "ChatAnswerFeedback",
    ),
    "semantic_memory": (
        "SemanticOntologySnapshot",
        "WorkspaceSemanticState",
        "SemanticGraphSnapshot",
        "WorkspaceSemanticGraphState",
        "SemanticConcept",
        "SemanticCategory",
        "SemanticTerm",
        "SemanticConceptTerm",
        "SemanticConceptCategoryBinding",
        "DocumentSemanticConceptReview",
        "DocumentSemanticCategoryReview",
        "DocumentRunSemanticPass",
        "SemanticAssertion",
        "SemanticAssertionCategoryBinding",
        "SemanticAssertionEvidence",
        "SemanticEntity",
        "SemanticFact",
        "SemanticFactEvidence",
        "SemanticGovernanceEvent",
    ),
    "agent_tasks": (
        "AgentTask",
        "AgentTaskDependency",
        "AgentTaskAttempt",
        "AgentTaskArtifact",
        "AgentTaskArtifactImmutabilityEvent",
        "AgentTaskOutcome",
        "AgentTaskVerification",
        "KnowledgeOperatorRun",
        "KnowledgeOperatorInput",
        "KnowledgeOperatorOutput",
    ),
    "audit_and_evidence": (
        "AuditBundleExport",
        "AuditBundleValidationReceipt",
        "EvidencePackageExport",
        "EvidenceManifest",
        "TechnicalReportReleaseReadinessDbGate",
        "TechnicalReportClaimRetrievalFeedback",
        "EvidenceTraceNode",
        "EvidenceTraceEdge",
        "ClaimEvidenceDerivation",
    ),
    "claim_support": (
        "ClaimSupportReplayAlertFixtureCoverageWaiverLedger",
        "ClaimSupportReplayAlertFixtureCoverageWaiverEscalation",
        "ClaimSupportFixtureSet",
        "ClaimSupportReplayAlertFixtureCorpusSnapshot",
        "ClaimSupportReplayAlertFixtureCorpusRow",
        "ClaimSupportCalibrationPolicy",
        "ClaimSupportEvaluation",
        "ClaimSupportEvaluationCase",
        "ClaimSupportPolicyChangeImpact",
    ),
    "evaluation_feedback": (
        "EvalObservation",
        "EvalFailureCase",
    ),
    "platform_support": (
        "ApiIdempotencyKey",
    ),
}

MODEL_SYMBOLS = tuple(
    symbol
    for domain_symbols in MODEL_DOMAIN_SYMBOLS.values()
    for symbol in domain_symbols
)

PUBLIC_MODEL_IMPORT_SYMBOLS = ENUM_SYMBOLS + MODEL_SYMBOLS

EXPECTED_TABLE_NAMES = frozenset(
    {
        "agent_task_artifact_immutability_events",
        "agent_task_artifacts",
        "agent_task_attempts",
        "agent_task_dependencies",
        "agent_task_outcomes",
        "agent_task_verifications",
        "agent_tasks",
        "api_idempotency_keys",
        "audit_bundle_exports",
        "audit_bundle_validation_receipts",
        "chat_answer_feedback",
        "chat_answer_records",
        "claim_evidence_derivations",
        "claim_support_calibration_policies",
        "claim_support_evaluation_cases",
        "claim_support_evaluations",
        "claim_support_fixture_sets",
        "claim_support_policy_change_impacts",
        "claim_support_replay_alert_fixture_corpus_rows",
        "claim_support_replay_alert_fixture_corpus_snapshots",
        "claim_support_replay_alert_fixture_coverage_waiver_escalations",
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers",
        "document_chunks",
        "document_figures",
        "document_run_evaluation_queries",
        "document_run_evaluations",
        "document_run_semantic_passes",
        "document_runs",
        "document_semantic_category_reviews",
        "document_semantic_concept_reviews",
        "document_table_segments",
        "document_tables",
        "documents",
        "eval_failure_cases",
        "eval_observations",
        "evidence_manifests",
        "evidence_package_exports",
        "evidence_trace_edges",
        "evidence_trace_nodes",
        "ingest_batch_items",
        "ingest_batches",
        "knowledge_operator_inputs",
        "knowledge_operator_outputs",
        "knowledge_operator_runs",
        "retrieval_evidence_span_multivectors",
        "retrieval_evidence_spans",
        "retrieval_hard_negatives",
        "retrieval_judgment_sets",
        "retrieval_judgments",
        "retrieval_learning_candidate_evaluations",
        "retrieval_reranker_artifacts",
        "retrieval_training_runs",
        "search_feedback",
        "search_harness_evaluation_sources",
        "search_harness_evaluations",
        "search_harness_release_readiness_assessments",
        "search_harness_releases",
        "search_replay_queries",
        "search_replay_runs",
        "search_request_result_spans",
        "search_request_results",
        "search_requests",
        "semantic_assertion_category_bindings",
        "semantic_assertion_evidence",
        "semantic_assertions",
        "semantic_categories",
        "semantic_concept_category_bindings",
        "semantic_concept_terms",
        "semantic_concepts",
        "semantic_entities",
        "semantic_fact_evidence",
        "semantic_facts",
        "semantic_governance_events",
        "semantic_graph_snapshots",
        "semantic_ontology_snapshots",
        "semantic_terms",
        "technical_report_claim_retrieval_feedback",
        "technical_report_release_readiness_db_gates",
        "workspace_semantic_graph_state",
        "workspace_semantic_state",
    }
)

REQUIRED_TABLE_INDEX_NAMES = {
    "api_idempotency_keys": frozenset(
        {
            "ix_api_idempotency_keys_created_at",
        }
    ),
    "document_runs": frozenset(
        {
            "ix_document_runs_locked_at",
            "ix_document_runs_status_completed_at",
            "ix_document_runs_status_next_attempt_at",
        }
    )
}

REQUIRED_TABLE_INDEX_COLUMNS = {
    "api_idempotency_keys": {
        "ix_api_idempotency_keys_created_at": ("created_at",),
    }
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "api_idempotency_keys": frozenset(
        {
            "uq_api_idempotency_keys_scope_key",
        }
    )
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "api_idempotency_keys": {
        "uq_api_idempotency_keys_scope_key": ("scope", "idempotency_key"),
    }
}

PLATFORM_SUPPORT_TABLE_COLUMNS = {
    "api_idempotency_keys": frozenset(
        {
            "id",
            "scope",
            "idempotency_key",
            "request_fingerprint",
            "status_code",
            "response",
            "created_at",
        }
    )
}
