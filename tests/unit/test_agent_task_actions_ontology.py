from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ApplyOntologyExtensionTaskInput,
    DraftOntologyExtensionTaskInput,
    GetActiveOntologySnapshotTaskInput,
    InitializeWorkspaceOntologyTaskInput,
    VerifyDraftOntologyExtensionTaskInput,
)
from app.services.agent_actions.semantic_analysis_actions import (
    _get_active_ontology_snapshot_executor,
    _initialize_workspace_ontology_executor,
)
from app.services.agent_actions.semantic_governance_actions import (
    _apply_ontology_extension_executor,
    _draft_ontology_extension_executor,
    _verify_draft_ontology_extension_executor,
)


def test_initialize_workspace_ontology_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="initialize_workspace_ontology",
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
    snapshot_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.initialize_workspace_ontology",
        lambda session: {
            "snapshot": {
                "snapshot_id": snapshot_id,
                "ontology_name": "portable_upper_ontology",
                "ontology_version": "portable-upper-ontology-v1",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "sha256": "ontology-sha",
                "source_kind": "upper_seed",
                "source_task_id": None,
                "source_task_type": None,
                "concept_count": 0,
                "category_count": 0,
                "relation_count": 1,
                "relation_keys": ["document_mentions_concept"],
                "created_at": datetime.now(UTC).isoformat(),
                "activated_at": datetime.now(UTC).isoformat(),
            },
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/active_ontology_snapshot.json",
        ),
    )

    result = _initialize_workspace_ontology_executor(
        session=object(),
        task=task,
        _payload=InitializeWorkspaceOntologyTaskInput(),
    )

    assert result["snapshot"]["snapshot_id"] == snapshot_id
    assert result["artifact_kind"] == "active_ontology_snapshot"

def test_get_active_ontology_snapshot_executor_returns_payload(monkeypatch) -> None:
    snapshot_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.get_active_ontology_snapshot_payload",
        lambda session: {
            "snapshot": {
                "snapshot_id": snapshot_id,
                "ontology_name": "portable_upper_ontology",
                "ontology_version": "portable-upper-ontology-v1",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "sha256": "ontology-sha",
                "source_kind": "upper_seed",
                "source_task_id": None,
                "source_task_type": None,
                "concept_count": 0,
                "category_count": 0,
                "relation_count": 1,
                "relation_keys": ["document_mentions_concept"],
                "created_at": datetime.now(UTC).isoformat(),
                "activated_at": datetime.now(UTC).isoformat(),
            },
            "success_metrics": [],
        },
    )

    result = _get_active_ontology_snapshot_executor(
        session=object(),
        _task=object(),
        _payload=GetActiveOntologySnapshotTaskInput(),
    )

    assert result["snapshot"]["snapshot_id"] == snapshot_id

def test_draft_ontology_extension_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_ontology_extension",
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
    source_task_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output={
                "report": {
                    "input_document_ids": [str(uuid4())],
                    "candidate_count": 1,
                    "candidates": [
                        {
                            "candidate_id": "bootstrap:incident_response_latency",
                            "concept_key": "incident_response_latency",
                            "preferred_label": "Incident Response Latency",
                            "normalized_phrase": "incident response latency",
                            "phrase_tokens": ["incident", "response", "latency"],
                            "document_ids": [str(uuid4())],
                            "document_count": 1,
                            "source_count": 2,
                            "source_types": ["chunk"],
                            "score": 0.84,
                            "evidence_refs": [],
                            "details": {},
                        }
                    ],
                    "warnings": [],
                    "success_metrics": [],
                    "extraction_strategy": "phrase_mining_v1",
                    "document_count": 1,
                    "total_source_count": 2,
                    "existing_registry_term_exclusion": True,
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_bootstrap_candidate_report",
                "artifact_path": "/tmp/semantic_bootstrap_candidate_report.json",
            },
            task_type="discover_semantic_bootstrap_candidates",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.draft_ontology_extension_from_bootstrap_report",
        lambda session, report, **kwargs: {
            "base_snapshot_id": uuid4(),
            "base_ontology_version": "portable-upper-ontology-v1",
            "proposed_ontology_version": "portable-upper-ontology-v1.1",
            "upper_ontology_version": "portable-upper-ontology-v1",
            "source_task_id": source_task_id,
            "source_task_type": "discover_semantic_bootstrap_candidates",
            "rationale": kwargs["rationale"],
            "document_ids": [uuid4()],
            "operations": [
                {
                    "operation_id": "add_concept:incident_response_latency",
                    "operation_type": "add_concept",
                    "concept_key": "incident_response_latency",
                    "preferred_label": "Incident Response Latency",
                    "alias_text": None,
                    "category_key": None,
                    "source_issue_ids": [],
                    "rationale": "bootstrap discovery",
                }
            ],
            "effective_ontology": {"registry_version": "portable-upper-ontology-v1.1"},
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/ontology_extension_draft.json",
        ),
    )
    session = SimpleNamespace(
        get=lambda model, key: SimpleNamespace(task_type="discover_semantic_bootstrap_candidates")
    )

    result = _draft_ontology_extension_executor(
        session=session,
        task=task,
        payload=DraftOntologyExtensionTaskInput(
            source_task_id=source_task_id,
            rationale="extend ontology from corpus evidence",
        ),
    )

    assert result["draft"]["proposed_ontology_version"] == "portable-upper-ontology-v1.1"
    assert result["artifact_kind"] == "ontology_extension_draft"

def test_verify_draft_ontology_extension_executor_writes_verification_artifact(
    monkeypatch,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_ontology_extension",
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
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            task_id=draft_task_id,
            task_type="draft_ontology_extension",
            output={
                "draft": {
                    "base_snapshot_id": str(uuid4()),
                    "base_ontology_version": "portable-upper-ontology-v1",
                    "proposed_ontology_version": "portable-upper-ontology-v1.1",
                    "upper_ontology_version": "portable-upper-ontology-v1",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "discover_semantic_bootstrap_candidates",
                    "rationale": "extend ontology from corpus evidence",
                    "document_ids": [str(uuid4())],
                    "operations": [],
                    "effective_ontology": {"registry_version": "portable-upper-ontology-v1.1"},
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "ontology_extension_draft",
                "artifact_path": "/tmp/ontology_extension_draft.json",
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.verify_draft_ontology_extension",
        lambda session, draft, **kwargs: (
            [],
            {"document_count": 1, "improved_document_count": 1, "regressed_document_count": 0},
            {"document_count": 1},
            [],
            "passed",
            [],
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(draft_task_id),
                "verification_task_id": str(task.id),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/ontology_extension_draft_verification.json",
        ),
    )

    result = _verify_draft_ontology_extension_executor(
        session=object(),
        task=task,
        payload=VerifyDraftOntologyExtensionTaskInput(target_task_id=draft_task_id),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "ontology_extension_draft_verification"

def test_apply_ontology_extension_executor_writes_artifact(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="apply_ontology_extension",
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
    dependencies = {
        ("draft_ontology_extension", draft_task_id): SimpleNamespace(
            output={
                "draft": {
                    "base_snapshot_id": str(uuid4()),
                    "base_ontology_version": "portable-upper-ontology-v1",
                    "proposed_ontology_version": "portable-upper-ontology-v1.1",
                    "upper_ontology_version": "portable-upper-ontology-v1",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "discover_semantic_bootstrap_candidates",
                    "rationale": "extend ontology from corpus evidence",
                    "document_ids": [str(uuid4())],
                    "operations": [],
                    "effective_ontology": {"registry_version": "portable-upper-ontology-v1.1"},
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "ontology_extension_draft",
                "artifact_path": "/tmp/ontology_extension_draft.json",
            }
        ),
        ("verify_draft_ontology_extension", verification_task_id): SimpleNamespace(
            output={
                "draft": {
                    "base_snapshot_id": str(uuid4()),
                    "base_ontology_version": "portable-upper-ontology-v1",
                    "proposed_ontology_version": "portable-upper-ontology-v1.1",
                    "upper_ontology_version": "portable-upper-ontology-v1",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "discover_semantic_bootstrap_candidates",
                    "rationale": "extend ontology from corpus evidence",
                    "document_ids": [str(uuid4())],
                    "operations": [],
                    "effective_ontology": {"registry_version": "portable-upper-ontology-v1.1"},
                    "success_metrics": [],
                },
                "document_deltas": [],
                "summary": {},
                "success_metrics": [],
                "verification": {
                    "verification_id": str(uuid4()),
                    "target_task_id": str(draft_task_id),
                    "verification_task_id": str(verification_task_id),
                    "verifier_type": "ontology_extension_draft_gate",
                    "outcome": "passed",
                    "metrics": {"document_count": 1},
                    "reasons": [],
                    "details": {},
                    "created_at": datetime.now(UTC).isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "ontology_extension_draft_verification",
                "artifact_path": "/tmp/ontology_extension_draft_verification.json",
            }
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
        lambda session, task_id, depends_on_task_id, expected_task_type, **kwargs: dependencies[
            (expected_task_type, depends_on_task_id)
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.apply_ontology_extension",
        lambda session, draft, **kwargs: {
            "applied_snapshot_id": uuid4(),
            "applied_ontology_version": "portable-upper-ontology-v1.1",
            "applied_ontology_sha256": "ontology-sha",
            "upper_ontology_version": "portable-upper-ontology-v1",
            "reason": kwargs["reason"],
            "applied_operations": [],
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/applied_ontology_extension.json",
        ),
    )

    result = _apply_ontology_extension_executor(
        session=object(),
        task=task,
        payload=ApplyOntologyExtensionTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish verified ontology extension",
        ),
    )

    assert result["applied_ontology_version"] == "portable-upper-ontology-v1.1"
    assert result["artifact_kind"] == "applied_ontology_extension"
