from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact
from app.services.agent_task_context import build_agent_task_context
from tests.unit.agent_task_context_semantic_governance_support import (
    FakeSession,
    bootstrap_discovery_output_payload,
    initialize_ontology_output_payload,
)


def test_build_agent_task_context_for_bootstrap_discovery_includes_artifact_ref() -> None:
    now = datetime.now(UTC)
    task_id = uuid4()
    document_id = uuid4()
    task = AgentTask(
        id=task_id,
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
    output = bootstrap_discovery_output_payload(document_id=document_id)
    artifact_id = UUID(output["artifact_id"])
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="semantic_bootstrap_candidate_report",
        storage_path=output["artifact_path"],
        payload_json=output["report"],
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(tasks={task_id: task}, artifacts={artifact_id: artifact}),
        task,
        {"payload": output},
    )

    assert context.summary.next_action == (
        "Create draft_semantic_registry_update to turn selected bootstrap candidates into "
        "a reviewable additive registry draft."
    )
    assert context.summary.metrics["candidate_count"] == 1
    assert context.refs[0].artifact_kind == "semantic_bootstrap_candidate_report"


def test_build_agent_task_context_for_initialize_workspace_ontology_snapshot_artifact() -> None:
    now = datetime.now(UTC)
    task_id = uuid4()
    artifact_id = uuid4()
    task = AgentTask(
        id=task_id,
        task_type="initialize_workspace_ontology",
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
    output = initialize_ontology_output_payload(artifact_id=artifact_id)
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="active_ontology_snapshot",
        storage_path=output["artifact_path"],
        payload_json=output["snapshot"],
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(tasks={task_id: task}, artifacts={artifact_id: artifact}),
        task,
        {"payload": output},
    )

    assert context.summary.next_action.startswith("Ingest documents or create")
    assert context.refs[0].artifact_kind == "active_ontology_snapshot"
