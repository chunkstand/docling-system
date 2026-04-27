from __future__ import annotations

import importlib.util
import json
import os
from copy import deepcopy
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select, text, update

from app.core.config import get_settings
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    ClaimEvidenceDerivation,
    EvidenceManifest,
    EvidencePackageExport,
    EvidenceTraceEdge,
    EvidenceTraceNode,
    KnowledgeOperatorRun,
)
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import create_agent_task
from app.services.semantic_registry import clear_semantic_registry_cache
from tests.integration.pdf_fixtures import valid_test_pdf_bytes
from tests.integration.test_semantic_generation_roundtrip import (
    StubParser,
    _build_parsed_document,
    _write_registry,
    _write_semantic_eval_corpus,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def _load_revision_0044():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0044_prov_artifact_immutability.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0044_prov_artifact_immutability", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0044 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _process_next_task(postgres_integration_harness) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "technical-report-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id


def test_technical_report_harness_roundtrip(
    postgres_integration_harness,
    postgres_schema_engine,
    monkeypatch,
    tmp_path,
):
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    eval_corpus_path = tmp_path / "docs" / "semantic_evaluation_corpus.yaml"
    _write_registry(registry_path)
    _write_semantic_eval_corpus(eval_corpus_path)
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH", str(eval_corpus_path))
    monkeypatch.setenv("DOCLING_SYSTEM_AUDIT_BUNDLE_SIGNING_KEY", "technical-report-secret")
    monkeypatch.setenv("DOCLING_SYSTEM_AUDIT_BUNDLE_SIGNING_KEY_ID", "technical-report-key")
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    client = postgres_integration_harness.client
    create_response = client.post(
        "/documents",
        files={
            "file": (
                "integration-guardrail-report.pdf",
                valid_test_pdf_bytes(),
                "application/pdf",
            )
        },
    )
    assert create_response.status_code == 202
    document_id = UUID(create_response.json()["document_id"])
    run_id = UUID(create_response.json()["run_id"])
    assert (
        postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))
        == run_id
    )

    workflow_version = "technical_report_harness_integration"
    with postgres_integration_harness.session_factory() as session:
        plan_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="plan_technical_report",
                input={
                    "title": "Integration Governance Technical Report",
                    "goal": "Write a technical report from integration governance evidence.",
                    "audience": "Operators",
                    "document_ids": [str(document_id)],
                    "target_length": "medium",
                    "review_policy": "allow_candidate_with_disclosure",
                },
                workflow_version=workflow_version,
            ),
        )
        plan_task_id = plan_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        evidence_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="build_report_evidence_cards",
                input={"target_task_id": str(plan_task_id)},
                workflow_version=workflow_version,
            ),
        )
        evidence_task_id = evidence_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        harness_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="prepare_report_agent_harness",
                input={"target_task_id": str(evidence_task_id)},
                workflow_version=workflow_version,
            ),
        )
        harness_task_id = harness_task.task_id

    _process_next_task(postgres_integration_harness)

    harness_context_response = client.get(f"/agent-tasks/{harness_task_id}/context")
    assert harness_context_response.status_code == 200
    harness_context = harness_context_response.json()
    assert harness_context["summary"]["next_action"] == (
        "Create draft_technical_report to render a verification-ready report draft."
    )
    harness_output = harness_context["output"]["harness"]
    assert harness_output["workflow_state"]["next_task_type"] == "draft_technical_report"
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
    assert harness_output["llm_adapter_contract"]["harness_context_refs"]

    harness_artifact_ref = next(
        ref for ref in harness_context["refs"] if ref["ref_key"] == "report_agent_harness_artifact"
    )
    artifact_response = client.get(
        f"/agent-tasks/{harness_task_id}/artifacts/{harness_artifact_ref['artifact_id']}"
    )
    assert artifact_response.status_code == 200
    artifact_payload = artifact_response.json()
    assert artifact_payload["schema_name"] == "report_agent_harness"
    assert artifact_payload["verification_gate"]["target_task_type"] == "verify_technical_report"

    with postgres_integration_harness.session_factory() as session:
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_technical_report",
                input={"target_task_id": str(harness_task_id)},
                workflow_version=workflow_version,
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_technical_report",
                input={"target_task_id": str(draft_task_id)},
                workflow_version=workflow_version,
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    prov_artifact_id = None
    prov_artifact_sha256 = None
    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        markdown_path = Path(draft_task_row.result_json["payload"]["draft"]["markdown_path"])
        assert markdown_path.exists()
        assert "Evidence Cards" in markdown_path.read_text()
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        assert draft_payload["evidence_package_sha256"]
        assert draft_payload["evidence_package_export_id"]
        assert draft_payload["source_evidence_package_exports"]
        assert draft_payload["claim_derivations"]
        assert all(claim["derivation_sha256"] for claim in draft_payload["claims"])
        assert all(
            claim["source_evidence_package_export_ids"] for claim in draft_payload["claims"]
        )
        cited_card_ids = {
            card_id
            for claim in draft_payload["claims"]
            for card_id in claim["evidence_card_ids"]
        }
        cited_source_cards = [
            card
            for card in draft_payload["evidence_cards"]
            if card["evidence_card_id"] in cited_card_ids
            and card["evidence_kind"] in {"source_evidence", "semantic_fact"}
        ]
        assert cited_source_cards
        assert all(
            card["source_evidence_match_status"]
            in {"matched_source_record", "matched_page_span"}
            for card in cited_source_cards
        )
        assert all(card["source_evidence_match_keys"] for card in cited_source_cards)
        assert all(
            claim["source_evidence_match_status"]
            in {"matched_source_record", "matched_page_span"}
            for claim in draft_payload["claims"]
        )
        draft_operator_rows = list(
            session.scalars(
                select(KnowledgeOperatorRun).where(
                    KnowledgeOperatorRun.agent_task_id == draft_task_id
                )
            )
        )
        assert [row.operator_kind for row in draft_operator_rows] == ["generate"]
        export_rows = list(
            session.scalars(
                select(EvidencePackageExport).where(
                    EvidencePackageExport.agent_task_id == draft_task_id
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

        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        verification = verify_task_row.result_json["payload"]["verification"]
        assert verification["outcome"] == "passed"
        assert verification["metrics"]["context_ref_count"] >= 1
        assert verification["metrics"]["unsupported_claim_count"] == 0
        assert verification["metrics"]["missing_derivation_hash_count"] == 0
        assert verification["metrics"]["missing_evidence_package_hash_count"] == 0
        assert verification["metrics"]["evidence_package_integrity_mismatch_count"] == 0
        assert verification["metrics"]["derivation_integrity_mismatch_count"] == 0
        assert verification["metrics"]["source_evidence_closure_complete"] is True
        assert verification["metrics"]["source_evidence_package_trace_incomplete_count"] == 0
        assert verification["metrics"]["source_record_recall"] == 1.0
        assert (
            verification["metrics"][
                "cited_cards_without_acceptable_source_evidence_match_count"
            ]
            == 0
        )
        assert (
            verification["metrics"]["cited_cards_without_recomputed_source_coverage_count"]
            == 0
        )
        assert (
            verification["metrics"][
                "cited_cards_with_expected_record_without_recomputed_record_match_count"
            ]
            == 0
        )
        assert verification["metrics"]["reported_recomputed_match_mismatch_count"] == 0
        assert (
            verification["metrics"]["cited_cards_with_document_run_fallback_match_count"]
            == 0
        )
        verify_operator_rows = list(
            session.scalars(
                select(KnowledgeOperatorRun).where(
                    KnowledgeOperatorRun.agent_task_id == verify_task_id
                )
            )
        )
        assert [row.operator_kind for row in verify_operator_rows] == ["verify"]
        assert verify_operator_rows[0].output_sha256
        manifest_rows = list(
            session.scalars(
                select(EvidenceManifest).where(
                    EvidenceManifest.verification_task_id == verify_task_id
                )
            )
        )
        assert len(manifest_rows) == 1
        assert manifest_rows[0].manifest_kind == "technical_report_court_evidence"
        assert manifest_rows[0].manifest_sha256
        assert manifest_rows[0].document_ids_json == [str(document_id)]
        assert manifest_rows[0].run_ids_json == [str(run_id)]
        assert manifest_rows[0].manifest_payload_json["audit_checklist"]["complete"] is True
        assert manifest_rows[0].manifest_payload_json["audit_checklist"][
            "hash_integrity_verified"
        ] is True
        prov_artifacts = list(
            session.scalars(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == verify_task_id,
                    AgentTaskArtifact.artifact_kind == "technical_report_prov_export",
                )
            )
        )
        assert len(prov_artifacts) == 1
        prov_artifact = prov_artifacts[0]
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
        prov_artifact_id = prov_artifact.id
        prov_artifact_sha256 = stored_prov_export["frozen_export"]["export_payload_sha256"]

    verify_context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert verify_context_response.status_code == 200
    assert verify_context_response.json()["summary"]["verification_state"] == "passed"

    audit_response = client.get(f"/agent-tasks/{verify_task_id}/audit-bundle")
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    assert audit_bundle["schema_name"] == "technical_report_audit_bundle"
    assert audit_bundle["audit_checklist"]["has_frozen_evidence_package"] is True
    assert audit_bundle["audit_checklist"]["all_claims_have_derivations"] is True
    assert audit_bundle["audit_checklist"]["hash_integrity_verified"] is True
    assert audit_bundle["audit_checklist"]["has_frozen_source_evidence_packages"] is True
    assert audit_bundle["audit_checklist"]["has_frozen_prov_export"] is True
    assert audit_bundle["audit_checklist"]["has_prov_export_receipt"] is True
    assert audit_bundle["audit_checklist"]["has_signed_prov_export_receipt"] is True
    assert audit_bundle["audit_checklist"][
        "prov_export_receipts_integrity_verified"
    ] is True
    assert audit_bundle["audit_checklist"][
        "prov_export_receipt_signature_verified"
    ] is True
    assert audit_bundle["audit_checklist"]["no_prov_export_immutability_events"] is True
    assert audit_bundle["audit_checklist"]["source_evidence_trace_integrity_verified"] is True
    assert audit_bundle["audit_checklist"]["generation_evidence_closed"] is True
    assert audit_bundle["audit_checklist"]["has_generation_operator_run"] is True
    assert audit_bundle["audit_checklist"]["has_verification_operator_run"] is True
    assert audit_bundle["audit_checklist"]["verification_passed"] is True
    assert audit_bundle["audit_checklist"]["change_impact_clear"] is True
    assert audit_bundle["integrity"]["draft_package_hash_matches"] is True
    assert audit_bundle["integrity"]["export_package_hash_matches"] is True
    assert audit_bundle["integrity"]["claim_derivation_count_matches"] is True
    assert audit_bundle["integrity"]["claim_derivation_hash_mismatch_count"] == 0
    assert audit_bundle["integrity"]["claim_package_hash_mismatch_count"] == 0
    report_export = next(
        row
        for row in audit_bundle["evidence_package_exports"]
        if row["package_kind"] == "technical_report_claims"
    )
    search_exports = [
        row
        for row in audit_bundle["evidence_package_exports"]
        if row["package_kind"] == "search_request"
    ]
    assert report_export["package_sha256"] == draft_payload["evidence_package_sha256"]
    assert search_exports
    search_export_id = UUID(search_exports[0]["evidence_package_export_id"])
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
        row["artifact_kind"] == "technical_report_prov_export"
        for row in audit_bundle["artifacts"]
    )
    assert len(audit_bundle["provenance_export_receipts"]) == 1
    assert audit_bundle["provenance_export_receipts"][0]["export_receipt"][
        "signature_status"
    ] == "signed"
    assert audit_bundle["provenance_export_receipts"][0]["receipt_integrity"][
        "complete"
    ] is True
    assert audit_bundle["provenance_export_receipts"][0]["receipt_integrity"][
        "signature_verification_status"
    ] == "verified"
    assert audit_bundle["provenance_export_immutability_events"] == []
    assert all(
        row["trace_integrity"]["complete"]
        for row in audit_bundle["search_evidence_package_traces"]
    )
    assert len(audit_bundle["claim_derivations"]) == len(draft_payload["claims"])
    assert audit_bundle["audit_bundle_sha256"]

    manifest_response = client.get(f"/agent-tasks/{verify_task_id}/evidence-manifest")
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["schema_name"] == "technical_report_evidence_manifest"
    assert manifest["manifest_kind"] == "technical_report_court_evidence"
    assert manifest["manifest_sha256"]
    assert manifest["trace_sha256"]
    assert manifest["audit_checklist"]["complete"] is True
    assert manifest["audit_checklist"]["all_source_documents_hashed"] is True
    assert manifest["audit_checklist"]["all_document_runs_validation_passed"] is True
    assert manifest["audit_checklist"]["hash_integrity_verified"] is True
    assert manifest["source_documents"][0]["sha256"]
    assert manifest["document_runs"][0]["artifact_hashes"]["docling_json_sha256"]
    assert manifest["report_trace"]["evidence_package_integrity"][
        "draft_package_hash_matches"
    ] is True
    assert manifest["report_trace"]["verification"]["outcome"] == "passed"
    assert manifest["retrieval_trace"]["source_evidence_closure"]["complete"] is True
    assert manifest["retrieval_trace"]["source_evidence_closure"]["source_record_recall"] == 1.0
    assert (
        manifest["retrieval_trace"]["source_evidence_closure"][
            "cited_cards_without_acceptable_source_evidence_match_count"
        ]
        == 0
    )
    assert manifest["retrieval_trace"]["search_evidence_package_trace_summaries"]
    assert manifest["provenance_edges"]
    assert manifest["manifest_integrity"]["complete"] is True
    assert manifest["manifest_integrity"]["stored_payload_hash_matches"] is True
    assert manifest["manifest_integrity"]["recomputed_manifest_hash_matches"] is True
    assert manifest["manifest_integrity"]["stored_payload_matches_recomputed"] is True

    trace_response = client.get(f"/agent-tasks/{verify_task_id}/evidence-trace")
    assert trace_response.status_code == 200
    trace = trace_response.json()
    assert trace["schema_name"] == "technical_report_evidence_trace"
    assert trace["manifest_sha256"] == manifest["manifest_sha256"]
    assert trace["trace_sha256"] == manifest["trace_sha256"]
    assert trace["manifest_provenance_edge_count"] == len(manifest["provenance_edges"])
    assert trace["trace_integrity"]["complete"] is True
    assert trace["trace_integrity"]["persisted_trace_hash_matches"] is True
    assert trace["trace_integrity"]["recomputed_trace_hash_matches"] is True
    assert trace["trace_integrity"]["persisted_trace_matches_recomputed"] is True
    assert trace["trace_integrity"]["node_payload_hash_mismatch_count"] == 0
    assert trace["trace_integrity"]["edge_payload_hash_mismatch_count"] == 0
    node_kinds = {node["node_kind"] for node in trace["nodes"]}
    assert {
        "source_document",
        "document_run",
        "semantic_assertion_evidence",
        "evidence_card",
        "technical_report_claim",
        "claim_derivation",
        "operator_run",
        "verification_record",
        "evidence_manifest",
    }.issubset(node_kinds)
    assert any(
        edge["payload"].get("source") == "manifest_provenance_edges"
        for edge in trace["edges"]
    )

    provenance_response = client.get(f"/agent-tasks/{verify_task_id}/provenance")
    assert provenance_response.status_code == 200
    provenance = provenance_response.json()
    assert provenance["schema_name"] == "technical_report_prov_export"
    assert provenance["prefix"]["prov"] == "http://www.w3.org/ns/prov#"
    assert provenance["prov_summary"]["source_record_recall"] == 1.0
    assert provenance["retrieval_evaluation"]["complete"] is True
    assert provenance["retrieval_evaluation"]["source_record_recall"] == 1.0
    assert provenance["prov_integrity"]["complete"] is True
    assert provenance["prov_integrity"]["hash_policy"] == (
        "sha256 over canonical JSON excluding frozen_export and prov_integrity"
    )
    assert "prov_integrity" not in provenance["prov_integrity"]["hash_basis_fields"]
    assert "frozen_export" not in provenance["prov_integrity"]["hash_basis_fields"]
    assert provenance["prov_integrity"]["prov_sha256"]
    assert provenance["frozen_export"]["artifact_id"] == str(prov_artifact_id)
    assert provenance["frozen_export"]["artifact_kind"] == "technical_report_prov_export"
    assert provenance["frozen_export"]["export_payload_sha256"] == prov_artifact_sha256
    assert provenance["frozen_export"]["export_receipt"]["signature_status"] == "signed"
    assert provenance["frozen_export"]["export_receipt"]["hash_chain_complete"] is True
    assert provenance["prov_integrity"]["all_relation_references_declared"] is True
    assert provenance["prov_integrity"]["missing_relation_reference_count"] == 0
    assert provenance["prov_integrity"]["relation_count"] == provenance["prov_summary"][
        "relation_count"
    ]
    assert provenance["entity"]
    assert provenance["activity"]
    assert provenance["agent"]["docling:agent/technical-report-gate"]["prov:type"] == (
        "prov:SoftwareAgent"
    )
    assert provenance["wasDerivedFrom"]
    assert provenance["used"]
    artifact_response = client.get(
        f"/agent-tasks/{verify_task_id}/artifacts/{prov_artifact_id}"
    )
    assert artifact_response.status_code == 200
    assert artifact_response.json()["frozen_export"]["artifact_id"] == str(prov_artifact_id)
    prov_storage_path = Path(provenance["frozen_export"]["storage_path"])
    original_prov_file = prov_storage_path.read_text()
    try:
        prov_storage_path.write_text(json.dumps({**provenance, "tampered": True}))
        tampered_artifact_response = client.get(
            f"/agent-tasks/{verify_task_id}/artifacts/{prov_artifact_id}"
        )
        assert tampered_artifact_response.status_code == 409
        assert (
            tampered_artifact_response.json()["error_code"]
            == "agent_task_artifact_integrity_mismatch"
        )
    finally:
        prov_storage_path.write_text(original_prov_file)

    second_provenance_response = client.get(f"/agent-tasks/{verify_task_id}/provenance")
    assert second_provenance_response.status_code == 200
    assert second_provenance_response.json()["frozen_export"]["artifact_id"] == str(
        prov_artifact_id
    )
    with postgres_integration_harness.session_factory() as session:
        prov_artifact_count = len(
            list(
                session.scalars(
                    select(AgentTaskArtifact).where(
                        AgentTaskArtifact.task_id == verify_task_id,
                        AgentTaskArtifact.artifact_kind == "technical_report_prov_export",
                    )
                )
            )
        )
    assert prov_artifact_count == 1

    revision_0044 = _load_revision_0044()
    _engine, schema_name = postgres_schema_engine
    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(
            text(
                revision_0044.PREVENT_FROZEN_AGENT_TASK_ARTIFACT_MUTATION_FUNCTION_SQL
            )
        )
        session.execute(
            text(
                revision_0044.PREVENT_FROZEN_AGENT_TASK_ARTIFACT_MUTATION_TRIGGER_SQL
            )
        )
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(
            update(AgentTaskArtifact)
            .where(AgentTaskArtifact.id == prov_artifact_id)
            .values(payload_json={"tampered": True})
        )
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        prov_artifact = session.get(AgentTaskArtifact, prov_artifact_id)
        assert prov_artifact is not None
        assert prov_artifact.payload_json["frozen_export"]["artifact_id"] == str(
            prov_artifact_id
        )
        mutation_events = list(
            session.scalars(
                select(AgentTaskArtifactImmutabilityEvent).where(
                    AgentTaskArtifactImmutabilityEvent.artifact_id == prov_artifact_id
                )
            )
        )
        assert len(mutation_events) == 1
        assert mutation_events[0].event_kind == "mutation_blocked"
        assert mutation_events[0].mutation_operation == "UPDATE"
        assert mutation_events[0].attempted_payload_sha256 is None

    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(
            delete(AgentTaskArtifact).where(AgentTaskArtifact.id == prov_artifact_id)
        )
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        assert session.get(AgentTaskArtifact, prov_artifact_id) is not None
        mutation_events = list(
            session.scalars(
                select(AgentTaskArtifactImmutabilityEvent)
                .where(AgentTaskArtifactImmutabilityEvent.artifact_id == prov_artifact_id)
                .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
            )
        )
        assert [row.mutation_operation for row in mutation_events] == ["UPDATE", "DELETE"]

    with postgres_integration_harness.session_factory() as session:
        manifest_row = session.scalar(
            select(EvidenceManifest).where(EvidenceManifest.verification_task_id == verify_task_id)
        )
        assert manifest_row is not None
        session.execute(
            delete(EvidenceTraceEdge).where(
                EvidenceTraceEdge.evidence_manifest_id == manifest_row.id
            )
        )
        session.execute(
            delete(EvidenceTraceNode).where(
                EvidenceTraceNode.evidence_manifest_id == manifest_row.id
            )
        )
        manifest_row.trace_sha256 = None
        session.commit()

    legacy_trace_response = client.get(f"/agent-tasks/{verify_task_id}/evidence-trace")
    assert legacy_trace_response.status_code == 200
    legacy_trace = legacy_trace_response.json()
    assert legacy_trace["trace_sha256"] == trace["trace_sha256"]
    assert legacy_trace["trace_integrity"]["complete"] is True

    with postgres_integration_harness.session_factory() as session:
        manifest_row = session.scalar(
            select(EvidenceManifest).where(EvidenceManifest.verification_task_id == verify_task_id)
        )
        assert manifest_row is not None
        assert manifest_row.trace_sha256 == trace["trace_sha256"]
        assert (
            session.scalar(
                select(EvidenceTraceNode).where(
                    EvidenceTraceNode.evidence_manifest_id == manifest_row.id
                )
            )
            is not None
        )
        assert (
            session.scalar(
                select(EvidenceTraceEdge).where(
                    EvidenceTraceEdge.evidence_manifest_id == manifest_row.id
                )
            )
            is not None
        )

    with postgres_integration_harness.session_factory() as session:
        manifest_row = session.scalar(
            select(EvidenceManifest).where(EvidenceManifest.verification_task_id == verify_task_id)
        )
        assert manifest_row is not None
        trace_nodes = list(
            session.scalars(
                select(EvidenceTraceNode).where(
                    EvidenceTraceNode.evidence_manifest_id == manifest_row.id
                )
            )
        )
        trace_edges = list(
            session.scalars(
                select(EvidenceTraceEdge).where(
                    EvidenceTraceEdge.evidence_manifest_id == manifest_row.id
                )
            )
        )
        assert len(trace_nodes) == trace["node_count"]
        assert len(trace_edges) == trace["edge_count"]
        assert sum(
            1
            for edge in trace_edges
            if (edge.payload_json or {}).get("source") == "manifest_provenance_edges"
        ) == len(manifest["provenance_edges"])
        tampered_node = next(node for node in trace_nodes if node.node_kind == "source_document")
        tampered_trace_payload = deepcopy(tampered_node.payload_json)
        tampered_trace_payload["sha256"] = "tampered-trace-source-checksum"
        tampered_node.payload_json = tampered_trace_payload
        session.commit()

    tampered_trace_response = client.get(f"/agent-tasks/{verify_task_id}/evidence-trace")
    assert tampered_trace_response.status_code == 200
    tampered_trace = tampered_trace_response.json()
    assert tampered_trace["trace_integrity"]["complete"] is False
    assert tampered_trace["trace_integrity"]["node_payload_hash_mismatch_count"] == 1
    assert tampered_trace["trace_integrity"]["persisted_trace_hash_matches"] is False
    assert tampered_trace["trace_integrity"]["recomputed_trace_hash_matches"] is True
    assert tampered_trace["trace_integrity"]["persisted_trace_matches_recomputed"] is False

    with postgres_integration_harness.session_factory() as session:
        manifest_row = session.scalar(
            select(EvidenceManifest).where(EvidenceManifest.verification_task_id == verify_task_id)
        )
        assert manifest_row is not None
        tampered_payload = deepcopy(manifest_row.manifest_payload_json)
        tampered_payload["source_documents"][0]["sha256"] = "tampered-source-checksum"
        manifest_row.manifest_payload_json = tampered_payload
        session.commit()

    tampered_manifest_response = client.get(f"/agent-tasks/{verify_task_id}/evidence-manifest")
    assert tampered_manifest_response.status_code == 200
    tampered_manifest = tampered_manifest_response.json()
    assert tampered_manifest["source_documents"][0]["sha256"] == "tampered-source-checksum"
    assert tampered_manifest["manifest_integrity"]["complete"] is False
    assert tampered_manifest["manifest_integrity"]["stored_payload_hash_matches"] is False
    assert tampered_manifest["manifest_integrity"]["recomputed_manifest_hash_matches"] is True
    assert tampered_manifest["manifest_integrity"]["stored_payload_matches_recomputed"] is False

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        original_draft_result = deepcopy(draft_task_row.result_json)
        draft_context_row = session.scalar(
            select(AgentTaskArtifact)
            .where(
                AgentTaskArtifact.task_id == draft_task_id,
                AgentTaskArtifact.artifact_kind == "context",
            )
            .order_by(AgentTaskArtifact.created_at.desc())
            .limit(1)
        )
        assert draft_context_row is not None
        original_draft_context = deepcopy(draft_context_row.payload_json)
        uncovered_context = deepcopy(original_draft_context)
        uncovered_draft = uncovered_context["output"]["draft"]
        uncovered_card = next(
            card
            for card in uncovered_draft["evidence_cards"]
            if card["evidence_kind"] == "source_evidence"
            and card["source_evidence_match_status"] == "matched_source_record"
        )
        bogus_source_id = str(uuid4())
        uncovered_card["source_locator"] = bogus_source_id
        if uncovered_card["source_type"] == "chunk":
            uncovered_card["chunk_id"] = bogus_source_id
        elif uncovered_card["source_type"] == "table":
            uncovered_card["table_id"] = bogus_source_id
        uncovered_card["metadata"]["source_locator"] = bogus_source_id
        uncovered_card["metadata"]["source_record_keys"] = [
            f"source:{uncovered_card['source_type']}:{bogus_source_id}"
        ]
        uncovered_result = deepcopy(original_draft_result)
        uncovered_result["payload"]["draft"] = deepcopy(uncovered_draft)
        draft_task_row.result_json = uncovered_result
        draft_context_row.payload_json = uncovered_context
        uncovered_verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_technical_report",
                input={"target_task_id": str(draft_task_id)},
                workflow_version=workflow_version,
            ),
        )
        uncovered_verify_task_id = uncovered_verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        uncovered_verify_task_row = session.get(AgentTask, uncovered_verify_task_id)
        assert uncovered_verify_task_row is not None
        uncovered_verification = uncovered_verify_task_row.result_json["payload"][
            "verification"
        ]
        assert uncovered_verification["outcome"] == "failed"
        assert uncovered_verification["metrics"]["source_evidence_closure_complete"] is False
        assert (
            uncovered_verification["metrics"][
                "cited_cards_with_expected_record_without_recomputed_record_match_count"
            ]
            == 1
        )
        assert uncovered_verification["metrics"]["reported_recomputed_match_mismatch_count"] == 1
        assert uncovered_verification["metrics"]["source_record_recall"] < 1.0
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        draft_task_row.result_json = original_draft_result
        draft_context_row = session.scalar(
            select(AgentTaskArtifact)
            .where(
                AgentTaskArtifact.task_id == draft_task_id,
                AgentTaskArtifact.artifact_kind == "context",
            )
            .order_by(AgentTaskArtifact.created_at.desc())
            .limit(1)
        )
        assert draft_context_row is not None
        draft_context_row.payload_json = original_draft_context

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        original_draft_result = deepcopy(draft_task_row.result_json)
        draft_context_row = session.scalar(
            select(AgentTaskArtifact)
            .where(
                AgentTaskArtifact.task_id == draft_task_id,
                AgentTaskArtifact.artifact_kind == "context",
            )
            .order_by(AgentTaskArtifact.created_at.desc())
            .limit(1)
        )
        assert draft_context_row is not None
        original_draft_context = deepcopy(draft_context_row.payload_json)
        weak_match_context = deepcopy(original_draft_context)
        weak_draft = weak_match_context["output"]["draft"]
        weak_card = next(
            card
            for card in weak_draft["evidence_cards"]
            if card["evidence_kind"] == "source_evidence"
            and card["source_evidence_match_status"]
            in {"matched_source_record", "matched_page_span"}
        )
        weak_card["source_evidence_match_status"] = "matched_document_run_fallback"
        weak_card["source_evidence_match_keys"] = [
            f"document-run-fallback:{weak_card['document_id']}:{weak_card['run_id']}"
        ]
        for claim in weak_draft["claims"]:
            if weak_card["evidence_card_id"] in claim["evidence_card_ids"]:
                claim["source_evidence_match_status"] = "matched_document_run_fallback"
                claim["source_evidence_match_keys"] = list(
                    weak_card["source_evidence_match_keys"]
                )
        weak_match_result = deepcopy(original_draft_result)
        weak_match_result["payload"]["draft"] = deepcopy(weak_draft)
        draft_task_row.result_json = weak_match_result
        draft_context_row.payload_json = weak_match_context
        weak_match_verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_technical_report",
                input={"target_task_id": str(draft_task_id)},
                workflow_version=workflow_version,
            ),
        )
        weak_match_verify_task_id = weak_match_verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        weak_match_verify_task_row = session.get(AgentTask, weak_match_verify_task_id)
        assert weak_match_verify_task_row is not None
        weak_match_verification = weak_match_verify_task_row.result_json["payload"][
            "verification"
        ]
        assert weak_match_verification["outcome"] == "failed"
        assert (
            weak_match_verification["metrics"]["source_evidence_closure_complete"]
            is False
        )
        assert (
            weak_match_verification["metrics"][
                "cited_cards_without_acceptable_source_evidence_match_count"
            ]
            == 1
        )
        assert any(
            "source-record or page-span coverage" in reason
            for reason in weak_match_verification["reasons"]
        )
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        draft_task_row.result_json = original_draft_result
        draft_context_row = session.scalar(
            select(AgentTaskArtifact)
            .where(
                AgentTaskArtifact.task_id == draft_task_id,
                AgentTaskArtifact.artifact_kind == "context",
            )
            .order_by(AgentTaskArtifact.created_at.desc())
            .limit(1)
        )
        assert draft_context_row is not None
        draft_context_row.payload_json = original_draft_context

    with postgres_integration_harness.session_factory() as session:
        source_trace_node = session.scalar(
            select(EvidenceTraceNode)
            .where(EvidenceTraceNode.evidence_package_export_id == search_export_id)
            .limit(1)
        )
        assert source_trace_node is not None
        tampered_source_payload = deepcopy(source_trace_node.payload_json)
        tampered_source_payload["tampered_for_verification_gate"] = True
        source_trace_node.payload_json = tampered_source_payload
        tampered_verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_technical_report",
                input={"target_task_id": str(draft_task_id)},
                workflow_version=workflow_version,
            ),
        )
        tampered_verify_task_id = tampered_verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        tampered_verify_task_row = session.get(AgentTask, tampered_verify_task_id)
        assert tampered_verify_task_row is not None
        tampered_verification = tampered_verify_task_row.result_json["payload"][
            "verification"
        ]
        assert tampered_verification["outcome"] == "failed"
        assert (
            tampered_verification["metrics"]["source_evidence_closure_complete"]
            is False
        )
        assert (
            tampered_verification["metrics"][
                "source_evidence_package_trace_incomplete_count"
            ]
            == 1
        )
        assert any(
            "frozen search evidence packages" in reason
            for reason in tampered_verification["reasons"]
        )
