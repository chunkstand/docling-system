from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ApplySemanticRegistryUpdateTaskInput,
    DiscoverSemanticBootstrapCandidatesTaskInput,
    DraftSemanticRegistryUpdateTaskInput,
    LatestSemanticPassTaskInput,
    TriageSemanticPassTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
)
from app.services.agent_actions.semantic_analysis_actions import (
    _discover_semantic_bootstrap_candidates_executor,
    _latest_semantic_pass_executor,
)
from app.services.agent_actions.semantic_governance_actions import (
    _apply_semantic_registry_update_executor,
    _draft_semantic_registry_update_executor,
    _verify_draft_semantic_registry_update_executor,
)
from app.services.agent_actions.semantic_verification_actions import (
    _triage_semantic_pass_executor,
)
from tests.unit.agent_task_actions_support import _semantic_pass_response


def test_latest_semantic_pass_executor_returns_typed_output(monkeypatch) -> None:
    semantic_pass = _semantic_pass_response()
    document_id = semantic_pass.document_id

    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.get_active_semantic_pass_detail",
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
        "app.services.agent_actions.semantic_verification_actions.resolve_required_dependency_task_output_context",
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
        "app.services.agent_actions.semantic_verification_actions.triage_semantic_pass",
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
        "app.services.agent_actions.semantic_verification_actions.create_agent_task_verification_record",
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
        "app.services.agent_actions.semantic_verification_actions.create_agent_task_artifact",
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
    session = SimpleNamespace(
        get=lambda model, key: (
            AgentTask(
                id=source_task_id,
                task_type="triage_semantic_pass",
                status="completed",
                priority=100,
                side_effect_level="read_only",
                requires_approval=False,
                input_json={},
                result_json={},
                workflow_version="v1",
                model_settings_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
            if model is AgentTask and key == source_task_id
            else None
        )
    )

    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
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
        "app.services.agent_actions.semantic_governance_actions.draft_semantic_registry_update",
        lambda session, gap_report, **kwargs: {
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
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_registry_draft.json",
        ),
    )

    result = _draft_semantic_registry_update_executor(
        session=session,
        task=task,
        payload=DraftSemanticRegistryUpdateTaskInput(
            source_task_id=source_task_id,
            rationale="add the missing alias",
        ),
    )

    assert result["draft"]["proposed_registry_version"] == "semantics-layer-foundation-alpha.3"
    assert result["artifact_kind"] == "semantic_registry_draft"

def test_discover_semantic_bootstrap_candidates_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="discover_semantic_bootstrap_candidates",
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
        "app.services.agent_actions.semantic_analysis_actions.discover_semantic_bootstrap_candidates",
        lambda session, **kwargs: {
            "report_name": "semantic_bootstrap_candidate_report",
            "extraction_strategy": "corpus_phrase_mining_v1",
            "input_document_ids": [str(document_id)],
            "document_count": 1,
            "total_source_count": 2,
            "existing_registry_term_exclusion": True,
            "candidate_count": 1,
            "candidates": [
                {
                    "candidate_id": "bootstrap:incident_response_latency",
                    "concept_key": "incident_response_latency",
                    "preferred_label": "Incident Response Latency",
                    "normalized_phrase": "incident response latency",
                    "phrase_tokens": ["incident", "response", "latency"],
                    "epistemic_status": "candidate_bootstrap",
                    "document_ids": [str(document_id)],
                    "document_count": 1,
                    "source_count": 2,
                    "source_types": ["chunk", "table"],
                    "score": 0.88,
                    "evidence_refs": [],
                    "details": {},
                }
            ],
            "warnings": [],
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_bootstrap_candidate_report.json",
        ),
    )

    result = _discover_semantic_bootstrap_candidates_executor(
        session=object(),
        task=task,
        payload=DiscoverSemanticBootstrapCandidatesTaskInput(document_ids=[document_id]),
    )

    assert result["report"]["candidate_count"] == 1
    assert result["artifact_kind"] == "semantic_bootstrap_candidate_report"

def test_draft_semantic_registry_update_executor_supports_bootstrap_source(monkeypatch) -> None:
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
    session = SimpleNamespace(
        get=lambda model, key: (
            AgentTask(
                id=source_task_id,
                task_type="discover_semantic_bootstrap_candidates",
                status="completed",
                priority=100,
                side_effect_level="read_only",
                requires_approval=False,
                input_json={},
                result_json={},
                workflow_version="v1",
                model_settings_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
            if model is AgentTask and key == source_task_id
            else None
        )
    )

    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            task_id=source_task_id,
            task_type="discover_semantic_bootstrap_candidates",
            output={
                "report": {
                    "report_name": "semantic_bootstrap_candidate_report",
                    "extraction_strategy": "corpus_phrase_mining_v1",
                    "input_document_ids": [str(uuid4())],
                    "document_count": 1,
                    "total_source_count": 2,
                    "existing_registry_term_exclusion": True,
                    "candidate_count": 1,
                    "candidates": [
                        {
                            "candidate_id": "bootstrap:incident_response_latency",
                            "concept_key": "incident_response_latency",
                            "preferred_label": "Incident Response Latency",
                            "normalized_phrase": "incident response latency",
                            "phrase_tokens": ["incident", "response", "latency"],
                            "epistemic_status": "candidate_bootstrap",
                            "document_ids": [str(uuid4())],
                            "document_count": 1,
                            "source_count": 2,
                            "source_types": ["chunk", "table"],
                            "score": 0.88,
                            "evidence_refs": [],
                            "details": {},
                        }
                    ],
                    "warnings": [],
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_bootstrap_candidate_report",
                "artifact_path": "/tmp/semantic_bootstrap_candidate_report.json",
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.draft_semantic_registry_update_from_bootstrap_report",
        lambda session, report, **kwargs: {
            "base_registry_version": "semantics-layer-foundation-alpha.2",
            "proposed_registry_version": "semantics-layer-foundation-alpha.3",
            "source_task_id": kwargs["source_task_id"],
            "source_task_type": kwargs["source_task_type"],
            "rationale": kwargs["rationale"],
            "document_ids": report["input_document_ids"],
            "operations": [
                {
                    "operation_id": (
                        "add_concept:incident_response_latency:incident_response_latency"
                    ),
                    "operation_type": "add_concept",
                    "concept_key": "incident_response_latency",
                    "alias_text": None,
                    "category_key": None,
                    "source_issue_ids": ["bootstrap:incident_response_latency"],
                    "rationale": "bootstrap concept",
                }
            ],
            "effective_registry": {"registry_version": "semantics-layer-foundation-alpha.3"},
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_registry_draft.json",
        ),
    )

    result = _draft_semantic_registry_update_executor(
        session=session,
        task=task,
        payload=DraftSemanticRegistryUpdateTaskInput(
            source_task_id=source_task_id,
            rationale="bootstrap the registry from corpus evidence",
        ),
    )

    assert result["draft"]["operations"][0]["operation_type"] == "add_concept"
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
        "app.services.agent_actions.semantic_governance_actions.verify_draft_semantic_registry_update_task",
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
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
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
    committed = {"value": False}
    fake_session = SimpleNamespace(commit=lambda: committed.__setitem__("value", True))
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
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
        lambda session, task_id, depends_on_task_id, expected_task_type, **kwargs: dependencies[
            (expected_task_type, depends_on_task_id)
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.persist_semantic_ontology_snapshot",
        lambda session, payload, **kwargs: SimpleNamespace(id=uuid4()),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.get_semantic_registry",
        lambda session: SimpleNamespace(
            registry_version="semantics-layer-foundation-alpha.3",
            sha256="new-registry-sha",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/applied_semantic_registry_update.json",
        ),
    )

    result = _apply_semantic_registry_update_executor(
        session=fake_session,
        task=task,
        payload=ApplySemanticRegistryUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish the verified registry update",
        ),
    )

    assert result["applied_registry_version"] == "semantics-layer-foundation-alpha.3"
    assert result["applied_registry_sha256"] == "new-registry-sha"
    assert result["config_path"].startswith("db://semantic_ontology_snapshots/")
    assert result["artifact_kind"] == "applied_semantic_registry_update"
    assert committed["value"] is True
