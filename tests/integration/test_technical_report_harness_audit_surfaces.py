from __future__ import annotations

import os
from copy import deepcopy

import pytest
from sqlalchemy import select

from app.db.public.agent_tasks import AgentTask
from app.db.public.audit_and_evidence import (
    TechnicalReportClaimRetrievalFeedback,
    TechnicalReportReleaseReadinessDbGate,
)
from tests.integration.technical_report_harness_support import run_verified_report_roundtrip

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_verified_report_audit_bundle_captures_release_readiness_lineage(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    scenario = run_verified_report_roundtrip(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
    client = scenario["client"]
    context_pack_eval_context = client.get(
        f"/agent-tasks/{scenario['context_pack_eval_task_id']}/context"
    ).json()
    context_pack_sha256 = context_pack_eval_context["output"]["context_pack"]["context_pack_sha256"]
    context_pack_release_readiness_db_summary = context_pack_eval_context["output"]["evaluation"][
        "trace"
    ]["release_readiness_db_summary"]

    with postgres_integration_harness.session_factory() as session:
        db_gate = session.scalars(
            select(TechnicalReportReleaseReadinessDbGate).where(
                TechnicalReportReleaseReadinessDbGate.technical_report_verification_task_id
                == scenario["verify_task_id"]
            )
        ).one()
        draft_task_row = session.get(AgentTask, scenario["draft_task_id"])
        assert draft_task_row is not None
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        release_readiness_db_gate_id = db_gate.id
        release_readiness_db_gate_payload_sha256 = db_gate.gate_payload_sha256

    audit_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/audit-bundle")
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    assert audit_bundle["schema_name"] == "technical_report_audit_bundle"
    audit_checklist = audit_bundle["audit_checklist"]
    for key in [
        "has_frozen_evidence_package",
        "all_claims_have_derivations",
        "all_claims_have_provenance_locks",
        "all_claim_provenance_locks_match_claim_fields",
        "all_claims_have_support_judgments",
        "all_claim_support_judgments_match_claim_fields",
        "claim_support_judgment_integrity_verified",
        "all_claims_have_source_search_results",
        "hash_integrity_verified",
        "has_frozen_source_evidence_packages",
        "has_frozen_prov_export",
        "has_prov_export_receipt",
        "has_signed_prov_export_receipt",
        "prov_export_receipts_integrity_verified",
        "prov_export_receipt_signature_verified",
        "no_prov_export_immutability_events",
        "has_semantic_governance_chain",
        "semantic_governance_chain_integrity_verified",
        "semantic_governance_chain_links_prov_receipt",
        "semantic_governance_chain_change_impact_evaluated",
        "source_evidence_trace_integrity_verified",
        "generation_evidence_closed",
        "has_generation_operator_run",
        "has_support_judge_operator_run",
        "has_verification_operator_run",
        "has_context_pack_artifact",
        "has_context_pack_evaluation_artifact",
        "has_context_pack_verifier_record",
        "has_context_pack_evaluation_operator_run",
        "context_pack_evaluation_passed",
        "context_pack_hash_verified",
        "has_release_readiness_assessments",
        "release_readiness_assessments_cover_source_requests",
        "release_readiness_assessments_ready",
        "release_readiness_assessment_integrity_verified",
        "release_readiness_db_gate_verified",
        "release_readiness_db_gate_complete",
        "release_readiness_db_covers_source_requests",
        "has_persisted_release_readiness_db_gate",
        "persisted_release_readiness_db_gate_integrity_verified",
        "context_pack_audit_complete",
        "verification_passed",
        "change_impact_clear",
        "has_claim_retrieval_feedback_ledger",
        "claim_retrieval_feedback_coverage_complete",
        "claim_retrieval_feedback_integrity_verified",
        "complete",
    ]:
        assert audit_checklist[key] is True

    assert audit_bundle["context_pack_audit"]["integrity"]["complete"] is True
    assert audit_bundle["context_pack_audit"]["context_pack_sha256s"] == [context_pack_sha256]
    assert (
        audit_bundle["context_pack_audit"]["release_readiness_assessments"][0]["assessment_id"]
        == scenario["release_readiness_assessment"]["assessment_id"]
    )
    assert audit_bundle["context_pack_audit"]["release_readiness_summary"]["failed_ref_count"] == 0
    audit_release_readiness_db_gate = audit_bundle["context_pack_audit"][
        "release_readiness_db_gate"
    ]
    assert audit_release_readiness_db_gate["check_key"] == (
        "release_readiness_assessment_db_integrity"
    )
    assert audit_release_readiness_db_gate["complete"] is True
    assert audit_release_readiness_db_gate["verification_task_id"] == str(
        scenario["context_pack_eval_task_id"]
    )
    assert audit_release_readiness_db_gate["summary"] == context_pack_release_readiness_db_summary
    assert audit_release_readiness_db_gate["coverage_complete"] is True
    assert audit_release_readiness_db_gate["gate_id"] == str(release_readiness_db_gate_id)
    assert (
        audit_release_readiness_db_gate["gate_payload_sha256"]
        == release_readiness_db_gate_payload_sha256
    )
    assert set(audit_release_readiness_db_gate["source_search_request_ids"]) == set(
        audit_release_readiness_db_gate["verified_request_ids"]
    )
    assert audit_release_readiness_db_gate["missing_expected_request_ids"] == []
    assert audit_release_readiness_db_gate["unexpected_verified_request_ids"] == []
    audit_release_readiness_db_gate_record = audit_bundle["context_pack_audit"][
        "release_readiness_db_gate_record"
    ]
    assert audit_release_readiness_db_gate_record["gate_id"] == str(release_readiness_db_gate_id)
    assert (
        audit_release_readiness_db_gate_record["gate_payload_sha256"]
        == release_readiness_db_gate_payload_sha256
    )
    assert audit_release_readiness_db_gate_record["prov_export_artifact_id"]
    assert audit_release_readiness_db_gate_record["semantic_governance_event_id"]
    assert audit_release_readiness_db_gate_record["integrity"]["complete"] is True
    assert (
        audit_bundle["context_pack_audit"]["release_readiness_db_gate_record_integrity"][
            "stored_payload_matches_current_gate"
        ]
        is True
    )
    assert audit_bundle["context_pack_audit"]["release_readiness_db_summary"] == (
        context_pack_release_readiness_db_summary
    )
    assert audit_bundle["context_pack_audit"]["evaluation_task_ids"] == [
        str(scenario["context_pack_eval_task_id"])
    ]
    assert {
        row["artifact_kind"] for row in audit_bundle["context_pack_audit"]["context_pack_artifacts"]
    } == {"document_generation_context_pack"}
    assert {
        row["artifact_kind"] for row in audit_bundle["context_pack_audit"]["evaluation_artifacts"]
    } == {"document_generation_context_pack_evaluation"}
    assert any(
        row["operator_name"] == "document_generation_context_pack_evaluation"
        for row in audit_bundle["context_pack_audit"]["operator_runs"]
    )

    report_export = next(
        row
        for row in audit_bundle["evidence_package_exports"]
        if row["package_kind"] == "technical_report_claims"
    )
    assert report_export["package_sha256"] == draft_payload["evidence_package_sha256"]
    assert audit_bundle["integrity"]["draft_package_hash_matches"] is True
    assert audit_bundle["integrity"]["export_package_hash_matches"] is True
    assert audit_bundle["integrity"]["claim_derivation_count_matches"] is True
    assert audit_bundle["integrity"]["claim_derivation_hash_mismatch_count"] == 0
    assert audit_bundle["integrity"]["claim_package_hash_mismatch_count"] == 0
    assert audit_bundle["integrity"]["claim_provenance_lock_mismatch_count"] == 0
    assert audit_bundle["integrity"]["claim_provenance_lock_contract_mismatch_count"] == 0
    assert audit_bundle["integrity"]["missing_claim_provenance_lock_count"] == 0
    assert audit_bundle["integrity"]["claim_support_judgment_mismatch_count"] == 0
    assert audit_bundle["integrity"]["claim_support_judgment_contract_mismatch_count"] == 0
    assert audit_bundle["integrity"]["missing_claim_support_judgment_count"] == 0
    assert audit_bundle["integrity"]["failed_claim_support_judgment_count"] == 0

    assert audit_bundle["source_evidence_closure"]["complete"] is True
    assert audit_bundle["source_evidence_closure"]["source_record_recall"] == 1.0
    assert audit_bundle["source_evidence_closure"]["card_source_coverage"]
    assert (
        audit_bundle["source_evidence_closure"][
            "cited_cards_without_acceptable_source_evidence_match_count"
        ]
        == 0
    )
    assert (
        audit_bundle["source_evidence_closure"][
            "cited_cards_without_recomputed_source_coverage_count"
        ]
        == 0
    )
    assert (
        audit_bundle["source_evidence_closure"][
            "cited_cards_with_document_run_fallback_match_count"
        ]
        == 0
    )
    assert audit_bundle["search_evidence_package_traces"]
    assert any(
        row["artifact_kind"] == "technical_report_prov_export" for row in audit_bundle["artifacts"]
    )
    assert len(audit_bundle["provenance_export_receipts"]) == 1
    assert audit_bundle["provenance_export_receipts"][0]["export_receipt"]["signature_status"] == (
        "signed"
    )
    assert audit_bundle["provenance_export_receipts"][0]["receipt_integrity"]["complete"] is True
    assert (
        audit_bundle["provenance_export_receipts"][0]["receipt_integrity"][
            "signature_verification_status"
        ]
        == "verified"
    )
    assert audit_bundle["provenance_export_immutability_events"] == []
    assert audit_bundle["semantic_governance_chain"]["integrity"]["complete"] is True
    assert (
        audit_bundle["semantic_governance_chain"]["integrity"][
            "has_technical_report_prov_export_event"
        ]
        is True
    )
    assert audit_bundle["semantic_governance_chain"]["integrity"]["change_impact_evaluated"] is True
    assert audit_bundle["semantic_governance_chain"]["integrity"]["change_impact_clear"] is True
    assert any(
        row["event_kind"] == "technical_report_prov_export_frozen"
        and row["receipt_sha256"]
        == audit_bundle["provenance_export_receipts"][0]["export_receipt"]["receipt_sha256"]
        and row["event_payload"]["change_impact"]["impacted"] is False
        for row in audit_bundle["semantic_governance_chain"]["events"]
    )
    assert any(
        row["event_kind"] == "technical_report_readiness_db_gate_recorded"
        and row["subject_table"] == "technical_report_release_readiness_db_gates"
        and row["subject_id"] == str(release_readiness_db_gate_id)
        for row in audit_bundle["semantic_governance_chain"]["events"]
    )
    assert all(
        row["trace_integrity"]["complete"] for row in audit_bundle["search_evidence_package_traces"]
    )
    assert len(audit_bundle["claim_derivations"]) == len(draft_payload["claims"])
    assert len(audit_bundle["claim_retrieval_feedback"]) == len(draft_payload["claims"])
    assert audit_bundle["claim_retrieval_feedback_integrity"]["complete"] is True
    assert audit_bundle["claim_retrieval_feedback_integrity"]["coverage_complete"] is True
    assert audit_bundle["claim_retrieval_feedback_integrity"]["integrity_verified"] is True
    assert (
        audit_bundle["claim_retrieval_feedback_integrity"]["live_link_integrity_required"] is True
    )
    assert (
        audit_bundle["claim_retrieval_feedback_integrity"]["live_link_integrity_verified"] is True
    )
    feedback_payload = audit_bundle["claim_retrieval_feedback"][0]
    assert feedback_payload["feedback_payload_sha256"]
    assert feedback_payload["source_payload_sha256"]
    assert feedback_payload["learning_label"] == "positive"
    assert feedback_payload["source_search_request_ids"]
    assert feedback_payload["source_search_request_result_ids"]
    assert feedback_payload["evidence_refs"]
    assert feedback_payload["release_readiness_db_gate_id"] == str(release_readiness_db_gate_id)
    assert feedback_payload["prov_export_artifact_id"]
    assert feedback_payload["semantic_governance_event_id"]
    assert any(
        row["event_kind"] == "technical_report_claim_retrieval_feedback_recorded"
        and row["subject_table"] == "technical_report_claim_retrieval_feedback"
        for row in audit_bundle["semantic_governance_chain"]["events"]
    )
    assert audit_bundle["audit_bundle_sha256"]


def test_audit_bundle_flags_feedback_and_release_readiness_db_gate_tampering(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    scenario = run_verified_report_roundtrip(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
    client = scenario["client"]

    with postgres_integration_harness.session_factory() as session:
        feedback_row = session.scalar(
            select(TechnicalReportClaimRetrievalFeedback).where(
                TechnicalReportClaimRetrievalFeedback.technical_report_verification_task_id
                == scenario["verify_task_id"]
            )
        )
        assert feedback_row is not None
        original_feedback_gate_id = feedback_row.release_readiness_db_gate_id
        feedback_row.release_readiness_db_gate_id = None
        session.commit()

    tampered_feedback_link_audit = client.get(
        f"/agent-tasks/{scenario['verify_task_id']}/audit-bundle"
    ).json()
    assert (
        tampered_feedback_link_audit["claim_retrieval_feedback_integrity"][
            "source_payload_column_mismatch_count"
        ]
        == 1
    )
    assert (
        tampered_feedback_link_audit["claim_retrieval_feedback_integrity"][
            "live_link_mismatch_count"
        ]
        == 1
    )
    assert (
        tampered_feedback_link_audit["audit_checklist"][
            "claim_retrieval_feedback_integrity_verified"
        ]
        is False
    )
    assert tampered_feedback_link_audit["audit_checklist"]["complete"] is False

    with postgres_integration_harness.session_factory() as session:
        feedback_row = session.scalar(
            select(TechnicalReportClaimRetrievalFeedback).where(
                TechnicalReportClaimRetrievalFeedback.technical_report_verification_task_id
                == scenario["verify_task_id"]
            )
        )
        gate_row = session.scalars(
            select(TechnicalReportReleaseReadinessDbGate).where(
                TechnicalReportReleaseReadinessDbGate.technical_report_verification_task_id
                == scenario["verify_task_id"]
            )
        ).one()
        assert feedback_row is not None
        feedback_row.release_readiness_db_gate_id = original_feedback_gate_id
        original_gate_payload = deepcopy(gate_row.gate_payload_json)
        gate_row.gate_payload_json = {**original_gate_payload, "verified_request_ids": []}
        session.commit()

    tampered_audit = client.get(f"/agent-tasks/{scenario['verify_task_id']}/audit-bundle").json()
    assert (
        tampered_audit["context_pack_audit"]["release_readiness_db_gate_record_integrity"][
            "stored_payload_hash_matches"
        ]
        is False
    )
    assert (
        tampered_audit["audit_checklist"]["persisted_release_readiness_db_gate_integrity_verified"]
        is False
    )
    assert tampered_audit["audit_checklist"]["context_pack_audit_complete"] is False
    assert tampered_audit["audit_checklist"]["complete"] is False

    with postgres_integration_harness.session_factory() as session:
        feedback_row = session.scalar(
            select(TechnicalReportClaimRetrievalFeedback).where(
                TechnicalReportClaimRetrievalFeedback.technical_report_verification_task_id
                == scenario["verify_task_id"]
            )
        )
        gate_row = session.scalars(
            select(TechnicalReportReleaseReadinessDbGate).where(
                TechnicalReportReleaseReadinessDbGate.technical_report_verification_task_id
                == scenario["verify_task_id"]
            )
        ).one()
        assert feedback_row is not None
        gate_row.gate_payload_json = original_gate_payload
        original_feedback_payload = deepcopy(feedback_row.feedback_payload_json)
        feedback_row.feedback_payload_json = {
            **original_feedback_payload,
            "learning_label": "negative",
        }
        session.commit()

    tampered_feedback_audit = client.get(
        f"/agent-tasks/{scenario['verify_task_id']}/audit-bundle"
    ).json()
    assert (
        tampered_feedback_audit["claim_retrieval_feedback_integrity"][
            "feedback_payload_hash_mismatch_count"
        ]
        == 1
    )
    assert (
        tampered_feedback_audit["audit_checklist"]["claim_retrieval_feedback_integrity_verified"]
        is False
    )
    assert tampered_feedback_audit["audit_checklist"]["complete"] is False
