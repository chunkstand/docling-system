from __future__ import annotations

import importlib.util
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.retrieval import (
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchReplayRun,
)
from app.schemas.agent_task_core import AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import create_agent_task
from app.services.evidence_common import payload_sha256
from app.services.semantic_registry import clear_semantic_registry_cache
from tests.integration.pdf_fixtures import valid_test_pdf_bytes
from tests.integration.test_semantic_generation_roundtrip import (
    StubParser,
    _build_parsed_document,
    _write_registry,
    _write_semantic_eval_corpus,
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


def create_task_and_process(
    postgres_integration_harness,
    *,
    workflow_version: str,
    task_type: str,
    task_input: dict,
) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type=task_type,
                input=task_input,
                workflow_version=workflow_version,
            ),
        )
        task_id = task.task_id
    _process_next_task(postgres_integration_harness)
    return task_id


def prepare_base_harness_scenario(postgres_integration_harness, monkeypatch, tmp_path) -> dict:
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
    plan_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=workflow_version,
        task_type="plan_technical_report",
        task_input={
            "title": "Integration Governance Technical Report",
            "goal": "Write a technical report from integration governance evidence.",
            "audience": "Operators",
            "document_ids": [str(document_id)],
            "target_length": "medium",
            "review_policy": "allow_candidate_with_disclosure",
        },
    )
    evidence_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=workflow_version,
        task_type="build_report_evidence_cards",
        task_input={"target_task_id": str(plan_task_id)},
    )
    return {
        "client": client,
        "workflow_version": workflow_version,
        "release_fixture": release_fixture,
        "document_id": document_id,
        "run_id": run_id,
        "evidence_task_id": evidence_task_id,
    }


def run_verified_report_roundtrip(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> dict:
    base = prepare_base_harness_scenario(postgres_integration_harness, monkeypatch, tmp_path)
    release_readiness_assessment = _freeze_release_readiness_assessment(
        postgres_integration_harness,
        base["release_fixture"]["release"]["release_id"],
    )
    harness_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=base["workflow_version"],
        task_type="prepare_report_agent_harness",
        task_input={"target_task_id": str(base["evidence_task_id"])},
    )
    context_pack_eval_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=base["workflow_version"],
        task_type="evaluate_document_generation_context_pack",
        task_input={"target_task_id": str(harness_task_id)},
    )
    draft_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=base["workflow_version"],
        task_type="draft_technical_report",
        task_input={"target_task_id": str(harness_task_id)},
    )
    verify_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=base["workflow_version"],
        task_type="verify_technical_report",
        task_input={"target_task_id": str(draft_task_id)},
    )
    return {
        **base,
        "release_readiness_assessment": release_readiness_assessment,
        "harness_task_id": harness_task_id,
        "context_pack_eval_task_id": context_pack_eval_task_id,
        "draft_task_id": draft_task_id,
        "verify_task_id": verify_task_id,
    }
