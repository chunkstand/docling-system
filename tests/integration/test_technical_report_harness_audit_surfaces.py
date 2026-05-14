from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    ClaimEvidenceDerivation,
    EvidenceManifest,
    EvidencePackageExport,
    KnowledgeOperatorRun,
    SemanticGovernanceEvent,
    TechnicalReportClaimRetrievalFeedback,
    TechnicalReportReleaseReadinessDbGate,
)
from app.services.evidence import payload_sha256
from tests.integration.technical_report_harness_support import run_verified_report_roundtrip

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_verified_report_audit_bundle_and_manifest_capture_release_readiness_lineage(
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
        markdown_path = Path(draft_payload["markdown_path"])
        assert markdown_path.exists()
        assert "Evidence Cards" in markdown_path.read_text()
        assert draft_task_row.result_json["payload"]["context_pack_evaluation_task_id"] == str(
            scenario["context_pack_eval_task_id"]
        )
        assert draft_task_row.result_json["payload"]["context_pack_sha256"] == context_pack_sha256
        assert (
            draft_payload["llm_adapter_contract"]["context_pack_gate"]["context_pack_sha256"]
            == context_pack_sha256
        )
        assert (
            draft_payload["llm_adapter_contract"]["context_pack_gate"]["release_readiness_summary"][
                "failed_ref_count"
            ]
            == 0
        )
        assert draft_payload["evidence_package_sha256"]
        assert draft_payload["evidence_package_export_id"]
        assert draft_payload["source_evidence_package_exports"]
        assert draft_payload["claim_derivations"]
        assert all(claim["derivation_sha256"] for claim in draft_payload["claims"])
        assert all(claim["source_evidence_package_export_ids"] for claim in draft_payload["claims"])
        assert all(claim["source_search_request_result_ids"] for claim in draft_payload["claims"])
        assert all(claim["provenance_lock_sha256"] for claim in draft_payload["claims"])
        assert all(
            claim["provenance_lock_sha256"] == payload_sha256(claim["provenance_lock"])
            for claim in draft_payload["claims"]
        )
        assert all(
            claim["provenance_lock"]["source_search_request_ids"]
            == claim["source_search_request_ids"]
            for claim in draft_payload["claims"]
        )
        assert all(
            claim["provenance_lock"]["source_search_request_result_ids"]
            == claim["source_search_request_result_ids"]
            for claim in draft_payload["claims"]
        )
        assert all(claim["support_verdict"] == "supported" for claim in draft_payload["claims"])
        assert all(claim["support_score"] >= 0.34 for claim in draft_payload["claims"])
        assert all(claim["support_judge_run_id"] for claim in draft_payload["claims"])
        assert all(claim["support_judgment_sha256"] for claim in draft_payload["claims"])
        assert all(
            claim["support_judgment_sha256"] == payload_sha256(claim["support_judgment"])
            for claim in draft_payload["claims"]
        )
        assert draft_payload["claim_support_summary"]["claims_with_support_judgment_count"] == len(
            draft_payload["claims"]
        )
        assert all(
            {
                "semantic_ontology_snapshot_ids",
                "semantic_graph_snapshot_ids",
                "retrieval_reranker_artifact_ids",
                "release_audit_bundle_ids",
                "release_validation_receipt_ids",
            }.issubset(claim["provenance_lock"])
            for claim in draft_payload["claims"]
        )
        assert draft_payload["provenance_lock_summary"]["claims_with_provenance_lock_count"] == len(
            draft_payload["claims"]
        )
        assert draft_payload["provenance_lock_summary"][
            "source_search_request_result_id_count"
        ] >= len(draft_payload["claims"])
        cited_card_ids = {
            card_id for claim in draft_payload["claims"] for card_id in claim["evidence_card_ids"]
        }
        cited_source_cards = [
            card
            for card in draft_payload["evidence_cards"]
            if card["evidence_card_id"] in cited_card_ids
            and card["evidence_kind"] in {"source_evidence", "semantic_fact"}
        ]
        assert cited_source_cards
        assert all(
            card["source_evidence_match_status"] in {"matched_source_record", "matched_page_span"}
            for card in cited_source_cards
        )
        assert all(card["source_evidence_match_keys"] for card in cited_source_cards)
        assert all(
            claim["source_evidence_match_status"] in {"matched_source_record", "matched_page_span"}
            for claim in draft_payload["claims"]
        )

        draft_operator_rows = list(
            session.scalars(
                select(KnowledgeOperatorRun)
                .where(KnowledgeOperatorRun.agent_task_id == scenario["draft_task_id"])
                .order_by(KnowledgeOperatorRun.created_at.asc())
            )
        )
        assert [row.operator_kind for row in draft_operator_rows] == ["judge", "generate"]
        assert draft_operator_rows[0].operator_name == "technical_report_claim_support_judge"

        export_rows = list(
            session.scalars(
                select(EvidencePackageExport).where(
                    EvidencePackageExport.agent_task_id == scenario["draft_task_id"]
                )
            )
        )
        assert [row.package_kind for row in export_rows] == ["technical_report_claims"]
        assert export_rows[0].package_sha256 == draft_payload["evidence_package_sha256"]

        derivation_rows = list(
            session.scalars(
                select(ClaimEvidenceDerivation).where(
                    ClaimEvidenceDerivation.evidence_package_export_id == export_rows[0].id
                )
            )
        )
        assert len(derivation_rows) == len(draft_payload["claims"])
        assert all(row.derivation_sha256 for row in derivation_rows)
        assert all(row.provenance_lock_sha256 for row in derivation_rows)
        assert all(row.support_verdict == "supported" for row in derivation_rows)
        assert all(
            row.support_score is not None and row.support_score >= 0.34 for row in derivation_rows
        )
        assert all(row.support_judge_run_id for row in derivation_rows)
        assert all(row.support_judgment_sha256 for row in derivation_rows)
        assert all(row.source_search_request_result_ids_json for row in derivation_rows)
        assert all(
            row.provenance_lock_sha256 == payload_sha256(row.provenance_lock_json)
            for row in derivation_rows
        )
        assert all(
            row.support_judgment_sha256 == payload_sha256(row.support_judgment_json)
            for row in derivation_rows
        )

        verify_task_row = session.get(AgentTask, scenario["verify_task_id"])
        assert verify_task_row is not None
        verification = verify_task_row.result_json["payload"]["verification"]
        assert verification["outcome"] == "passed"
        metric_keys = [
            "context_ref_count",
            "unsupported_claim_count",
            "missing_derivation_hash_count",
            "missing_provenance_lock_count",
            "missing_evidence_package_hash_count",
            "evidence_package_integrity_mismatch_count",
            "derivation_integrity_mismatch_count",
            "provenance_lock_integrity_mismatch_count",
            "provenance_lock_contract_mismatch_count",
            "missing_support_judgment_count",
            "support_judgment_integrity_mismatch_count",
            "support_judgment_contract_mismatch_count",
            "unsupported_support_judgment_count",
            "claim_support_score_below_threshold_count",
            "claims_missing_source_search_request_result_count",
            "source_evidence_package_trace_incomplete_count",
            "cited_cards_without_acceptable_source_evidence_match_count",
            "cited_cards_without_recomputed_source_coverage_count",
            "cited_cards_with_expected_record_without_recomputed_record_match_count",
            "reported_recomputed_match_mismatch_count",
            "cited_cards_with_document_run_fallback_match_count",
        ]
        assert verification["metrics"]["context_ref_count"] >= 1
        assert verification["metrics"]["source_evidence_closure_complete"] is True
        assert verification["metrics"]["source_record_recall"] == 1.0
        assert all(
            verification["metrics"][metric] == 0
            for metric in metric_keys
            if metric != "context_ref_count"
        )

        verify_operator_rows = list(
            session.scalars(
                select(KnowledgeOperatorRun).where(
                    KnowledgeOperatorRun.agent_task_id == scenario["verify_task_id"]
                )
            )
        )
        assert [row.operator_kind for row in verify_operator_rows] == ["verify"]
        assert verify_operator_rows[0].output_sha256

        manifest_rows = list(
            session.scalars(
                select(EvidenceManifest).where(
                    EvidenceManifest.verification_task_id == scenario["verify_task_id"]
                )
            )
        )
        assert len(manifest_rows) == 1
        assert manifest_rows[0].manifest_kind == "technical_report_court_evidence"
        assert manifest_rows[0].manifest_sha256
        assert manifest_rows[0].document_ids_json == [str(scenario["document_id"])]
        assert manifest_rows[0].run_ids_json == [str(scenario["run_id"])]
        assert manifest_rows[0].manifest_payload_json["audit_checklist"]["complete"] is True
        assert (
            manifest_rows[0].manifest_payload_json["audit_checklist"]["hash_integrity_verified"]
            is True
        )

        prov_artifact = session.scalars(
            select(AgentTaskArtifact).where(
                AgentTaskArtifact.task_id == scenario["verify_task_id"],
                AgentTaskArtifact.artifact_kind == "technical_report_prov_export",
            )
        ).one()
        assert prov_artifact.storage_path is not None
        stored_prov_export = json.loads(Path(prov_artifact.storage_path).read_text())
        assert stored_prov_export == prov_artifact.payload_json
        assert stored_prov_export["schema_name"] == "technical_report_prov_export"
        assert stored_prov_export["frozen_export"]["artifact_id"] == str(prov_artifact.id)
        assert stored_prov_export["frozen_export"]["storage_path"] == prov_artifact.storage_path
        assert stored_prov_export["frozen_export"]["export_payload_sha256"]
        receipt = stored_prov_export["frozen_export"]["export_receipt"]
        assert receipt["schema_name"] == "technical_report_prov_export_receipt"
        assert receipt["hash_chain_complete"] is True
        assert receipt["signature_status"] == "signed"
        assert receipt["signature_algorithm"] == "hmac-sha256"
        assert receipt["signing_key_id"] == "technical-report-key"
        assert receipt["receipt_sha256"]
        assert receipt["signature"]

        governance_events = list(
            session.scalars(
                select(SemanticGovernanceEvent).where(
                    SemanticGovernanceEvent.agent_task_artifact_id == prov_artifact.id
                )
            )
        )
        governance_events_by_kind = {row.event_kind: row for row in governance_events}
        assert set(governance_events_by_kind) == {
            "technical_report_prov_export_frozen",
            "technical_report_readiness_db_gate_recorded",
            "technical_report_claim_retrieval_feedback_recorded",
        }
        assert (
            governance_events_by_kind["technical_report_prov_export_frozen"].event_payload_json[
                "change_impact"
            ]["impacted"]
            is False
        )
        assert (
            governance_events_by_kind["technical_report_prov_export_frozen"].receipt_sha256
            == receipt["receipt_sha256"]
        )

        db_gate = session.scalars(
            select(TechnicalReportReleaseReadinessDbGate).where(
                TechnicalReportReleaseReadinessDbGate.technical_report_verification_task_id
                == scenario["verify_task_id"]
            )
        ).one()
        release_readiness_db_gate_id = db_gate.id
        release_readiness_db_gate_payload_sha256 = db_gate.gate_payload_sha256
        assert db_gate.source_verification_task_id == scenario["context_pack_eval_task_id"]
        assert db_gate.evidence_manifest_id == manifest_rows[0].id
        assert db_gate.prov_export_artifact_id == prov_artifact.id
        assert db_gate.semantic_governance_event_id is not None
        assert db_gate.complete is True
        assert db_gate.coverage_complete is True
        assert db_gate.failure_count == 0
        assert db_gate.source_search_request_ids_json == db_gate.verified_request_ids_json
        assert db_gate.missing_expected_request_ids_json == []
        assert db_gate.unexpected_verified_request_ids_json == []
        assert db_gate.gate_payload_json["complete"] is True
        gate_event = session.get(SemanticGovernanceEvent, db_gate.semantic_governance_event_id)
        assert gate_event is not None
        assert gate_event.event_kind == "technical_report_readiness_db_gate_recorded"
        assert gate_event.subject_table == "technical_report_release_readiness_db_gates"
        assert gate_event.subject_id == db_gate.id
        assert gate_event.evidence_manifest_id == manifest_rows[0].id
        assert gate_event.agent_task_artifact_id == prov_artifact.id

    verify_context_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/context")
    assert verify_context_response.status_code == 200
    assert verify_context_response.json()["summary"]["verification_state"] == "passed"

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
        manifest["report_trace"]["evidence_package_integrity"]["draft_package_hash_matches"] is True
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
    assert manifest_gate_record["gate_id"] == str(release_readiness_db_gate_id)
    assert manifest_gate_record["gate_payload_sha256"] == release_readiness_db_gate_payload_sha256
    assert "prov_export_artifact_id" not in manifest_gate_record
    assert "semantic_governance_event_id" not in manifest_gate_record
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
        and edge["to"]["id"] == str(release_readiness_db_gate_id)
        for edge in manifest["provenance_edges"]
    )
    assert manifest["manifest_integrity"]["complete"] is True
    assert manifest["manifest_integrity"]["stored_payload_hash_matches"] is True
    assert manifest["manifest_integrity"]["recomputed_manifest_hash_matches"] is True
    assert manifest["manifest_integrity"]["stored_payload_matches_recomputed"] is True

    with postgres_integration_harness.session_factory() as session:
        feedback_rows = list(
            session.scalars(
                select(TechnicalReportClaimRetrievalFeedback).where(
                    TechnicalReportClaimRetrievalFeedback.technical_report_verification_task_id
                    == scenario["verify_task_id"]
                )
            )
        )
        assert len(feedback_rows) == len(draft_payload["claims"])
        assert all(row.feedback_payload_sha256 for row in feedback_rows)
        assert all(row.source_payload_sha256 for row in feedback_rows)
        assert all(row.evidence_manifest_id for row in feedback_rows)
        assert all(row.semantic_governance_event_id for row in feedback_rows)


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
