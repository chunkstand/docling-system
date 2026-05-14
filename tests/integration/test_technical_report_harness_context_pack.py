from __future__ import annotations

import os

import pytest

from app.db.models import AgentTask
from tests.integration.technical_report_harness_support import (
    _create_audit_bundle_validation_receipt,
    _forge_harness_context_latest_bundle_ref,
    _freeze_release_readiness_assessment,
    create_task_and_process,
    prepare_base_harness_scenario,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_harness_context_pack_blocks_without_release_readiness_assessment(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    scenario = prepare_base_harness_scenario(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
    client = scenario["client"]
    workflow_version = scenario["workflow_version"]
    blocked_harness_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=workflow_version,
        task_type="prepare_report_agent_harness",
        task_input={"target_task_id": str(scenario["evidence_task_id"])},
    )

    blocked_harness_context_response = client.get(f"/agent-tasks/{blocked_harness_task_id}/context")
    assert blocked_harness_context_response.status_code == 200
    blocked_harness_output = blocked_harness_context_response.json()["output"]["harness"]
    blocked_readiness_refs = blocked_harness_output["document_generation_context_pack"][
        "audit_refs"
    ]["release_readiness_assessments"]
    assert blocked_readiness_refs
    assert {ref["selection_status"] for ref in blocked_readiness_refs} == {"missing_assessment"}

    blocked_context_pack_eval_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=workflow_version,
        task_type="evaluate_document_generation_context_pack",
        task_input={"target_task_id": str(blocked_harness_task_id)},
    )
    blocked_context_pack_eval_response = client.get(
        f"/agent-tasks/{blocked_context_pack_eval_task_id}/context"
    )
    assert blocked_context_pack_eval_response.status_code == 200
    blocked_context_pack_eval_context = blocked_context_pack_eval_response.json()
    assert blocked_context_pack_eval_context["summary"]["verification_state"] == "failed"
    assert blocked_context_pack_eval_context["output"]["evaluation"]["gate_outcome"] == "failed"
    assert any(
        check["check_key"] == "release_readiness_assessments" and check["passed"] is False
        for check in blocked_context_pack_eval_context["output"]["evaluation"]["checks"]
    )
    assert any(
        "release_readiness_assessments failed" in reason
        for reason in blocked_context_pack_eval_context["output"]["evaluation"]["reasons"]
    )

    blocked_draft_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=workflow_version,
        task_type="draft_technical_report",
        task_input={"target_task_id": str(blocked_harness_task_id)},
    )
    with postgres_integration_harness.session_factory() as session:
        blocked_draft_row = session.get(AgentTask, blocked_draft_task_id)
        assert blocked_draft_row is not None
        assert blocked_draft_row.status == "failed"
        assert "context-pack gate to pass" in (blocked_draft_row.error_message or "")


def test_context_pack_evaluation_detects_tampered_release_readiness_refs(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    scenario = prepare_base_harness_scenario(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
    _freeze_release_readiness_assessment(
        postgres_integration_harness,
        scenario["release_fixture"]["release"]["release_id"],
    )
    harness_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="prepare_report_agent_harness",
        task_input={"target_task_id": str(scenario["evidence_task_id"])},
    )
    tampered_search_request_id = _forge_harness_context_latest_bundle_ref(
        postgres_integration_harness,
        harness_task_id,
    )

    context_pack_eval_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="evaluate_document_generation_context_pack",
        task_input={"target_task_id": str(harness_task_id)},
    )
    context_pack_eval_response = scenario["client"].get(
        f"/agent-tasks/{context_pack_eval_task_id}/context"
    )
    assert context_pack_eval_response.status_code == 200
    tampered_eval = context_pack_eval_response.json()["output"]["evaluation"]
    assert tampered_eval["gate_outcome"] == "failed"
    assert any(
        check["check_key"] == "release_readiness_assessments" and check["passed"] is True
        for check in tampered_eval["checks"]
    )
    tampered_db_check = next(
        check
        for check in tampered_eval["checks"]
        if check["check_key"] == "release_readiness_assessment_db_integrity"
    )
    assert tampered_db_check["passed"] is False
    assert tampered_db_check["observed"]["ref_field_mismatch_request_ids"] == [
        tampered_search_request_id
    ]
    assert any(
        row["field"] == "latest_release_audit_bundle_id"
        for row in tampered_db_check["observed"]["ref_field_mismatches"][tampered_search_request_id]
    )


def test_context_pack_roundtrip_surfaces_ready_release_and_rejects_stale_assessment(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    scenario = prepare_base_harness_scenario(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
    client = scenario["client"]
    release_readiness_assessment = _freeze_release_readiness_assessment(
        postgres_integration_harness,
        scenario["release_fixture"]["release"]["release_id"],
    )
    harness_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="prepare_report_agent_harness",
        task_input={"target_task_id": str(scenario["evidence_task_id"])},
    )

    harness_context_response = client.get(f"/agent-tasks/{harness_task_id}/context")
    assert harness_context_response.status_code == 200
    harness_context = harness_context_response.json()
    assert harness_context["summary"]["next_action"] == (
        "Create evaluate_document_generation_context_pack before rendering a report draft."
    )
    harness_output = harness_context["output"]["harness"]
    assert harness_output["workflow_state"]["next_task_type"] == (
        "evaluate_document_generation_context_pack"
    )
    assert {tool["tool_name"] for tool in harness_output["allowed_tools"]} >= {
        "read_task_context",
        "read_task_artifact",
        "search_corpus",
        "create_followup_task",
    }
    assert {skill["skill_name"] for skill in harness_output["required_skills"]} >= {
        "technical_report_planning",
        "evidence_card_usage",
        "graph_context_usage",
        "unsupported_claim_handling",
        "verification_ready_drafting",
    }
    assert harness_output["evidence_cards"]
    assert harness_output["claim_contract"]
    assert harness_output["search_evidence_package_exports"]
    assert harness_output["release_readiness_assessments"]
    assert {ref["assessment_id"] for ref in harness_output["release_readiness_assessments"]} == {
        release_readiness_assessment["assessment_id"]
    }
    assert all(
        ref["selection_status"] == "ready_integrity_complete"
        and ref["integrity"]["complete"] is True
        for ref in harness_output["release_readiness_assessments"]
    )
    assert harness_output["llm_adapter_contract"]["harness_context_refs"]

    harness_artifact_ref = next(
        ref for ref in harness_context["refs"] if ref["ref_key"] == "report_agent_harness_artifact"
    )
    harness_artifact_response = client.get(
        f"/agent-tasks/{harness_task_id}/artifacts/{harness_artifact_ref['artifact_id']}"
    )
    assert harness_artifact_response.status_code == 200
    harness_artifact = harness_artifact_response.json()
    assert harness_artifact["schema_name"] == "report_agent_harness"
    assert harness_artifact["verification_gate"]["target_task_type"] == "verify_technical_report"
    assert harness_artifact["document_generation_context_pack"]["schema_name"] == (
        "document_generation_context_pack"
    )
    assert harness_artifact["document_generation_context_pack"]["audit_refs"][
        "release_readiness_assessment_ids"
    ] == [release_readiness_assessment["assessment_id"]]
    assert harness_artifact["document_generation_context_pack"]["audit_refs"][
        "release_readiness_assessment_sha256s"
    ] == [release_readiness_assessment["assessment_payload_sha256"]]
    assert harness_artifact["llm_adapter_contract"]["primary_context_schema"] == (
        "document_generation_context_pack"
    )

    premature_draft_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="draft_technical_report",
        task_input={"target_task_id": str(harness_task_id)},
    )
    with postgres_integration_harness.session_factory() as session:
        premature_draft_row = session.get(AgentTask, premature_draft_task_id)
        assert premature_draft_row is not None
        assert premature_draft_row.status == "failed"
        assert "evaluate_document_generation_context_pack" in (
            premature_draft_row.error_message or ""
        )

    context_pack_eval_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="evaluate_document_generation_context_pack",
        task_input={"target_task_id": str(harness_task_id)},
    )
    context_pack_eval_response = client.get(f"/agent-tasks/{context_pack_eval_task_id}/context")
    assert context_pack_eval_response.status_code == 200
    context_pack_eval_context = context_pack_eval_response.json()
    assert context_pack_eval_context["summary"]["verification_state"] == "passed"
    assert context_pack_eval_context["summary"]["metrics"]["traceable_claim_ratio"] == 1.0
    assert (
        context_pack_eval_context["output"]["evaluation"]["summary"][
            "release_readiness_failed_ref_count"
        ]
        == 0
    )
    assert context_pack_eval_context["output"]["evaluation"]["gate_outcome"] == "passed"
    assert any(
        check["check_key"] == "release_readiness_assessments" and check["passed"] is True
        for check in context_pack_eval_context["output"]["evaluation"]["checks"]
    )
    assert any(
        check["check_key"] == "release_readiness_assessment_db_integrity"
        and check["passed"] is True
        for check in context_pack_eval_context["output"]["evaluation"]["checks"]
    )
    db_summary = context_pack_eval_context["output"]["evaluation"]["trace"][
        "release_readiness_db_summary"
    ]
    assert db_summary["complete"] is True
    assert db_summary["verified_request_count"] == db_summary["source_search_request_count"]
    assert (
        context_pack_eval_context["output"]["evaluation"]["trace"]["release_readiness_assessments"][
            0
        ]["assessment_id"]
        == release_readiness_assessment["assessment_id"]
    )
    assert context_pack_eval_context["output"]["context_pack"]["context_pack_sha256"]
    assert any(
        ref["ref_key"] == "document_generation_context_pack_artifact"
        for ref in context_pack_eval_context["refs"]
    )

    stale_harness_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="prepare_report_agent_harness",
        task_input={"target_task_id": str(scenario["evidence_task_id"])},
    )
    _create_audit_bundle_validation_receipt(
        postgres_integration_harness,
        scenario["release_fixture"]["audit_bundle"]["bundle_id"],
    )
    stale_context_pack_eval_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="evaluate_document_generation_context_pack",
        task_input={"target_task_id": str(stale_harness_task_id)},
    )
    stale_eval_context_response = client.get(
        f"/agent-tasks/{stale_context_pack_eval_task_id}/context"
    )
    assert stale_eval_context_response.status_code == 200
    stale_eval = stale_eval_context_response.json()["output"]["evaluation"]
    assert stale_eval["gate_outcome"] == "failed"
    assert any(
        check["check_key"] == "release_readiness_assessments" and check["passed"] is True
        for check in stale_eval["checks"]
    )
    stale_db_check = next(
        check
        for check in stale_eval["checks"]
        if check["check_key"] == "release_readiness_assessment_db_integrity"
    )
    assert stale_db_check["passed"] is False
    assert set(stale_db_check["observed"]["stale_assessment_ids"]) == {
        release_readiness_assessment["assessment_id"]
    }
