"""DB model retrieval contract fragment for retrieval learning."""

from __future__ import annotations

TABLE_COLUMNS = {
    "retrieval_judgment_sets": frozenset(
        {
            "created_at",
            "created_by",
            "criteria",
            "hard_negative_count",
            "id",
            "judgment_count",
            "missing_count",
            "negative_count",
            "payload_sha256",
            "positive_count",
            "set_kind",
            "set_name",
            "source_limit",
            "source_types",
            "summary",
        }
    ),
    "retrieval_judgments": frozenset(
        {
            "created_at",
            "deduplication_key",
            "document_id",
            "evaluation_query_id",
            "evidence_refs",
            "expected_result_type",
            "expected_top_n",
            "filters",
            "harness_name",
            "id",
            "judgment_kind",
            "judgment_label",
            "judgment_set_id",
            "mode",
            "payload",
            "query_text",
            "rationale",
            "rerank_features",
            "reranker_name",
            "reranker_version",
            "result_id",
            "result_rank",
            "result_type",
            "retrieval_profile_name",
            "run_id",
            "score",
            "search_feedback_id",
            "search_replay_query_id",
            "search_replay_run_id",
            "search_request_id",
            "search_request_result_id",
            "source_payload_sha256",
            "source_ref_id",
            "source_search_request_id",
            "source_type",
        }
    ),
    "retrieval_hard_negatives": frozenset(
        {
            "created_at",
            "deduplication_key",
            "details",
            "document_id",
            "evaluation_query_id",
            "evidence_refs",
            "expected_result_type",
            "expected_top_n",
            "filters",
            "hard_negative_kind",
            "id",
            "judgment_id",
            "judgment_set_id",
            "mode",
            "positive_judgment_id",
            "query_text",
            "reason",
            "rerank_features",
            "result_id",
            "result_rank",
            "result_type",
            "run_id",
            "score",
            "search_feedback_id",
            "search_replay_query_id",
            "search_replay_run_id",
            "search_request_id",
            "search_request_result_id",
            "source_payload_sha256",
            "source_ref_id",
            "source_search_request_id",
            "source_type",
        }
    ),
    "retrieval_training_runs": frozenset(
        {
            "completed_at",
            "created_at",
            "created_by",
            "example_count",
            "hard_negative_count",
            "id",
            "judgment_set_id",
            "missing_count",
            "negative_count",
            "positive_count",
            "run_kind",
            "search_harness_evaluation_id",
            "search_harness_release_id",
            "semantic_governance_event_id",
            "status",
            "summary",
            "training_dataset_sha256",
            "training_payload",
        }
    ),
    "retrieval_learning_candidate_evaluations": frozenset(
        {
            "baseline_harness_name",
            "candidate_harness_name",
            "completed_at",
            "created_at",
            "created_by",
            "details",
            "evaluation_snapshot",
            "gate_outcome",
            "hard_negative_count",
            "id",
            "judgment_set_id",
            "learning_package_sha256",
            "limit",
            "metrics",
            "missing_count",
            "negative_count",
            "positive_count",
            "reasons",
            "release_snapshot",
            "retrieval_training_run_id",
            "review_note",
            "search_harness_evaluation_id",
            "search_harness_release_id",
            "semantic_governance_event_id",
            "source_types",
            "status",
            "thresholds",
            "training_dataset_sha256",
            "training_example_count",
        }
    ),
    "retrieval_reranker_artifacts": frozenset(
        {
            "artifact_kind",
            "artifact_name",
            "artifact_payload",
            "artifact_sha256",
            "artifact_version",
            "baseline_harness_name",
            "candidate_harness_name",
            "change_impact_report",
            "change_impact_sha256",
            "completed_at",
            "created_at",
            "created_by",
            "evaluation_snapshot",
            "feature_weights",
            "gate_outcome",
            "hard_negative_count",
            "harness_overrides",
            "id",
            "judgment_set_id",
            "limit",
            "metrics",
            "missing_count",
            "negative_count",
            "positive_count",
            "reasons",
            "release_snapshot",
            "retrieval_learning_candidate_evaluation_id",
            "retrieval_training_run_id",
            "review_note",
            "search_harness_evaluation_id",
            "search_harness_release_id",
            "semantic_governance_event_id",
            "source_types",
            "status",
            "thresholds",
            "training_dataset_sha256",
            "training_example_count",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "retrieval_judgment_sets": frozenset(
        {
            "ix_retrieval_judgment_sets_created_at",
            "ix_retrieval_judgment_sets_payload_sha",
            "ix_retrieval_judgment_sets_set_kind_created",
        }
    ),
    "retrieval_judgments": frozenset(
        {
            "ix_retrieval_judgments_created_at",
            "ix_retrieval_judgments_feedback",
            "ix_retrieval_judgments_replay_query",
            "ix_retrieval_judgments_result",
            "ix_retrieval_judgments_search_request",
            "ix_retrieval_judgments_search_result",
            "ix_retrieval_judgments_set_kind",
            "ix_retrieval_judgments_source",
            "ix_retrieval_judgments_source_payload_sha",
            "ix_retrieval_judgments_source_request",
        }
    ),
    "retrieval_hard_negatives": frozenset(
        {
            "ix_retrieval_hard_negatives_created_at",
            "ix_retrieval_hard_negatives_feedback",
            "ix_retrieval_hard_negatives_judgment",
            "ix_retrieval_hard_negatives_positive_judgment",
            "ix_retrieval_hard_negatives_replay_query",
            "ix_retrieval_hard_negatives_request",
            "ix_retrieval_hard_negatives_result",
            "ix_retrieval_hard_negatives_search_result",
            "ix_retrieval_hard_negatives_set_kind",
            "ix_retrieval_hard_negatives_source",
            "ix_retrieval_hard_negatives_source_payload_sha",
            "ix_retrieval_hard_negatives_source_request",
        }
    ),
    "retrieval_training_runs": frozenset(
        {
            "ix_retrieval_training_runs_created_at",
            "ix_retrieval_training_runs_dataset_sha",
            "ix_retrieval_training_runs_governance",
            "ix_retrieval_training_runs_judgment_set",
            "ix_retrieval_training_runs_release",
        }
    ),
    "retrieval_learning_candidate_evaluations": frozenset(
        {
            "ix_retrieval_learning_candidate_created_at",
            "ix_retrieval_learning_candidate_dataset_sha",
            "ix_retrieval_learning_candidate_evaluation",
            "ix_retrieval_learning_candidate_governance",
            "ix_retrieval_learning_candidate_harness_created",
            "ix_retrieval_learning_candidate_judgment_set",
            "ix_retrieval_learning_candidate_outcome_created",
            "ix_retrieval_learning_candidate_package_sha",
            "ix_retrieval_learning_candidate_release",
            "ix_retrieval_learning_candidate_training",
        }
    ),
    "retrieval_reranker_artifacts": frozenset(
        {
            "ix_retrieval_reranker_artifacts_artifact_sha",
            "ix_retrieval_reranker_artifacts_candidate_created",
            "ix_retrieval_reranker_artifacts_candidate_eval",
            "ix_retrieval_reranker_artifacts_evaluation",
            "ix_retrieval_reranker_artifacts_gate_created",
            "ix_retrieval_reranker_artifacts_governance",
            "ix_retrieval_reranker_artifacts_impact_sha",
            "ix_retrieval_reranker_artifacts_release",
            "ix_retrieval_reranker_artifacts_training_created",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
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
        "ix_retrieval_learning_candidate_training": ("retrieval_training_run_id", "created_at"),
        "ix_retrieval_learning_candidate_judgment_set": ("judgment_set_id", "created_at"),
        "ix_retrieval_learning_candidate_evaluation": ("search_harness_evaluation_id",),
        "ix_retrieval_learning_candidate_release": ("search_harness_release_id",),
        "ix_retrieval_learning_candidate_governance": ("semantic_governance_event_id",),
        "ix_retrieval_learning_candidate_dataset_sha": ("training_dataset_sha256",),
        "ix_retrieval_learning_candidate_harness_created": ("candidate_harness_name", "created_at"),
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
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "retrieval_judgment_sets": frozenset({"uq_retrieval_judgment_sets_set_name"}),
    "retrieval_judgments": frozenset({"uq_retrieval_judgments_dedup_key"}),
    "retrieval_hard_negatives": frozenset({"uq_retrieval_hard_negatives_dedup_key"}),
    "retrieval_learning_candidate_evaluations": frozenset(
        {"uq_retrieval_learning_candidate_training_eval"}
    ),
    "retrieval_reranker_artifacts": frozenset({"uq_retrieval_reranker_artifacts_candidate_eval"}),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "retrieval_judgment_sets": {"uq_retrieval_judgment_sets_set_name": ("set_name",)},
    "retrieval_judgments": {"uq_retrieval_judgments_dedup_key": ("deduplication_key",)},
    "retrieval_hard_negatives": {"uq_retrieval_hard_negatives_dedup_key": ("deduplication_key",)},
    "retrieval_learning_candidate_evaluations": {
        "uq_retrieval_learning_candidate_training_eval": (
            "retrieval_training_run_id",
            "search_harness_evaluation_id",
        )
    },
    "retrieval_reranker_artifacts": {
        "uq_retrieval_reranker_artifacts_candidate_eval": (
            "retrieval_learning_candidate_evaluation_id",
        )
    },
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
