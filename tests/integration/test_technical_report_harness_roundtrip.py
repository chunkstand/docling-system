from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import (
    AgentTask,
    ClaimEvidenceDerivation,
    EvidencePackageExport,
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


def _process_next_task(postgres_integration_harness) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "technical-report-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id


def test_technical_report_harness_roundtrip(postgres_integration_harness, monkeypatch, tmp_path):
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    eval_corpus_path = tmp_path / "docs" / "semantic_evaluation_corpus.yaml"
    _write_registry(registry_path)
    _write_semantic_eval_corpus(eval_corpus_path)
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH", str(eval_corpus_path))
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

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        markdown_path = Path(draft_task_row.result_json["payload"]["draft"]["markdown_path"])
        assert markdown_path.exists()
        assert "Evidence Cards" in markdown_path.read_text()
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        assert draft_payload["evidence_package_sha256"]
        assert draft_payload["evidence_package_export_id"]
        assert draft_payload["claim_derivations"]
        assert all(claim["derivation_sha256"] for claim in draft_payload["claims"])
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
        verify_operator_rows = list(
            session.scalars(
                select(KnowledgeOperatorRun).where(
                    KnowledgeOperatorRun.agent_task_id == verify_task_id
                )
            )
        )
        assert [row.operator_kind for row in verify_operator_rows] == ["verify"]
        assert verify_operator_rows[0].output_sha256

    verify_context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert verify_context_response.status_code == 200
    assert verify_context_response.json()["summary"]["verification_state"] == "passed"

    audit_response = client.get(f"/agent-tasks/{verify_task_id}/audit-bundle")
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    assert audit_bundle["schema_name"] == "technical_report_audit_bundle"
    assert audit_bundle["audit_checklist"]["has_frozen_evidence_package"] is True
    assert audit_bundle["audit_checklist"]["all_claims_have_derivations"] is True
    assert audit_bundle["audit_checklist"]["has_generation_operator_run"] is True
    assert audit_bundle["audit_checklist"]["has_verification_operator_run"] is True
    assert audit_bundle["audit_checklist"]["verification_passed"] is True
    assert audit_bundle["audit_checklist"]["change_impact_clear"] is True
    assert audit_bundle["evidence_package_exports"][0]["package_sha256"] == draft_payload[
        "evidence_package_sha256"
    ]
    assert len(audit_bundle["claim_derivations"]) == len(draft_payload["claims"])
    assert audit_bundle["audit_bundle_sha256"]
