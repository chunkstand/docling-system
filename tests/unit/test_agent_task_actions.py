from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ApplyClaimSupportCalibrationPolicyTaskInput,
    ApplyClaimSupportCalibrationPolicyTaskOutput,
    DraftClaimSupportCalibrationPolicyTaskInput,
    DraftClaimSupportCalibrationPolicyTaskOutput,
    EnqueueDocumentReprocessTaskInput,
    EvaluateClaimSupportJudgeTaskInput,
    EvaluateDocumentGenerationContextPackTaskInput,
    QueueClaimSupportPolicyChangeImpactReplayTaskInput,
    QueueClaimSupportPolicyChangeImpactReplayTaskOutput,
    VerifyClaimSupportCalibrationPolicyTaskInput,
    VerifyClaimSupportCalibrationPolicyTaskOutput,
)
from app.schemas.documents import DocumentUploadResponse
from app.services.agent_actions.report_actions import build_report_action_definitions
from app.services.agent_task_actions import (
    _enqueue_document_reprocess_executor,
    _replay_alert_fixture_coverage_waiver_sha256,
    _require_active_replay_alert_fixture_coverage_waiver,
    execute_agent_task_action,
    get_agent_task_action,
    validate_agent_task_output,
)


def test_enqueue_document_reprocess_executor_queues_reprocess(monkeypatch) -> None:
    document_id = uuid4()
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="enqueue_document_reprocess",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.reprocess_document",
        lambda session, requested_document_id: DocumentUploadResponse(
            document_id=requested_document_id,
            run_id=uuid4(),
            status="queued",
            duplicate=False,
        ),
    )

    result = _enqueue_document_reprocess_executor(
        session=object(),
        _task=task,
        payload=EnqueueDocumentReprocessTaskInput(
            document_id=document_id,
            source_task_id=source_task_id,
            reason="triage requested reprocess",
        ),
    )

    assert result["document_id"] == str(document_id)
    assert result["source_task_id"] == str(source_task_id)
    assert result["reason"] == "triage requested reprocess"
    assert result["reprocess"]["document_id"] == str(document_id)
    assert result["reprocess"]["status"] == "queued"

def test_validate_agent_task_output_accepts_migrated_draft_shape() -> None:
    artifact_id = uuid4()
    source_task_id = uuid4()

    validated = validate_agent_task_output(
        "draft_harness_config_update",
        {
            "draft": {
                "draft_harness_name": "wide_v2_review",
                "base_harness_name": "wide_v2",
                "source_task_id": str(source_task_id),
                "source_task_type": "triage_replay_regression",
                "rationale": "publish review harness",
                "override_spec": {
                    "base_harness_name": "wide_v2",
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {"result_type_priority_bonus": 0.009},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(uuid4()),
                    "source_task_id": str(source_task_id),
                    "rationale": "publish review harness",
                },
                "effective_harness_config": {"base_harness_name": "wide_v2"},
            },
            "artifact_id": str(artifact_id),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    )

    assert validated["artifact_id"] == str(artifact_id)
    assert validated["draft"]["source_task_id"] == str(source_task_id)

def test_validate_agent_task_output_rejects_invalid_migrated_draft_shape() -> None:
    try:
        validate_agent_task_output(
            "draft_harness_config_update",
            {
                "artifact_id": str(uuid4()),
                "artifact_kind": "harness_config_draft",
                "artifact_path": "/tmp/harness_config_draft.json",
            },
        )
    except ValidationError as exc:
        assert "draft" in str(exc)
    else:
        raise AssertionError("Expected draft output validation to fail")

def test_validate_agent_task_output_accepts_migrated_evaluate_shape() -> None:
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    validated = validate_agent_task_output(
        "evaluate_search_harness",
        {
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "evaluation": {
                "baseline_harness_name": "default_v1",
                "candidate_harness_name": "wide_v2",
                "limit": 12,
                "total_shared_query_count": 4,
                "total_improved_count": 1,
                "total_regressed_count": 0,
                "total_unchanged_count": 3,
                "sources": [
                    {
                        "source_type": "evaluation_queries",
                        "baseline_replay_run_id": str(baseline_replay_run_id),
                        "candidate_replay_run_id": str(candidate_replay_run_id),
                        "baseline_query_count": 4,
                        "candidate_query_count": 4,
                        "baseline_passed_count": 4,
                        "candidate_passed_count": 4,
                        "baseline_zero_result_count": 0,
                        "candidate_zero_result_count": 0,
                        "baseline_table_hit_count": 1,
                        "candidate_table_hit_count": 1,
                        "baseline_top_result_changes": 0,
                        "candidate_top_result_changes": 0,
                        "baseline_mrr": 1.0,
                        "candidate_mrr": 1.0,
                        "baseline_foreign_top_result_count": 0,
                        "candidate_foreign_top_result_count": 0,
                        "acceptance_checks": {"no_regressions": True},
                        "shared_query_count": 4,
                        "improved_count": 1,
                        "regressed_count": 0,
                        "unchanged_count": 3,
                    }
                ],
            },
        },
    )

    assert validated["candidate_harness_name"] == "wide_v2"
    assert validated["evaluation"]["sources"][0]["source_type"] == "evaluation_queries"

def test_execute_agent_task_action_includes_output_schema_metadata(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={
            "draft_harness_name": "wide_v2_review",
            "base_harness_name": "wide_v2",
        },
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    action = replace(
        get_agent_task_action("draft_harness_config_update"),
        executor=lambda session, current_task, payload: {
            "draft": {
                "draft_harness_name": payload.draft_harness_name,
                "base_harness_name": payload.base_harness_name,
                "source_task_id": None,
                "source_task_type": None,
                "rationale": None,
                "override_spec": {
                    "base_harness_name": payload.base_harness_name,
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(current_task.id),
                    "source_task_id": None,
                    "rationale": None,
                },
                "effective_harness_config": {"base_harness_name": payload.base_harness_name},
            },
            "artifact_id": str(uuid4()),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.get_agent_task_action", lambda _task_type: action
    )

    result = execute_agent_task_action(object(), task)

    assert result["output_schema_name"] == "draft_harness_config_update_output"
    assert result["output_schema_version"] == "1.0"
    assert result["payload"]["draft"]["draft_harness_name"] == "wide_v2_review"

def test_get_agent_task_action_exposes_evaluate_output_schema_metadata() -> None:
    action = get_agent_task_action("evaluate_search_harness")

    assert action.output_schema_name == "evaluate_search_harness_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None

def test_get_agent_task_action_exposes_verify_evaluation_output_schema_metadata() -> None:
    action = get_agent_task_action("verify_search_harness_evaluation")

    assert action.output_schema_name == "verify_search_harness_evaluation_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None

def test_get_agent_task_action_exposes_triage_output_schema_metadata() -> None:
    action = get_agent_task_action("triage_replay_regression")

    assert action.output_schema_name == "triage_replay_regression_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None

def test_get_agent_task_action_exposes_claim_support_judge_eval_metadata() -> None:
    action = get_agent_task_action("evaluate_claim_support_judge")

    assert action.capability == "technical_reports"
    assert action.definition_kind == "workflow"
    assert action.payload_model is EvaluateClaimSupportJudgeTaskInput
    assert action.output_schema_name == "evaluate_claim_support_judge_output"
    assert action.output_schema_version == "1.0"
    assert action.context_builder_name == "evaluate_claim_support_judge"
    assert action.output_model is not None

def test_get_agent_task_action_exposes_claim_support_policy_workflow_metadata() -> None:
    draft_action = get_agent_task_action("draft_claim_support_calibration_policy")
    verify_action = get_agent_task_action("verify_claim_support_calibration_policy")
    apply_action = get_agent_task_action("apply_claim_support_calibration_policy")
    replay_action = get_agent_task_action("queue_claim_support_policy_change_impact_replay")

    assert draft_action.capability == "technical_reports"
    assert draft_action.definition_kind == "draft"
    assert draft_action.side_effect_level == "draft_change"
    assert draft_action.requires_approval is False
    assert draft_action.payload_model is DraftClaimSupportCalibrationPolicyTaskInput
    assert draft_action.output_model is DraftClaimSupportCalibrationPolicyTaskOutput
    assert draft_action.output_schema_name == "draft_claim_support_calibration_policy_output"
    assert draft_action.output_schema_version == "1.0"

    assert verify_action.capability == "technical_reports"
    assert verify_action.definition_kind == "verifier"
    assert verify_action.side_effect_level == "read_only"
    assert verify_action.requires_approval is False
    assert verify_action.payload_model is VerifyClaimSupportCalibrationPolicyTaskInput
    assert verify_action.output_model is VerifyClaimSupportCalibrationPolicyTaskOutput
    assert verify_action.output_schema_name == "verify_claim_support_calibration_policy_output"
    assert verify_action.output_schema_version == "1.0"

    assert apply_action.capability == "technical_reports"
    assert apply_action.definition_kind == "promotion"
    assert apply_action.side_effect_level == "promotable"
    assert apply_action.requires_approval is True
    assert apply_action.payload_model is ApplyClaimSupportCalibrationPolicyTaskInput
    assert apply_action.output_model is ApplyClaimSupportCalibrationPolicyTaskOutput
    assert apply_action.output_schema_name == "apply_claim_support_calibration_policy_output"
    assert apply_action.output_schema_version == "1.0"

    assert replay_action.capability == "technical_reports"
    assert replay_action.definition_kind == "draft"
    assert replay_action.side_effect_level == "draft_change"
    assert replay_action.requires_approval is False
    assert replay_action.payload_model is QueueClaimSupportPolicyChangeImpactReplayTaskInput
    assert replay_action.output_model is QueueClaimSupportPolicyChangeImpactReplayTaskOutput
    assert (
        replay_action.output_schema_name
        == "queue_claim_support_policy_change_impact_replay_output"
    )
    assert replay_action.output_schema_version == "1.0"

def test_replay_alert_waiver_activation_requires_integrity_and_independent_approval() -> None:
    now = datetime.now(UTC)
    waiver_basis = {
        "schema_name": "claim_support_replay_alert_fixture_coverage_waiver",
        "schema_version": "1.1",
        "verification_task_id": str(uuid4()),
        "target_task_id": str(uuid4()),
        "policy_id": str(uuid4()),
        "policy_sha256": "policy-sha",
        "fixture_set_id": str(uuid4()),
        "fixture_set_sha256": "fixture-sha",
        "waived_by": "waiver-creator@example.com",
        "waiver_reason": "temporary emergency validation",
        "waiver_severity": "high",
        "waiver_expires_at": (now + timedelta(hours=2)).isoformat(),
        "waiver_review_due_at": (now + timedelta(hours=1)).isoformat(),
        "waiver_remediation_owner": "remediation@example.com",
        "waiver_status": "active",
        "waived_at": now.isoformat(),
        "replay_alert_fixture_summary": {"included_replay_alert_fixture_count": 0},
        "replay_alert_fixture_summary_sha256": "summary-sha",
        "stale_unconverted_escalation_event_count": 1,
    }
    waiver = {
        **waiver_basis,
        "waiver_sha256": _replay_alert_fixture_coverage_waiver_sha256(waiver_basis),
        "artifact_id": str(uuid4()),
        "artifact_kind": "claim_support_replay_alert_fixture_coverage_waiver",
        "artifact_path": "storage/waiver.json",
    }
    task = SimpleNamespace(
        approved_by="task-approver@example.com",
        approved_at=now,
    )
    payload = ApplyClaimSupportCalibrationPolicyTaskInput(
        draft_task_id=uuid4(),
        verification_task_id=uuid4(),
        reason="activate under managed waiver",
        waiver_activation_approved_by="waiver-reviewer@example.com",
        waiver_activation_approval_note="reviewed active waiver before activation",
    )

    approval = _require_active_replay_alert_fixture_coverage_waiver(
        waiver=waiver,
        payload=payload,
        task=task,
    )

    assert approval["waiver_sha256"] == waiver["waiver_sha256"]
    assert approval["approved_by"] == "waiver-reviewer@example.com"

    tampered_waiver = {**waiver, "waiver_reason": "tampered after verification"}
    with pytest.raises(ValueError, match="hash does not match"):
        _require_active_replay_alert_fixture_coverage_waiver(
            waiver=tampered_waiver,
            payload=payload,
            task=task,
        )

    same_creator_payload = payload.model_copy(
        update={"waiver_activation_approved_by": "waiver-creator@example.com"}
    )
    with pytest.raises(ValueError, match="different operator than the waiver creator"):
        _require_active_replay_alert_fixture_coverage_waiver(
            waiver=waiver,
            payload=same_creator_payload,
            task=task,
        )

def test_get_agent_task_action_exposes_context_pack_eval_metadata() -> None:
    action = get_agent_task_action("evaluate_document_generation_context_pack")

    assert action.capability == "technical_reports"
    assert action.definition_kind == "verifier"
    assert action.payload_model is EvaluateDocumentGenerationContextPackTaskInput
    assert action.output_schema_name == "evaluate_document_generation_context_pack_output"
    assert action.output_schema_version == "1.0"
    assert action.context_builder_name == "evaluate_document_generation_context_pack"
    assert action.output_model is not None

def test_report_action_registry_is_composed_from_owner_module() -> None:
    owner_actions = build_report_action_definitions()

    for task_type in (
        "plan_technical_report",
        "build_report_evidence_cards",
        "prepare_report_agent_harness",
        "evaluate_document_generation_context_pack",
        "draft_technical_report",
        "verify_technical_report",
    ):
        assert get_agent_task_action(task_type) == owner_actions[task_type]

def test_get_agent_task_action_exposes_eval_control_plane_actions() -> None:
    refresh_action = get_agent_task_action("refresh_eval_failure_cases")
    inspect_action = get_agent_task_action("inspect_eval_failure_case")
    triage_action = get_agent_task_action("triage_eval_failure_case")
    optimize_action = get_agent_task_action("optimize_search_harness_from_case")
    draft_action = get_agent_task_action("draft_harness_config_update_from_optimization")

    assert refresh_action.output_schema_name == "refresh_eval_failure_cases_output"
    assert inspect_action.output_schema_name == "inspect_eval_failure_case_output"
    assert triage_action.output_schema_name == "triage_eval_failure_case_output"
    assert optimize_action.output_schema_name == "optimize_search_harness_from_case_output"
    assert draft_action.output_schema_name == "draft_harness_config_update_output"
    assert draft_action.side_effect_level == "draft_change"
