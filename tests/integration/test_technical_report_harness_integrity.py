from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest
from sqlalchemy import delete, select, text, update

from app.db.public.agent_tasks import AgentTaskArtifact, AgentTaskArtifactImmutabilityEvent
from app.db.public.audit_and_evidence import (
    EvidenceManifest,
    EvidenceTraceEdge,
    EvidenceTraceNode,
    TechnicalReportReleaseReadinessDbGate,
)
from tests.integration.technical_report_harness_support import (
    _load_revision_0044,
    run_verified_report_roundtrip,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_technical_report_provenance_and_trace_integrity_surfaces(
    postgres_integration_harness,
    postgres_schema_engine,
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
    context_pack_release_readiness_db_summary = context_pack_eval_context["output"]["evaluation"][
        "trace"
    ]["release_readiness_db_summary"]
    manifest = client.get(f"/agent-tasks/{scenario['verify_task_id']}/evidence-manifest").json()
    trace_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/evidence-trace")
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
    assert {
        "source_document",
        "document_run",
        "semantic_assertion_evidence",
        "evidence_card",
        "technical_report_claim",
        "claim_provenance_lock",
        "claim_support_judgment",
        "claim_derivation",
        "claim_retrieval_feedback",
        "search_result",
        "operator_run",
        "verification_record",
        "agent_task_artifact",
        "context_pack_evaluation_task",
        "release_readiness_assessment",
        "release_readiness_db_gate",
        "evidence_manifest",
    }.issubset({node["node_kind"] for node in trace["nodes"]})

    with postgres_integration_harness.session_factory() as session:
        prov_artifact = session.scalars(
            select(AgentTaskArtifact).where(
                AgentTaskArtifact.task_id == scenario["verify_task_id"],
                AgentTaskArtifact.artifact_kind == "technical_report_prov_export",
            )
        ).one()
        release_readiness_db_gate = session.scalars(
            select(TechnicalReportReleaseReadinessDbGate).where(
                TechnicalReportReleaseReadinessDbGate.technical_report_verification_task_id
                == scenario["verify_task_id"]
            )
        ).one()
        prov_artifact_id = prov_artifact.id
        release_readiness_db_gate_id = release_readiness_db_gate.id
        release_readiness_db_gate_payload_sha256 = release_readiness_db_gate.gate_payload_sha256

    provenance_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/provenance")
    assert provenance_response.status_code == 200
    provenance = provenance_response.json()
    assert provenance["schema_name"] == "technical_report_prov_export"
    assert provenance["prefix"]["prov"] == "http://www.w3.org/ns/prov#"
    assert provenance["prov_summary"]["source_record_recall"] == 1.0
    assert provenance["prov_summary"]["release_readiness_db_gate_complete"] is True
    assert provenance["prov_summary"]["release_readiness_db_gate_failure_count"] == 0
    assert (
        provenance["prov_summary"]["release_readiness_db_verified_request_count"]
        == context_pack_release_readiness_db_summary["verified_request_count"]
    )
    assert (
        provenance["prov_summary"]["release_readiness_db_source_search_request_count"]
        == context_pack_release_readiness_db_summary["source_search_request_count"]
    )
    assert provenance["retrieval_evaluation"]["complete"] is True
    assert provenance["retrieval_evaluation"]["source_record_recall"] == 1.0
    assert provenance["audit"]["release_readiness_db_gate"]["complete"] is True
    assert provenance["audit"]["release_readiness_db_gate"]["gate_id"] == str(
        release_readiness_db_gate_id
    )
    assert provenance["prov_integrity"]["complete"] is True
    assert provenance["prov_integrity"]["hash_policy"] == (
        "sha256 over canonical JSON excluding frozen_export and prov_integrity"
    )
    assert "prov_integrity" not in provenance["prov_integrity"]["hash_basis_fields"]
    assert "frozen_export" not in provenance["prov_integrity"]["hash_basis_fields"]
    assert provenance["prov_integrity"]["prov_sha256"]
    assert provenance["frozen_export"]["artifact_id"] == str(prov_artifact_id)
    assert provenance["frozen_export"]["artifact_kind"] == "technical_report_prov_export"
    assert provenance["frozen_export"]["export_payload_sha256"]
    assert provenance["frozen_export"]["export_receipt"]["signature_status"] == "signed"
    assert provenance["frozen_export"]["export_receipt"]["hash_chain_complete"] is True
    assert provenance["prov_integrity"]["all_relation_references_declared"] is True
    assert provenance["prov_integrity"]["missing_relation_reference_count"] == 0
    assert (
        provenance["prov_integrity"]["relation_count"]
        == provenance["prov_summary"]["relation_count"]
    )
    assert provenance["entity"]
    assert provenance["activity"]
    assert provenance["agent"]["docling:agent/technical-report-gate"]["prov:type"] == (
        "prov:SoftwareAgent"
    )
    assert provenance["agent"]["docling:agent/context-pack-gate"]["prov:type"] == (
        "prov:SoftwareAgent"
    )
    assert any(
        entity.get("prov:type") == "docling:DocumentGenerationContextPack"
        for entity in provenance["entity"].values()
    )
    assert any(
        entity.get("prov:type") == "docling:SearchHarnessReleaseReadinessAssessment"
        and entity.get("docling:assessment_payload_sha256")
        == scenario["release_readiness_assessment"]["assessment_payload_sha256"]
        for entity in provenance["entity"].values()
    )
    assert any(
        entity.get("prov:type") == "docling:ReleaseReadinessDbGate"
        and entity.get("docling:complete") is True
        and entity.get("docling:failure_count") == 0
        and entity.get("docling:gate_id") == str(release_readiness_db_gate_id)
        and entity.get("docling:gate_payload_sha256") == release_readiness_db_gate_payload_sha256
        for entity in provenance["entity"].values()
    )
    assert any(
        entity.get("prov:type") == "docling:ClaimRetrievalFeedback"
        and entity.get("docling:learning_label") == "positive"
        and entity.get("docling:feedback_payload_sha256")
        for entity in provenance["entity"].values()
    )
    assert any(
        activity.get("prov:type") == "docling:ContextPackEvaluationTask"
        for activity in provenance["activity"].values()
    )
    assert provenance["wasDerivedFrom"]
    assert provenance["used"]

    artifact_response = client.get(
        f"/agent-tasks/{scenario['verify_task_id']}/artifacts/{prov_artifact_id}"
    )
    assert artifact_response.status_code == 200
    assert artifact_response.json()["frozen_export"]["artifact_id"] == str(prov_artifact_id)
    prov_storage_path = Path(provenance["frozen_export"]["storage_path"])
    original_prov_file = prov_storage_path.read_text()
    try:
        prov_storage_path.write_text(json.dumps({**provenance, "tampered": True}))
        tampered_artifact_response = client.get(
            f"/agent-tasks/{scenario['verify_task_id']}/artifacts/{prov_artifact_id}"
        )
        assert tampered_artifact_response.status_code == 409
        assert (
            tampered_artifact_response.json()["error_code"]
            == "agent_task_artifact_integrity_mismatch"
        )
    finally:
        prov_storage_path.write_text(original_prov_file)

    second_provenance_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/provenance")
    assert second_provenance_response.status_code == 200
    assert second_provenance_response.json()["frozen_export"]["artifact_id"] == str(
        prov_artifact_id
    )

    with postgres_integration_harness.session_factory() as session:
        immutability_events = list(
            session.scalars(
                select(AgentTaskArtifactImmutabilityEvent)
                .where(AgentTaskArtifactImmutabilityEvent.artifact_id == prov_artifact_id)
                .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
            )
        )
        assert [row.mutation_operation for row in immutability_events] == ["FREEZE_REUSE"]
        assert immutability_events[0].event_kind == "supersession_attempt"
        assert immutability_events[0].attempted_payload_sha256 is not None

    with postgres_integration_harness.session_factory() as session:
        prov_artifact_count = len(
            list(
                session.scalars(
                    select(AgentTaskArtifact).where(
                        AgentTaskArtifact.task_id == scenario["verify_task_id"],
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
            text(revision_0044.PREVENT_FROZEN_AGENT_TASK_ARTIFACT_MUTATION_FUNCTION_SQL)
        )
        session.execute(text(revision_0044.PREVENT_FROZEN_AGENT_TASK_ARTIFACT_MUTATION_TRIGGER_SQL))
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
        assert prov_artifact.payload_json["frozen_export"]["artifact_id"] == str(prov_artifact_id)
        mutation_events = list(
            session.scalars(
                select(AgentTaskArtifactImmutabilityEvent)
                .where(AgentTaskArtifactImmutabilityEvent.artifact_id == prov_artifact_id)
                .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
            )
        )
        assert [row.mutation_operation for row in mutation_events] == ["FREEZE_REUSE", "UPDATE"]
        assert mutation_events[0].event_kind == "supersession_attempt"
        assert mutation_events[0].attempted_payload_sha256 is not None
        assert mutation_events[1].event_kind == "mutation_blocked"
        assert mutation_events[1].attempted_payload_sha256 is None

    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(delete(AgentTaskArtifact).where(AgentTaskArtifact.id == prov_artifact_id))
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
        assert [row.mutation_operation for row in mutation_events] == [
            "FREEZE_REUSE",
            "UPDATE",
            "DELETE",
        ]

    with postgres_integration_harness.session_factory() as session:
        manifest_row = session.scalar(
            select(EvidenceManifest).where(
                EvidenceManifest.verification_task_id == scenario["verify_task_id"]
            )
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

    legacy_trace_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/evidence-trace")
    assert legacy_trace_response.status_code == 200
    legacy_trace = legacy_trace_response.json()
    assert legacy_trace["trace_sha256"] == trace["trace_sha256"]
    assert legacy_trace["trace_integrity"]["complete"] is True

    with postgres_integration_harness.session_factory() as session:
        manifest_row = session.scalar(
            select(EvidenceManifest).where(
                EvidenceManifest.verification_task_id == scenario["verify_task_id"]
            )
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
            select(EvidenceManifest).where(
                EvidenceManifest.verification_task_id == scenario["verify_task_id"]
            )
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
        tampered_payload = deepcopy(tampered_node.payload_json)
        tampered_payload["sha256"] = "tampered-trace-source-checksum"
        tampered_node.payload_json = tampered_payload
        session.commit()

    tampered_trace_response = client.get(
        f"/agent-tasks/{scenario['verify_task_id']}/evidence-trace"
    )
    assert tampered_trace_response.status_code == 200
    tampered_trace = tampered_trace_response.json()
    assert tampered_trace["trace_integrity"]["complete"] is False
    assert tampered_trace["trace_integrity"]["node_payload_hash_mismatch_count"] == 1
    assert tampered_trace["trace_integrity"]["persisted_trace_hash_matches"] is False
    assert tampered_trace["trace_integrity"]["recomputed_trace_hash_matches"] is True
    assert tampered_trace["trace_integrity"]["persisted_trace_matches_recomputed"] is False

    with postgres_integration_harness.session_factory() as session:
        manifest_row = session.scalar(
            select(EvidenceManifest).where(
                EvidenceManifest.verification_task_id == scenario["verify_task_id"]
            )
        )
        assert manifest_row is not None
        tampered_manifest_payload = deepcopy(manifest_row.manifest_payload_json)
        tampered_manifest_payload["source_documents"][0]["sha256"] = "tampered-source-checksum"
        manifest_row.manifest_payload_json = tampered_manifest_payload
        session.commit()

    tampered_manifest_response = client.get(
        f"/agent-tasks/{scenario['verify_task_id']}/evidence-manifest"
    )
    assert tampered_manifest_response.status_code == 200
    tampered_manifest = tampered_manifest_response.json()
    assert tampered_manifest["source_documents"][0]["sha256"] == "tampered-source-checksum"
    assert tampered_manifest["manifest_integrity"]["complete"] is False
    assert tampered_manifest["manifest_integrity"]["stored_payload_hash_matches"] is False
    assert tampered_manifest["manifest_integrity"]["recomputed_manifest_hash_matches"] is True
    assert tampered_manifest["manifest_integrity"]["stored_payload_matches_recomputed"] is False
