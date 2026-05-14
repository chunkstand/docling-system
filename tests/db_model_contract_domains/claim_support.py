"""DB model contract fragment for claim support."""

from __future__ import annotations

MODEL_SYMBOLS = (
    "ClaimSupportReplayAlertFixtureCoverageWaiverLedger",
    "ClaimSupportReplayAlertFixtureCoverageWaiverEscalation",
    "ClaimSupportFixtureSet",
    "ClaimSupportReplayAlertFixtureCorpusSnapshot",
    "ClaimSupportReplayAlertFixtureCorpusRow",
    "ClaimSupportCalibrationPolicy",
    "ClaimSupportEvaluation",
    "ClaimSupportEvaluationCase",
    "ClaimSupportPolicyChangeImpact",
)

CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS = {
    "claim_support_replay_alert_fixture_coverage_waiver_ledgers": frozenset(
        {
            "closed_at",
            "closure_artifact_id",
            "closure_event_id",
            "closure_receipt_sha256",
            "coverage_complete",
            "coverage_status",
            "covered_escalation_event_count",
            "covered_escalation_set_sha256",
            "created_at",
            "fixture_set_id",
            "id",
            "ledger_payload_sha256",
            "policy_id",
            "promotion_artifact_ids",
            "promotion_event_ids",
            "promotion_receipt_sha256s",
            "source_change_impact_ids",
            "source_verification_task_ids",
            "target_task_id",
            "updated_at",
            "verification_task_id",
            "waived_by",
            "waived_escalation_event_count",
            "waived_escalation_set_sha256",
            "waiver_artifact_id",
            "waiver_expires_at",
            "waiver_remediation_owner",
            "waiver_review_due_at",
            "waiver_severity",
            "waiver_sha256",
        }
    ),
    "claim_support_replay_alert_fixture_coverage_waiver_escalations": frozenset(
        {
            "alert_kind",
            "change_impact_id",
            "covered",
            "covered_at",
            "covered_by_promotion_artifact_id",
            "covered_by_promotion_event_id",
            "covered_by_promotion_receipt_sha256",
            "created_at",
            "escalation_event_hash",
            "escalation_event_id",
            "escalation_receipt_sha256",
            "id",
            "ledger_id",
            "replay_status",
            "waiver_artifact_id",
        }
    ),
    "claim_support_fixture_sets": frozenset(
        {
            "created_at",
            "fixture_count",
            "fixture_set_name",
            "fixture_set_sha256",
            "fixture_set_version",
            "fixtures",
            "hard_case_kinds",
            "id",
            "metadata",
            "status",
            "verdicts",
        }
    ),
    "claim_support_replay_alert_fixture_corpus_snapshots": frozenset(
        {
            "created_at",
            "fixture_count",
            "governance_artifact_id",
            "governance_receipt_sha256",
            "id",
            "invalid_promotion_event_count",
            "invalid_promotion_event_ids",
            "promotion_event_count",
            "promotion_fixture_set_count",
            "semantic_governance_event_id",
            "snapshot_name",
            "snapshot_payload",
            "snapshot_sha256",
            "source_escalation_event_ids",
            "source_fixture_set_ids",
            "source_fixture_set_sha256s",
            "source_promotion_artifact_ids",
            "source_promotion_event_ids",
            "source_promotion_receipt_sha256s",
            "status",
            "superseded_at",
        }
    ),
    "claim_support_replay_alert_fixture_corpus_rows": frozenset(
        {
            "case_id",
            "case_identity_sha256",
            "created_at",
            "fixture",
            "fixture_set_id",
            "fixture_sha256",
            "id",
            "promotion_artifact_id",
            "promotion_event_id",
            "promotion_receipt_sha256",
            "replay_alert_source",
            "row_index",
            "snapshot_id",
            "source_change_impact_ids",
            "source_escalation_event_ids",
        }
    ),
    "claim_support_calibration_policies": frozenset(
        {
            "created_at",
            "id",
            "metadata",
            "min_hard_case_kind_count",
            "owner",
            "policy_name",
            "policy_payload",
            "policy_sha256",
            "policy_version",
            "required_hard_case_kinds",
            "required_verdicts",
            "source",
            "status",
            "thresholds",
        }
    ),
    "claim_support_evaluations": frozenset(
        {
            "agent_task_id",
            "completed_at",
            "created_at",
            "evaluation_name",
            "evaluation_payload",
            "evaluation_payload_sha256",
            "fixture_set_id",
            "fixture_set_name",
            "fixture_set_sha256",
            "fixture_set_version",
            "gate_outcome",
            "id",
            "judge_name",
            "judge_version",
            "metrics",
            "min_support_score",
            "operator_run_id",
            "policy_id",
            "policy_name",
            "policy_sha256",
            "policy_version",
            "reasons",
            "status",
            "thresholds",
        }
    ),
    "claim_support_evaluation_cases": frozenset(
        {
            "case_id",
            "case_index",
            "claim_payload",
            "created_at",
            "evaluation_id",
            "expected_verdict",
            "failure_reasons",
            "hard_case_kind",
            "id",
            "passed",
            "predicted_verdict",
            "support_judgment",
            "support_score",
        }
    ),
    "claim_support_policy_change_impacts": frozenset(
        {
            "activated_policy_id",
            "activated_policy_sha256",
            "activation_task_id",
            "affected_generated_document_count",
            "affected_support_judgment_count",
            "affected_verification_count",
            "created_at",
            "governance_artifact_id",
            "id",
            "impact_payload",
            "impact_payload_sha256",
            "impact_scope",
            "impacted_claim_derivation_ids",
            "impacted_task_ids",
            "impacted_verification_task_ids",
            "policy_name",
            "policy_version",
            "previous_policy_id",
            "previous_policy_sha256",
            "replay_closed_at",
            "replay_closure",
            "replay_closure_sha256",
            "replay_recommended_count",
            "replay_status",
            "replay_status_updated_at",
            "replay_task_ids",
            "replay_task_plan",
            "semantic_governance_event_id",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "claim_support_replay_alert_fixture_coverage_waiver_ledgers": frozenset(
        {
            "ix_cs_waiver_ledgers_artifact",
            "ix_cs_waiver_ledgers_closure",
            "ix_cs_waiver_ledgers_status",
            "ix_cs_waiver_ledgers_task",
        }
    ),
    "claim_support_replay_alert_fixture_coverage_waiver_escalations": frozenset(
        {
            "ix_cs_waiver_escalations_covered",
            "ix_cs_waiver_escalations_event",
            "ix_cs_waiver_escalations_impact",
            "ix_cs_waiver_escalations_ledger",
        }
    ),
    "claim_support_fixture_sets": frozenset(
        {
            "ix_claim_support_fixture_sets_name_version",
            "ix_claim_support_fixture_sets_sha",
            "ix_claim_support_fixture_sets_status",
        }
    ),
    "claim_support_replay_alert_fixture_corpus_snapshots": frozenset(
        {
            "ix_cs_replay_fixture_corpus_snapshots_governance_artifact",
            "ix_cs_replay_fixture_corpus_snapshots_governance_event",
            "ix_cs_replay_fixture_corpus_snapshots_sha",
            "ix_cs_replay_fixture_corpus_snapshots_status_created",
        }
    ),
    "claim_support_replay_alert_fixture_corpus_rows": frozenset(
        {
            "ix_cs_replay_fixture_corpus_rows_case",
            "ix_cs_replay_fixture_corpus_rows_fixture_sha",
            "ix_cs_replay_fixture_corpus_rows_promotion",
            "ix_cs_replay_fixture_corpus_rows_snapshot",
        }
    ),
    "claim_support_calibration_policies": frozenset(
        {
            "ix_claim_support_calibration_policies_name_version",
            "ix_claim_support_calibration_policies_sha",
            "ix_claim_support_calibration_policies_status",
            "uq_claim_support_calibration_policies_active_name",
        }
    ),
    "claim_support_evaluations": frozenset(
        {
            "ix_claim_support_evaluations_agent_task_id",
            "ix_claim_support_evaluations_created_at",
            "ix_claim_support_evaluations_fixture_set_id",
            "ix_claim_support_evaluations_fixture_sha",
            "ix_claim_support_evaluations_gate_created",
            "ix_claim_support_evaluations_operator_run_id",
            "ix_claim_support_evaluations_policy_id",
            "ix_claim_support_evaluations_policy_sha",
        }
    ),
    "claim_support_evaluation_cases": frozenset(
        {
            "ix_claim_support_evaluation_cases_case_id",
            "ix_claim_support_evaluation_cases_eval_id",
            "ix_claim_support_evaluation_cases_expected",
            "ix_claim_support_evaluation_cases_hard_kind",
            "ix_claim_support_evaluation_cases_passed",
            "ix_claim_support_evaluation_cases_predicted",
        }
    ),
    "claim_support_policy_change_impacts": frozenset(
        {
            "ix_claim_support_policy_change_impacts_activation_task",
            "ix_claim_support_policy_change_impacts_governance_artifact",
            "ix_claim_support_policy_change_impacts_governance_event",
            "ix_claim_support_policy_change_impacts_payload_sha",
            "ix_claim_support_policy_change_impacts_policy",
            "ix_claim_support_policy_change_impacts_replay_status",
            "ix_claim_support_policy_change_impacts_scope_created",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
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
        "ix_claim_support_fixture_sets_name_version": ("fixture_set_name", "fixture_set_version"),
        "ix_claim_support_fixture_sets_status": ("status",),
        "ix_claim_support_fixture_sets_sha": ("fixture_set_sha256",),
    },
    "claim_support_replay_alert_fixture_corpus_snapshots": {
        "ix_cs_replay_fixture_corpus_snapshots_status_created": ("status", "created_at"),
        "ix_cs_replay_fixture_corpus_snapshots_sha": ("snapshot_sha256",),
        "ix_cs_replay_fixture_corpus_snapshots_governance_event": ("semantic_governance_event_id",),
        "ix_cs_replay_fixture_corpus_snapshots_governance_artifact": ("governance_artifact_id",),
    },
    "claim_support_replay_alert_fixture_corpus_rows": {
        "ix_cs_replay_fixture_corpus_rows_snapshot": ("snapshot_id",),
        "ix_cs_replay_fixture_corpus_rows_case": ("case_id",),
        "ix_cs_replay_fixture_corpus_rows_fixture_sha": ("fixture_sha256",),
        "ix_cs_replay_fixture_corpus_rows_promotion": ("promotion_event_id",),
    },
    "claim_support_calibration_policies": {
        "ix_claim_support_calibration_policies_name_version": ("policy_name", "policy_version"),
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
        "ix_claim_support_policy_change_impacts_policy": ("activated_policy_id", "created_at"),
        "ix_claim_support_policy_change_impacts_governance_event": (
            "semantic_governance_event_id",
        ),
        "ix_claim_support_policy_change_impacts_governance_artifact": ("governance_artifact_id",),
        "ix_claim_support_policy_change_impacts_scope_created": ("impact_scope", "created_at"),
        "ix_claim_support_policy_change_impacts_payload_sha": ("impact_payload_sha256",),
        "ix_claim_support_policy_change_impacts_replay_status": ("replay_status", "created_at"),
    },
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "claim_support_replay_alert_fixture_coverage_waiver_ledgers": frozenset(
        {"uq_cs_waiver_ledgers_artifact_sha"}
    ),
    "claim_support_replay_alert_fixture_coverage_waiver_escalations": frozenset(
        {"uq_cs_waiver_escalations_ledger_event"}
    ),
    "claim_support_fixture_sets": frozenset({"uq_claim_support_fixture_sets_identity"}),
    "claim_support_replay_alert_fixture_corpus_snapshots": frozenset(
        {"uq_cs_replay_fixture_corpus_snapshots_sha"}
    ),
    "claim_support_replay_alert_fixture_corpus_rows": frozenset(
        {
            "uq_cs_replay_fixture_corpus_rows_snapshot_identity",
            "uq_cs_replay_fixture_corpus_rows_snapshot_index",
        }
    ),
    "claim_support_calibration_policies": frozenset(
        {"uq_claim_support_calibration_policies_identity"}
    ),
    "claim_support_evaluation_cases": frozenset({"uq_claim_support_evaluation_cases_eval_case"}),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "claim_support_replay_alert_fixture_coverage_waiver_ledgers": {
        "uq_cs_waiver_ledgers_artifact_sha": ("waiver_artifact_id", "waiver_sha256")
    },
    "claim_support_replay_alert_fixture_coverage_waiver_escalations": {
        "uq_cs_waiver_escalations_ledger_event": ("ledger_id", "escalation_event_id")
    },
    "claim_support_fixture_sets": {
        "uq_claim_support_fixture_sets_identity": (
            "fixture_set_name",
            "fixture_set_version",
            "fixture_set_sha256",
        )
    },
    "claim_support_replay_alert_fixture_corpus_snapshots": {
        "uq_cs_replay_fixture_corpus_snapshots_sha": ("snapshot_sha256",)
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
        )
    },
    "claim_support_evaluation_cases": {
        "uq_claim_support_evaluation_cases_eval_case": ("evaluation_id", "case_id")
    },
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
