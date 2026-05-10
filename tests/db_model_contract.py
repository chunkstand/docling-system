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
