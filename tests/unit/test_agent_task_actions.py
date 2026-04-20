from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ApplyHarnessConfigUpdateTaskInput,
    ApplySemanticRegistryUpdateTaskInput,
    DraftHarnessConfigUpdateTaskInput,
    DraftSemanticGroundedDocumentTaskInput,
    DraftSemanticRegistryUpdateTaskInput,
    EnqueueDocumentReprocessTaskInput,
    LatestSemanticPassTaskInput,
    PrepareSemanticGenerationBriefTaskInput,
    TriageSemanticPassTaskInput,
    VerifyDraftHarnessConfigTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifySemanticGroundedDocumentTaskInput,
)
from app.schemas.documents import DocumentUploadResponse
from app.schemas.semantics import DocumentSemanticPassResponse
from app.services.agent_task_actions import (
    _apply_harness_config_update_executor,
    _apply_semantic_registry_update_executor,
    _draft_harness_config_update_executor,
    _draft_semantic_grounded_document_executor,
    _draft_semantic_registry_update_executor,
    _enqueue_document_reprocess_executor,
    _latest_semantic_pass_executor,
    _prepare_semantic_generation_brief_executor,
    _triage_semantic_pass_executor,
    _verify_draft_harness_config_executor,
    _verify_draft_semantic_registry_update_executor,
    _verify_semantic_grounded_document_executor,
    execute_agent_task_action,
    get_agent_task_action,
    validate_agent_task_output,
)


def _draft_output_payload(*, draft_task_id, draft_harness_name="wide_v2_review") -> dict:
    return {
        "draft": {
            "draft_harness_name": draft_harness_name,
            "base_harness_name": "wide_v2",
            "source_task_id": None,
            "source_task_type": None,
            "rationale": "publish review harness",
            "override_spec": {
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                "reranker_overrides": {"result_type_priority_bonus": 0.009},
                "override_type": "draft_harness_config_update",
                "override_source": "task_draft",
                "draft_task_id": str(draft_task_id),
                "source_task_id": None,
                "rationale": "publish review harness",
            },
            "effective_harness_config": {"base_harness_name": "wide_v2"},
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft",
        "artifact_path": "/tmp/harness_config_draft.json",
    }


def _verification_output_payload(
    *,
    verification_task_id,
    draft_task_id,
    draft_harness_name="wide_v2_review",
    outcome="passed",
) -> dict:
    return {
        "draft": _draft_output_payload(
            draft_task_id=draft_task_id,
            draft_harness_name=draft_harness_name,
        )["draft"],
        "evaluation": {
            "baseline_harness_name": "wide_v2",
            "total_regressed_count": 0,
            "total_improved_count": 1,
        },
        "verification": {
            "verification_id": str(uuid4()),
            "target_task_id": str(draft_task_id),
            "verification_task_id": str(verification_task_id),
            "verifier_type": "draft_harness_config_gate",
            "outcome": outcome,
            "metrics": {"total_shared_query_count": 10},
            "reasons": [],
            "details": {"draft_harness_name": draft_harness_name},
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft_verification",
        "artifact_path": "/tmp/harness_config_draft_verification.json",
    }


def _semantic_pass_response() -> DocumentSemanticPassResponse:
    now = datetime.now(UTC)
    return DocumentSemanticPassResponse(
        semantic_pass_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        status="completed",
        registry_version="semantics-layer-foundation-alpha.2",
        registry_sha256="registry-sha",
        extractor_version="semantics_sidecar_v2_1",
        artifact_schema_version="2.1",
        baseline_run_id=None,
        baseline_semantic_pass_id=None,
        has_json_artifact=True,
        has_yaml_artifact=True,
        artifact_json_sha256="json-sha",
        artifact_yaml_sha256="yaml-sha",
        assertion_count=0,
        evidence_count=0,
        summary={"concept_keys": []},
        evaluation_status="completed",
        evaluation_fixture_name="semantic_fixture",
        evaluation_version=2,
        evaluation_summary={"all_expectations_passed": True, "expectations": []},
        continuity_summary={"reason": "no_prior_active_run", "change_count": 0},
        error_message=None,
        created_at=now,
        completed_at=now,
        concept_category_bindings=[],
        assertions=[],
    )


def test_enqueue_document_reprocess_executor_queues_reprocess(monkeypatch) -> None:
    document_id = uuid4()
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="enqueue_document_reprocess",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.reprocess_document",
        lambda session, requested_document_id: DocumentUploadResponse(
            document_id=requested_document_id,
            run_id=uuid4(),
            status="queued",
            duplicate=False,
        ),
    )

    result = _enqueue_document_reprocess_executor(
        session=object(),
        _task=task,
        payload=EnqueueDocumentReprocessTaskInput(
            document_id=document_id,
            source_task_id=source_task_id,
            reason="triage requested reprocess",
        ),
    )

    assert result["document_id"] == str(document_id)
    assert result["source_task_id"] == str(source_task_id)
    assert result["reason"] == "triage requested reprocess"
    assert result["reprocess"]["document_id"] == str(document_id)
    assert result["reprocess"]["status"] == "queued"


def test_latest_semantic_pass_executor_returns_typed_output(monkeypatch) -> None:
    semantic_pass = _semantic_pass_response()
    document_id = semantic_pass.document_id

    monkeypatch.setattr(
        "app.services.agent_task_actions.get_active_semantic_pass_detail",
        lambda session, requested_document_id: (
            semantic_pass if requested_document_id == document_id else None
        ),
    )

    result = _latest_semantic_pass_executor(
        session=object(),
        _task=AgentTask(
            id=uuid4(),
            task_type="get_latest_semantic_pass",
            status="processing",
            priority=100,
            side_effect_level="read_only",
            requires_approval=False,
            input_json={},
            result_json={},
            workflow_version="v1",
            model_settings_json={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        payload=LatestSemanticPassTaskInput(document_id=document_id),
    )

    assert result["document_id"] == str(document_id)
    assert result["semantic_pass"]["semantic_pass_id"] == str(semantic_pass.semantic_pass_id)
    assert result["success_metrics"]


def test_draft_harness_config_update_executor_writes_draft_artifact(
    monkeypatch,
    tmp_path,
) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/harness_config_draft.json",
            },
        )(),
    )
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )

    session = type(
        "FakeSession",
        (),
        {
            "get": lambda self, model, key: type(
                "SourceTask",
                (),
                {"id": key, "task_type": "triage_replay_regression"},
            )()
        },
    )()

    result = _draft_harness_config_update_executor(
        session=session,
        task=task,
        payload=DraftHarnessConfigUpdateTaskInput(
            draft_harness_name="wide_v2_review",
            base_harness_name="wide_v2",
            source_task_id=source_task_id,
            rationale="publish review harness",
            reranker_overrides={"result_type_priority_bonus": 0.009},
        ),
    )

    assert result["draft"]["draft_harness_name"] == "wide_v2_review"
    assert result["draft"]["base_harness_name"] == "wide_v2"
    assert result["draft"]["source_task_id"] == str(source_task_id)
    assert result["draft"]["effective_harness_config"]["base_harness_name"] == "wide_v2"
    assert result["artifact_kind"] == "harness_config_draft"


def test_triage_semantic_pass_executor_writes_gap_report_artifact(monkeypatch) -> None:
    target_task_id = uuid4()
    semantic_pass = _semantic_pass_response()
    task = AgentTask(
        id=uuid4(),
        task_type="triage_semantic_pass",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            task_id=target_task_id,
            task_type="get_latest_semantic_pass",
            output_schema_name="get_latest_semantic_pass_output",
            output_schema_version="1.0",
            task_updated_at=datetime.now(UTC),
            output={
                "document_id": str(semantic_pass.document_id),
                "semantic_pass": json.loads(semantic_pass.model_dump_json()),
                "success_metrics": [],
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.triage_semantic_pass",
        lambda semantic_pass, low_evidence_threshold: SimpleNamespace(
            gap_report={
                "document_id": semantic_pass.document_id,
                "run_id": semantic_pass.run_id,
                "semantic_pass_id": semantic_pass.semantic_pass_id,
                "registry_version": semantic_pass.registry_version,
                "registry_sha256": semantic_pass.registry_sha256,
                "evaluation_status": semantic_pass.evaluation_status,
                "evaluation_fixture_name": semantic_pass.evaluation_fixture_name,
                "evaluation_version": semantic_pass.evaluation_version,
                "continuity_summary": semantic_pass.continuity_summary,
                "issue_count": 1,
                "issues": [],
                "recommended_followups": [],
                "success_metrics": [],
            },
            recommendation={
                "next_action": "draft_registry_update",
                "confidence": "high",
                "summary": "draft an additive registry update",
            },
            verification_outcome="failed",
            verification_metrics={"issue_count": 1},
            verification_reasons=["Expected concept missing."],
            verification_details={"issue_types": ["missing_expected_concept"]},
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            verification_id=uuid4(),
            target_task_id=kwargs["target_task_id"],
            verification_task_id=kwargs["verification_task_id"],
            verifier_type=kwargs["verifier_type"],
            outcome=kwargs["outcome"],
            metrics=kwargs["metrics"],
            reasons=kwargs["reasons"],
            details=kwargs["details"],
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(kwargs["target_task_id"]),
                "verification_task_id": str(kwargs["verification_task_id"]),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_gap_report.json",
        ),
    )

    result = _triage_semantic_pass_executor(
        session=object(),
        task=task,
        payload=TriageSemanticPassTaskInput(
            target_task_id=target_task_id,
            low_evidence_threshold=2,
        ),
    )

    assert result["document_id"] == str(semantic_pass.document_id)
    assert result["recommendation"]["next_action"] == "draft_registry_update"
    assert result["artifact_kind"] == "semantic_gap_report"
    assert result["verification"]["verifier_type"] == "semantic_gap_gate"


def test_draft_semantic_registry_update_executor_writes_draft_artifact(monkeypatch) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            task_id=source_task_id,
            task_type="triage_semantic_pass",
            output={
                "document_id": str(uuid4()),
                "run_id": str(uuid4()),
                "semantic_pass_id": str(uuid4()),
                "registry_version": "semantics-layer-foundation-alpha.2",
                "evaluation_fixture_name": "semantic_fixture",
                "evaluation_status": "completed",
                "gap_report": {
                    "document_id": str(uuid4()),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "registry_version": "semantics-layer-foundation-alpha.2",
                    "registry_sha256": "registry-sha",
                    "evaluation_status": "completed",
                    "evaluation_fixture_name": "semantic_fixture",
                    "evaluation_version": 2,
                    "continuity_summary": {"reason": "no_prior_active_run", "change_count": 0},
                    "issue_count": 1,
                    "issues": [
                        {
                            "issue_id": "missing_expected_concept:integration_threshold",
                            "issue_type": "missing_expected_concept",
                            "severity": "high",
                            "concept_key": "integration_threshold",
                            "category_key": None,
                            "assertion_id": None,
                            "binding_id": None,
                            "summary": "Expected concept missing.",
                            "details": {},
                            "evidence_refs": [],
                            "registry_update_hints": [
                                {
                                    "update_type": "add_alias",
                                    "concept_key": "integration_threshold",
                                    "alias_text": "integration guardrail",
                                    "category_key": None,
                                    "reason": "missing alias",
                                }
                            ],
                        }
                    ],
                    "recommended_followups": [],
                    "success_metrics": [],
                },
                "verification": {
                    "verification_id": str(uuid4()),
                    "target_task_id": str(source_task_id),
                    "verification_task_id": str(uuid4()),
                    "verifier_type": "semantic_gap_gate",
                    "outcome": "failed",
                    "metrics": {},
                    "reasons": [],
                    "details": {},
                    "created_at": datetime.now(UTC).isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                },
                "recommendation": {
                    "next_action": "draft_registry_update",
                    "confidence": "high",
                    "summary": "draft registry update",
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_gap_report",
                "artifact_path": "/tmp/semantic_gap_report.json",
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.draft_semantic_registry_update",
        lambda gap_report, **kwargs: {
            "base_registry_version": "semantics-layer-foundation-alpha.2",
            "proposed_registry_version": "semantics-layer-foundation-alpha.3",
            "source_task_id": kwargs["source_task_id"],
            "source_task_type": kwargs["source_task_type"],
            "rationale": kwargs["rationale"],
            "document_ids": [gap_report["document_id"]],
            "operations": [
                {
                    "operation_id": "add_alias:integration_threshold:integration_guardrail",
                    "operation_type": "add_alias",
                    "concept_key": "integration_threshold",
                    "alias_text": "integration guardrail",
                    "category_key": None,
                    "source_issue_ids": ["missing_expected_concept:integration_threshold"],
                    "rationale": "missing alias",
                }
            ],
            "effective_registry": {"registry_version": "semantics-layer-foundation-alpha.3"},
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_registry_draft.json",
        ),
    )

    result = _draft_semantic_registry_update_executor(
        session=object(),
        task=task,
        payload=DraftSemanticRegistryUpdateTaskInput(
            source_task_id=source_task_id,
            rationale="add the missing alias",
        ),
    )

    assert result["draft"]["proposed_registry_version"] == "semantics-layer-foundation-alpha.3"
    assert result["artifact_kind"] == "semantic_registry_draft"


def test_verify_draft_semantic_registry_update_executor_writes_verification_artifact(
    monkeypatch,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_draft_semantic_registry_update_task",
        lambda session, verification_task, payload: {
            "draft": {
                "base_registry_version": "semantics-layer-foundation-alpha.2",
                "proposed_registry_version": "semantics-layer-foundation-alpha.3",
                "source_task_id": str(uuid4()),
                "source_task_type": "triage_semantic_pass",
                "rationale": "alias update",
                "document_ids": [str(uuid4())],
                "operations": [],
                "effective_registry": {"registry_version": "semantics-layer-foundation-alpha.3"},
                "success_metrics": [],
            },
            "document_deltas": [],
            "summary": {"improved_document_count": 1, "regressed_document_count": 0},
            "success_metrics": [],
            "verification": {
                "verification_id": str(uuid4()),
                "target_task_id": str(uuid4()),
                "verification_task_id": str(task.id),
                "verifier_type": "semantic_registry_draft_gate",
                "outcome": "passed",
                "metrics": {"document_count": 1},
                "reasons": [],
                "details": {},
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_registry_draft_verification.json",
        ),
    )

    result = _verify_draft_semantic_registry_update_executor(
        session=object(),
        task=task,
        payload=VerifyDraftSemanticRegistryUpdateTaskInput(target_task_id=uuid4()),
    )

    assert result["artifact_kind"] == "semantic_registry_draft_verification"
    assert result["verification"]["verifier_type"] == "semantic_registry_draft_gate"


def test_apply_semantic_registry_update_executor_persists_registry(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="apply_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    dependencies = {
        ("draft_semantic_registry_update", draft_task_id): SimpleNamespace(
            task_id=draft_task_id,
            task_type="draft_semantic_registry_update",
            output={
                "draft": {
                    "base_registry_version": "semantics-layer-foundation-alpha.2",
                    "proposed_registry_version": "semantics-layer-foundation-alpha.3",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "triage_semantic_pass",
                    "rationale": "alias update",
                    "document_ids": [str(uuid4())],
                    "operations": [
                        {
                            "operation_id": "add_alias:integration_threshold:integration_guardrail",
                            "operation_type": "add_alias",
                            "concept_key": "integration_threshold",
                            "alias_text": "integration guardrail",
                            "category_key": None,
                            "source_issue_ids": ["missing_expected_concept:integration_threshold"],
                            "rationale": "missing alias",
                        }
                    ],
                    "effective_registry": {
                        "registry_version": "semantics-layer-foundation-alpha.3"
                    },
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_registry_draft",
                "artifact_path": "/tmp/semantic_registry_draft.json",
            },
        ),
        ("verify_draft_semantic_registry_update", verification_task_id): SimpleNamespace(
            task_id=verification_task_id,
            task_type="verify_draft_semantic_registry_update",
            output={
                "draft": {
                    "base_registry_version": "semantics-layer-foundation-alpha.2",
                    "proposed_registry_version": "semantics-layer-foundation-alpha.3",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "triage_semantic_pass",
                    "rationale": "alias update",
                    "document_ids": [str(uuid4())],
                    "operations": [
                        {
                            "operation_id": "add_alias:integration_threshold:integration_guardrail",
                            "operation_type": "add_alias",
                            "concept_key": "integration_threshold",
                            "alias_text": "integration guardrail",
                            "category_key": None,
                            "source_issue_ids": ["missing_expected_concept:integration_threshold"],
                            "rationale": "missing alias",
                        }
                    ],
                    "effective_registry": {
                        "registry_version": "semantics-layer-foundation-alpha.3"
                    },
                    "success_metrics": [],
                },
                "document_deltas": [],
                "summary": {"improved_document_count": 1, "regressed_document_count": 0},
                "success_metrics": [],
                "verification": {
                    "verification_id": str(uuid4()),
                    "target_task_id": str(draft_task_id),
                    "verification_task_id": str(verification_task_id),
                    "verifier_type": "semantic_registry_draft_gate",
                    "outcome": "passed",
                    "metrics": {"document_count": 1},
                    "reasons": [],
                    "details": {},
                    "created_at": datetime.now(UTC).isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_registry_draft_verification",
                "artifact_path": "/tmp/semantic_registry_draft_verification.json",
            },
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, task_id, depends_on_task_id, expected_task_type, **kwargs: dependencies[
            (expected_task_type, depends_on_task_id)
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.write_semantic_registry_payload",
        lambda payload: Path("/tmp/semantic_registry.yaml"),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.get_semantic_registry",
        lambda: SimpleNamespace(
            registry_version="semantics-layer-foundation-alpha.3",
            sha256="new-registry-sha",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/applied_semantic_registry_update.json",
        ),
    )

    result = _apply_semantic_registry_update_executor(
        session=object(),
        task=task,
        payload=ApplySemanticRegistryUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish the verified registry update",
        ),
    )

    assert result["applied_registry_version"] == "semantics-layer-foundation-alpha.3"
    assert result["applied_registry_sha256"] == "new-registry-sha"
    assert result["artifact_kind"] == "applied_semantic_registry_update"


def test_validate_agent_task_output_accepts_migrated_draft_shape() -> None:
    artifact_id = uuid4()
    source_task_id = uuid4()

    validated = validate_agent_task_output(
        "draft_harness_config_update",
        {
            "draft": {
                "draft_harness_name": "wide_v2_review",
                "base_harness_name": "wide_v2",
                "source_task_id": str(source_task_id),
                "source_task_type": "triage_replay_regression",
                "rationale": "publish review harness",
                "override_spec": {
                    "base_harness_name": "wide_v2",
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {"result_type_priority_bonus": 0.009},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(uuid4()),
                    "source_task_id": str(source_task_id),
                    "rationale": "publish review harness",
                },
                "effective_harness_config": {"base_harness_name": "wide_v2"},
            },
            "artifact_id": str(artifact_id),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    )

    assert validated["artifact_id"] == str(artifact_id)
    assert validated["draft"]["source_task_id"] == str(source_task_id)


def test_validate_agent_task_output_rejects_invalid_migrated_draft_shape() -> None:
    try:
        validate_agent_task_output(
            "draft_harness_config_update",
            {
                "artifact_id": str(uuid4()),
                "artifact_kind": "harness_config_draft",
                "artifact_path": "/tmp/harness_config_draft.json",
            },
        )
    except ValidationError as exc:
        assert "draft" in str(exc)
    else:
        raise AssertionError("Expected draft output validation to fail")


def test_validate_agent_task_output_accepts_migrated_evaluate_shape() -> None:
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    validated = validate_agent_task_output(
        "evaluate_search_harness",
        {
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "evaluation": {
                "baseline_harness_name": "default_v1",
                "candidate_harness_name": "wide_v2",
                "limit": 12,
                "total_shared_query_count": 4,
                "total_improved_count": 1,
                "total_regressed_count": 0,
                "total_unchanged_count": 3,
                "sources": [
                    {
                        "source_type": "evaluation_queries",
                        "baseline_replay_run_id": str(baseline_replay_run_id),
                        "candidate_replay_run_id": str(candidate_replay_run_id),
                        "baseline_query_count": 4,
                        "candidate_query_count": 4,
                        "baseline_passed_count": 4,
                        "candidate_passed_count": 4,
                        "baseline_zero_result_count": 0,
                        "candidate_zero_result_count": 0,
                        "baseline_table_hit_count": 1,
                        "candidate_table_hit_count": 1,
                        "baseline_top_result_changes": 0,
                        "candidate_top_result_changes": 0,
                        "baseline_mrr": 1.0,
                        "candidate_mrr": 1.0,
                        "baseline_foreign_top_result_count": 0,
                        "candidate_foreign_top_result_count": 0,
                        "acceptance_checks": {"no_regressions": True},
                        "shared_query_count": 4,
                        "improved_count": 1,
                        "regressed_count": 0,
                        "unchanged_count": 3,
                    }
                ],
            },
        },
    )

    assert validated["candidate_harness_name"] == "wide_v2"
    assert validated["evaluation"]["sources"][0]["source_type"] == "evaluation_queries"


def test_execute_agent_task_action_includes_output_schema_metadata(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={
            "draft_harness_name": "wide_v2_review",
            "base_harness_name": "wide_v2",
        },
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    action = replace(
        get_agent_task_action("draft_harness_config_update"),
        executor=lambda session, current_task, payload: {
            "draft": {
                "draft_harness_name": payload.draft_harness_name,
                "base_harness_name": payload.base_harness_name,
                "source_task_id": None,
                "source_task_type": None,
                "rationale": None,
                "override_spec": {
                    "base_harness_name": payload.base_harness_name,
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(current_task.id),
                    "source_task_id": None,
                    "rationale": None,
                },
                "effective_harness_config": {"base_harness_name": payload.base_harness_name},
            },
            "artifact_id": str(uuid4()),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.get_agent_task_action", lambda _task_type: action
    )

    result = execute_agent_task_action(object(), task)

    assert result["output_schema_name"] == "draft_harness_config_update_output"
    assert result["output_schema_version"] == "1.0"
    assert result["payload"]["draft"]["draft_harness_name"] == "wide_v2_review"


def test_get_agent_task_action_exposes_evaluate_output_schema_metadata() -> None:
    action = get_agent_task_action("evaluate_search_harness")

    assert action.output_schema_name == "evaluate_search_harness_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None


def test_get_agent_task_action_exposes_verify_evaluation_output_schema_metadata() -> None:
    action = get_agent_task_action("verify_search_harness_evaluation")

    assert action.output_schema_name == "verify_search_harness_evaluation_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None


def test_get_agent_task_action_exposes_triage_output_schema_metadata() -> None:
    action = get_agent_task_action("triage_replay_regression")

    assert action.output_schema_name == "triage_replay_regression_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None


def test_verify_draft_harness_config_executor_writes_verification_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_harness_config",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    target_task_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_draft_harness_config_task",
        lambda session, verification_task, payload: {
            "draft": {"draft_harness_name": "wide_v2_review"},
            "evaluation": {"candidate_harness_name": "wide_v2_review"},
            "verification": {"outcome": "passed"},
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/harness_config_draft_verification.json",
            },
        )(),
    )

    result = _verify_draft_harness_config_executor(
        session=object(),
        task=task,
        payload=VerifyDraftHarnessConfigTaskInput(
            target_task_id=target_task_id,
            baseline_harness_name="wide_v2",
            source_types=["evaluation_queries"],
            limit=10,
        ),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "harness_config_draft_verification"


def test_apply_harness_config_update_executor_persists_review_harness(
    monkeypatch,
    tmp_path,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/applied_harness_config_update.json",
            },
        )(),
    )
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
            )
        ),
    }

    def fake_resolve(
        session,
        *,
        expected_task_type,
        **_kwargs,
    ):
        return resolver_payloads[expected_task_type]

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    result = _apply_harness_config_update_executor(
        session=object(),
        task=apply_task,
        payload=ApplyHarnessConfigUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish review harness",
        ),
    )

    assert result["draft_harness_name"] == "wide_v2_review"
    assert result["applied_override"]["verification_task_id"] == str(verification_task_id)
    assert result["applied_override"]["applied_by"] == "operator@example.com"
    assert Path(result["config_path"]).exists()
    payload = json.loads(Path(result["config_path"]).read_text())
    assert payload["harnesses"]["wide_v2_review"]["base_harness_name"] == "wide_v2"


def test_apply_harness_config_update_executor_rejects_mismatched_verification_target(
    monkeypatch,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    other_draft_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=other_draft_task_id,
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: resolver_payloads[expected_task_type],
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except ValueError as exc:
        assert "does not target the requested draft task" in str(exc)
    else:
        raise AssertionError("Expected mismatched verifier target to be rejected")


def test_apply_harness_config_update_executor_rejects_failed_verification(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
                outcome="failed",
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: resolver_payloads[expected_task_type],
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except ValueError as exc:
        assert "Only passed draft harness verifications can be applied" in str(exc)
    else:
        raise AssertionError("Expected failed verification to be rejected")


def test_apply_harness_config_update_executor_bubbles_dependency_role_errors(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    def fake_resolve(session, *, dependency_kind, **_kwargs):
        if dependency_kind == "draft_task":
            raise HTTPException(status_code=409, detail="wrong dependency kind")
        return SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
            )
        )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "wrong dependency kind"
    else:
        raise AssertionError("Expected dependency role validation to bubble")


def test_apply_harness_config_update_executor_bubbles_schema_errors(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    def fake_resolve(session, *, dependency_kind, **_kwargs):
        if dependency_kind == "verification_task":
            raise HTTPException(status_code=409, detail="rerun required")
        return SimpleNamespace(output=_draft_output_payload(draft_task_id=draft_task_id))

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "rerun required"
    else:
        raise AssertionError("Expected schema/rerun validation to bubble")


def test_apply_harness_config_update_executor_bubbles_missing_verification(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    def fake_resolve(session, *, dependency_kind, depends_on_task_id, **_kwargs):
        if dependency_kind == "verification_task":
            raise HTTPException(
                status_code=404, detail=f"Target task not found: {depends_on_task_id}"
            )
        return SimpleNamespace(output=_draft_output_payload(draft_task_id=draft_task_id))

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert str(verification_task_id) in exc.detail
    else:
        raise AssertionError("Expected missing verification task to bubble")


def _semantic_generation_brief_output_payload(*, task_id, document_id) -> dict:
    return {
        "brief": {
            "document_kind": "knowledge_brief",
            "title": "Integration Governance Brief",
            "goal": "Summarize the knowledge base guidance on integration governance.",
            "audience": "Operators",
            "review_policy": "allow_candidate_with_disclosure",
            "target_length": "medium",
            "document_refs": [
                {
                    "document_id": str(document_id),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "source_filename": "integration-one.pdf",
                    "title": "Integration One",
                    "registry_version": "semantics-layer-foundation-alpha.3",
                    "registry_sha256": "registry-sha",
                    "evaluation_fixture_name": "integration_fixture",
                    "evaluation_status": "completed",
                    "assertion_count": 1,
                    "evidence_count": 2,
                    "all_expectations_passed": True,
                }
            ],
            "selected_concept_keys": ["integration_threshold"],
            "selected_category_keys": ["integration_governance"],
            "semantic_dossier": [
                {
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "category_keys": ["integration_governance"],
                    "category_labels": {"integration_governance": "Integration Governance"},
                    "document_ids": [str(document_id)],
                    "document_count": 1,
                    "evidence_count": 2,
                    "source_types": ["chunk", "table"],
                    "support_level": "supported",
                    "review_policy_status": "candidate_disclosed",
                    "disclosure_note": "Candidate-backed support requires review.",
                    "assertions": [
                        {
                            "document_id": str(document_id),
                            "run_id": str(uuid4()),
                            "semantic_pass_id": str(uuid4()),
                            "assertion_id": str(uuid4()),
                            "concept_key": "integration_threshold",
                            "preferred_label": "Integration Threshold",
                            "review_status": "candidate",
                            "support_level": "supported",
                            "source_types": ["chunk", "table"],
                            "evidence_count": 2,
                            "category_keys": ["integration_governance"],
                            "category_labels": ["Integration Governance"],
                        }
                    ],
                    "evidence_refs": [
                        {
                            "citation_label": "E1",
                            "document_id": str(document_id),
                            "run_id": str(uuid4()),
                            "semantic_pass_id": str(uuid4()),
                            "assertion_id": str(uuid4()),
                            "evidence_id": str(uuid4()),
                            "concept_key": "integration_threshold",
                            "preferred_label": "Integration Threshold",
                            "review_status": "candidate",
                            "source_filename": "integration-one.pdf",
                            "source_type": "chunk",
                            "page_from": 1,
                            "page_to": 1,
                            "excerpt": "Integration threshold guidance remains in force.",
                            "source_artifact_api_path": "/documents/example/chunks/1",
                            "matched_terms": ["integration threshold"],
                        }
                    ],
                }
            ],
            "sections": [
                {
                    "section_id": "section:integration_governance",
                    "title": "Integration Governance",
                    "summary": (
                        "This section covers one semantic concept from the "
                        "selected corpus scope."
                    ),
                    "focus_concept_keys": ["integration_threshold"],
                    "focus_category_keys": ["integration_governance"],
                    "claim_ids": ["claim:integration_threshold"],
                }
            ],
            "claim_candidates": [
                {
                    "claim_id": "claim:integration_threshold",
                    "section_id": "section:integration_governance",
                    "summary": (
                        "Integration Threshold appears in Integration One with "
                        "2 evidence items across chunk and table sources."
                    ),
                    "concept_keys": ["integration_threshold"],
                    "assertion_ids": [str(uuid4())],
                    "evidence_labels": ["E1"],
                    "source_document_ids": [str(document_id)],
                    "support_level": "supported",
                    "review_policy_status": "candidate_disclosed",
                    "disclosure_note": "Candidate-backed support requires review.",
                }
            ],
            "evidence_pack": [
                {
                    "citation_label": "E1",
                    "document_id": str(document_id),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "assertion_id": str(uuid4()),
                    "evidence_id": str(uuid4()),
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "review_status": "candidate",
                    "source_filename": "integration-one.pdf",
                    "source_type": "chunk",
                    "page_from": 1,
                    "page_to": 1,
                    "excerpt": "Integration threshold guidance remains in force.",
                    "source_artifact_api_path": "/documents/example/chunks/1",
                    "matched_terms": ["integration threshold"],
                }
            ],
            "warnings": [],
            "success_metrics": [
                {
                    "metric_key": "agent_legibility",
                    "stakeholder": "Lopopolo",
                    "passed": True,
                    "summary": "Typed brief ready",
                    "details": {},
                }
            ],
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "semantic_generation_brief",
        "artifact_path": "/tmp/semantic_generation_brief.json",
    }


def test_prepare_semantic_generation_brief_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="prepare_semantic_generation_brief",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.prepare_semantic_generation_brief",
        lambda session, **kwargs: _semantic_generation_brief_output_payload(
            task_id=task.id,
            document_id=document_id,
        )["brief"],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_generation_brief.json",
            },
        )(),
    )

    result = _prepare_semantic_generation_brief_executor(
        session=object(),
        task=task,
        payload=PrepareSemanticGenerationBriefTaskInput(
            title="Integration Governance Brief",
            goal="Summarize the knowledge base guidance on integration governance.",
            audience="Operators",
            document_ids=[document_id],
            target_length="medium",
            review_policy="allow_candidate_with_disclosure",
        ),
    )

    assert result["brief"]["title"] == "Integration Governance Brief"
    assert result["artifact_kind"] == "semantic_generation_brief"


def test_draft_semantic_grounded_document_executor_writes_artifact_and_markdown(
    monkeypatch,
    tmp_path,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_semantic_grounded_document",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    brief_task_id = uuid4()
    document_id = uuid4()
    brief_output = _semantic_generation_brief_output_payload(
        task_id=brief_task_id,
        document_id=document_id,
    )
    draft_payload = {
        "document_kind": "knowledge_brief",
        "title": "Integration Governance Brief",
        "goal": "Summarize the knowledge base guidance on integration governance.",
        "audience": "Operators",
        "review_policy": "allow_candidate_with_disclosure",
        "target_length": "medium",
        "brief_task_id": str(brief_task_id),
        "generator_name": "structured_fallback",
        "generator_model": None,
        "used_fallback": True,
        "required_concept_keys": ["integration_threshold"],
        "document_refs": brief_output["brief"]["document_refs"],
        "assertion_index": brief_output["brief"]["semantic_dossier"][0]["assertions"],
        "sections": [
            {
                "section_id": "section:integration_governance",
                "title": "Integration Governance",
                "body_markdown": "- Integration Threshold appears in Integration One.",
                "claim_ids": ["claim:integration_threshold"],
            }
        ],
        "claims": [
            {
                "claim_id": "claim:integration_threshold",
                "section_id": "section:integration_governance",
                "rendered_text": "Integration Threshold appears in Integration One.",
                "concept_keys": ["integration_threshold"],
                "assertion_ids": [
                    brief_output["brief"]["semantic_dossier"][0]["assertions"][0][
                        "assertion_id"
                    ]
                ],
                "evidence_labels": ["E1"],
                "source_document_ids": [str(document_id)],
                "support_level": "supported",
                "review_policy_status": "candidate_disclosed",
                "disclosure_note": "Candidate-backed support requires review.",
            }
        ],
        "evidence_pack": brief_output["brief"]["evidence_pack"],
        "markdown": "# Integration Governance Brief\n\n## Evidence Appendix\n",
        "markdown_path": None,
        "warnings": [],
        "success_metrics": [],
    }

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, **kwargs: SimpleNamespace(output=brief_output),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.draft_semantic_grounded_document",
        lambda brief_payload, *, brief_task_id: {
            **draft_payload,
            "brief_task_id": brief_task_id,
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.StorageService",
        lambda: type(
            "FakeStorage",
            (),
            {"get_agent_task_dir": lambda self, _task_id: tmp_path},
        )(),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_grounded_document_draft.json",
            },
        )(),
    )

    result = _draft_semantic_grounded_document_executor(
        session=object(),
        task=task,
        payload=DraftSemanticGroundedDocumentTaskInput(target_task_id=brief_task_id),
    )

    assert result["draft"]["brief_task_id"] == brief_task_id
    assert result["artifact_kind"] == "semantic_grounded_document_draft"
    assert Path(result["draft"]["markdown_path"]).name == "semantic_grounded_document.md"
    assert Path(result["draft"]["markdown_path"]).read_text().startswith(
        "# Integration Governance Brief"
    )


def test_verify_semantic_grounded_document_executor_writes_verification_artifact(
    monkeypatch,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_semantic_grounded_document",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    draft_task_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_semantic_grounded_document_task",
        lambda session, task, payload: {
            "draft": {
                "document_kind": "knowledge_brief",
                "title": "Integration Governance Brief",
                "goal": "Summarize the knowledge base guidance on integration governance.",
                "audience": "Operators",
                "review_policy": "allow_candidate_with_disclosure",
                "target_length": "medium",
                "brief_task_id": str(uuid4()),
                "generator_name": "structured_fallback",
                "generator_model": None,
                "used_fallback": True,
                "required_concept_keys": ["integration_threshold"],
                "document_refs": [],
                "assertion_index": [],
                "sections": [],
                "claims": [],
                "evidence_pack": [],
                "markdown": "# Integration Governance Brief\n",
                "markdown_path": "/tmp/semantic_grounded_document.md",
                "warnings": [],
                "success_metrics": [],
            },
            "summary": {
                "claim_count": 1,
                "unsupported_claim_count": 0,
                "required_concept_coverage_ratio": 1.0,
            },
            "success_metrics": [],
            "verification": {
                "verification_id": str(uuid4()),
                "target_task_id": str(draft_task_id),
                "verification_task_id": str(task.id),
                "verifier_type": "semantic_grounded_document_gate",
                "outcome": "passed",
                "metrics": {"claim_count": 1},
                "reasons": [],
                "details": {},
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_grounded_document_verification.json",
            },
        )(),
    )

    result = _verify_semantic_grounded_document_executor(
        session=object(),
        task=task,
        payload=VerifySemanticGroundedDocumentTaskInput(target_task_id=draft_task_id),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "semantic_grounded_document_verification"
