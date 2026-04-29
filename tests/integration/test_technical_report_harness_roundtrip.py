from __future__ import annotations

import importlib.util
import json
import os
from copy import deepcopy
from datetime import UTC, datetime, timedelta
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
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchReplayRun,
    SemanticGovernanceEvent,
    TechnicalReportReleaseReadinessDbGate,
)
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import create_agent_task
from app.services.evidence import payload_sha256
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


def _search_replay_run(
    *,
    replay_run_id: UUID,
    harness_name: str,
    now: datetime,
) -> SearchReplayRun:
    return SearchReplayRun(
        id=replay_run_id,
        source_type="evaluation_queries",
        status="completed",
        harness_name=harness_name,
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name=harness_name,
        harness_config_json={},
        query_count=2,
        passed_count=2,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        error_message=None,
        created_at=now,
        completed_at=now + timedelta(seconds=1),
    )


def _create_release_audit_bundle_with_validation(
    postgres_integration_harness,
    release_id: str,
) -> dict:
    audit_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "technical-report-integration"},
    )
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    assert audit_bundle["bundle"]["payload"]["audit_checklist"]["complete"] is True

    validation_receipt = _create_audit_bundle_validation_receipt(
        postgres_integration_harness,
        audit_bundle["bundle_id"],
    )

    return {
        "audit_bundle": audit_bundle,
        "validation_receipt": validation_receipt,
    }


def _create_audit_bundle_validation_receipt(
    postgres_integration_harness,
    audit_bundle_id: str,
) -> dict:
    validation_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{audit_bundle_id}/validation-receipts",
        json={"created_by": "technical-report-integration"},
    )
    assert validation_response.status_code == 200
    validation_receipt = validation_response.json()
    assert validation_receipt["validation_status"] == "passed"
    return validation_receipt


def _create_default_harness_release_with_validation(postgres_integration_harness) -> dict:
    now = datetime.now(UTC)
    evaluation_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()
    with postgres_integration_harness.session_factory() as session:
        session.add_all(
            [
                _search_replay_run(
                    replay_run_id=baseline_replay_run_id,
                    harness_name="default_v1",
                    now=now,
                ),
                _search_replay_run(
                    replay_run_id=candidate_replay_run_id,
                    harness_name="default_v1",
                    now=now,
                ),
                SearchHarnessEvaluation(
                    id=evaluation_id,
                    status="completed",
                    baseline_harness_name="default_v1",
                    candidate_harness_name="default_v1",
                    limit=2,
                    source_types_json=["evaluation_queries"],
                    harness_overrides_json={},
                    total_shared_query_count=2,
                    total_improved_count=0,
                    total_regressed_count=0,
                    total_unchanged_count=2,
                    summary_json={},
                    error_message=None,
                    created_at=now,
                    completed_at=now + timedelta(seconds=2),
                ),
            ]
        )
        session.flush()
        session.add(
            SearchHarnessEvaluationSource(
                id=uuid4(),
                search_harness_evaluation_id=evaluation_id,
                source_index=0,
                source_type="evaluation_queries",
                baseline_replay_run_id=baseline_replay_run_id,
                candidate_replay_run_id=candidate_replay_run_id,
                baseline_status="completed",
                candidate_status="completed",
                baseline_query_count=2,
                candidate_query_count=2,
                baseline_passed_count=2,
                candidate_passed_count=2,
                baseline_zero_result_count=0,
                candidate_zero_result_count=0,
                baseline_table_hit_count=1,
                candidate_table_hit_count=1,
                baseline_top_result_changes=0,
                candidate_top_result_changes=0,
                baseline_mrr=1.0,
                candidate_mrr=1.0,
                baseline_foreign_top_result_count=0,
                candidate_foreign_top_result_count=0,
                acceptance_checks_json={"no_regressions": True},
                shared_query_count=2,
                improved_count=0,
                regressed_count=0,
                unchanged_count=2,
                created_at=now,
            )
        )
        session.commit()

    release_response = postgres_integration_harness.client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "min_total_shared_query_count": 1,
            "requested_by": "technical-report-integration",
            "review_note": "default harness release for document-generation context packs",
        },
    )
    assert release_response.status_code == 200
    release = release_response.json()
    assert release["outcome"] == "passed"

    bundle_fixture = _create_release_audit_bundle_with_validation(
        postgres_integration_harness,
        release["release_id"],
    )

    return {
        "release": release,
        **bundle_fixture,
    }


def _freeze_release_readiness_assessment(postgres_integration_harness, release_id: str) -> dict:
    assessment_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/readiness-assessments",
        json={
            "created_by": "technical-report-integration",
            "review_note": "freeze ready release for document generation",
        },
    )
    assert assessment_response.status_code == 200
    assessment = assessment_response.json()
    assert assessment["ready"] is True
    assert assessment["readiness_status"] == "ready"
    assert assessment["integrity"]["complete"] is True
    return assessment


def _refresh_context_pack_sha256(context_pack: dict) -> None:
    hash_basis = dict(context_pack)
    hash_basis.pop("context_pack_sha256", None)
    context_pack["context_pack_sha256"] = payload_sha256(hash_basis)


def _forge_harness_context_latest_bundle_ref(
    postgres_integration_harness,
    harness_task_id: UUID,
) -> str:
    with postgres_integration_harness.session_factory() as session:
        context_artifact = session.scalars(
            select(AgentTaskArtifact).where(
                AgentTaskArtifact.task_id == harness_task_id,
                AgentTaskArtifact.artifact_kind == "context",
            )
        ).one()
        payload = deepcopy(context_artifact.payload_json or {})
        output = payload["output"]
        forged_bundle_id = str(uuid4())
        source_search_request_id = None
        for context_pack in (
            output["context_pack"],
            output["harness"]["document_generation_context_pack"],
        ):
            readiness_refs = context_pack["audit_refs"]["release_readiness_assessments"]
            assert readiness_refs
            source_search_request_id = readiness_refs[0]["search_request_id"]
            readiness_refs[0]["latest_release_audit_bundle_id"] = forged_bundle_id
            _refresh_context_pack_sha256(context_pack)
        output["harness"]["release_readiness_assessments"][0]["latest_release_audit_bundle_id"] = (
            forged_bundle_id
        )
        context_artifact.payload_json = payload
        session.commit()
        assert source_search_request_id is not None
        return source_search_request_id


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

    release_fixture = _create_default_harness_release_with_validation(postgres_integration_harness)
    release_id = release_fixture["release"]["release_id"]

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
        blocked_harness_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="prepare_report_agent_harness",
                input={"target_task_id": str(evidence_task_id)},
                workflow_version=workflow_version,
            ),
        )
        blocked_harness_task_id = blocked_harness_task.task_id

    _process_next_task(postgres_integration_harness)

    blocked_harness_context_response = client.get(f"/agent-tasks/{blocked_harness_task_id}/context")
    assert blocked_harness_context_response.status_code == 200
    blocked_harness_output = blocked_harness_context_response.json()["output"]["harness"]
    blocked_readiness_refs = blocked_harness_output["document_generation_context_pack"][
        "audit_refs"
    ]["release_readiness_assessments"]
    assert blocked_readiness_refs
    assert {ref["selection_status"] for ref in blocked_readiness_refs} == {"missing_assessment"}

    with postgres_integration_harness.session_factory() as session:
        blocked_context_pack_eval_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_document_generation_context_pack",
                input={"target_task_id": str(blocked_harness_task_id)},
                workflow_version=workflow_version,
            ),
        )
        blocked_context_pack_eval_task_id = blocked_context_pack_eval_task.task_id

    _process_next_task(postgres_integration_harness)

    blocked_context_pack_eval_context_response = client.get(
        f"/agent-tasks/{blocked_context_pack_eval_task_id}/context"
    )
    assert blocked_context_pack_eval_context_response.status_code == 200
    blocked_context_pack_eval_context = blocked_context_pack_eval_context_response.json()
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

    with postgres_integration_harness.session_factory() as session:
        blocked_draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_technical_report",
                input={"target_task_id": str(blocked_harness_task_id)},
                workflow_version=workflow_version,
            ),
        )
        blocked_draft_task_id = blocked_draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        blocked_draft_row = session.get(AgentTask, blocked_draft_task_id)
        assert blocked_draft_row is not None
        assert blocked_draft_row.status == "failed"
        assert "context-pack gate to pass" in (blocked_draft_row.error_message or "")

    release_readiness_assessment = _freeze_release_readiness_assessment(
        postgres_integration_harness,
        release_id,
    )

    with postgres_integration_harness.session_factory() as session:
        tampered_harness_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="prepare_report_agent_harness",
                input={"target_task_id": str(evidence_task_id)},
                workflow_version=workflow_version,
            ),
        )
        tampered_harness_task_id = tampered_harness_task.task_id

    _process_next_task(postgres_integration_harness)
    tampered_search_request_id = _forge_harness_context_latest_bundle_ref(
        postgres_integration_harness,
        tampered_harness_task_id,
    )

    with postgres_integration_harness.session_factory() as session:
        tampered_context_pack_eval_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_document_generation_context_pack",
                input={"target_task_id": str(tampered_harness_task_id)},
                workflow_version=workflow_version,
            ),
        )
        tampered_context_pack_eval_task_id = tampered_context_pack_eval_task.task_id

    _process_next_task(postgres_integration_harness)

    tampered_eval_context_response = client.get(
        f"/agent-tasks/{tampered_context_pack_eval_task_id}/context"
    )
    assert tampered_eval_context_response.status_code == 200
    tampered_eval_context = tampered_eval_context_response.json()
    tampered_eval = tampered_eval_context["output"]["evaluation"]
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
    artifact_response = client.get(
        f"/agent-tasks/{harness_task_id}/artifacts/{harness_artifact_ref['artifact_id']}"
    )
    assert artifact_response.status_code == 200
    artifact_payload = artifact_response.json()
    assert artifact_payload["schema_name"] == "report_agent_harness"
    assert artifact_payload["verification_gate"]["target_task_type"] == "verify_technical_report"
    assert artifact_payload["document_generation_context_pack"]["schema_name"] == (
        "document_generation_context_pack"
    )
    assert artifact_payload["document_generation_context_pack"]["audit_refs"][
        "release_readiness_assessment_ids"
    ] == [release_readiness_assessment["assessment_id"]]
    assert artifact_payload["document_generation_context_pack"]["audit_refs"][
        "release_readiness_assessment_sha256s"
    ] == [release_readiness_assessment["assessment_payload_sha256"]]
    assert artifact_payload["llm_adapter_contract"]["primary_context_schema"] == (
        "document_generation_context_pack"
    )

    with postgres_integration_harness.session_factory() as session:
        premature_draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_technical_report",
                input={"target_task_id": str(harness_task_id)},
                workflow_version=workflow_version,
            ),
        )
        premature_draft_task_id = premature_draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        premature_draft_row = session.get(AgentTask, premature_draft_task_id)
        assert premature_draft_row is not None
        assert premature_draft_row.status == "failed"
        assert "evaluate_document_generation_context_pack" in (
            premature_draft_row.error_message or ""
        )

    with postgres_integration_harness.session_factory() as session:
        context_pack_eval_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_document_generation_context_pack",
                input={"target_task_id": str(harness_task_id)},
                workflow_version=workflow_version,
            ),
        )
        context_pack_eval_task_id = context_pack_eval_task.task_id

    _process_next_task(postgres_integration_harness)

    context_pack_eval_context_response = client.get(
        f"/agent-tasks/{context_pack_eval_task_id}/context"
    )
    assert context_pack_eval_context_response.status_code == 200
    context_pack_eval_context = context_pack_eval_context_response.json()
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
    context_pack_release_readiness_db_summary = context_pack_eval_context["output"]["evaluation"][
        "trace"
    ]["release_readiness_db_summary"]
    assert context_pack_release_readiness_db_summary["complete"] is True
    assert (
        context_pack_release_readiness_db_summary["verified_request_count"]
        == context_pack_release_readiness_db_summary["source_search_request_count"]
    )
    assert (
        context_pack_eval_context["output"]["evaluation"]["trace"]["release_readiness_assessments"][
            0
        ]["assessment_id"]
        == release_readiness_assessment["assessment_id"]
    )
    assert context_pack_eval_context["output"]["context_pack"]["context_pack_sha256"]
    context_pack_sha256 = context_pack_eval_context["output"]["context_pack"]["context_pack_sha256"]
    assert any(
        ref["ref_key"] == "document_generation_context_pack_artifact"
        for ref in context_pack_eval_context["refs"]
    )

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
    release_readiness_db_gate_id = None
    release_readiness_db_gate_payload_sha256 = None
    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        markdown_path = Path(draft_task_row.result_json["payload"]["draft"]["markdown_path"])
        assert markdown_path.exists()
        assert "Evidence Cards" in markdown_path.read_text()
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        assert draft_task_row.result_json["payload"]["context_pack_evaluation_task_id"] == str(
            context_pack_eval_task_id
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
            "semantic_ontology_snapshot_ids" in claim["provenance_lock"]
            and "semantic_graph_snapshot_ids" in claim["provenance_lock"]
            and "retrieval_reranker_artifact_ids" in claim["provenance_lock"]
            and "release_audit_bundle_ids" in claim["provenance_lock"]
            and "release_validation_receipt_ids" in claim["provenance_lock"]
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
                .where(KnowledgeOperatorRun.agent_task_id == draft_task_id)
                .order_by(KnowledgeOperatorRun.created_at.asc())
            )
        )
        assert [row.operator_kind for row in draft_operator_rows] == ["judge", "generate"]
        assert draft_operator_rows[0].operator_name == "technical_report_claim_support_judge"
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

        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        verification = verify_task_row.result_json["payload"]["verification"]
        assert verification["outcome"] == "passed"
        assert verification["metrics"]["context_ref_count"] >= 1
        assert verification["metrics"]["unsupported_claim_count"] == 0
        assert verification["metrics"]["missing_derivation_hash_count"] == 0
        assert verification["metrics"]["missing_provenance_lock_count"] == 0
        assert verification["metrics"]["missing_evidence_package_hash_count"] == 0
        assert verification["metrics"]["evidence_package_integrity_mismatch_count"] == 0
        assert verification["metrics"]["derivation_integrity_mismatch_count"] == 0
        assert verification["metrics"]["provenance_lock_integrity_mismatch_count"] == 0
        assert verification["metrics"]["provenance_lock_contract_mismatch_count"] == 0
        assert verification["metrics"]["missing_support_judgment_count"] == 0
        assert verification["metrics"]["support_judgment_integrity_mismatch_count"] == 0
        assert verification["metrics"]["support_judgment_contract_mismatch_count"] == 0
        assert verification["metrics"]["unsupported_support_judgment_count"] == 0
        assert verification["metrics"]["claim_support_score_below_threshold_count"] == 0
        assert verification["metrics"]["claims_missing_source_search_request_result_count"] == 0
        assert verification["metrics"]["source_evidence_closure_complete"] is True
        assert verification["metrics"]["source_evidence_package_trace_incomplete_count"] == 0
        assert verification["metrics"]["source_record_recall"] == 1.0
        assert (
            verification["metrics"]["cited_cards_without_acceptable_source_evidence_match_count"]
            == 0
        )
        assert verification["metrics"]["cited_cards_without_recomputed_source_coverage_count"] == 0
        assert (
            verification["metrics"][
                "cited_cards_with_expected_record_without_recomputed_record_match_count"
            ]
            == 0
        )
        assert verification["metrics"]["reported_recomputed_match_mismatch_count"] == 0
        assert verification["metrics"]["cited_cards_with_document_run_fallback_match_count"] == 0
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
        assert (
            manifest_rows[0].manifest_payload_json["audit_checklist"]["hash_integrity_verified"]
            is True
        )
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
        governance_events = list(
            session.scalars(
                select(SemanticGovernanceEvent).where(
                    SemanticGovernanceEvent.agent_task_artifact_id == prov_artifact.id
                )
            )
        )
        assert len(governance_events) == 1
        assert governance_events[0].event_kind == "technical_report_prov_export_frozen"
        assert governance_events[0].receipt_sha256 == receipt["receipt_sha256"]
        assert governance_events[0].event_payload_json["change_impact"]["impacted"] is False
        db_gate_rows = list(
            session.scalars(
                select(TechnicalReportReleaseReadinessDbGate).where(
                    TechnicalReportReleaseReadinessDbGate.technical_report_verification_task_id
                    == verify_task_id
                )
            )
        )
        assert len(db_gate_rows) == 1
        db_gate = db_gate_rows[0]
        release_readiness_db_gate_id = db_gate.id
        release_readiness_db_gate_payload_sha256 = db_gate.gate_payload_sha256
        assert db_gate.source_verification_task_id == context_pack_eval_task_id
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

    verify_context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert verify_context_response.status_code == 200
    assert verify_context_response.json()["summary"]["verification_state"] == "passed"

    audit_response = client.get(f"/agent-tasks/{verify_task_id}/audit-bundle")
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    assert audit_bundle["schema_name"] == "technical_report_audit_bundle"
    assert audit_bundle["audit_checklist"]["has_frozen_evidence_package"] is True
    assert audit_bundle["audit_checklist"]["all_claims_have_derivations"] is True
    assert audit_bundle["audit_checklist"]["all_claims_have_provenance_locks"] is True
    assert audit_bundle["audit_checklist"]["all_claim_provenance_locks_match_claim_fields"] is True
    assert audit_bundle["audit_checklist"]["all_claims_have_support_judgments"] is True
    assert audit_bundle["audit_checklist"]["all_claim_support_judgments_match_claim_fields"] is True
    assert audit_bundle["audit_checklist"]["claim_support_judgment_integrity_verified"] is True
    assert audit_bundle["audit_checklist"]["all_claims_have_source_search_results"] is True
    assert audit_bundle["audit_checklist"]["hash_integrity_verified"] is True
    assert audit_bundle["audit_checklist"]["has_frozen_source_evidence_packages"] is True
    assert audit_bundle["audit_checklist"]["has_frozen_prov_export"] is True
    assert audit_bundle["audit_checklist"]["has_prov_export_receipt"] is True
    assert audit_bundle["audit_checklist"]["has_signed_prov_export_receipt"] is True
    assert audit_bundle["audit_checklist"]["prov_export_receipts_integrity_verified"] is True
    assert audit_bundle["audit_checklist"]["prov_export_receipt_signature_verified"] is True
    assert audit_bundle["audit_checklist"]["no_prov_export_immutability_events"] is True
    assert audit_bundle["audit_checklist"]["has_semantic_governance_chain"] is True
    assert audit_bundle["audit_checklist"]["semantic_governance_chain_integrity_verified"] is True
    assert audit_bundle["audit_checklist"]["semantic_governance_chain_links_prov_receipt"] is True
    assert (
        audit_bundle["audit_checklist"]["semantic_governance_chain_change_impact_evaluated"] is True
    )
    assert audit_bundle["audit_checklist"]["source_evidence_trace_integrity_verified"] is True
    assert audit_bundle["audit_checklist"]["generation_evidence_closed"] is True
    assert audit_bundle["audit_checklist"]["has_generation_operator_run"] is True
    assert audit_bundle["audit_checklist"]["has_support_judge_operator_run"] is True
    assert audit_bundle["audit_checklist"]["has_verification_operator_run"] is True
    assert audit_bundle["audit_checklist"]["has_context_pack_artifact"] is True
    assert audit_bundle["audit_checklist"]["has_context_pack_evaluation_artifact"] is True
    assert audit_bundle["audit_checklist"]["has_context_pack_verifier_record"] is True
    assert audit_bundle["audit_checklist"]["has_context_pack_evaluation_operator_run"] is True
    assert audit_bundle["audit_checklist"]["context_pack_evaluation_passed"] is True
    assert audit_bundle["audit_checklist"]["context_pack_hash_verified"] is True
    assert audit_bundle["audit_checklist"]["has_release_readiness_assessments"] is True
    assert (
        audit_bundle["audit_checklist"]["release_readiness_assessments_cover_source_requests"]
        is True
    )
    assert audit_bundle["audit_checklist"]["release_readiness_assessments_ready"] is True
    assert (
        audit_bundle["audit_checklist"]["release_readiness_assessment_integrity_verified"] is True
    )
    assert audit_bundle["audit_checklist"]["release_readiness_db_gate_verified"] is True
    assert audit_bundle["audit_checklist"]["release_readiness_db_gate_complete"] is True
    assert audit_bundle["audit_checklist"]["release_readiness_db_covers_source_requests"] is True
    assert audit_bundle["audit_checklist"]["has_persisted_release_readiness_db_gate"] is True
    assert audit_bundle["audit_checklist"]["context_pack_audit_complete"] is True
    assert audit_bundle["audit_checklist"]["verification_passed"] is True
    assert audit_bundle["audit_checklist"]["change_impact_clear"] is True
    assert audit_bundle["context_pack_audit"]["integrity"]["complete"] is True
    assert audit_bundle["context_pack_audit"]["context_pack_sha256s"] == [context_pack_sha256]
    assert (
        audit_bundle["context_pack_audit"]["release_readiness_assessments"][0]["assessment_id"]
        == release_readiness_assessment["assessment_id"]
    )
    assert audit_bundle["context_pack_audit"]["release_readiness_summary"]["failed_ref_count"] == 0
    audit_release_readiness_db_gate = audit_bundle["context_pack_audit"][
        "release_readiness_db_gate"
    ]
    assert audit_release_readiness_db_gate["check_key"] == (
        "release_readiness_assessment_db_integrity"
    )
    assert audit_release_readiness_db_gate["complete"] is True
    assert audit_release_readiness_db_gate["verification_task_id"] == str(context_pack_eval_task_id)
    assert audit_release_readiness_db_gate["summary"] == (context_pack_release_readiness_db_summary)
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
    assert audit_release_readiness_db_gate_record["source_verification_id"] == (
        audit_release_readiness_db_gate["verification_id"]
    )
    assert audit_release_readiness_db_gate_record["prov_export_artifact_id"] == str(
        prov_artifact_id
    )
    assert audit_release_readiness_db_gate_record["semantic_governance_event_id"]
    assert audit_bundle["context_pack_audit"]["release_readiness_db_summary"] == (
        context_pack_release_readiness_db_summary
    )
    assert audit_bundle["context_pack_audit"]["evaluation_task_ids"] == [
        str(context_pack_eval_task_id)
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
        row["artifact_kind"] == "technical_report_prov_export" for row in audit_bundle["artifacts"]
    )
    assert len(audit_bundle["provenance_export_receipts"]) == 1
    assert (
        audit_bundle["provenance_export_receipts"][0]["export_receipt"]["signature_status"]
        == "signed"
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
    assert manifest["audit_checklist"]["has_claim_provenance_locks"] is True
    assert manifest["audit_checklist"]["has_claim_support_judgments"] is True
    assert manifest["audit_checklist"]["has_support_judge_operator_run"] is True
    assert manifest["audit_checklist"]["has_context_pack_artifact"] is True
    assert manifest["audit_checklist"]["has_context_pack_evaluation_artifact"] is True
    assert manifest["audit_checklist"]["has_context_pack_verifier_record"] is True
    assert manifest["audit_checklist"]["has_context_pack_evaluation_operator_run"] is True
    assert manifest["audit_checklist"]["context_pack_evaluation_passed"] is True
    assert manifest["audit_checklist"]["context_pack_hash_verified"] is True
    assert manifest["audit_checklist"]["has_release_readiness_assessments"] is True
    assert manifest["audit_checklist"]["release_readiness_assessments_ready"] is True
    assert manifest["audit_checklist"]["release_readiness_assessment_integrity_verified"] is True
    assert manifest["audit_checklist"]["release_readiness_db_gate_verified"] is True
    assert manifest["audit_checklist"]["release_readiness_db_gate_complete"] is True
    assert manifest["audit_checklist"]["release_readiness_db_covers_source_requests"] is True
    assert manifest["audit_checklist"]["has_persisted_release_readiness_db_gate"] is True
    assert manifest["audit_checklist"]["has_claim_source_search_results"] is True
    assert manifest["audit_checklist"]["hash_integrity_verified"] is True
    assert manifest["source_documents"][0]["sha256"]
    assert manifest["document_runs"][0]["artifact_hashes"]["docling_json_sha256"]
    assert (
        manifest["report_trace"]["evidence_package_integrity"]["draft_package_hash_matches"] is True
    )
    assert manifest["report_trace"]["verification"]["outcome"] == "passed"
    assert manifest["report_trace"]["context_pack_audit"]["integrity"]["complete"] is True
    assert manifest["report_trace"]["context_pack_audit"]["context_pack_sha256s"] == [
        context_pack_sha256
    ]
    assert (
        manifest["report_trace"]["context_pack_audit"]["release_readiness_assessments"][0][
            "assessment_id"
        ]
        == release_readiness_assessment["assessment_id"]
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
    assert manifest["provenance_edges"]
    assert {
        "claim_to_provenance_lock",
        "claim_to_support_judgment",
        "support_judge_run_to_claim",
        "search_result_to_claim",
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
        "claim_provenance_lock",
        "claim_support_judgment",
        "claim_derivation",
        "search_result",
        "operator_run",
        "verification_record",
        "agent_task_artifact",
        "context_pack_evaluation_task",
        "release_readiness_assessment",
        "release_readiness_db_gate",
        "evidence_manifest",
    }.issubset(node_kinds)
    assert any(
        node["node_kind"] == "release_readiness_db_gate"
        and node["source_table"] == "technical_report_release_readiness_db_gates"
        and node["source_id"] == str(release_readiness_db_gate_id)
        for node in trace["nodes"]
    )
    assert any(
        edge["payload"].get("source") == "manifest_provenance_edges" for edge in trace["edges"]
    )

    provenance_response = client.get(f"/agent-tasks/{verify_task_id}/provenance")
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
    assert provenance["frozen_export"]["export_payload_sha256"] == prov_artifact_sha256
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
        and entity.get("docling:context_pack_sha256") == context_pack_sha256
        for entity in provenance["entity"].values()
    )
    assert any(
        entity.get("prov:type") == "docling:SearchHarnessReleaseReadinessAssessment"
        and entity.get("docling:assessment_payload_sha256")
        == release_readiness_assessment["assessment_payload_sha256"]
        for entity in provenance["entity"].values()
    )
    assert any(
        entity.get("prov:type") == "docling:ReleaseReadinessDbGate"
        and entity.get("docling:complete") is True
        and entity.get("docling:failure_count") == 0
        and entity.get("docling:gate_id") == str(release_readiness_db_gate_id)
        and entity.get("docling:gate_payload_sha256")
        == release_readiness_db_gate_payload_sha256
        for entity in provenance["entity"].values()
    )
    assert (
        f"docling:technical-report-release-readiness-db-gates/"
        f"{release_readiness_db_gate_id}"
        in provenance["entity"]
    )
    assert any(
        activity.get("prov:type") == "docling:ContextPackEvaluationTask"
        for activity in provenance["activity"].values()
    )
    assert provenance["wasDerivedFrom"]
    assert provenance["used"]
    artifact_response = client.get(f"/agent-tasks/{verify_task_id}/artifacts/{prov_artifact_id}")
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

    with postgres_integration_harness.session_factory() as session:
        stale_harness_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="prepare_report_agent_harness",
                input={"target_task_id": str(evidence_task_id)},
                workflow_version=workflow_version,
            ),
        )
        stale_harness_task_id = stale_harness_task.task_id

    _process_next_task(postgres_integration_harness)
    _create_audit_bundle_validation_receipt(
        postgres_integration_harness,
        release_fixture["audit_bundle"]["bundle_id"],
    )

    with postgres_integration_harness.session_factory() as session:
        stale_context_pack_eval_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_document_generation_context_pack",
                input={"target_task_id": str(stale_harness_task_id)},
                workflow_version=workflow_version,
            ),
        )
        stale_context_pack_eval_task_id = stale_context_pack_eval_task.task_id

    _process_next_task(postgres_integration_harness)

    stale_eval_context_response = client.get(
        f"/agent-tasks/{stale_context_pack_eval_task_id}/context"
    )
    assert stale_eval_context_response.status_code == 200
    stale_eval_context = stale_eval_context_response.json()
    stale_eval = stale_eval_context["output"]["evaluation"]
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
        uncovered_verification = uncovered_verify_task_row.result_json["payload"]["verification"]
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
                claim["source_evidence_match_keys"] = list(weak_card["source_evidence_match_keys"])
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
        weak_match_verification = weak_match_verify_task_row.result_json["payload"]["verification"]
        assert weak_match_verification["outcome"] == "failed"
        assert weak_match_verification["metrics"]["source_evidence_closure_complete"] is False
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
        tampered_verification = tampered_verify_task_row.result_json["payload"]["verification"]
        assert tampered_verification["outcome"] == "failed"
        assert tampered_verification["metrics"]["source_evidence_closure_complete"] is False
        assert (
            tampered_verification["metrics"]["source_evidence_package_trace_incomplete_count"] == 1
        )
        assert any(
            "frozen search evidence packages" in reason
            for reason in tampered_verification["reasons"]
        )
