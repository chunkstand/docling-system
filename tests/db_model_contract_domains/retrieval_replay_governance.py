"""DB model retrieval contract fragment for retrieval replay governance."""

from __future__ import annotations

TABLE_COLUMNS = {
    "search_replay_runs": frozenset(
        {
            "completed_at",
            "created_at",
            "error_message",
            "failed_count",
            "harness_config",
            "harness_name",
            "id",
            "max_rank_shift",
            "passed_count",
            "query_count",
            "reranker_name",
            "reranker_version",
            "retrieval_profile_name",
            "source_type",
            "status",
            "summary",
            "table_hit_count",
            "top_result_changes",
            "zero_result_count",
        }
    ),
    "search_replay_queries": frozenset(
        {
            "added_count",
            "created_at",
            "details",
            "evaluation_query_id",
            "expected_result_type",
            "expected_top_n",
            "feedback_id",
            "filters",
            "id",
            "max_rank_shift",
            "mode",
            "overlap_count",
            "passed",
            "query_text",
            "removed_count",
            "replay_run_id",
            "replay_search_request_id",
            "result_count",
            "source_search_request_id",
            "table_hit_count",
            "top_result_changed",
        }
    ),
    "search_harness_evaluations": frozenset(
        {
            "baseline_harness_name",
            "candidate_harness_name",
            "completed_at",
            "created_at",
            "error_message",
            "harness_overrides",
            "id",
            "limit",
            "source_types",
            "status",
            "summary",
            "total_improved_count",
            "total_regressed_count",
            "total_shared_query_count",
            "total_unchanged_count",
        }
    ),
    "search_harness_evaluation_sources": frozenset(
        {
            "acceptance_checks",
            "baseline_foreign_top_result_count",
            "baseline_mrr",
            "baseline_passed_count",
            "baseline_query_count",
            "baseline_replay_run_id",
            "baseline_status",
            "baseline_table_hit_count",
            "baseline_top_result_changes",
            "baseline_zero_result_count",
            "candidate_foreign_top_result_count",
            "candidate_mrr",
            "candidate_passed_count",
            "candidate_query_count",
            "candidate_replay_run_id",
            "candidate_status",
            "candidate_table_hit_count",
            "candidate_top_result_changes",
            "candidate_zero_result_count",
            "created_at",
            "id",
            "improved_count",
            "regressed_count",
            "search_harness_evaluation_id",
            "shared_query_count",
            "source_index",
            "source_type",
            "unchanged_count",
        }
    ),
    "search_harness_releases": frozenset(
        {
            "baseline_harness_name",
            "candidate_harness_name",
            "created_at",
            "details",
            "evaluation_snapshot",
            "id",
            "limit",
            "metrics",
            "outcome",
            "reasons",
            "release_package_sha256",
            "requested_by",
            "review_note",
            "search_harness_evaluation_id",
            "source_types",
            "thresholds",
        }
    ),
    "search_harness_release_readiness_assessments": frozenset(
        {
            "assessment_payload",
            "assessment_payload_sha256",
            "blocker_details",
            "blockers",
            "checks",
            "created_at",
            "created_by",
            "diagnostics",
            "id",
            "lineage_remediation",
            "readiness_payload",
            "readiness_payload_sha256",
            "readiness_profile",
            "readiness_status",
            "ready",
            "release_audit_bundle_id",
            "release_validation_receipt_id",
            "review_note",
            "search_harness_release_id",
            "semantic_governance_event_id",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "search_replay_runs": frozenset(
        {"ix_search_replay_runs_created_at", "ix_search_replay_runs_source_type_created_at"}
    ),
    "search_replay_queries": frozenset(
        {
            "ix_search_replay_queries_created_at",
            "ix_search_replay_queries_evaluation_query_id",
            "ix_search_replay_queries_feedback_id",
            "ix_search_replay_queries_replay_run_id",
            "ix_search_replay_queries_replay_search_request_id",
            "ix_search_replay_queries_source_search_request_id",
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
            "ix_search_harness_evaluation_sources_baseline_replay",
            "ix_search_harness_evaluation_sources_candidate_replay",
            "ix_search_harness_evaluation_sources_eval_id",
        }
    ),
    "search_harness_releases": frozenset(
        {
            "ix_search_harness_releases_candidate_created_at",
            "ix_search_harness_releases_created_at",
            "ix_search_harness_releases_evaluation_id",
            "ix_search_harness_releases_outcome_created_at",
        }
    ),
    "search_harness_release_readiness_assessments": frozenset(
        {
            "ix_shr_readiness_assessments_bundle_created",
            "ix_shr_readiness_assessments_governance",
            "ix_shr_readiness_assessments_payload_sha",
            "ix_shr_readiness_assessments_readiness_sha",
            "ix_shr_readiness_assessments_receipt_created",
            "ix_shr_readiness_assessments_release_created",
            "ix_shr_readiness_assessments_status_created",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
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
        "ix_search_harness_evaluation_sources_candidate_replay": ("candidate_replay_run_id",),
    },
    "search_harness_releases": {
        "ix_search_harness_releases_evaluation_id": ("search_harness_evaluation_id",),
        "ix_search_harness_releases_candidate_created_at": ("candidate_harness_name", "created_at"),
        "ix_search_harness_releases_outcome_created_at": ("outcome", "created_at"),
        "ix_search_harness_releases_created_at": ("created_at",),
    },
    "search_harness_release_readiness_assessments": {
        "ix_shr_readiness_assessments_release_created": ("search_harness_release_id", "created_at"),
        "ix_shr_readiness_assessments_bundle_created": ("release_audit_bundle_id", "created_at"),
        "ix_shr_readiness_assessments_receipt_created": (
            "release_validation_receipt_id",
            "created_at",
        ),
        "ix_shr_readiness_assessments_governance": ("semantic_governance_event_id",),
        "ix_shr_readiness_assessments_status_created": ("readiness_status", "created_at"),
        "ix_shr_readiness_assessments_readiness_sha": ("readiness_payload_sha256",),
        "ix_shr_readiness_assessments_payload_sha": ("assessment_payload_sha256",),
    },
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "search_harness_evaluation_sources": frozenset(
        {"uq_search_harness_evaluation_sources_eval_source"}
    )
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "search_harness_evaluation_sources": {
        "uq_search_harness_evaluation_sources_eval_source": (
            "search_harness_evaluation_id",
            "source_type",
        )
    }
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
