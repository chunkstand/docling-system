"""DB model contract fragment for evaluation feedback."""

from __future__ import annotations

MODEL_SYMBOLS = ("EvalObservation", "EvalFailureCase")

EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS = {
    "eval_observations": frozenset(
        {
            "agent_task_id",
            "created_at",
            "details",
            "document_id",
            "evaluation_id",
            "evaluation_query_id",
            "evidence_refs",
            "failure_classification",
            "harness_evaluation_id",
            "id",
            "last_seen_at",
            "observation_key",
            "replay_run_id",
            "run_id",
            "search_request_id",
            "severity",
            "status",
            "subject_id",
            "subject_kind",
            "summary",
            "surface",
            "updated_at",
        }
    ),
    "eval_failure_cases": frozenset(
        {
            "agent_task_id",
            "agent_task_payloads",
            "allowed_repair_surfaces",
            "blocked_repair_surfaces",
            "case_key",
            "created_at",
            "details",
            "diagnosis",
            "document_id",
            "evaluation_id",
            "evaluation_query_id",
            "evidence_refs",
            "expected_behavior",
            "failure_classification",
            "harness_evaluation_id",
            "id",
            "last_seen_at",
            "observed_behavior",
            "problem_statement",
            "recommended_next_actions",
            "replay_run_id",
            "resolved_at",
            "run_id",
            "search_request_id",
            "severity",
            "source_observation_id",
            "status",
            "surface",
            "updated_at",
            "verification_requirements",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "eval_observations": frozenset(
        {
            "ix_eval_observations_document_id",
            "ix_eval_observations_evaluation_id",
            "ix_eval_observations_search_request_id",
            "ix_eval_observations_status_last_seen",
            "ix_eval_observations_surface_last_seen",
        }
    ),
    "eval_failure_cases": frozenset(
        {
            "ix_eval_failure_cases_document_id",
            "ix_eval_failure_cases_evaluation_id",
            "ix_eval_failure_cases_search_request_id",
            "ix_eval_failure_cases_status_updated",
            "ix_eval_failure_cases_surface_status",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
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
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "eval_observations": frozenset({"uq_eval_observations_observation_key"}),
    "eval_failure_cases": frozenset({"uq_eval_failure_cases_case_key"}),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "eval_observations": {"uq_eval_observations_observation_key": ("observation_key",)},
    "eval_failure_cases": {"uq_eval_failure_cases_case_key": ("case_key",)},
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
