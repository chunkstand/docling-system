from __future__ import annotations

import os

import pytest
from sqlalchemy import select

from app.db.models import AgentTask, TechnicalReportClaimRetrievalFeedback
from tests.integration.technical_report_harness_support import run_verified_report_roundtrip

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_evidence_manifest_captures_context_pack_and_feedback_lineage(
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
        draft_task_row = session.get(AgentTask, scenario["draft_task_id"])
        assert draft_task_row is not None
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        feedback_rows = list(
            session.scalars(
                select(TechnicalReportClaimRetrievalFeedback).where(
                    TechnicalReportClaimRetrievalFeedback.technical_report_verification_task_id
                    == scenario["verify_task_id"]
                )
            )
        )

    manifest_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/evidence-manifest")
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["schema_name"] == "technical_report_evidence_manifest"
    assert manifest["manifest_kind"] == "technical_report_court_evidence"
    assert manifest["manifest_sha256"]
    assert manifest["trace_sha256"]
    for key in [
        "complete",
        "all_source_documents_hashed",
        "all_document_runs_validation_passed",
        "has_claim_provenance_locks",
        "has_claim_support_judgments",
        "has_support_judge_operator_run",
        "has_context_pack_artifact",
        "has_context_pack_evaluation_artifact",
        "has_context_pack_verifier_record",
        "has_context_pack_evaluation_operator_run",
        "context_pack_evaluation_passed",
        "context_pack_hash_verified",
        "has_release_readiness_assessments",
        "release_readiness_assessments_ready",
        "release_readiness_assessment_integrity_verified",
        "release_readiness_db_gate_verified",
        "release_readiness_db_gate_complete",
        "release_readiness_db_covers_source_requests",
        "has_persisted_release_readiness_db_gate",
        "persisted_release_readiness_db_gate_integrity_verified",
        "has_claim_source_search_results",
        "has_claim_retrieval_feedback_ledger",
        "claim_retrieval_feedback_coverage_complete",
        "claim_retrieval_feedback_integrity_verified",
        "hash_integrity_verified",
    ]:
        assert manifest["audit_checklist"][key] is True
    assert manifest["source_documents"][0]["sha256"]
    assert manifest["document_runs"][0]["artifact_hashes"]["docling_json_sha256"]
    assert (
        manifest["report_trace"]["evidence_package_integrity"]["draft_package_hash_matches"]
        is True
    )
    assert manifest["report_trace"]["verification"]["outcome"] == "passed"
    assert len(manifest["report_trace"]["claim_retrieval_feedback"]) == len(draft_payload["claims"])
    assert manifest["report_trace"]["claim_retrieval_feedback_integrity"]["complete"] is True
    assert (
        manifest["report_trace"]["claim_retrieval_feedback_integrity"][
            "live_link_integrity_required"
        ]
        is False
    )
    assert manifest["report_trace"]["context_pack_audit"]["integrity"]["complete"] is True
    assert manifest["report_trace"]["context_pack_audit"]["context_pack_sha256s"] == [
        context_pack_sha256
    ]
    assert (
        manifest["report_trace"]["context_pack_audit"]["release_readiness_assessments"][0][
            "assessment_id"
        ]
        == scenario["release_readiness_assessment"]["assessment_id"]
    )
    assert (
        manifest["report_trace"]["context_pack_audit"]["release_readiness_db_gate"]["complete"]
        is True
    )
    manifest_gate_record = manifest["report_trace"]["context_pack_audit"][
        "release_readiness_db_gate_record"
    ]
    assert manifest_gate_record["integrity"]["complete"] is True
    assert manifest["report_trace"]["context_pack_audit"]["release_readiness_db_summary"] == (
        context_pack_release_readiness_db_summary
    )
    assert manifest["retrieval_trace"]["source_evidence_closure"]["complete"] is True
    assert manifest["retrieval_trace"]["source_evidence_closure"]["source_record_recall"] == 1.0
    assert (
        manifest["retrieval_trace"]["source_evidence_closure"][
            "cited_cards_without_acceptable_source_evidence_match_count"
        ]
        == 0
    )
    assert manifest["retrieval_trace"]["search_evidence_package_trace_summaries"]
    assert {
        "claim_to_provenance_lock",
        "claim_to_support_judgment",
        "claim_to_retrieval_feedback",
        "support_judge_run_to_claim",
        "search_result_to_claim",
        "search_result_to_claim_retrieval_feedback",
        "selected_span_to_claim_retrieval_feedback",
        "harness_task_to_context_pack_artifact",
        "context_pack_eval_task_to_verifier_record",
        "context_pack_artifact_to_verifier_record",
        "context_pack_eval_task_to_evaluation_artifact",
        "context_pack_eval_operator_to_verifier_record",
        "search_harness_release_to_readiness_assessment",
        "release_readiness_assessment_to_context_pack_artifact",
        "release_readiness_assessment_to_context_pack_verifier_record",
        "context_pack_verifier_record_to_release_readiness_db_gate",
        "release_readiness_assessment_to_release_readiness_db_gate",
    }.issubset({edge["edge_type"] for edge in manifest["provenance_edges"]})
    assert any(
        edge["edge_type"] == "context_pack_verifier_record_to_release_readiness_db_gate"
        and edge["to"]["table"] == "technical_report_release_readiness_db_gates"
        for edge in manifest["provenance_edges"]
    )
    assert manifest["manifest_integrity"]["complete"] is True
    assert manifest["manifest_integrity"]["stored_payload_hash_matches"] is True
    assert manifest["manifest_integrity"]["recomputed_manifest_hash_matches"] is True
    assert manifest["manifest_integrity"]["stored_payload_matches_recomputed"] is True

    assert len(feedback_rows) == len(draft_payload["claims"])
    assert all(row.feedback_payload_sha256 for row in feedback_rows)
    assert all(row.source_payload_sha256 for row in feedback_rows)
    assert all(row.evidence_manifest_id for row in feedback_rows)
    assert all(row.semantic_governance_event_id for row in feedback_rows)
