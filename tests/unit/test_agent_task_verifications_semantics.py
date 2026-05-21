from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact, AgentTaskDependency
from app.schemas.agent_tasks import (
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifySemanticGroundedDocumentTaskInput,
)
from app.services.agent_task_verifications import (
    verify_draft_semantic_registry_update_task,
    verify_semantic_grounded_document_task,
)
from tests.unit.agent_task_verification_support import FakeSession


def test_verify_draft_semantic_registry_update_task_uses_migrated_context_output(
    monkeypatch,
) -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    document_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="draft_semantic_registry_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_draft_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    artifact = AgentTaskArtifact(
        id=uuid4(),
        task_id=target_task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(target_task_id),
            "task_type": "draft_semantic_registry_update",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "draft_semantic_registry_update_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Semantic draft ready"},
            "refs": [],
            "output": {
                "draft": {
                    "base_registry_version": "semantics-layer-foundation-alpha.2",
                    "proposed_registry_version": "semantics-layer-foundation-alpha.3",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "triage_semantic_pass",
                    "rationale": "add the missing alias",
                    "document_ids": [str(document_id)],
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
        },
        created_at=now,
    )
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=target_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    session = FakeSession(
        tasks={target_task_id: target_task, verification_task_id: verification_task},
        replay_runs={},
        artifacts={artifact.id: artifact},
        dependencies={(verification_task_id, target_task_id): dependency},
    )

    monkeypatch.setattr(
        "app.services.agent_task_verifications.preview_semantic_registry_update_for_document",
        lambda session, requested_document_id, registry_payload: {
            "document_id": requested_document_id,
            "run_id": uuid4(),
            "evaluation_fixture_name": "semantic_fixture",
            "before_all_expectations_passed": False,
            "after_all_expectations_passed": True,
            "before_failed_expectations": 1,
            "after_failed_expectations": 0,
            "before_assertion_count": 0,
            "after_assertion_count": 1,
            "added_concept_keys": ["integration_threshold"],
            "removed_concept_keys": [],
            "introduced_expected_concepts": ["integration_threshold"],
            "regressed_expected_concepts": [],
        },
    )

    result = verify_draft_semantic_registry_update_task(
        session,
        verification_task,
        VerifyDraftSemanticRegistryUpdateTaskInput(target_task_id=target_task_id),
    )

    assert result["draft"]["proposed_registry_version"] == "semantics-layer-foundation-alpha.3"
    assert result["summary"]["improved_document_count"] == 1
    assert result["verification"]["outcome"] == "passed"


def test_verify_draft_semantic_registry_update_task_rejects_pre_context_drafts() -> None:
    target_task_id = uuid4()
    verification_task_id = uuid4()
    now = datetime.now(UTC)
    target_task = AgentTask(
        id=target_task_id,
        task_type="draft_semantic_registry_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={"payload": {"draft": {"proposed_registry_version": "legacy"}}},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_draft_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=target_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    session = FakeSession(
        tasks={target_task_id: target_task, verification_task_id: verification_task},
        replay_runs={},
        dependencies={(verification_task_id, target_task_id): dependency},
    )

    try:
        verify_draft_semantic_registry_update_task(
            session,
            verification_task,
            VerifyDraftSemanticRegistryUpdateTaskInput(target_task_id=target_task_id),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "rerun after the context migration" in exc.detail["message"]
    else:
        raise AssertionError("Expected legacy semantic draft task to be rejected")


def test_verify_semantic_grounded_document_task_uses_migrated_context_output() -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    now = datetime.now(UTC)
    draft_task = AgentTask(
        id=draft_task_id,
        task_type="draft_semantic_grounded_document",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=verification_task_id,
        task_type="verify_semantic_grounded_document",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    dependency = AgentTaskDependency(
        task_id=verification_task_id,
        depends_on_task_id=draft_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    assertion_id = uuid4()
    draft_context_artifact = AgentTaskArtifact(
        id=uuid4(),
        task_id=draft_task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(draft_task_id),
            "task_type": "draft_semantic_grounded_document",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "draft_semantic_grounded_document_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Draft ready"},
            "refs": [],
            "output": {
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
                    "assertion_index": [
                        {
                            "document_id": str(uuid4()),
                            "run_id": str(uuid4()),
                            "semantic_pass_id": str(uuid4()),
                            "assertion_id": str(assertion_id),
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
                            "assertion_ids": [str(assertion_id)],
                            "evidence_labels": ["E1"],
                            "source_document_ids": [str(uuid4())],
                            "support_level": "supported",
                            "review_policy_status": "candidate_disclosed",
                            "disclosure_note": "Candidate-backed support requires review.",
                        }
                    ],
                    "evidence_pack": [
                        {
                            "citation_label": "E1",
                            "document_id": str(uuid4()),
                            "run_id": str(uuid4()),
                            "semantic_pass_id": str(uuid4()),
                            "assertion_id": str(assertion_id),
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
                    "markdown": "# Integration Governance Brief\n",
                    "markdown_path": "/tmp/semantic_grounded_document.md",
                    "warnings": [],
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_grounded_document_draft",
                "artifact_path": "/tmp/semantic_grounded_document_draft.json",
            },
        },
        created_at=now,
    )
    session = FakeSession(
        tasks={draft_task_id: draft_task, verification_task_id: verification_task},
        replay_runs={},
        artifacts={draft_context_artifact.id: draft_context_artifact},
        dependencies={(verification_task_id, draft_task_id): dependency},
    )

    result = verify_semantic_grounded_document_task(
        session,
        verification_task,
        VerifySemanticGroundedDocumentTaskInput(target_task_id=draft_task_id),
    )

    assert result["summary"]["claim_count"] == 1
    assert result["verification"]["outcome"] == "passed"
