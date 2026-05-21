from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact, AgentTaskDependency
from app.services.agent_task_context import build_agent_task_context
from tests.unit.agent_task_context_semantic_graph_promotions_support import (
    FakeSession,
    apply_graph_promotions_output_payload,
    build_context_artifact,
    build_task_context_payload,
    draft_graph_promotions_output_payload,
    graph_triage_output_payload,
    verify_graph_promotions_output_payload,
)


def test_build_agent_task_context_for_draft_graph_promotions_includes_source_ref() -> None:
    now = datetime.now(UTC)
    source_task_id = uuid4()
    task_id = uuid4()
    artifact_id = uuid4()
    source_task = AgentTask(
        id=source_task_id,
        task_type="triage_semantic_graph_disagreements",
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
        task_type="draft_graph_promotions",
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
    source_output = graph_triage_output_payload(
        evaluation_task_id=uuid4(),
        verification_id=uuid4(),
    )
    source_context_artifact = build_context_artifact(
        task_id=source_task_id,
        payload=build_task_context_payload(
            task_id=source_task_id,
            task_type="triage_semantic_graph_disagreements",
            output_schema_name="triage_semantic_graph_disagreements_output",
            output=source_output,
            updated_at=now,
        ),
    )
    output = draft_graph_promotions_output_payload(
        source_task_id=source_task_id,
        source_task_type="triage_semantic_graph_disagreements",
        artifact_id=artifact_id,
    )
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="semantic_graph_promotion_draft",
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

    assert context.summary.metrics["promoted_edge_count"] == 1
    assert context.refs[0].ref_kind == "task_output"


def test_build_agent_task_context_for_apply_graph_promotions_includes_dependencies() -> None:
    now = datetime.now(UTC)
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    task_id = uuid4()
    artifact_id = uuid4()
    draft_task = AgentTask(
        id=draft_task_id,
        task_type="draft_graph_promotions",
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
        task_type="verify_draft_graph_promotions",
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
        task_type="apply_graph_promotions",
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
    draft_output = draft_graph_promotions_output_payload(
        source_task_id=uuid4(),
        source_task_type="triage_semantic_graph_disagreements",
    )
    verification_output = verify_graph_promotions_output_payload(
        draft_task_id=draft_task_id,
        verification_task_id=verification_task_id,
    )
    draft_context_artifact = build_context_artifact(
        task_id=draft_task_id,
        payload=build_task_context_payload(
            task_id=draft_task_id,
            task_type="draft_graph_promotions",
            output_schema_name="draft_graph_promotions_output",
            output=draft_output,
            updated_at=now,
        ),
    )
    verification_context_artifact = build_context_artifact(
        task_id=verification_task_id,
        payload=build_task_context_payload(
            task_id=verification_task_id,
            task_type="verify_draft_graph_promotions",
            output_schema_name="verify_draft_graph_promotions_output",
            output=verification_output,
            updated_at=now,
        ),
    )
    output = apply_graph_promotions_output_payload(
        draft_task_id=draft_task_id,
        verification_task_id=verification_task_id,
        artifact_id=artifact_id,
    )
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="applied_semantic_graph_snapshot",
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
        ),
        task,
        {"payload": output},
    )

    assert context.summary.approval_state == "approved"
    assert context.summary.metrics["applied_edge_count"] == 1
    assert [ref.ref_kind for ref in context.refs[:2]] == ["task_output", "task_output"]
