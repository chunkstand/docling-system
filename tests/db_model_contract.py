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
    "document_chunks": frozenset(
        {
            "ix_document_chunks_document_id",
            "ix_document_chunks_embedding_hnsw",
            "ix_document_chunks_page_from",
            "ix_document_chunks_page_to",
            "ix_document_chunks_textsearch",
        }
    ),
    "document_figures": frozenset(
        {
            "ix_document_figures_document_id",
            "ix_document_figures_page_from",
            "ix_document_figures_page_to",
            "ix_document_figures_run_id",
        }
    ),
    "document_run_evaluation_queries": frozenset(
        {
            "ix_document_run_evaluation_queries_evaluation_id",
            "ix_document_run_evaluation_queries_query_text",
        }
    ),
    "document_run_evaluations": frozenset(
        {
            "ix_document_run_evaluations_run_id",
            "ix_document_run_evaluations_status",
        }
    ),
    "document_table_segments": frozenset(
        {
            "ix_document_table_segments_page_from",
            "ix_document_table_segments_page_to",
            "ix_document_table_segments_run_id",
        }
    ),
    "document_tables": frozenset(
        {
            "ix_document_tables_document_id",
            "ix_document_tables_embedding_hnsw",
            "ix_document_tables_page_from",
            "ix_document_tables_page_to",
            "ix_document_tables_textsearch",
        }
    ),
    "documents": frozenset(
        {
            "ix_documents_metadata_textsearch",
            "ix_documents_updated_at",
        }
    ),
    "ingest_batches": frozenset(
        {
            "ix_ingest_batches_created_at",
            "ix_ingest_batches_status_created_at",
        }
    ),
    "ingest_batch_items": frozenset(
        {
            "ix_ingest_batch_items_batch_id",
            "ix_ingest_batch_items_document_id",
            "ix_ingest_batch_items_run_id",
            "ix_ingest_batch_items_status",
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

REQUIRED_TABLE_INDEX_NAMES.update(
    {
        "agent_tasks": frozenset(
            {
                "ix_agent_tasks_status_priority_next_attempt_at",
                "ix_agent_tasks_locked_at",
                "ix_agent_tasks_parent_task_id",
                "ix_agent_tasks_task_type_created_at",
            }
        ),
        "agent_task_dependencies": frozenset(
            {
                "ix_agent_task_dependencies_depends_on_task_id",
            }
        ),
        "agent_task_attempts": frozenset(
            {
                "ix_agent_task_attempts_task_id",
                "ix_agent_task_attempts_created_at",
            }
        ),
        "agent_task_artifacts": frozenset(
            {
                "ix_agent_task_artifacts_task_id",
                "ix_agent_task_artifacts_attempt_id",
                "ix_agent_task_artifacts_artifact_kind",
            }
        ),
        "agent_task_artifact_immutability_events": frozenset(
            {
                "ix_agent_artifact_immut_events_artifact_created",
                "ix_agent_artifact_immut_events_task_created",
                "ix_agent_artifact_immut_events_kind",
            }
        ),
        "agent_task_outcomes": frozenset(
            {
                "ix_agent_task_outcomes_task_id",
                "ix_agent_task_outcomes_outcome_label",
                "ix_agent_task_outcomes_created_at",
            }
        ),
        "agent_task_verifications": frozenset(
            {
                "ix_agent_task_verifications_target_task_id",
                "ix_agent_task_verifications_verification_task_id",
                "ix_agent_task_verifications_verifier_type",
                "ix_agent_task_verifications_created_at",
            }
        ),
        "knowledge_operator_runs": frozenset(
            {
                "ix_knowledge_operator_runs_created_at",
                "ix_knowledge_operator_runs_search_request_id",
                "ix_knowledge_operator_runs_agent_task_id",
                "ix_knowledge_operator_runs_parent_id",
                "ix_knowledge_operator_runs_kind_created_at",
            }
        ),
        "knowledge_operator_inputs": frozenset(
            {
                "ix_knowledge_operator_inputs_operator_run_id",
                "ix_knowledge_operator_inputs_source",
            }
        ),
        "knowledge_operator_outputs": frozenset(
            {
                "ix_knowledge_operator_outputs_operator_run_id",
                "ix_knowledge_operator_outputs_target",
            }
        ),
        "search_requests": frozenset(
            {
                "ix_search_requests_created_at",
                "ix_search_requests_origin_created_at",
                "ix_search_requests_evaluation_id",
                "ix_search_requests_parent_request_id",
            }
        ),
        "search_request_results": frozenset(
            {
                "ix_search_request_results_search_request_id",
                "ix_search_request_results_result_type",
            }
        ),
        "retrieval_evidence_spans": frozenset(
            {
                "ix_retrieval_evidence_spans_document_id",
                "ix_retrieval_evidence_spans_run_id",
                "ix_retrieval_evidence_spans_source",
                "ix_retrieval_evidence_spans_chunk_id",
                "ix_retrieval_evidence_spans_table_id",
                "ix_retrieval_evidence_spans_page_from",
                "ix_retrieval_evidence_spans_page_to",
                "ix_retrieval_evidence_spans_content_sha256",
                "ix_retrieval_evidence_spans_textsearch",
                "ix_retrieval_evidence_spans_embedding_hnsw",
            }
        ),
        "retrieval_evidence_span_multivectors": frozenset(
            {
                "ix_retrieval_span_multivectors_span_id",
                "ix_retrieval_span_multivectors_document_id",
                "ix_retrieval_span_multivectors_run_id",
                "ix_retrieval_span_multivectors_source",
                "ix_retrieval_span_multivectors_model",
                "ix_retrieval_span_multivectors_content_sha256",
                "ix_retrieval_span_multivectors_embedding_sha256",
                "ix_retrieval_span_multivectors_embedding_hnsw",
            }
        ),
        "search_request_result_spans": frozenset(
            {
                "ix_search_request_result_spans_request_id",
                "ix_search_request_result_spans_result_id",
                "ix_search_request_result_spans_span_id",
                "ix_search_request_result_spans_source",
                "ix_search_request_result_spans_content_sha256",
            }
        ),
        "search_feedback": frozenset(
            {
                "ix_search_feedback_search_request_id",
                "ix_search_feedback_search_request_result_id",
                "ix_search_feedback_feedback_type",
                "ix_search_feedback_created_at",
            }
        ),
        "chat_answer_records": frozenset(
            {
                "ix_chat_answer_records_search_request_id",
                "ix_chat_answer_records_created_at",
            }
        ),
        "chat_answer_feedback": frozenset(
            {
                "ix_chat_answer_feedback_answer_id",
                "ix_chat_answer_feedback_feedback_type",
                "ix_chat_answer_feedback_created_at",
            }
        ),
        "search_replay_runs": frozenset(
            {
                "ix_search_replay_runs_created_at",
                "ix_search_replay_runs_source_type_created_at",
            }
        ),
        "search_replay_queries": frozenset(
            {
                "ix_search_replay_queries_replay_run_id",
                "ix_search_replay_queries_source_search_request_id",
                "ix_search_replay_queries_replay_search_request_id",
                "ix_search_replay_queries_feedback_id",
                "ix_search_replay_queries_evaluation_query_id",
                "ix_search_replay_queries_created_at",
            }
        ),
        "search_harness_evaluations": frozenset(
            {
                "ix_search_harness_evaluations_baseline_candidate",
                "ix_search_harness_evaluations_candidate_created_at",
                "ix_search_harness_evaluations_created_at",
            }
        ),
        "search_harness_evaluation_sources": frozenset(
            {
                "ix_search_harness_evaluation_sources_eval_id",
                "ix_search_harness_evaluation_sources_baseline_replay",
                "ix_search_harness_evaluation_sources_candidate_replay",
            }
        ),
        "search_harness_releases": frozenset(
            {
                "ix_search_harness_releases_evaluation_id",
                "ix_search_harness_releases_candidate_created_at",
                "ix_search_harness_releases_outcome_created_at",
                "ix_search_harness_releases_created_at",
            }
        ),
        "search_harness_release_readiness_assessments": frozenset(
            {
                "ix_shr_readiness_assessments_release_created",
                "ix_shr_readiness_assessments_bundle_created",
                "ix_shr_readiness_assessments_receipt_created",
                "ix_shr_readiness_assessments_governance",
                "ix_shr_readiness_assessments_status_created",
                "ix_shr_readiness_assessments_readiness_sha",
                "ix_shr_readiness_assessments_payload_sha",
            }
        ),
        "retrieval_judgment_sets": frozenset(
            {
                "ix_retrieval_judgment_sets_created_at",
                "ix_retrieval_judgment_sets_set_kind_created",
                "ix_retrieval_judgment_sets_payload_sha",
            }
        ),
        "retrieval_judgments": frozenset(
            {
                "ix_retrieval_judgments_set_kind",
                "ix_retrieval_judgments_source",
                "ix_retrieval_judgments_search_request",
                "ix_retrieval_judgments_source_request",
                "ix_retrieval_judgments_search_result",
                "ix_retrieval_judgments_feedback",
                "ix_retrieval_judgments_replay_query",
                "ix_retrieval_judgments_result",
                "ix_retrieval_judgments_source_payload_sha",
                "ix_retrieval_judgments_created_at",
            }
        ),
        "retrieval_hard_negatives": frozenset(
            {
                "ix_retrieval_hard_negatives_set_kind",
                "ix_retrieval_hard_negatives_judgment",
                "ix_retrieval_hard_negatives_positive_judgment",
                "ix_retrieval_hard_negatives_source",
                "ix_retrieval_hard_negatives_feedback",
                "ix_retrieval_hard_negatives_replay_query",
                "ix_retrieval_hard_negatives_source_request",
                "ix_retrieval_hard_negatives_request",
                "ix_retrieval_hard_negatives_search_result",
                "ix_retrieval_hard_negatives_result",
                "ix_retrieval_hard_negatives_source_payload_sha",
                "ix_retrieval_hard_negatives_created_at",
            }
        ),
        "retrieval_training_runs": frozenset(
            {
                "ix_retrieval_training_runs_judgment_set",
                "ix_retrieval_training_runs_release",
                "ix_retrieval_training_runs_governance",
                "ix_retrieval_training_runs_dataset_sha",
                "ix_retrieval_training_runs_created_at",
            }
        ),
        "retrieval_learning_candidate_evaluations": frozenset(
            {
                "ix_retrieval_learning_candidate_training",
                "ix_retrieval_learning_candidate_judgment_set",
                "ix_retrieval_learning_candidate_evaluation",
                "ix_retrieval_learning_candidate_release",
                "ix_retrieval_learning_candidate_governance",
                "ix_retrieval_learning_candidate_dataset_sha",
                "ix_retrieval_learning_candidate_harness_created",
                "ix_retrieval_learning_candidate_outcome_created",
                "ix_retrieval_learning_candidate_package_sha",
                "ix_retrieval_learning_candidate_created_at",
            }
        ),
        "retrieval_reranker_artifacts": frozenset(
            {
                "ix_retrieval_reranker_artifacts_training_created",
                "ix_retrieval_reranker_artifacts_candidate_eval",
                "ix_retrieval_reranker_artifacts_evaluation",
                "ix_retrieval_reranker_artifacts_release",
                "ix_retrieval_reranker_artifacts_governance",
                "ix_retrieval_reranker_artifacts_candidate_created",
                "ix_retrieval_reranker_artifacts_gate_created",
                "ix_retrieval_reranker_artifacts_artifact_sha",
                "ix_retrieval_reranker_artifacts_impact_sha",
            }
        ),
        "eval_observations": frozenset(
            {
                "ix_eval_observations_surface_last_seen",
                "ix_eval_observations_status_last_seen",
                "ix_eval_observations_document_id",
                "ix_eval_observations_search_request_id",
                "ix_eval_observations_evaluation_id",
            }
        ),
        "eval_failure_cases": frozenset(
            {
                "ix_eval_failure_cases_status_updated",
                "ix_eval_failure_cases_surface_status",
                "ix_eval_failure_cases_document_id",
                "ix_eval_failure_cases_search_request_id",
                "ix_eval_failure_cases_evaluation_id",
            }
        ),
        "semantic_ontology_snapshots": frozenset(
            {
                "ix_semantic_ontology_snapshots_created_at",
                "ix_semantic_ontology_snapshots_upper_ontology_version",
            }
        ),
        "semantic_graph_snapshots": frozenset(
            {
                "ix_semantic_graph_snapshots_created_at",
                "ix_semantic_graph_snapshots_ontology_snapshot_id",
            }
        ),
        "semantic_concepts": frozenset(
            {
                "ix_semantic_concepts_concept_key",
                "ix_semantic_concepts_registry_version",
            }
        ),
        "semantic_categories": frozenset(
            {
                "ix_semantic_categories_category_key",
                "ix_semantic_categories_registry_version",
            }
        ),
        "semantic_terms": frozenset(
            {
                "ix_semantic_terms_registry_version",
                "ix_semantic_terms_normalized_text",
            }
        ),
        "semantic_concept_terms": frozenset(
            {
                "ix_semantic_concept_terms_concept_id",
                "ix_semantic_concept_terms_term_id",
            }
        ),
        "semantic_concept_category_bindings": frozenset(
            {
                "ix_semantic_concept_category_bindings_concept_id",
                "ix_semantic_concept_category_bindings_category_id",
            }
        ),
        "document_semantic_concept_reviews": frozenset(
            {
                "ix_document_semantic_concept_reviews_document_id",
                "ix_document_semantic_concept_reviews_concept_id",
                "ix_doc_sem_concept_reviews_doc_concept_created_at",
            }
        ),
        "document_semantic_category_reviews": frozenset(
            {
                "ix_document_semantic_category_reviews_document_id",
                "ix_document_semantic_category_reviews_concept_id",
                "ix_document_semantic_category_reviews_category_id",
                "ix_doc_sem_category_reviews_doc_binding_created_at",
            }
        ),
        "document_run_semantic_passes": frozenset(
            {
                "ix_document_run_semantic_passes_document_id",
                "ix_document_run_semantic_passes_run_id",
                "ix_document_run_semantic_passes_baseline_run_id",
                "ix_document_run_semantic_passes_ontology_snapshot_id",
                "ix_document_run_semantic_passes_status",
            }
        ),
        "semantic_assertions": frozenset(
            {
                "ix_semantic_assertions_semantic_pass_id",
                "ix_semantic_assertions_concept_id",
            }
        ),
        "semantic_assertion_category_bindings": frozenset(
            {
                "ix_semantic_assertion_category_bindings_assertion_id",
                "ix_semantic_assertion_category_bindings_category_id",
            }
        ),
        "semantic_assertion_evidence": frozenset(
            {
                "ix_semantic_assertion_evidence_assertion_id",
                "ix_semantic_assertion_evidence_run_id",
                "ix_semantic_assertion_evidence_source_type",
            }
        ),
        "semantic_entities": frozenset(
            {
                "ix_semantic_entities_document_id",
                "ix_semantic_entities_concept_id",
            }
        ),
        "semantic_facts": frozenset(
            {
                "ix_semantic_facts_document_id",
                "ix_semantic_facts_run_id",
                "ix_semantic_facts_semantic_pass_id",
                "ix_semantic_facts_relation_key",
                "ix_semantic_facts_subject_entity_id",
                "ix_semantic_facts_object_entity_id",
            }
        ),
        "semantic_fact_evidence": frozenset(
            {
                "ix_semantic_fact_evidence_fact_id",
                "ix_semantic_fact_evidence_assertion_id",
                "ix_semantic_fact_evidence_evidence_id",
            }
        ),
        "semantic_governance_events": frozenset(
            {
                "ix_semantic_governance_events_scope_created",
                "ix_semantic_governance_events_kind_created",
                "ix_semantic_governance_events_subject",
                "ix_semantic_governance_events_task_created",
                "ix_semantic_governance_events_ontology",
                "ix_semantic_governance_events_graph",
                "ix_semantic_governance_events_release",
                "ix_semantic_governance_events_manifest",
                "ix_semantic_governance_events_artifact",
                "ix_semantic_governance_events_receipt_sha",
                "ix_semantic_governance_events_payload_sha",
                "ix_semantic_governance_events_event_hash",
            }
        ),
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers": frozenset(
            {
                "ix_cs_waiver_ledgers_artifact",
                "ix_cs_waiver_ledgers_task",
                "ix_cs_waiver_ledgers_status",
                "ix_cs_waiver_ledgers_closure",
            }
        ),
        "claim_support_replay_alert_fixture_coverage_waiver_escalations": frozenset(
            {
                "ix_cs_waiver_escalations_ledger",
                "ix_cs_waiver_escalations_event",
                "ix_cs_waiver_escalations_covered",
                "ix_cs_waiver_escalations_impact",
            }
        ),
        "claim_support_fixture_sets": frozenset(
            {
                "ix_claim_support_fixture_sets_name_version",
                "ix_claim_support_fixture_sets_status",
                "ix_claim_support_fixture_sets_sha",
            }
        ),
        "claim_support_replay_alert_fixture_corpus_snapshots": frozenset(
            {
                "ix_cs_replay_fixture_corpus_snapshots_status_created",
                "ix_cs_replay_fixture_corpus_snapshots_sha",
                "ix_cs_replay_fixture_corpus_snapshots_governance_event",
                "ix_cs_replay_fixture_corpus_snapshots_governance_artifact",
            }
        ),
        "claim_support_replay_alert_fixture_corpus_rows": frozenset(
            {
                "ix_cs_replay_fixture_corpus_rows_snapshot",
                "ix_cs_replay_fixture_corpus_rows_case",
                "ix_cs_replay_fixture_corpus_rows_fixture_sha",
                "ix_cs_replay_fixture_corpus_rows_promotion",
            }
        ),
        "claim_support_calibration_policies": frozenset(
            {
                "ix_claim_support_calibration_policies_name_version",
                "uq_claim_support_calibration_policies_active_name",
                "ix_claim_support_calibration_policies_status",
                "ix_claim_support_calibration_policies_sha",
            }
        ),
        "claim_support_evaluations": frozenset(
            {
                "ix_claim_support_evaluations_agent_task_id",
                "ix_claim_support_evaluations_operator_run_id",
                "ix_claim_support_evaluations_created_at",
                "ix_claim_support_evaluations_gate_created",
                "ix_claim_support_evaluations_fixture_sha",
                "ix_claim_support_evaluations_fixture_set_id",
                "ix_claim_support_evaluations_policy_id",
                "ix_claim_support_evaluations_policy_sha",
            }
        ),
        "claim_support_evaluation_cases": frozenset(
            {
                "ix_claim_support_evaluation_cases_eval_id",
                "ix_claim_support_evaluation_cases_case_id",
                "ix_claim_support_evaluation_cases_expected",
                "ix_claim_support_evaluation_cases_predicted",
                "ix_claim_support_evaluation_cases_passed",
                "ix_claim_support_evaluation_cases_hard_kind",
            }
        ),
        "claim_support_policy_change_impacts": frozenset(
            {
                "ix_claim_support_policy_change_impacts_activation_task",
                "ix_claim_support_policy_change_impacts_policy",
                "ix_claim_support_policy_change_impacts_governance_event",
                "ix_claim_support_policy_change_impacts_governance_artifact",
                "ix_claim_support_policy_change_impacts_scope_created",
                "ix_claim_support_policy_change_impacts_payload_sha",
                "ix_claim_support_policy_change_impacts_replay_status",
            }
        ),
        "audit_bundle_exports": frozenset(
            {
                "ix_audit_bundle_exports_bundle_kind_created_at",
                "ix_audit_bundle_exports_source",
                "ix_audit_bundle_exports_release_created_at",
                "ix_audit_bundle_exports_training_run_created_at",
                "ix_audit_bundle_exports_payload_sha256",
                "ix_audit_bundle_exports_bundle_sha256",
            }
        ),
        "audit_bundle_validation_receipts": frozenset(
            {
                "ix_audit_bundle_validation_receipts_bundle_created",
                "ix_audit_bundle_validation_receipts_source",
                "ix_audit_bundle_validation_receipts_receipt_sha",
                "ix_audit_bundle_validation_receipts_prov_jsonld_sha",
                "ix_audit_bundle_validation_receipts_status_created",
            }
        ),
        "evidence_package_exports": frozenset(
            {
                "ix_evidence_package_exports_created_at",
                "ix_evidence_package_exports_search_request_id",
                "ix_evidence_package_exports_agent_task_id",
                "ix_evidence_package_exports_package_sha256",
                "ix_evidence_package_exports_trace_sha256",
            }
        ),
        "evidence_manifests": frozenset(
            {
                "ix_evidence_manifests_agent_task_id",
                "ix_evidence_manifests_draft_task_id",
                "ix_evidence_manifests_verification_task_id",
                "ix_evidence_manifests_export_id",
                "ix_evidence_manifests_manifest_sha256",
                "ix_evidence_manifests_trace_sha256",
                "ix_evidence_manifests_created_at",
            }
        ),
        "technical_report_release_readiness_db_gates": frozenset(
            {
                "ix_tr_readiness_db_gates_verification_task",
                "ix_tr_readiness_db_gates_source_verification",
                "ix_tr_readiness_db_gates_harness_task",
                "ix_tr_readiness_db_gates_manifest",
                "ix_tr_readiness_db_gates_prov_artifact",
                "ix_tr_readiness_db_gates_governance",
                "ix_tr_readiness_db_gates_payload_sha",
                "ix_tr_readiness_db_gates_created",
            }
        ),
        "technical_report_claim_retrieval_feedback": frozenset(
            {
                "ix_tr_claim_feedback_verification_task",
                "ix_tr_claim_feedback_claim",
                "ix_tr_claim_feedback_derivation",
                "ix_tr_claim_feedback_manifest",
                "ix_tr_claim_feedback_prov_artifact",
                "ix_tr_claim_feedback_release_gate",
                "ix_tr_claim_feedback_governance",
                "ix_tr_claim_feedback_source_request",
                "ix_tr_claim_feedback_search_result",
                "ix_tr_claim_feedback_status_label",
                "ix_tr_claim_feedback_payload_sha",
                "ix_tr_claim_feedback_created",
            }
        ),
        "evidence_trace_nodes": frozenset(
            {
                "ix_evidence_trace_nodes_manifest_id",
                "ix_evidence_trace_nodes_export_id",
                "ix_evidence_trace_nodes_node_kind",
                "ix_evidence_trace_nodes_source",
                "ix_evidence_trace_nodes_source_ref",
                "ix_evidence_trace_nodes_content_sha256",
            }
        ),
        "evidence_trace_edges": frozenset(
            {
                "ix_evidence_trace_edges_manifest_id",
                "ix_evidence_trace_edges_export_id",
                "ix_evidence_trace_edges_edge_kind",
                "ix_evidence_trace_edges_from_node_id",
                "ix_evidence_trace_edges_to_node_id",
                "ix_evidence_trace_edges_derivation_sha256",
                "ix_evidence_trace_edges_content_sha256",
            }
        ),
        "claim_evidence_derivations": frozenset(
            {
                "ix_claim_evidence_derivations_export_id",
                "ix_claim_evidence_derivations_agent_task_id",
                "ix_claim_evidence_derivations_claim_id",
                "ix_claim_evidence_derivations_derivation_sha256",
                "ix_claim_evidence_derivations_support_verdict",
                "ix_claim_evidence_derivations_support_judge_run_id",
                "ix_claim_evidence_derivations_provenance_lock_sha",
            }
        ),
    }
)

REQUIRED_TABLE_INDEX_COLUMNS = {
    "api_idempotency_keys": {
        "ix_api_idempotency_keys_created_at": ("created_at",),
    },
    "document_chunks": {
        "ix_document_chunks_document_id": ("document_id",),
        "ix_document_chunks_embedding_hnsw": ("embedding",),
        "ix_document_chunks_page_from": ("page_from",),
        "ix_document_chunks_page_to": ("page_to",),
        "ix_document_chunks_textsearch": ("textsearch",),
    },
    "document_figures": {
        "ix_document_figures_document_id": ("document_id",),
        "ix_document_figures_page_from": ("page_from",),
        "ix_document_figures_page_to": ("page_to",),
        "ix_document_figures_run_id": ("run_id",),
    },
    "document_run_evaluation_queries": {
        "ix_document_run_evaluation_queries_evaluation_id": ("evaluation_id",),
        "ix_document_run_evaluation_queries_query_text": ("query_text",),
    },
    "document_run_evaluations": {
        "ix_document_run_evaluations_run_id": ("run_id",),
        "ix_document_run_evaluations_status": ("status",),
    },
    "document_table_segments": {
        "ix_document_table_segments_page_from": ("page_from",),
        "ix_document_table_segments_page_to": ("page_to",),
        "ix_document_table_segments_run_id": ("run_id",),
    },
    "document_tables": {
        "ix_document_tables_document_id": ("document_id",),
        "ix_document_tables_embedding_hnsw": ("embedding",),
        "ix_document_tables_page_from": ("page_from",),
        "ix_document_tables_page_to": ("page_to",),
        "ix_document_tables_textsearch": ("textsearch",),
    },
    "documents": {
        "ix_documents_metadata_textsearch": ("metadata_textsearch",),
        "ix_documents_updated_at": ("updated_at",),
    },
    "ingest_batches": {
        "ix_ingest_batches_created_at": ("created_at",),
        "ix_ingest_batches_status_created_at": ("status", "created_at"),
    },
    "ingest_batch_items": {
        "ix_ingest_batch_items_batch_id": ("batch_id",),
        "ix_ingest_batch_items_document_id": ("document_id",),
        "ix_ingest_batch_items_run_id": ("run_id",),
        "ix_ingest_batch_items_status": ("status",),
    },
    "document_runs": {
        "ix_document_runs_locked_at": ("locked_at",),
        "ix_document_runs_status_completed_at": ("status", "completed_at"),
        "ix_document_runs_status_next_attempt_at": ("status", "next_attempt_at"),
    }
}

REQUIRED_TABLE_INDEX_COLUMNS.update(
    {
        "agent_tasks": {
            "ix_agent_tasks_status_priority_next_attempt_at": (
                "status",
                "priority",
                "next_attempt_at",
            ),
            "ix_agent_tasks_locked_at": ("locked_at",),
            "ix_agent_tasks_parent_task_id": ("parent_task_id",),
            "ix_agent_tasks_task_type_created_at": ("task_type", "created_at"),
        },
        "agent_task_dependencies": {
            "ix_agent_task_dependencies_depends_on_task_id": ("depends_on_task_id",),
        },
        "agent_task_attempts": {
            "ix_agent_task_attempts_task_id": ("task_id",),
            "ix_agent_task_attempts_created_at": ("created_at",),
        },
        "agent_task_artifacts": {
            "ix_agent_task_artifacts_task_id": ("task_id",),
            "ix_agent_task_artifacts_attempt_id": ("attempt_id",),
            "ix_agent_task_artifacts_artifact_kind": ("artifact_kind",),
        },
        "agent_task_artifact_immutability_events": {
            "ix_agent_artifact_immut_events_artifact_created": ("artifact_id", "created_at"),
            "ix_agent_artifact_immut_events_task_created": ("task_id", "created_at"),
            "ix_agent_artifact_immut_events_kind": ("event_kind",),
        },
        "agent_task_outcomes": {
            "ix_agent_task_outcomes_task_id": ("task_id",),
            "ix_agent_task_outcomes_outcome_label": ("outcome_label",),
            "ix_agent_task_outcomes_created_at": ("created_at",),
        },
        "agent_task_verifications": {
            "ix_agent_task_verifications_target_task_id": ("target_task_id",),
            "ix_agent_task_verifications_verification_task_id": ("verification_task_id",),
            "ix_agent_task_verifications_verifier_type": ("verifier_type",),
            "ix_agent_task_verifications_created_at": ("created_at",),
        },
        "knowledge_operator_runs": {
            "ix_knowledge_operator_runs_created_at": ("created_at",),
            "ix_knowledge_operator_runs_search_request_id": ("search_request_id",),
            "ix_knowledge_operator_runs_agent_task_id": ("agent_task_id",),
            "ix_knowledge_operator_runs_parent_id": ("parent_operator_run_id",),
            "ix_knowledge_operator_runs_kind_created_at": ("operator_kind", "created_at"),
        },
        "knowledge_operator_inputs": {
            "ix_knowledge_operator_inputs_operator_run_id": ("operator_run_id",),
            "ix_knowledge_operator_inputs_source": ("source_table", "source_id"),
        },
        "knowledge_operator_outputs": {
            "ix_knowledge_operator_outputs_operator_run_id": ("operator_run_id",),
            "ix_knowledge_operator_outputs_target": ("target_table", "target_id"),
        },
        "search_requests": {
            "ix_search_requests_created_at": ("created_at",),
            "ix_search_requests_origin_created_at": ("origin", "created_at"),
            "ix_search_requests_evaluation_id": ("evaluation_id",),
            "ix_search_requests_parent_request_id": ("parent_request_id",),
        },
        "search_request_results": {
            "ix_search_request_results_search_request_id": ("search_request_id",),
            "ix_search_request_results_result_type": ("result_type",),
        },
        "retrieval_evidence_spans": {
            "ix_retrieval_evidence_spans_document_id": ("document_id",),
            "ix_retrieval_evidence_spans_run_id": ("run_id",),
            "ix_retrieval_evidence_spans_source": ("source_type", "source_id"),
            "ix_retrieval_evidence_spans_chunk_id": ("chunk_id",),
            "ix_retrieval_evidence_spans_table_id": ("table_id",),
            "ix_retrieval_evidence_spans_page_from": ("page_from",),
            "ix_retrieval_evidence_spans_page_to": ("page_to",),
            "ix_retrieval_evidence_spans_content_sha256": ("content_sha256",),
            "ix_retrieval_evidence_spans_textsearch": ("textsearch",),
            "ix_retrieval_evidence_spans_embedding_hnsw": ("embedding",),
        },
        "retrieval_evidence_span_multivectors": {
            "ix_retrieval_span_multivectors_span_id": ("retrieval_evidence_span_id",),
            "ix_retrieval_span_multivectors_document_id": ("document_id",),
            "ix_retrieval_span_multivectors_run_id": ("run_id",),
            "ix_retrieval_span_multivectors_source": ("source_type", "source_id"),
            "ix_retrieval_span_multivectors_model": ("embedding_model",),
            "ix_retrieval_span_multivectors_content_sha256": ("content_sha256",),
            "ix_retrieval_span_multivectors_embedding_sha256": ("embedding_sha256",),
            "ix_retrieval_span_multivectors_embedding_hnsw": ("embedding",),
        },
        "search_request_result_spans": {
            "ix_search_request_result_spans_request_id": ("search_request_id",),
            "ix_search_request_result_spans_result_id": ("search_request_result_id",),
            "ix_search_request_result_spans_span_id": ("retrieval_evidence_span_id",),
            "ix_search_request_result_spans_source": ("source_type", "source_id"),
            "ix_search_request_result_spans_content_sha256": ("content_sha256",),
        },
        "search_feedback": {
            "ix_search_feedback_search_request_id": ("search_request_id",),
            "ix_search_feedback_search_request_result_id": ("search_request_result_id",),
            "ix_search_feedback_feedback_type": ("feedback_type",),
            "ix_search_feedback_created_at": ("created_at",),
        },
        "chat_answer_records": {
            "ix_chat_answer_records_search_request_id": ("search_request_id",),
            "ix_chat_answer_records_created_at": ("created_at",),
        },
        "chat_answer_feedback": {
            "ix_chat_answer_feedback_answer_id": ("chat_answer_id",),
            "ix_chat_answer_feedback_feedback_type": ("feedback_type",),
            "ix_chat_answer_feedback_created_at": ("created_at",),
        },
        "search_replay_runs": {
            "ix_search_replay_runs_created_at": ("created_at",),
            "ix_search_replay_runs_source_type_created_at": ("source_type", "created_at"),
        },
        "search_replay_queries": {
            "ix_search_replay_queries_replay_run_id": ("replay_run_id",),
            "ix_search_replay_queries_source_search_request_id": ("source_search_request_id",),
            "ix_search_replay_queries_replay_search_request_id": ("replay_search_request_id",),
            "ix_search_replay_queries_feedback_id": ("feedback_id",),
            "ix_search_replay_queries_evaluation_query_id": ("evaluation_query_id",),
            "ix_search_replay_queries_created_at": ("created_at",),
        },
        "search_harness_evaluations": {
            "ix_search_harness_evaluations_baseline_candidate": (
                "baseline_harness_name",
                "candidate_harness_name",
            ),
            "ix_search_harness_evaluations_candidate_created_at": (
                "candidate_harness_name",
                "created_at",
            ),
            "ix_search_harness_evaluations_created_at": ("created_at",),
        },
        "search_harness_evaluation_sources": {
            "ix_search_harness_evaluation_sources_eval_id": ("search_harness_evaluation_id",),
            "ix_search_harness_evaluation_sources_baseline_replay": ("baseline_replay_run_id",),
            "ix_search_harness_evaluation_sources_candidate_replay": (
                "candidate_replay_run_id",
            ),
        },
        "search_harness_releases": {
            "ix_search_harness_releases_evaluation_id": ("search_harness_evaluation_id",),
            "ix_search_harness_releases_candidate_created_at": (
                "candidate_harness_name",
                "created_at",
            ),
            "ix_search_harness_releases_outcome_created_at": ("outcome", "created_at"),
            "ix_search_harness_releases_created_at": ("created_at",),
        },
        "search_harness_release_readiness_assessments": {
            "ix_shr_readiness_assessments_release_created": (
                "search_harness_release_id",
                "created_at",
            ),
            "ix_shr_readiness_assessments_bundle_created": (
                "release_audit_bundle_id",
                "created_at",
            ),
            "ix_shr_readiness_assessments_receipt_created": (
                "release_validation_receipt_id",
                "created_at",
            ),
            "ix_shr_readiness_assessments_governance": ("semantic_governance_event_id",),
            "ix_shr_readiness_assessments_status_created": ("readiness_status", "created_at"),
            "ix_shr_readiness_assessments_readiness_sha": ("readiness_payload_sha256",),
            "ix_shr_readiness_assessments_payload_sha": ("assessment_payload_sha256",),
        },
        "retrieval_judgment_sets": {
            "ix_retrieval_judgment_sets_created_at": ("created_at",),
            "ix_retrieval_judgment_sets_set_kind_created": ("set_kind", "created_at"),
            "ix_retrieval_judgment_sets_payload_sha": ("payload_sha256",),
        },
        "retrieval_judgments": {
            "ix_retrieval_judgments_set_kind": ("judgment_set_id", "judgment_kind"),
            "ix_retrieval_judgments_source": ("source_type", "source_ref_id"),
            "ix_retrieval_judgments_search_request": ("search_request_id",),
            "ix_retrieval_judgments_source_request": ("source_search_request_id",),
            "ix_retrieval_judgments_search_result": ("search_request_result_id",),
            "ix_retrieval_judgments_feedback": ("search_feedback_id",),
            "ix_retrieval_judgments_replay_query": ("search_replay_query_id",),
            "ix_retrieval_judgments_result": ("result_type", "result_id"),
            "ix_retrieval_judgments_source_payload_sha": ("source_payload_sha256",),
            "ix_retrieval_judgments_created_at": ("created_at",),
        },
        "retrieval_hard_negatives": {
            "ix_retrieval_hard_negatives_set_kind": ("judgment_set_id", "hard_negative_kind"),
            "ix_retrieval_hard_negatives_judgment": ("judgment_id",),
            "ix_retrieval_hard_negatives_positive_judgment": ("positive_judgment_id",),
            "ix_retrieval_hard_negatives_source": ("source_type", "source_ref_id"),
            "ix_retrieval_hard_negatives_feedback": ("search_feedback_id",),
            "ix_retrieval_hard_negatives_replay_query": ("search_replay_query_id",),
            "ix_retrieval_hard_negatives_source_request": ("source_search_request_id",),
            "ix_retrieval_hard_negatives_request": ("search_request_id",),
            "ix_retrieval_hard_negatives_search_result": ("search_request_result_id",),
            "ix_retrieval_hard_negatives_result": ("result_type", "result_id"),
            "ix_retrieval_hard_negatives_source_payload_sha": ("source_payload_sha256",),
            "ix_retrieval_hard_negatives_created_at": ("created_at",),
        },
        "retrieval_training_runs": {
            "ix_retrieval_training_runs_judgment_set": ("judgment_set_id",),
            "ix_retrieval_training_runs_release": ("search_harness_release_id",),
            "ix_retrieval_training_runs_governance": ("semantic_governance_event_id",),
            "ix_retrieval_training_runs_dataset_sha": ("training_dataset_sha256",),
            "ix_retrieval_training_runs_created_at": ("created_at",),
        },
        "retrieval_learning_candidate_evaluations": {
            "ix_retrieval_learning_candidate_training": (
                "retrieval_training_run_id",
                "created_at",
            ),
            "ix_retrieval_learning_candidate_judgment_set": ("judgment_set_id", "created_at"),
            "ix_retrieval_learning_candidate_evaluation": ("search_harness_evaluation_id",),
            "ix_retrieval_learning_candidate_release": ("search_harness_release_id",),
            "ix_retrieval_learning_candidate_governance": ("semantic_governance_event_id",),
            "ix_retrieval_learning_candidate_dataset_sha": ("training_dataset_sha256",),
            "ix_retrieval_learning_candidate_harness_created": (
                "candidate_harness_name",
                "created_at",
            ),
            "ix_retrieval_learning_candidate_outcome_created": ("gate_outcome", "created_at"),
            "ix_retrieval_learning_candidate_package_sha": ("learning_package_sha256",),
            "ix_retrieval_learning_candidate_created_at": ("created_at",),
        },
        "retrieval_reranker_artifacts": {
            "ix_retrieval_reranker_artifacts_training_created": (
                "retrieval_training_run_id",
                "created_at",
            ),
            "ix_retrieval_reranker_artifacts_candidate_eval": (
                "retrieval_learning_candidate_evaluation_id",
            ),
            "ix_retrieval_reranker_artifacts_evaluation": ("search_harness_evaluation_id",),
            "ix_retrieval_reranker_artifacts_release": ("search_harness_release_id",),
            "ix_retrieval_reranker_artifacts_governance": ("semantic_governance_event_id",),
            "ix_retrieval_reranker_artifacts_candidate_created": (
                "candidate_harness_name",
                "created_at",
            ),
            "ix_retrieval_reranker_artifacts_gate_created": ("gate_outcome", "created_at"),
            "ix_retrieval_reranker_artifacts_artifact_sha": ("artifact_sha256",),
            "ix_retrieval_reranker_artifacts_impact_sha": ("change_impact_sha256",),
        },
        "eval_observations": {
            "ix_eval_observations_surface_last_seen": ("surface", "last_seen_at"),
            "ix_eval_observations_status_last_seen": ("status", "last_seen_at"),
            "ix_eval_observations_document_id": ("document_id",),
            "ix_eval_observations_search_request_id": ("search_request_id",),
            "ix_eval_observations_evaluation_id": ("evaluation_id",),
        },
        "eval_failure_cases": {
            "ix_eval_failure_cases_status_updated": ("status", "updated_at"),
            "ix_eval_failure_cases_surface_status": ("surface", "status"),
            "ix_eval_failure_cases_document_id": ("document_id",),
            "ix_eval_failure_cases_search_request_id": ("search_request_id",),
            "ix_eval_failure_cases_evaluation_id": ("evaluation_id",),
        },
        "semantic_ontology_snapshots": {
            "ix_semantic_ontology_snapshots_created_at": ("created_at",),
            "ix_semantic_ontology_snapshots_upper_ontology_version": (
                "upper_ontology_version",
            ),
        },
        "semantic_graph_snapshots": {
            "ix_semantic_graph_snapshots_created_at": ("created_at",),
            "ix_semantic_graph_snapshots_ontology_snapshot_id": ("ontology_snapshot_id",),
        },
        "semantic_concepts": {
            "ix_semantic_concepts_concept_key": ("concept_key",),
            "ix_semantic_concepts_registry_version": ("registry_version",),
        },
        "semantic_categories": {
            "ix_semantic_categories_category_key": ("category_key",),
            "ix_semantic_categories_registry_version": ("registry_version",),
        },
        "semantic_terms": {
            "ix_semantic_terms_registry_version": ("registry_version",),
            "ix_semantic_terms_normalized_text": ("normalized_text",),
        },
        "semantic_concept_terms": {
            "ix_semantic_concept_terms_concept_id": ("concept_id",),
            "ix_semantic_concept_terms_term_id": ("term_id",),
        },
        "semantic_concept_category_bindings": {
            "ix_semantic_concept_category_bindings_concept_id": ("concept_id",),
            "ix_semantic_concept_category_bindings_category_id": ("category_id",),
        },
        "document_semantic_concept_reviews": {
            "ix_document_semantic_concept_reviews_document_id": ("document_id",),
            "ix_document_semantic_concept_reviews_concept_id": ("concept_id",),
            "ix_doc_sem_concept_reviews_doc_concept_created_at": (
                "document_id",
                "concept_id",
                "created_at",
            ),
        },
        "document_semantic_category_reviews": {
            "ix_document_semantic_category_reviews_document_id": ("document_id",),
            "ix_document_semantic_category_reviews_concept_id": ("concept_id",),
            "ix_document_semantic_category_reviews_category_id": ("category_id",),
            "ix_doc_sem_category_reviews_doc_binding_created_at": (
                "document_id",
                "concept_id",
                "category_id",
                "created_at",
            ),
        },
        "document_run_semantic_passes": {
            "ix_document_run_semantic_passes_document_id": ("document_id",),
            "ix_document_run_semantic_passes_run_id": ("run_id",),
            "ix_document_run_semantic_passes_baseline_run_id": ("baseline_run_id",),
            "ix_document_run_semantic_passes_ontology_snapshot_id": (
                "ontology_snapshot_id",
            ),
            "ix_document_run_semantic_passes_status": ("status",),
        },
        "semantic_assertions": {
            "ix_semantic_assertions_semantic_pass_id": ("semantic_pass_id",),
            "ix_semantic_assertions_concept_id": ("concept_id",),
        },
        "semantic_assertion_category_bindings": {
            "ix_semantic_assertion_category_bindings_assertion_id": ("assertion_id",),
            "ix_semantic_assertion_category_bindings_category_id": ("category_id",),
        },
        "semantic_assertion_evidence": {
            "ix_semantic_assertion_evidence_assertion_id": ("assertion_id",),
            "ix_semantic_assertion_evidence_run_id": ("run_id",),
            "ix_semantic_assertion_evidence_source_type": ("source_type",),
        },
        "semantic_entities": {
            "ix_semantic_entities_document_id": ("document_id",),
            "ix_semantic_entities_concept_id": ("concept_id",),
        },
        "semantic_facts": {
            "ix_semantic_facts_document_id": ("document_id",),
            "ix_semantic_facts_run_id": ("run_id",),
            "ix_semantic_facts_semantic_pass_id": ("semantic_pass_id",),
            "ix_semantic_facts_relation_key": ("relation_key",),
            "ix_semantic_facts_subject_entity_id": ("subject_entity_id",),
            "ix_semantic_facts_object_entity_id": ("object_entity_id",),
        },
        "semantic_fact_evidence": {
            "ix_semantic_fact_evidence_fact_id": ("fact_id",),
            "ix_semantic_fact_evidence_assertion_id": ("assertion_id",),
            "ix_semantic_fact_evidence_evidence_id": ("assertion_evidence_id",),
        },
        "semantic_governance_events": {
            "ix_semantic_governance_events_scope_created": ("governance_scope", "created_at"),
            "ix_semantic_governance_events_kind_created": ("event_kind", "created_at"),
            "ix_semantic_governance_events_subject": ("subject_table", "subject_id"),
            "ix_semantic_governance_events_task_created": ("task_id", "created_at"),
            "ix_semantic_governance_events_ontology": (
                "ontology_snapshot_id",
                "created_at",
            ),
            "ix_semantic_governance_events_graph": (
                "semantic_graph_snapshot_id",
                "created_at",
            ),
            "ix_semantic_governance_events_release": (
                "search_harness_release_id",
                "created_at",
            ),
            "ix_semantic_governance_events_manifest": (
                "evidence_manifest_id",
                "created_at",
            ),
            "ix_semantic_governance_events_artifact": (
                "agent_task_artifact_id",
                "created_at",
            ),
            "ix_semantic_governance_events_receipt_sha": ("receipt_sha256",),
            "ix_semantic_governance_events_payload_sha": ("payload_sha256",),
            "ix_semantic_governance_events_event_hash": ("event_hash",),
        },
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers": {
            "ix_cs_waiver_ledgers_artifact": ("waiver_artifact_id",),
            "ix_cs_waiver_ledgers_task": ("verification_task_id",),
            "ix_cs_waiver_ledgers_status": ("coverage_status", "created_at"),
            "ix_cs_waiver_ledgers_closure": ("closure_event_id",),
        },
        "claim_support_replay_alert_fixture_coverage_waiver_escalations": {
            "ix_cs_waiver_escalations_ledger": ("ledger_id",),
            "ix_cs_waiver_escalations_event": ("escalation_event_id",),
            "ix_cs_waiver_escalations_covered": ("ledger_id", "covered"),
            "ix_cs_waiver_escalations_impact": ("change_impact_id",),
        },
        "claim_support_fixture_sets": {
            "ix_claim_support_fixture_sets_name_version": (
                "fixture_set_name",
                "fixture_set_version",
            ),
            "ix_claim_support_fixture_sets_status": ("status",),
            "ix_claim_support_fixture_sets_sha": ("fixture_set_sha256",),
        },
        "claim_support_replay_alert_fixture_corpus_snapshots": {
            "ix_cs_replay_fixture_corpus_snapshots_status_created": ("status", "created_at"),
            "ix_cs_replay_fixture_corpus_snapshots_sha": ("snapshot_sha256",),
            "ix_cs_replay_fixture_corpus_snapshots_governance_event": (
                "semantic_governance_event_id",
            ),
            "ix_cs_replay_fixture_corpus_snapshots_governance_artifact": (
                "governance_artifact_id",
            ),
        },
        "claim_support_replay_alert_fixture_corpus_rows": {
            "ix_cs_replay_fixture_corpus_rows_snapshot": ("snapshot_id",),
            "ix_cs_replay_fixture_corpus_rows_case": ("case_id",),
            "ix_cs_replay_fixture_corpus_rows_fixture_sha": ("fixture_sha256",),
            "ix_cs_replay_fixture_corpus_rows_promotion": ("promotion_event_id",),
        },
        "claim_support_calibration_policies": {
            "ix_claim_support_calibration_policies_name_version": (
                "policy_name",
                "policy_version",
            ),
            "uq_claim_support_calibration_policies_active_name": ("policy_name",),
            "ix_claim_support_calibration_policies_status": ("status",),
            "ix_claim_support_calibration_policies_sha": ("policy_sha256",),
        },
        "claim_support_evaluations": {
            "ix_claim_support_evaluations_agent_task_id": ("agent_task_id",),
            "ix_claim_support_evaluations_operator_run_id": ("operator_run_id",),
            "ix_claim_support_evaluations_created_at": ("created_at",),
            "ix_claim_support_evaluations_gate_created": ("gate_outcome", "created_at"),
            "ix_claim_support_evaluations_fixture_sha": ("fixture_set_sha256",),
            "ix_claim_support_evaluations_fixture_set_id": ("fixture_set_id",),
            "ix_claim_support_evaluations_policy_id": ("policy_id",),
            "ix_claim_support_evaluations_policy_sha": ("policy_sha256",),
        },
        "claim_support_evaluation_cases": {
            "ix_claim_support_evaluation_cases_eval_id": ("evaluation_id",),
            "ix_claim_support_evaluation_cases_case_id": ("case_id",),
            "ix_claim_support_evaluation_cases_expected": ("expected_verdict",),
            "ix_claim_support_evaluation_cases_predicted": ("predicted_verdict",),
            "ix_claim_support_evaluation_cases_passed": ("passed",),
            "ix_claim_support_evaluation_cases_hard_kind": ("hard_case_kind",),
        },
        "claim_support_policy_change_impacts": {
            "ix_claim_support_policy_change_impacts_activation_task": (
                "activation_task_id",
                "created_at",
            ),
            "ix_claim_support_policy_change_impacts_policy": (
                "activated_policy_id",
                "created_at",
            ),
            "ix_claim_support_policy_change_impacts_governance_event": (
                "semantic_governance_event_id",
            ),
            "ix_claim_support_policy_change_impacts_governance_artifact": (
                "governance_artifact_id",
            ),
            "ix_claim_support_policy_change_impacts_scope_created": (
                "impact_scope",
                "created_at",
            ),
            "ix_claim_support_policy_change_impacts_payload_sha": ("impact_payload_sha256",),
            "ix_claim_support_policy_change_impacts_replay_status": (
                "replay_status",
                "created_at",
            ),
        },
        "audit_bundle_exports": {
            "ix_audit_bundle_exports_bundle_kind_created_at": ("bundle_kind", "created_at"),
            "ix_audit_bundle_exports_source": ("source_table", "source_id"),
            "ix_audit_bundle_exports_release_created_at": (
                "search_harness_release_id",
                "created_at",
            ),
            "ix_audit_bundle_exports_training_run_created_at": (
                "retrieval_training_run_id",
                "created_at",
            ),
            "ix_audit_bundle_exports_payload_sha256": ("payload_sha256",),
            "ix_audit_bundle_exports_bundle_sha256": ("bundle_sha256",),
        },
        "audit_bundle_validation_receipts": {
            "ix_audit_bundle_validation_receipts_bundle_created": (
                "audit_bundle_export_id",
                "created_at",
            ),
            "ix_audit_bundle_validation_receipts_source": (
                "source_table",
                "source_id",
                "created_at",
            ),
            "ix_audit_bundle_validation_receipts_receipt_sha": ("receipt_sha256",),
            "ix_audit_bundle_validation_receipts_prov_jsonld_sha": ("prov_jsonld_sha256",),
            "ix_audit_bundle_validation_receipts_status_created": (
                "validation_status",
                "created_at",
            ),
        },
        "evidence_package_exports": {
            "ix_evidence_package_exports_created_at": ("created_at",),
            "ix_evidence_package_exports_search_request_id": ("search_request_id",),
            "ix_evidence_package_exports_agent_task_id": ("agent_task_id",),
            "ix_evidence_package_exports_package_sha256": ("package_sha256",),
            "ix_evidence_package_exports_trace_sha256": ("trace_sha256",),
        },
        "evidence_manifests": {
            "ix_evidence_manifests_agent_task_id": ("agent_task_id",),
            "ix_evidence_manifests_draft_task_id": ("draft_task_id",),
            "ix_evidence_manifests_verification_task_id": ("verification_task_id",),
            "ix_evidence_manifests_export_id": ("evidence_package_export_id",),
            "ix_evidence_manifests_manifest_sha256": ("manifest_sha256",),
            "ix_evidence_manifests_trace_sha256": ("trace_sha256",),
            "ix_evidence_manifests_created_at": ("created_at",),
        },
        "technical_report_release_readiness_db_gates": {
            "ix_tr_readiness_db_gates_verification_task": (
                "technical_report_verification_task_id",
            ),
            "ix_tr_readiness_db_gates_source_verification": ("source_verification_id",),
            "ix_tr_readiness_db_gates_harness_task": ("harness_task_id",),
            "ix_tr_readiness_db_gates_manifest": ("evidence_manifest_id",),
            "ix_tr_readiness_db_gates_prov_artifact": ("prov_export_artifact_id",),
            "ix_tr_readiness_db_gates_governance": ("semantic_governance_event_id",),
            "ix_tr_readiness_db_gates_payload_sha": ("gate_payload_sha256",),
            "ix_tr_readiness_db_gates_created": ("created_at",),
        },
        "technical_report_claim_retrieval_feedback": {
            "ix_tr_claim_feedback_verification_task": (
                "technical_report_verification_task_id",
            ),
            "ix_tr_claim_feedback_claim": ("claim_id",),
            "ix_tr_claim_feedback_derivation": ("claim_evidence_derivation_id",),
            "ix_tr_claim_feedback_manifest": ("evidence_manifest_id",),
            "ix_tr_claim_feedback_prov_artifact": ("prov_export_artifact_id",),
            "ix_tr_claim_feedback_release_gate": ("release_readiness_db_gate_id",),
            "ix_tr_claim_feedback_governance": ("semantic_governance_event_id",),
            "ix_tr_claim_feedback_source_request": ("source_search_request_id",),
            "ix_tr_claim_feedback_search_result": ("search_request_result_id",),
            "ix_tr_claim_feedback_status_label": ("feedback_status", "learning_label"),
            "ix_tr_claim_feedback_payload_sha": ("feedback_payload_sha256",),
            "ix_tr_claim_feedback_created": ("created_at",),
        },
        "evidence_trace_nodes": {
            "ix_evidence_trace_nodes_manifest_id": ("evidence_manifest_id",),
            "ix_evidence_trace_nodes_export_id": ("evidence_package_export_id",),
            "ix_evidence_trace_nodes_node_kind": ("node_kind",),
            "ix_evidence_trace_nodes_source": ("source_table", "source_id"),
            "ix_evidence_trace_nodes_source_ref": ("source_table", "source_ref"),
            "ix_evidence_trace_nodes_content_sha256": ("content_sha256",),
        },
        "evidence_trace_edges": {
            "ix_evidence_trace_edges_manifest_id": ("evidence_manifest_id",),
            "ix_evidence_trace_edges_export_id": ("evidence_package_export_id",),
            "ix_evidence_trace_edges_edge_kind": ("edge_kind",),
            "ix_evidence_trace_edges_from_node_id": ("from_node_id",),
            "ix_evidence_trace_edges_to_node_id": ("to_node_id",),
            "ix_evidence_trace_edges_derivation_sha256": ("derivation_sha256",),
            "ix_evidence_trace_edges_content_sha256": ("content_sha256",),
        },
        "claim_evidence_derivations": {
            "ix_claim_evidence_derivations_export_id": ("evidence_package_export_id",),
            "ix_claim_evidence_derivations_agent_task_id": ("agent_task_id",),
            "ix_claim_evidence_derivations_claim_id": ("claim_id",),
            "ix_claim_evidence_derivations_derivation_sha256": ("derivation_sha256",),
            "ix_claim_evidence_derivations_support_verdict": ("support_verdict",),
            "ix_claim_evidence_derivations_support_judge_run_id": ("support_judge_run_id",),
            "ix_claim_evidence_derivations_provenance_lock_sha": ("provenance_lock_sha256",),
        },
    }
)

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "api_idempotency_keys": frozenset(
        {
            "uq_api_idempotency_keys_scope_key",
        }
    ),
    "document_chunks": frozenset(
        {
            "uq_document_chunks_run_chunk_index",
        }
    ),
    "document_figures": frozenset(
        {
            "uq_document_figures_run_figure_index",
        }
    ),
    "document_run_evaluations": frozenset(
        {
            "uq_document_run_evaluations_run_corpus_version",
        }
    ),
    "document_table_segments": frozenset(
        {
            "uq_document_table_segments_table_segment_index",
        }
    ),
    "document_tables": frozenset(
        {
            "uq_document_tables_run_table_index",
        }
    ),
    "ingest_batch_items": frozenset(
        {
            "uq_ingest_batch_items_batch_relative_path",
        }
    ),
    "document_runs": frozenset(
        {
            "uq_document_runs_doc_run_number",
        }
    )
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES.update(
    {
        "agent_task_dependencies": frozenset(
            {
                "uq_agent_task_dependencies_task_depends_on",
            }
        ),
        "agent_task_attempts": frozenset(
            {
                "uq_agent_task_attempts_task_attempt",
            }
        ),
        "agent_task_outcomes": frozenset(
            {
                "uq_agent_task_outcomes_task_label_actor",
            }
        ),
        "search_request_results": frozenset(
            {
                "uq_search_request_results_request_rank",
            }
        ),
        "retrieval_evidence_spans": frozenset(
            {
                "uq_retrieval_evidence_spans_run_source_span",
            }
        ),
        "retrieval_evidence_span_multivectors": frozenset(
            {
                "uq_retrieval_span_multivectors_span_vector",
            }
        ),
        "search_request_result_spans": frozenset(
            {
                "uq_search_request_result_spans_result_rank",
            }
        ),
        "search_harness_evaluation_sources": frozenset(
            {
                "uq_search_harness_evaluation_sources_eval_source",
            }
        ),
        "retrieval_judgment_sets": frozenset(
            {
                "uq_retrieval_judgment_sets_set_name",
            }
        ),
        "retrieval_judgments": frozenset(
            {
                "uq_retrieval_judgments_dedup_key",
            }
        ),
        "retrieval_hard_negatives": frozenset(
            {
                "uq_retrieval_hard_negatives_dedup_key",
            }
        ),
        "retrieval_learning_candidate_evaluations": frozenset(
            {
                "uq_retrieval_learning_candidate_training_eval",
            }
        ),
        "retrieval_reranker_artifacts": frozenset(
            {
                "uq_retrieval_reranker_artifacts_candidate_eval",
            }
        ),
        "eval_observations": frozenset(
            {
                "uq_eval_observations_observation_key",
            }
        ),
        "eval_failure_cases": frozenset(
            {
                "uq_eval_failure_cases_case_key",
            }
        ),
        "semantic_ontology_snapshots": frozenset(
            {
                "uq_semantic_ontology_snapshots_ontology_version",
            }
        ),
        "semantic_graph_snapshots": frozenset(
            {
                "uq_semantic_graph_snapshots_graph_version",
            }
        ),
        "semantic_concepts": frozenset(
            {
                "uq_semantic_concepts_key_registry_version",
            }
        ),
        "semantic_categories": frozenset(
            {
                "uq_semantic_categories_key_registry_version",
            }
        ),
        "semantic_terms": frozenset(
            {
                "uq_semantic_terms_registry_version_normalized_text",
            }
        ),
        "semantic_concept_terms": frozenset(
            {
                "uq_semantic_concept_terms_concept_term",
            }
        ),
        "semantic_concept_category_bindings": frozenset(
            {
                "uq_semantic_concept_category_bindings_concept_category",
            }
        ),
        "document_run_semantic_passes": frozenset(
            {
                "uq_document_run_semantic_passes_run_version_tuple",
            }
        ),
        "semantic_assertions": frozenset(
            {
                "uq_semantic_assertions_pass_concept_kind",
            }
        ),
        "semantic_assertion_category_bindings": frozenset(
            {
                "uq_semantic_assertion_category_bindings_assertion_category",
            }
        ),
        "semantic_assertion_evidence": frozenset(
            {
                "uq_semantic_assertion_evidence_assertion_source",
            }
        ),
        "semantic_entities": frozenset(
            {
                "uq_semantic_entities_entity_key",
            }
        ),
        "semantic_governance_events": frozenset(
            {
                "uq_semantic_governance_events_dedup_key",
                "uq_semantic_governance_events_sequence",
            }
        ),
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers": frozenset(
            {
                "uq_cs_waiver_ledgers_artifact_sha",
            }
        ),
        "claim_support_replay_alert_fixture_coverage_waiver_escalations": frozenset(
            {
                "uq_cs_waiver_escalations_ledger_event",
            }
        ),
        "claim_support_fixture_sets": frozenset(
            {
                "uq_claim_support_fixture_sets_identity",
            }
        ),
        "claim_support_replay_alert_fixture_corpus_snapshots": frozenset(
            {
                "uq_cs_replay_fixture_corpus_snapshots_sha",
            }
        ),
        "claim_support_replay_alert_fixture_corpus_rows": frozenset(
            {
                "uq_cs_replay_fixture_corpus_rows_snapshot_identity",
                "uq_cs_replay_fixture_corpus_rows_snapshot_index",
            }
        ),
        "claim_support_calibration_policies": frozenset(
            {
                "uq_claim_support_calibration_policies_identity",
            }
        ),
        "claim_support_evaluation_cases": frozenset(
            {
                "uq_claim_support_evaluation_cases_eval_case",
            }
        ),
        "evidence_manifests": frozenset(
            {
                "uq_evidence_manifests_verification_task_kind",
            }
        ),
        "technical_report_release_readiness_db_gates": frozenset(
            {
                "uq_tr_readiness_db_gates_verification_task",
            }
        ),
        "technical_report_claim_retrieval_feedback": frozenset(
            {
                "uq_tr_claim_feedback_verification_claim",
            }
        ),
        "evidence_trace_nodes": frozenset(
            {
                "uq_evidence_trace_nodes_manifest_node_key",
                "uq_evidence_trace_nodes_export_node_key",
            }
        ),
        "evidence_trace_edges": frozenset(
            {
                "uq_evidence_trace_edges_manifest_edge_key",
                "uq_evidence_trace_edges_export_edge_key",
            }
        ),
    }
)

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "api_idempotency_keys": {
        "uq_api_idempotency_keys_scope_key": ("scope", "idempotency_key"),
    },
    "document_chunks": {
        "uq_document_chunks_run_chunk_index": ("run_id", "chunk_index"),
    },
    "document_figures": {
        "uq_document_figures_run_figure_index": ("run_id", "figure_index"),
    },
    "document_run_evaluations": {
        "uq_document_run_evaluations_run_corpus_version": (
            "run_id",
            "corpus_name",
            "eval_version",
        ),
    },
    "document_table_segments": {
        "uq_document_table_segments_table_segment_index": ("table_id", "segment_index"),
    },
    "document_tables": {
        "uq_document_tables_run_table_index": ("run_id", "table_index"),
    },
    "ingest_batch_items": {
        "uq_ingest_batch_items_batch_relative_path": ("batch_id", "relative_path"),
    },
    "document_runs": {
        "uq_document_runs_doc_run_number": ("document_id", "run_number"),
    }
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS.update(
    {
        "agent_task_dependencies": {
            "uq_agent_task_dependencies_task_depends_on": ("task_id", "depends_on_task_id"),
        },
        "agent_task_attempts": {
            "uq_agent_task_attempts_task_attempt": ("task_id", "attempt_number"),
        },
        "agent_task_outcomes": {
            "uq_agent_task_outcomes_task_label_actor": (
                "task_id",
                "outcome_label",
                "created_by",
            ),
        },
        "search_request_results": {
            "uq_search_request_results_request_rank": ("search_request_id", "rank"),
        },
        "retrieval_evidence_spans": {
            "uq_retrieval_evidence_spans_run_source_span": (
                "run_id",
                "source_type",
                "source_id",
                "span_index",
            ),
        },
        "retrieval_evidence_span_multivectors": {
            "uq_retrieval_span_multivectors_span_vector": (
                "retrieval_evidence_span_id",
                "vector_index",
            ),
        },
        "search_request_result_spans": {
            "uq_search_request_result_spans_result_rank": (
                "search_request_result_id",
                "span_rank",
            ),
        },
        "search_harness_evaluation_sources": {
            "uq_search_harness_evaluation_sources_eval_source": (
                "search_harness_evaluation_id",
                "source_type",
            ),
        },
        "retrieval_judgment_sets": {
            "uq_retrieval_judgment_sets_set_name": ("set_name",),
        },
        "retrieval_judgments": {
            "uq_retrieval_judgments_dedup_key": ("deduplication_key",),
        },
        "retrieval_hard_negatives": {
            "uq_retrieval_hard_negatives_dedup_key": ("deduplication_key",),
        },
        "retrieval_learning_candidate_evaluations": {
            "uq_retrieval_learning_candidate_training_eval": (
                "retrieval_training_run_id",
                "search_harness_evaluation_id",
            ),
        },
        "retrieval_reranker_artifacts": {
            "uq_retrieval_reranker_artifacts_candidate_eval": (
                "retrieval_learning_candidate_evaluation_id",
            ),
        },
        "eval_observations": {
            "uq_eval_observations_observation_key": ("observation_key",),
        },
        "eval_failure_cases": {
            "uq_eval_failure_cases_case_key": ("case_key",),
        },
        "semantic_ontology_snapshots": {
            "uq_semantic_ontology_snapshots_ontology_version": ("ontology_version",),
        },
        "semantic_graph_snapshots": {
            "uq_semantic_graph_snapshots_graph_version": ("graph_version",),
        },
        "semantic_concepts": {
            "uq_semantic_concepts_key_registry_version": ("concept_key", "registry_version"),
        },
        "semantic_categories": {
            "uq_semantic_categories_key_registry_version": ("category_key", "registry_version"),
        },
        "semantic_terms": {
            "uq_semantic_terms_registry_version_normalized_text": (
                "registry_version",
                "normalized_text",
            ),
        },
        "semantic_concept_terms": {
            "uq_semantic_concept_terms_concept_term": ("concept_id", "term_id"),
        },
        "semantic_concept_category_bindings": {
            "uq_semantic_concept_category_bindings_concept_category": (
                "concept_id",
                "category_id",
            ),
        },
        "document_run_semantic_passes": {
            "uq_document_run_semantic_passes_run_version_tuple": (
                "run_id",
                "registry_version",
                "extractor_version",
                "artifact_schema_version",
            ),
        },
        "semantic_assertions": {
            "uq_semantic_assertions_pass_concept_kind": (
                "semantic_pass_id",
                "concept_id",
                "assertion_kind",
            ),
        },
        "semantic_assertion_category_bindings": {
            "uq_semantic_assertion_category_bindings_assertion_category": (
                "assertion_id",
                "category_id",
            ),
        },
        "semantic_assertion_evidence": {
            "uq_semantic_assertion_evidence_assertion_source": (
                "assertion_id",
                "source_type",
                "source_locator",
            ),
        },
        "semantic_entities": {
            "uq_semantic_entities_entity_key": ("entity_key",),
        },
        "semantic_governance_events": {
            "uq_semantic_governance_events_dedup_key": ("deduplication_key",),
            "uq_semantic_governance_events_sequence": ("event_sequence",),
        },
        "claim_support_replay_alert_fixture_coverage_waiver_ledgers": {
            "uq_cs_waiver_ledgers_artifact_sha": ("waiver_artifact_id", "waiver_sha256"),
        },
        "claim_support_replay_alert_fixture_coverage_waiver_escalations": {
            "uq_cs_waiver_escalations_ledger_event": ("ledger_id", "escalation_event_id"),
        },
        "claim_support_fixture_sets": {
            "uq_claim_support_fixture_sets_identity": (
                "fixture_set_name",
                "fixture_set_version",
                "fixture_set_sha256",
            ),
        },
        "claim_support_replay_alert_fixture_corpus_snapshots": {
            "uq_cs_replay_fixture_corpus_snapshots_sha": ("snapshot_sha256",),
        },
        "claim_support_replay_alert_fixture_corpus_rows": {
            "uq_cs_replay_fixture_corpus_rows_snapshot_identity": (
                "snapshot_id",
                "case_identity_sha256",
            ),
            "uq_cs_replay_fixture_corpus_rows_snapshot_index": ("snapshot_id", "row_index"),
        },
        "claim_support_calibration_policies": {
            "uq_claim_support_calibration_policies_identity": (
                "policy_name",
                "policy_version",
                "policy_sha256",
            ),
        },
        "claim_support_evaluation_cases": {
            "uq_claim_support_evaluation_cases_eval_case": ("evaluation_id", "case_id"),
        },
        "evidence_manifests": {
            "uq_evidence_manifests_verification_task_kind": (
                "verification_task_id",
                "manifest_kind",
            ),
        },
        "technical_report_release_readiness_db_gates": {
            "uq_tr_readiness_db_gates_verification_task": (
                "technical_report_verification_task_id",
            ),
        },
        "technical_report_claim_retrieval_feedback": {
            "uq_tr_claim_feedback_verification_claim": (
                "technical_report_verification_task_id",
                "claim_id",
            ),
        },
        "evidence_trace_nodes": {
            "uq_evidence_trace_nodes_manifest_node_key": (
                "evidence_manifest_id",
                "node_key",
            ),
            "uq_evidence_trace_nodes_export_node_key": (
                "evidence_package_export_id",
                "node_key",
            ),
        },
        "evidence_trace_edges": {
            "uq_evidence_trace_edges_manifest_edge_key": (
                "evidence_manifest_id",
                "edge_key",
            ),
            "uq_evidence_trace_edges_export_edge_key": (
                "evidence_package_export_id",
                "edge_key",
            ),
        },
    }
)

INGEST_DOMAIN_TABLE_COLUMNS = {
    "ingest_batches": frozenset(
        {
            "id",
            "source_type",
            "status",
            "root_path",
            "recursive",
            "file_count",
            "queued_count",
            "recovery_queued_count",
            "duplicate_count",
            "failed_count",
            "error_message",
            "created_at",
            "completed_at",
        }
    ),
    "ingest_batch_items": frozenset(
        {
            "id",
            "batch_id",
            "relative_path",
            "source_filename",
            "source_path",
            "file_size_bytes",
            "sha256",
            "status",
            "status_code",
            "document_id",
            "run_id",
            "duplicate",
            "recovery_run",
            "error_message",
            "created_at",
        }
    ),
    "documents": frozenset(
        {
            "id",
            "source_filename",
            "source_path",
            "sha256",
            "mime_type",
            "title",
            "metadata_textsearch",
            "page_count",
            "active_run_id",
            "latest_run_id",
            "created_at",
            "updated_at",
        }
    ),
    "document_runs": frozenset(
        {
            "id",
            "document_id",
            "run_number",
            "status",
            "attempts",
            "locked_at",
            "locked_by",
            "last_heartbeat_at",
            "next_attempt_at",
            "error_message",
            "failure_stage",
            "failure_artifact_path",
            "docling_json_path",
            "yaml_path",
            "chunk_count",
            "table_count",
            "figure_count",
            "embedding_model",
            "embedding_dim",
            "validation_status",
            "validation_results",
            "created_at",
            "started_at",
            "completed_at",
        }
    ),
}

DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS = {
    "document_run_evaluations": frozenset(
        {
            "id",
            "run_id",
            "corpus_name",
            "fixture_name",
            "eval_version",
            "status",
            "summary",
            "error_message",
            "created_at",
            "completed_at",
        }
    ),
    "document_run_evaluation_queries": frozenset(
        {
            "id",
            "evaluation_id",
            "query_text",
            "mode",
            "filters",
            "expected_result_type",
            "expected_top_n",
            "passed",
            "candidate_rank",
            "baseline_rank",
            "rank_delta",
            "candidate_score",
            "baseline_score",
            "candidate_result_type",
            "baseline_result_type",
            "candidate_label",
            "baseline_label",
            "details",
            "created_at",
        }
    ),
    "document_chunks": frozenset(
        {
            "id",
            "document_id",
            "run_id",
            "chunk_index",
            "text",
            "heading",
            "page_from",
            "page_to",
            "metadata",
            "embedding",
            "textsearch",
            "created_at",
        }
    ),
    "document_tables": frozenset(
        {
            "id",
            "document_id",
            "run_id",
            "table_index",
            "title",
            "logical_table_key",
            "table_version",
            "supersedes_table_id",
            "lineage_group",
            "heading",
            "page_from",
            "page_to",
            "row_count",
            "col_count",
            "status",
            "search_text",
            "preview_text",
            "metadata",
            "embedding",
            "json_path",
            "yaml_path",
            "textsearch",
            "created_at",
        }
    ),
    "document_table_segments": frozenset(
        {
            "id",
            "table_id",
            "run_id",
            "segment_index",
            "source_table_ref",
            "page_from",
            "page_to",
            "segment_order",
            "metadata",
            "created_at",
        }
    ),
    "document_figures": frozenset(
        {
            "id",
            "document_id",
            "run_id",
            "figure_index",
            "source_figure_ref",
            "caption",
            "heading",
            "page_from",
            "page_to",
            "confidence",
            "status",
            "metadata",
            "json_path",
            "yaml_path",
            "created_at",
        }
    ),
}

RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS = {
    "search_requests": frozenset(
        {
            "id",
            "parent_request_id",
            "evaluation_id",
            "run_id",
            "origin",
            "query_text",
            "mode",
            "filters",
            "details",
            "limit",
            "tabular_query",
            "harness_name",
            "reranker_name",
            "reranker_version",
            "retrieval_profile_name",
            "harness_config",
            "embedding_status",
            "embedding_error",
            "candidate_count",
            "result_count",
            "table_hit_count",
            "duration_ms",
            "created_at",
        }
    ),
    "search_request_results": frozenset(
        {
            "id",
            "search_request_id",
            "rank",
            "base_rank",
            "result_type",
            "document_id",
            "run_id",
            "chunk_id",
            "table_id",
            "score",
            "keyword_score",
            "semantic_score",
            "hybrid_score",
            "rerank_features",
            "page_from",
            "page_to",
            "source_filename",
            "label",
            "preview_text",
            "created_at",
        }
    ),
    "retrieval_evidence_spans": frozenset(
        {
            "id",
            "document_id",
            "run_id",
            "source_type",
            "source_id",
            "chunk_id",
            "table_id",
            "span_index",
            "span_text",
            "heading",
            "page_from",
            "page_to",
            "content_sha256",
            "source_snapshot_sha256",
            "metadata",
            "embedding",
            "textsearch",
            "created_at",
        }
    ),
    "retrieval_evidence_span_multivectors": frozenset(
        {
            "id",
            "retrieval_evidence_span_id",
            "document_id",
            "run_id",
            "source_type",
            "source_id",
            "vector_index",
            "token_start",
            "token_end",
            "vector_text",
            "content_sha256",
            "embedding_model",
            "embedding_dim",
            "embedding_sha256",
            "embedding",
            "metadata",
            "created_at",
        }
    ),
    "search_request_result_spans": frozenset(
        {
            "id",
            "search_request_id",
            "search_request_result_id",
            "retrieval_evidence_span_id",
            "span_rank",
            "score_kind",
            "score",
            "source_type",
            "source_id",
            "span_index",
            "page_from",
            "page_to",
            "text_excerpt",
            "content_sha256",
            "source_snapshot_sha256",
            "metadata",
            "created_at",
        }
    ),
    "search_feedback": frozenset(
        {
            "id",
            "search_request_id",
            "search_request_result_id",
            "result_rank",
            "feedback_type",
            "note",
            "created_at",
        }
    ),
    "chat_answer_records": frozenset(
        {
            "id",
            "search_request_id",
            "document_id",
            "question_text",
            "mode",
            "answer_text",
            "model",
            "used_fallback",
            "warning",
            "citations",
            "harness_name",
            "reranker_name",
            "reranker_version",
            "retrieval_profile_name",
            "created_at",
        }
    ),
    "chat_answer_feedback": frozenset(
        {
            "id",
            "chat_answer_id",
            "feedback_type",
            "note",
            "created_at",
        }
    ),
}

RETRIEVAL_REPLAY_GOVERNANCE_DOMAIN_TABLE_COLUMNS = {
    "search_replay_runs": frozenset(
        {
            "id",
            "source_type",
            "status",
            "harness_name",
            "reranker_name",
            "reranker_version",
            "retrieval_profile_name",
            "harness_config",
            "query_count",
            "passed_count",
            "failed_count",
            "zero_result_count",
            "table_hit_count",
            "top_result_changes",
            "max_rank_shift",
            "summary",
            "error_message",
            "created_at",
            "completed_at",
        }
    ),
    "search_replay_queries": frozenset(
        {
            "id",
            "replay_run_id",
            "source_search_request_id",
            "replay_search_request_id",
            "feedback_id",
            "evaluation_query_id",
            "query_text",
            "mode",
            "filters",
            "expected_result_type",
            "expected_top_n",
            "passed",
            "result_count",
            "table_hit_count",
            "overlap_count",
            "added_count",
            "removed_count",
            "top_result_changed",
            "max_rank_shift",
            "details",
            "created_at",
        }
    ),
    "search_harness_evaluations": frozenset(
        {
            "id",
            "status",
            "baseline_harness_name",
            "candidate_harness_name",
            "limit",
            "source_types",
            "harness_overrides",
            "total_shared_query_count",
            "total_improved_count",
            "total_regressed_count",
            "total_unchanged_count",
            "summary",
            "error_message",
            "created_at",
            "completed_at",
        }
    ),
    "search_harness_evaluation_sources": frozenset(
        {
            "id",
            "search_harness_evaluation_id",
            "source_index",
            "source_type",
            "baseline_replay_run_id",
            "candidate_replay_run_id",
            "baseline_status",
            "candidate_status",
            "baseline_query_count",
            "candidate_query_count",
            "baseline_passed_count",
            "candidate_passed_count",
            "baseline_zero_result_count",
            "candidate_zero_result_count",
            "baseline_table_hit_count",
            "candidate_table_hit_count",
            "baseline_top_result_changes",
            "candidate_top_result_changes",
            "baseline_mrr",
            "candidate_mrr",
            "baseline_foreign_top_result_count",
            "candidate_foreign_top_result_count",
            "acceptance_checks",
            "shared_query_count",
            "improved_count",
            "regressed_count",
            "unchanged_count",
            "created_at",
        }
    ),
    "search_harness_releases": frozenset(
        {
            "id",
            "search_harness_evaluation_id",
            "outcome",
            "baseline_harness_name",
            "candidate_harness_name",
            "limit",
            "source_types",
            "thresholds",
            "metrics",
            "reasons",
            "details",
            "evaluation_snapshot",
            "release_package_sha256",
            "requested_by",
            "review_note",
            "created_at",
        }
    ),
    "search_harness_release_readiness_assessments": frozenset(
        {
            "id",
            "search_harness_release_id",
            "release_audit_bundle_id",
            "release_validation_receipt_id",
            "semantic_governance_event_id",
            "readiness_profile",
            "readiness_status",
            "ready",
            "blockers",
            "blocker_details",
            "checks",
            "diagnostics",
            "lineage_remediation",
            "readiness_payload",
            "assessment_payload",
            "readiness_payload_sha256",
            "assessment_payload_sha256",
            "created_by",
            "review_note",
            "created_at",
        }
    ),
}

RETRIEVAL_LEARNING_DOMAIN_TABLE_COLUMNS = {
    "retrieval_judgment_sets": frozenset(
        {
            "id",
            "set_name",
            "set_kind",
            "source_types",
            "source_limit",
            "criteria",
            "summary",
            "judgment_count",
            "positive_count",
            "negative_count",
            "missing_count",
            "hard_negative_count",
            "payload_sha256",
            "created_by",
            "created_at",
        }
    ),
    "retrieval_judgments": frozenset(
        {
            "id",
            "judgment_set_id",
            "judgment_kind",
            "judgment_label",
            "source_type",
            "source_ref_id",
            "search_feedback_id",
            "search_replay_query_id",
            "search_replay_run_id",
            "evaluation_query_id",
            "source_search_request_id",
            "search_request_id",
            "search_request_result_id",
            "result_rank",
            "result_type",
            "result_id",
            "document_id",
            "run_id",
            "score",
            "query_text",
            "mode",
            "filters",
            "expected_result_type",
            "expected_top_n",
            "harness_name",
            "reranker_name",
            "reranker_version",
            "retrieval_profile_name",
            "rerank_features",
            "evidence_refs",
            "rationale",
            "payload",
            "source_payload_sha256",
            "deduplication_key",
            "created_at",
        }
    ),
    "retrieval_hard_negatives": frozenset(
        {
            "id",
            "judgment_set_id",
            "judgment_id",
            "positive_judgment_id",
            "hard_negative_kind",
            "source_type",
            "source_ref_id",
            "search_feedback_id",
            "search_replay_query_id",
            "search_replay_run_id",
            "evaluation_query_id",
            "source_search_request_id",
            "search_request_id",
            "search_request_result_id",
            "result_rank",
            "result_type",
            "result_id",
            "document_id",
            "run_id",
            "score",
            "query_text",
            "mode",
            "filters",
            "rerank_features",
            "expected_result_type",
            "expected_top_n",
            "evidence_refs",
            "reason",
            "details",
            "source_payload_sha256",
            "deduplication_key",
            "created_at",
        }
    ),
    "retrieval_training_runs": frozenset(
        {
            "id",
            "judgment_set_id",
            "run_kind",
            "status",
            "search_harness_evaluation_id",
            "search_harness_release_id",
            "semantic_governance_event_id",
            "training_dataset_sha256",
            "training_payload",
            "summary",
            "example_count",
            "positive_count",
            "negative_count",
            "missing_count",
            "hard_negative_count",
            "created_by",
            "created_at",
            "completed_at",
        }
    ),
    "retrieval_learning_candidate_evaluations": frozenset(
        {
            "id",
            "retrieval_training_run_id",
            "judgment_set_id",
            "search_harness_evaluation_id",
            "search_harness_release_id",
            "semantic_governance_event_id",
            "training_dataset_sha256",
            "training_example_count",
            "positive_count",
            "negative_count",
            "missing_count",
            "hard_negative_count",
            "baseline_harness_name",
            "candidate_harness_name",
            "source_types",
            "limit",
            "status",
            "gate_outcome",
            "thresholds",
            "metrics",
            "reasons",
            "evaluation_snapshot",
            "release_snapshot",
            "details",
            "learning_package_sha256",
            "created_by",
            "review_note",
            "created_at",
            "completed_at",
        }
    ),
    "retrieval_reranker_artifacts": frozenset(
        {
            "id",
            "retrieval_training_run_id",
            "judgment_set_id",
            "retrieval_learning_candidate_evaluation_id",
            "search_harness_evaluation_id",
            "search_harness_release_id",
            "semantic_governance_event_id",
            "artifact_kind",
            "artifact_name",
            "artifact_version",
            "status",
            "gate_outcome",
            "baseline_harness_name",
            "candidate_harness_name",
            "source_types",
            "limit",
            "training_dataset_sha256",
            "training_example_count",
            "positive_count",
            "negative_count",
            "missing_count",
            "hard_negative_count",
            "thresholds",
            "metrics",
            "reasons",
            "feature_weights",
            "harness_overrides",
            "artifact_payload",
            "evaluation_snapshot",
            "release_snapshot",
            "change_impact_report",
            "artifact_sha256",
            "change_impact_sha256",
            "created_by",
            "review_note",
            "created_at",
            "completed_at",
        }
    ),
}

SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS = {
    "semantic_ontology_snapshots": frozenset(
        {
            "id",
            "ontology_name",
            "ontology_version",
            "upper_ontology_version",
            "source_kind",
            "source_task_id",
            "source_task_type",
            "parent_snapshot_id",
            "payload",
            "sha256",
            "created_at",
            "activated_at",
        }
    ),
    "workspace_semantic_state": frozenset(
        {
            "workspace_key",
            "active_ontology_snapshot_id",
            "created_at",
            "updated_at",
        }
    ),
    "semantic_graph_snapshots": frozenset(
        {
            "id",
            "graph_name",
            "graph_version",
            "ontology_snapshot_id",
            "source_kind",
            "source_task_id",
            "source_task_type",
            "parent_snapshot_id",
            "payload",
            "sha256",
            "created_at",
            "activated_at",
        }
    ),
    "workspace_semantic_graph_state": frozenset(
        {
            "workspace_key",
            "active_graph_snapshot_id",
            "created_at",
            "updated_at",
        }
    ),
    "semantic_concepts": frozenset(
        {
            "id",
            "concept_key",
            "preferred_label",
            "scope_note",
            "registry_version",
            "metadata",
            "created_at",
            "updated_at",
        }
    ),
    "semantic_categories": frozenset(
        {
            "id",
            "category_key",
            "preferred_label",
            "scope_note",
            "registry_version",
            "metadata",
            "created_at",
            "updated_at",
        }
    ),
    "semantic_terms": frozenset(
        {
            "id",
            "registry_version",
            "term_text",
            "normalized_text",
            "term_kind",
            "metadata",
            "created_at",
        }
    ),
    "semantic_concept_terms": frozenset(
        {
            "id",
            "concept_id",
            "term_id",
            "mapping_kind",
            "created_from",
            "review_status",
            "details",
            "created_at",
        }
    ),
    "semantic_concept_category_bindings": frozenset(
        {
            "id",
            "concept_id",
            "category_id",
            "binding_type",
            "created_from",
            "review_status",
            "details",
            "created_at",
        }
    ),
    "document_semantic_concept_reviews": frozenset(
        {
            "id",
            "document_id",
            "concept_id",
            "review_status",
            "review_note",
            "reviewed_by",
            "created_at",
        }
    ),
    "document_semantic_category_reviews": frozenset(
        {
            "id",
            "document_id",
            "concept_id",
            "category_id",
            "review_status",
            "review_note",
            "reviewed_by",
            "created_at",
        }
    ),
    "document_run_semantic_passes": frozenset(
        {
            "id",
            "document_id",
            "run_id",
            "baseline_run_id",
            "baseline_semantic_pass_id",
            "ontology_snapshot_id",
            "upper_ontology_version",
            "status",
            "registry_version",
            "registry_sha256",
            "extractor_version",
            "artifact_schema_version",
            "summary",
            "evaluation_status",
            "evaluation_fixture_name",
            "evaluation_version",
            "evaluation_summary",
            "continuity_summary",
            "error_message",
            "artifact_json_path",
            "artifact_yaml_path",
            "artifact_json_sha256",
            "artifact_yaml_sha256",
            "assertion_count",
            "evidence_count",
            "created_at",
            "completed_at",
        }
    ),
    "semantic_assertions": frozenset(
        {
            "id",
            "semantic_pass_id",
            "concept_id",
            "assertion_kind",
            "epistemic_status",
            "context_scope",
            "review_status",
            "matched_terms",
            "source_types",
            "evidence_count",
            "confidence",
            "details",
            "created_at",
        }
    ),
    "semantic_assertion_category_bindings": frozenset(
        {
            "id",
            "assertion_id",
            "category_id",
            "concept_category_binding_id",
            "binding_type",
            "created_from",
            "review_status",
            "details",
            "created_at",
        }
    ),
    "semantic_assertion_evidence": frozenset(
        {
            "id",
            "assertion_id",
            "document_id",
            "run_id",
            "source_type",
            "source_locator",
            "chunk_id",
            "table_id",
            "figure_id",
            "page_from",
            "page_to",
            "matched_terms",
            "excerpt",
            "source_label",
            "source_artifact_path",
            "source_artifact_sha256",
            "details",
            "created_at",
        }
    ),
    "semantic_entities": frozenset(
        {
            "id",
            "entity_key",
            "entity_type",
            "preferred_label",
            "ontology_snapshot_id",
            "document_id",
            "concept_id",
            "details",
            "created_at",
        }
    ),
    "semantic_facts": frozenset(
        {
            "id",
            "document_id",
            "run_id",
            "semantic_pass_id",
            "ontology_snapshot_id",
            "subject_entity_id",
            "relation_key",
            "relation_label",
            "object_entity_id",
            "object_value_text",
            "source_assertion_id",
            "review_status",
            "confidence",
            "details",
            "created_at",
        }
    ),
    "semantic_fact_evidence": frozenset(
        {
            "id",
            "fact_id",
            "assertion_id",
            "assertion_evidence_id",
            "created_at",
        }
    ),
    "semantic_governance_events": frozenset(
        {
            "id",
            "event_sequence",
            "event_kind",
            "governance_scope",
            "subject_table",
            "subject_id",
            "task_id",
            "ontology_snapshot_id",
            "semantic_graph_snapshot_id",
            "search_harness_evaluation_id",
            "search_harness_release_id",
            "evidence_manifest_id",
            "evidence_package_export_id",
            "agent_task_artifact_id",
            "previous_event_id",
            "previous_event_hash",
            "receipt_sha256",
            "payload_sha256",
            "event_hash",
            "deduplication_key",
            "event_payload",
            "created_by",
            "created_at",
        }
    ),
}

AGENT_TASK_DOMAIN_TABLE_COLUMNS = {
    "agent_tasks": frozenset(
        {
            "id",
            "task_type",
            "status",
            "priority",
            "side_effect_level",
            "requires_approval",
            "parent_task_id",
            "input",
            "result",
            "error_message",
            "failure_artifact_path",
            "attempts",
            "locked_at",
            "locked_by",
            "last_heartbeat_at",
            "next_attempt_at",
            "workflow_version",
            "tool_version",
            "prompt_version",
            "model",
            "model_settings",
            "approved_at",
            "approved_by",
            "approval_note",
            "rejected_at",
            "rejected_by",
            "rejection_note",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        }
    ),
    "agent_task_dependencies": frozenset(
        {
            "id",
            "task_id",
            "depends_on_task_id",
            "dependency_kind",
            "created_at",
        }
    ),
    "agent_task_attempts": frozenset(
        {
            "id",
            "task_id",
            "attempt_number",
            "status",
            "worker_id",
            "input",
            "result",
            "cost",
            "performance",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
        }
    ),
    "agent_task_artifacts": frozenset(
        {
            "id",
            "task_id",
            "attempt_id",
            "artifact_kind",
            "storage_path",
            "payload",
            "created_at",
        }
    ),
    "agent_task_artifact_immutability_events": frozenset(
        {
            "id",
            "artifact_id",
            "task_id",
            "event_kind",
            "mutation_operation",
            "frozen_artifact_kind",
            "attempted_artifact_kind",
            "frozen_storage_path",
            "attempted_storage_path",
            "frozen_payload_sha256",
            "attempted_payload_sha256",
            "details",
            "created_at",
        }
    ),
    "agent_task_outcomes": frozenset(
        {
            "id",
            "task_id",
            "outcome_label",
            "created_by",
            "note",
            "created_at",
        }
    ),
    "agent_task_verifications": frozenset(
        {
            "id",
            "target_task_id",
            "verification_task_id",
            "verifier_type",
            "outcome",
            "metrics",
            "reasons",
            "details",
            "created_at",
            "completed_at",
        }
    ),
    "knowledge_operator_runs": frozenset(
        {
            "id",
            "parent_operator_run_id",
            "operator_kind",
            "operator_name",
            "operator_version",
            "status",
            "document_id",
            "run_id",
            "search_request_id",
            "search_harness_evaluation_id",
            "agent_task_id",
            "agent_task_attempt_id",
            "model_name",
            "model_version",
            "prompt_sha256",
            "config_sha256",
            "input_sha256",
            "output_sha256",
            "metrics",
            "metadata",
            "started_at",
            "completed_at",
            "duration_ms",
            "created_at",
        }
    ),
    "knowledge_operator_inputs": frozenset(
        {
            "id",
            "operator_run_id",
            "input_index",
            "input_kind",
            "source_table",
            "source_id",
            "artifact_path",
            "artifact_sha256",
            "payload",
            "created_at",
        }
    ),
    "knowledge_operator_outputs": frozenset(
        {
            "id",
            "operator_run_id",
            "output_index",
            "output_kind",
            "target_table",
            "target_id",
            "artifact_path",
            "artifact_sha256",
            "payload",
            "created_at",
        }
    ),
}

CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS = {
    "claim_support_replay_alert_fixture_coverage_waiver_ledgers": frozenset(
        {
            "id",
            "waiver_artifact_id",
            "verification_task_id",
            "target_task_id",
            "policy_id",
            "fixture_set_id",
            "waiver_sha256",
            "waiver_severity",
            "waived_by",
            "waiver_expires_at",
            "waiver_review_due_at",
            "waiver_remediation_owner",
            "waived_escalation_event_count",
            "covered_escalation_event_count",
            "coverage_complete",
            "coverage_status",
            "waived_escalation_set_sha256",
            "covered_escalation_set_sha256",
            "source_change_impact_ids",
            "source_verification_task_ids",
            "closure_event_id",
            "closure_artifact_id",
            "closure_receipt_sha256",
            "promotion_event_ids",
            "promotion_artifact_ids",
            "promotion_receipt_sha256s",
            "ledger_payload_sha256",
            "created_at",
            "updated_at",
            "closed_at",
        }
    ),
    "claim_support_replay_alert_fixture_coverage_waiver_escalations": frozenset(
        {
            "id",
            "ledger_id",
            "waiver_artifact_id",
            "escalation_event_id",
            "change_impact_id",
            "escalation_event_hash",
            "escalation_receipt_sha256",
            "alert_kind",
            "replay_status",
            "covered",
            "covered_by_promotion_event_id",
            "covered_by_promotion_artifact_id",
            "covered_by_promotion_receipt_sha256",
            "created_at",
            "covered_at",
        }
    ),
    "claim_support_fixture_sets": frozenset(
        {
            "id",
            "fixture_set_name",
            "fixture_set_version",
            "status",
            "fixture_set_sha256",
            "fixture_count",
            "hard_case_kinds",
            "verdicts",
            "fixtures",
            "metadata",
            "created_at",
        }
    ),
    "claim_support_replay_alert_fixture_corpus_snapshots": frozenset(
        {
            "id",
            "snapshot_name",
            "status",
            "snapshot_sha256",
            "fixture_count",
            "promotion_event_count",
            "promotion_fixture_set_count",
            "invalid_promotion_event_count",
            "source_promotion_event_ids",
            "source_promotion_artifact_ids",
            "source_promotion_receipt_sha256s",
            "source_fixture_set_ids",
            "source_fixture_set_sha256s",
            "source_escalation_event_ids",
            "invalid_promotion_event_ids",
            "snapshot_payload",
            "semantic_governance_event_id",
            "governance_artifact_id",
            "governance_receipt_sha256",
            "created_at",
            "superseded_at",
        }
    ),
    "claim_support_replay_alert_fixture_corpus_rows": frozenset(
        {
            "id",
            "snapshot_id",
            "row_index",
            "case_id",
            "case_identity_sha256",
            "fixture_sha256",
            "fixture",
            "fixture_set_id",
            "promotion_event_id",
            "promotion_artifact_id",
            "promotion_receipt_sha256",
            "source_change_impact_ids",
            "source_escalation_event_ids",
            "replay_alert_source",
            "created_at",
        }
    ),
    "claim_support_calibration_policies": frozenset(
        {
            "id",
            "policy_name",
            "policy_version",
            "status",
            "policy_sha256",
            "owner",
            "source",
            "min_hard_case_kind_count",
            "required_hard_case_kinds",
            "required_verdicts",
            "thresholds",
            "policy_payload",
            "metadata",
            "created_at",
        }
    ),
    "claim_support_evaluations": frozenset(
        {
            "id",
            "agent_task_id",
            "operator_run_id",
            "fixture_set_id",
            "policy_id",
            "evaluation_name",
            "fixture_set_name",
            "fixture_set_version",
            "fixture_set_sha256",
            "policy_name",
            "policy_version",
            "policy_sha256",
            "judge_name",
            "judge_version",
            "min_support_score",
            "status",
            "gate_outcome",
            "thresholds",
            "metrics",
            "reasons",
            "evaluation_payload",
            "evaluation_payload_sha256",
            "created_at",
            "completed_at",
        }
    ),
    "claim_support_evaluation_cases": frozenset(
        {
            "id",
            "evaluation_id",
            "case_index",
            "case_id",
            "hard_case_kind",
            "expected_verdict",
            "predicted_verdict",
            "support_score",
            "passed",
            "claim_payload",
            "support_judgment",
            "failure_reasons",
            "created_at",
        }
    ),
    "claim_support_policy_change_impacts": frozenset(
        {
            "id",
            "activation_task_id",
            "activated_policy_id",
            "previous_policy_id",
            "semantic_governance_event_id",
            "governance_artifact_id",
            "impact_scope",
            "policy_name",
            "policy_version",
            "activated_policy_sha256",
            "previous_policy_sha256",
            "affected_support_judgment_count",
            "affected_generated_document_count",
            "affected_verification_count",
            "replay_recommended_count",
            "replay_status",
            "impacted_claim_derivation_ids",
            "impacted_task_ids",
            "impacted_verification_task_ids",
            "impact_payload",
            "impact_payload_sha256",
            "replay_task_ids",
            "replay_task_plan",
            "replay_closure",
            "replay_closure_sha256",
            "replay_status_updated_at",
            "replay_closed_at",
            "created_at",
        }
    ),
}

AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS = {
    "audit_bundle_exports": frozenset(
        {
            "id",
            "bundle_kind",
            "source_table",
            "source_id",
            "search_harness_release_id",
            "retrieval_training_run_id",
            "storage_path",
            "payload_sha256",
            "bundle_sha256",
            "signature",
            "signature_algorithm",
            "signing_key_id",
            "bundle_payload",
            "integrity",
            "created_by",
            "export_status",
            "created_at",
        }
    ),
    "audit_bundle_validation_receipts": frozenset(
        {
            "id",
            "audit_bundle_export_id",
            "bundle_kind",
            "source_table",
            "source_id",
            "validation_profile",
            "validation_status",
            "payload_schema_valid",
            "prov_graph_valid",
            "bundle_integrity_valid",
            "source_integrity_valid",
            "semantic_governance_valid",
            "receipt_storage_path",
            "prov_jsonld_storage_path",
            "receipt_sha256",
            "prov_jsonld_sha256",
            "signature",
            "signature_algorithm",
            "signing_key_id",
            "validation_errors",
            "receipt_payload",
            "prov_jsonld",
            "created_by",
            "created_at",
        }
    ),
    "evidence_package_exports": frozenset(
        {
            "id",
            "package_kind",
            "search_request_id",
            "agent_task_id",
            "agent_task_artifact_id",
            "package_sha256",
            "trace_sha256",
            "package_payload",
            "source_snapshot_sha256s",
            "operator_run_ids",
            "document_ids",
            "run_ids",
            "claim_ids",
            "export_status",
            "created_at",
        }
    ),
    "evidence_manifests": frozenset(
        {
            "id",
            "manifest_kind",
            "agent_task_id",
            "draft_task_id",
            "verification_task_id",
            "evidence_package_export_id",
            "manifest_sha256",
            "trace_sha256",
            "manifest_payload",
            "source_snapshot_sha256s",
            "document_ids",
            "run_ids",
            "claim_ids",
            "search_request_ids",
            "operator_run_ids",
            "manifest_status",
            "created_at",
        }
    ),
    "technical_report_release_readiness_db_gates": frozenset(
        {
            "id",
            "technical_report_verification_task_id",
            "source_verification_id",
            "source_verification_task_id",
            "harness_task_id",
            "evidence_manifest_id",
            "prov_export_artifact_id",
            "semantic_governance_event_id",
            "check_key",
            "passed",
            "required",
            "coverage_complete",
            "complete",
            "source_search_request_count",
            "verified_request_count",
            "failure_count",
            "source_search_request_ids",
            "verified_request_ids",
            "missing_expected_request_ids",
            "unexpected_verified_request_ids",
            "summary",
            "gate_payload",
            "gate_payload_sha256",
            "created_at",
            "updated_at",
        }
    ),
    "technical_report_claim_retrieval_feedback": frozenset(
        {
            "id",
            "technical_report_verification_task_id",
            "claim_evidence_derivation_id",
            "evidence_manifest_id",
            "prov_export_artifact_id",
            "release_readiness_db_gate_id",
            "semantic_governance_event_id",
            "claim_id",
            "claim_text",
            "support_verdict",
            "support_score",
            "feedback_status",
            "learning_label",
            "hard_negative_kind",
            "source_search_request_id",
            "search_request_result_id",
            "source_search_request_ids",
            "source_search_request_result_ids",
            "search_request_result_span_ids",
            "retrieval_evidence_span_ids",
            "semantic_ontology_snapshot_ids",
            "semantic_graph_snapshot_ids",
            "retrieval_reranker_artifact_ids",
            "search_harness_release_ids",
            "release_audit_bundle_ids",
            "release_validation_receipt_ids",
            "evidence_refs",
            "retrieval_context",
            "feedback_payload",
            "feedback_payload_sha256",
            "source_payload",
            "source_payload_sha256",
            "created_at",
            "updated_at",
        }
    ),
    "evidence_trace_nodes": frozenset(
        {
            "id",
            "evidence_manifest_id",
            "evidence_package_export_id",
            "node_key",
            "node_kind",
            "source_table",
            "source_id",
            "source_ref",
            "content_sha256",
            "payload",
            "created_at",
        }
    ),
    "evidence_trace_edges": frozenset(
        {
            "id",
            "evidence_manifest_id",
            "evidence_package_export_id",
            "edge_key",
            "edge_kind",
            "from_node_id",
            "to_node_id",
            "from_node_key",
            "to_node_key",
            "derivation_sha256",
            "content_sha256",
            "payload",
            "created_at",
        }
    ),
    "claim_evidence_derivations": frozenset(
        {
            "id",
            "evidence_package_export_id",
            "agent_task_id",
            "claim_id",
            "claim_text",
            "derivation_rule",
            "evidence_card_ids",
            "graph_edge_ids",
            "fact_ids",
            "assertion_ids",
            "source_document_ids",
            "source_snapshot_sha256s",
            "source_search_request_ids",
            "source_search_request_result_ids",
            "source_evidence_package_export_ids",
            "source_evidence_package_sha256s",
            "source_evidence_trace_sha256s",
            "semantic_ontology_snapshot_ids",
            "semantic_graph_snapshot_ids",
            "retrieval_reranker_artifact_ids",
            "search_harness_release_ids",
            "release_audit_bundle_ids",
            "release_validation_receipt_ids",
            "provenance_lock",
            "provenance_lock_sha256",
            "support_verdict",
            "support_score",
            "support_judge_run_id",
            "support_judgment",
            "support_judgment_sha256",
            "evidence_package_sha256",
            "derivation_sha256",
            "created_at",
        }
    ),
}

EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS = {
    "eval_observations": frozenset(
        {
            "id",
            "observation_key",
            "surface",
            "subject_kind",
            "subject_id",
            "status",
            "severity",
            "failure_classification",
            "summary",
            "document_id",
            "run_id",
            "evaluation_id",
            "evaluation_query_id",
            "search_request_id",
            "replay_run_id",
            "harness_evaluation_id",
            "agent_task_id",
            "details",
            "evidence_refs",
            "created_at",
            "updated_at",
            "last_seen_at",
        }
    ),
    "eval_failure_cases": frozenset(
        {
            "id",
            "case_key",
            "status",
            "severity",
            "surface",
            "failure_classification",
            "problem_statement",
            "observed_behavior",
            "expected_behavior",
            "diagnosis",
            "source_observation_id",
            "document_id",
            "run_id",
            "evaluation_id",
            "evaluation_query_id",
            "search_request_id",
            "replay_run_id",
            "harness_evaluation_id",
            "agent_task_id",
            "recommended_next_actions",
            "allowed_repair_surfaces",
            "blocked_repair_surfaces",
            "evidence_refs",
            "verification_requirements",
            "agent_task_payloads",
            "details",
            "created_at",
            "updated_at",
            "last_seen_at",
            "resolved_at",
        }
    ),
}

REQUIRED_VECTOR_DIMENSIONS = {
    "retrieval_evidence_spans": {
        "embedding": 1536,
    },
    "retrieval_evidence_span_multivectors": {
        "embedding": 1536,
    },
}

REQUIRED_COMPUTED_SQL = {
    "retrieval_evidence_spans": {
        "textsearch": (
            "setweight(to_tsvector('english', coalesce(heading, '')), 'A') || "
            "to_tsvector('english', coalesce(span_text, ''))"
        ),
    },
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
