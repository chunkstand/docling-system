from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact, KnowledgeOperatorRun
from app.db.public.audit_and_evidence import (
    ClaimEvidenceDerivation,
    EvidenceManifest,
    EvidencePackageExport,
    TechnicalReportReleaseReadinessDbGate,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.evidence import payload_sha256
from tests.integration.technical_report_harness_support import run_verified_report_roundtrip

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_verified_report_persists_release_readiness_lineage_artifacts(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    scenario = run_verified_report_roundtrip(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
    context_pack_eval_context = scenario["client"].get(
        f"/agent-tasks/{scenario['context_pack_eval_task_id']}/context"
    ).json()
    context_pack_sha256 = context_pack_eval_context["output"]["context_pack"]["context_pack_sha256"]

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
