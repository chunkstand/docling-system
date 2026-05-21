from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskVerification,
)
from app.services.agent_task_context import build_agent_task_context
from tests.unit.agent_task_context_semantic_governance_support import (
    FakeSession,
    apply_ontology_output_payload,
    bootstrap_discovery_output_payload,
    build_context_artifact,
    build_task_context_payload,
    draft_ontology_output_payload,
    manual_lifecycle_draft_ontology_output_payload,
    verify_draft_ontology_output_payload,
)


def test_build_agent_task_context_for_draft_ontology_extension_includes_source_ref() -> None:
    now = datetime.now(UTC)
    source_task_id = uuid4()
    task_id = uuid4()
    artifact_id = uuid4()
    source_task = AgentTask(
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
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    task = AgentTask(
        id=task_id,
        task_type="draft_ontology_extension",
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
    source_output = bootstrap_discovery_output_payload(document_id=uuid4())
    source_context_artifact = build_context_artifact(
        task_id=source_task_id,
        payload=build_task_context_payload(
            task_id=source_task_id,
            task_type="discover_semantic_bootstrap_candidates",
            output_schema_name="discover_semantic_bootstrap_candidates_output",
            output=source_output,
            updated_at=now,
        ),
    )
    output = draft_ontology_output_payload(
        source_task_id=source_task_id,
        source_task_type="discover_semantic_bootstrap_candidates",
        artifact_id=artifact_id,
    )
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="ontology_extension_draft",
        storage_path=output["artifact_path"],
        payload_json=output["draft"],
        created_at=now,
    )
    dependency = AgentTaskDependency(
        task_id=task_id,
        depends_on_task_id=source_task_id,
        dependency_kind="source_task",
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(
            tasks={source_task_id: source_task, task_id: task},
            artifacts={
                source_context_artifact.id: source_context_artifact,
                artifact_id: artifact,
            },
            dependencies={uuid4(): dependency},
        ),
        task,
        {"payload": output},
    )

    assert context.summary.next_action == (
        "Create verify_draft_ontology_extension before any ontology publication step."
    )
    assert context.refs[0].ref_kind == "task_output"
    assert context.refs[1].artifact_kind == "ontology_extension_draft"
    assert context.output["draft"]["ontology_slice_count"] == 5
    assert context.output["draft"]["ontology_slices"][0]["slice_key"] == "core"


def test_build_agent_task_context_for_manual_lifecycle_draft_has_no_source_ref() -> None:
    now = datetime.now(UTC)
    task_id = uuid4()
    artifact_id = uuid4()
    task = AgentTask(
        id=task_id,
        task_type="draft_ontology_extension",
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
    output = manual_lifecycle_draft_ontology_output_payload(artifact_id=artifact_id)
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="ontology_extension_draft",
        storage_path=output["artifact_path"],
        payload_json=output["draft"],
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(tasks={task_id: task}, artifacts={artifact_id: artifact}),
        task,
        {"payload": output},
    )

    assert len(context.refs) == 1
    assert context.refs[0].artifact_kind == "ontology_extension_draft"
    assert context.summary.metrics["operation_count"] == 1
    assert context.output["draft"]["source_task_id"] is None
    assert context.output["draft"]["operations"][0]["operation_type"] == "replace_concept"


def test_build_agent_task_context_for_apply_ontology_extension_includes_dependencies() -> None:
    now = datetime.now(UTC)
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    task_id = uuid4()
    artifact_id = uuid4()
    draft_task = AgentTask(
        id=draft_task_id,
        task_type="draft_ontology_extension",
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
        task_type="verify_draft_ontology_extension",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    task = AgentTask(
        id=task_id,
        task_type="apply_ontology_extension",
        status="completed",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
        approved_at=now,
    )
    draft_output = draft_ontology_output_payload(
        source_task_id=uuid4(),
        source_task_type="discover_semantic_bootstrap_candidates",
    )
    verification_output = verify_draft_ontology_output_payload(
        draft_task_id=draft_task_id,
        include_lifecycle_preview=True,
    )
    draft_context_artifact = build_context_artifact(
        task_id=draft_task_id,
        payload=build_task_context_payload(
            task_id=draft_task_id,
            task_type="draft_ontology_extension",
            output_schema_name="draft_ontology_extension_output",
            output=draft_output,
            updated_at=now,
        ),
    )
    verification_context_artifact = build_context_artifact(
        task_id=verification_task_id,
        payload=build_task_context_payload(
            task_id=verification_task_id,
            task_type="verify_draft_ontology_extension",
            output_schema_name="verify_draft_ontology_extension_output",
            output=verification_output,
            updated_at=now,
        ),
    )
    verification_row = AgentTaskVerification(
        id=UUID(verification_output["verification"]["verification_id"]),
        target_task_id=draft_task_id,
        verification_task_id=verification_task_id,
        verifier_type="ontology_extension_gate",
        outcome="passed",
        metrics_json={"improved_document_count": 1},
        reasons_json=[],
        details_json={},
        created_at=now,
        completed_at=now,
    )
    output = apply_ontology_output_payload(
        draft_task_id=draft_task_id,
        verification_task_id=verification_task_id,
        artifact_id=artifact_id,
        include_lifecycle_preview=True,
    )
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="applied_ontology_extension",
        storage_path=output["artifact_path"],
        payload_json=output,
        created_at=now,
    )
    draft_dependency = AgentTaskDependency(
        task_id=task_id,
        depends_on_task_id=draft_task_id,
        dependency_kind="draft_task",
        created_at=now,
    )
    verification_dependency = AgentTaskDependency(
        task_id=task_id,
        depends_on_task_id=verification_task_id,
        dependency_kind="verification_task",
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(
            tasks={
                draft_task_id: draft_task,
                verification_task_id: verification_task,
                task_id: task,
            },
            artifacts={
                draft_context_artifact.id: draft_context_artifact,
                verification_context_artifact.id: verification_context_artifact,
                artifact_id: artifact,
            },
            dependencies={
                uuid4(): draft_dependency,
                uuid4(): verification_dependency,
            },
            verifications={verification_row.id: verification_row},
        ),
        task,
        {"payload": output},
    )

    assert context.summary.approval_state == "approved"
    assert context.summary.metrics["operation_count"] == 1
    assert context.summary.metrics["lifecycle_preview_required"] is True
    assert context.summary.metrics["lifecycle_preview_evidence_complete"] is True
    assert [ref.ref_kind for ref in context.refs[:2]] == ["task_output", "task_output"]
    assert context.output["ontology_slice_count"] == 5
    assert context.output["lifecycle_preview"]["evidence_complete"] is True
    assert context.output["competency_families"][0]["family_key"] == "claim_support"
