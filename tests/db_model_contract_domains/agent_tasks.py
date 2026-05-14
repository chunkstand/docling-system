"""DB model contract fragment for agent tasks."""

from __future__ import annotations

MODEL_SYMBOLS = (
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
)

AGENT_TASK_DOMAIN_TABLE_COLUMNS = {
    "agent_tasks": frozenset(
        {
            "approval_note",
            "approved_at",
            "approved_by",
            "attempts",
            "completed_at",
            "created_at",
            "error_message",
            "failure_artifact_path",
            "id",
            "input",
            "last_heartbeat_at",
            "locked_at",
            "locked_by",
            "model",
            "model_settings",
            "next_attempt_at",
            "parent_task_id",
            "priority",
            "prompt_version",
            "rejected_at",
            "rejected_by",
            "rejection_note",
            "requires_approval",
            "result",
            "side_effect_level",
            "started_at",
            "status",
            "task_type",
            "tool_version",
            "updated_at",
            "workflow_version",
        }
    ),
    "agent_task_dependencies": frozenset(
        {"created_at", "dependency_kind", "depends_on_task_id", "id", "task_id"}
    ),
    "agent_task_attempts": frozenset(
        {
            "attempt_number",
            "completed_at",
            "cost",
            "created_at",
            "error_message",
            "id",
            "input",
            "performance",
            "result",
            "started_at",
            "status",
            "task_id",
            "worker_id",
        }
    ),
    "agent_task_artifacts": frozenset(
        {"artifact_kind", "attempt_id", "created_at", "id", "payload", "storage_path", "task_id"}
    ),
    "agent_task_artifact_immutability_events": frozenset(
        {
            "artifact_id",
            "attempted_artifact_kind",
            "attempted_payload_sha256",
            "attempted_storage_path",
            "created_at",
            "details",
            "event_kind",
            "frozen_artifact_kind",
            "frozen_payload_sha256",
            "frozen_storage_path",
            "id",
            "mutation_operation",
            "task_id",
        }
    ),
    "agent_task_outcomes": frozenset(
        {"created_at", "created_by", "id", "note", "outcome_label", "task_id"}
    ),
    "agent_task_verifications": frozenset(
        {
            "completed_at",
            "created_at",
            "details",
            "id",
            "metrics",
            "outcome",
            "reasons",
            "target_task_id",
            "verification_task_id",
            "verifier_type",
        }
    ),
    "knowledge_operator_runs": frozenset(
        {
            "agent_task_attempt_id",
            "agent_task_id",
            "completed_at",
            "config_sha256",
            "created_at",
            "document_id",
            "duration_ms",
            "id",
            "input_sha256",
            "metadata",
            "metrics",
            "model_name",
            "model_version",
            "operator_kind",
            "operator_name",
            "operator_version",
            "output_sha256",
            "parent_operator_run_id",
            "prompt_sha256",
            "run_id",
            "search_harness_evaluation_id",
            "search_request_id",
            "started_at",
            "status",
        }
    ),
    "knowledge_operator_inputs": frozenset(
        {
            "artifact_path",
            "artifact_sha256",
            "created_at",
            "id",
            "input_index",
            "input_kind",
            "operator_run_id",
            "payload",
            "source_id",
            "source_table",
        }
    ),
    "knowledge_operator_outputs": frozenset(
        {
            "artifact_path",
            "artifact_sha256",
            "created_at",
            "id",
            "operator_run_id",
            "output_index",
            "output_kind",
            "payload",
            "target_id",
            "target_table",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "agent_tasks": frozenset(
        {
            "ix_agent_tasks_locked_at",
            "ix_agent_tasks_parent_task_id",
            "ix_agent_tasks_status_priority_next_attempt_at",
            "ix_agent_tasks_task_type_created_at",
        }
    ),
    "agent_task_dependencies": frozenset({"ix_agent_task_dependencies_depends_on_task_id"}),
    "agent_task_attempts": frozenset(
        {"ix_agent_task_attempts_created_at", "ix_agent_task_attempts_task_id"}
    ),
    "agent_task_artifacts": frozenset(
        {
            "ix_agent_task_artifacts_artifact_kind",
            "ix_agent_task_artifacts_attempt_id",
            "ix_agent_task_artifacts_task_id",
        }
    ),
    "agent_task_artifact_immutability_events": frozenset(
        {
            "ix_agent_artifact_immut_events_artifact_created",
            "ix_agent_artifact_immut_events_kind",
            "ix_agent_artifact_immut_events_task_created",
        }
    ),
    "agent_task_outcomes": frozenset(
        {
            "ix_agent_task_outcomes_created_at",
            "ix_agent_task_outcomes_outcome_label",
            "ix_agent_task_outcomes_task_id",
        }
    ),
    "agent_task_verifications": frozenset(
        {
            "ix_agent_task_verifications_created_at",
            "ix_agent_task_verifications_target_task_id",
            "ix_agent_task_verifications_verification_task_id",
            "ix_agent_task_verifications_verifier_type",
        }
    ),
    "knowledge_operator_runs": frozenset(
        {
            "ix_knowledge_operator_runs_agent_task_id",
            "ix_knowledge_operator_runs_created_at",
            "ix_knowledge_operator_runs_kind_created_at",
            "ix_knowledge_operator_runs_parent_id",
            "ix_knowledge_operator_runs_search_request_id",
        }
    ),
    "knowledge_operator_inputs": frozenset(
        {"ix_knowledge_operator_inputs_operator_run_id", "ix_knowledge_operator_inputs_source"}
    ),
    "knowledge_operator_outputs": frozenset(
        {"ix_knowledge_operator_outputs_operator_run_id", "ix_knowledge_operator_outputs_target"}
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
    "agent_tasks": {
        "ix_agent_tasks_status_priority_next_attempt_at": ("status", "priority", "next_attempt_at"),
        "ix_agent_tasks_locked_at": ("locked_at",),
        "ix_agent_tasks_parent_task_id": ("parent_task_id",),
        "ix_agent_tasks_task_type_created_at": ("task_type", "created_at"),
    },
    "agent_task_dependencies": {
        "ix_agent_task_dependencies_depends_on_task_id": ("depends_on_task_id",)
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
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "agent_task_dependencies": frozenset({"uq_agent_task_dependencies_task_depends_on"}),
    "agent_task_attempts": frozenset({"uq_agent_task_attempts_task_attempt"}),
    "agent_task_outcomes": frozenset({"uq_agent_task_outcomes_task_label_actor"}),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "agent_task_dependencies": {
        "uq_agent_task_dependencies_task_depends_on": ("task_id", "depends_on_task_id")
    },
    "agent_task_attempts": {"uq_agent_task_attempts_task_attempt": ("task_id", "attempt_number")},
    "agent_task_outcomes": {
        "uq_agent_task_outcomes_task_label_actor": ("task_id", "outcome_label", "created_by")
    },
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
