from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskDependency, AgentTaskVerification
from app.services.agent_task_context import build_agent_task_context
from tests.unit.agent_task_context_reports_claim_support_support import (
    FakeSession,
    build_context_artifact,
    build_task_context_payload,
    claim_support_judge_evaluation_output_payload,
    draft_grounded_document_output,
    prepare_generation_brief_output,
)


def test_build_agent_task_context_for_prepare_semantic_generation_brief_includes_artifact_ref() -> (
    None
):
    now = datetime.now(UTC)
    task_id = uuid4()
    artifact_id = uuid4()
    task = AgentTask(
        id=task_id,
        task_type="prepare_semantic_generation_brief",
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
    output = prepare_generation_brief_output(task_id=task_id)
    output["artifact_id"] = str(artifact_id)
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="semantic_generation_brief",
        storage_path="/tmp/semantic_generation_brief.json",
        payload_json=output["brief"],
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(tasks={task_id: task}, artifacts={artifact_id: artifact}),
        task,
        {"payload": output},
    )

    assert context is not None
    assert context.summary.next_action == (
        "Create draft_semantic_grounded_document to render a grounded knowledge brief."
    )
    assert context.refs[0].artifact_kind == "semantic_generation_brief"


def test_build_agent_task_context_for_draft_semantic_grounded_document_includes_target_ref() -> (
    None
):
    now = datetime.now(UTC)
    brief_task_id = uuid4()
    draft_task_id = uuid4()
    artifact_id = uuid4()
    brief_task = AgentTask(
        id=brief_task_id,
        task_type="prepare_semantic_generation_brief",
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
    brief_output = prepare_generation_brief_output(task_id=brief_task_id)
    brief_context_artifact = build_context_artifact(
        task_id=brief_task_id,
        payload=build_task_context_payload(
            task_id=brief_task_id,
            task_type="prepare_semantic_generation_brief",
            output_schema_name="prepare_semantic_generation_brief_output",
            output=brief_output,
            updated_at=now,
        ),
    )
    draft_artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=draft_task_id,
        attempt_id=None,
        artifact_kind="semantic_grounded_document_draft",
        storage_path="/tmp/semantic_grounded_document_draft.json",
        payload_json=draft_grounded_document_output(
            brief_task_id=brief_task_id,
            artifact_id=artifact_id,
        )["draft"],
        created_at=now,
    )
    dependency = AgentTaskDependency(
        task_id=draft_task_id,
        depends_on_task_id=brief_task_id,
        dependency_kind="target_task",
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(
            tasks={brief_task_id: brief_task, draft_task_id: draft_task},
            artifacts={
                brief_context_artifact.id: brief_context_artifact,
                artifact_id: draft_artifact,
            },
            dependencies={uuid4(): dependency},
        ),
        draft_task,
        {
            "payload": draft_grounded_document_output(
                brief_task_id=brief_task_id,
                artifact_id=artifact_id,
            )
        },
    )

    assert context is not None
    assert context.summary.next_action == (
        "Create verify_semantic_grounded_document to enforce traceability and coverage."
    )
    assert context.refs[0].ref_key == "brief_task_output"
    assert context.refs[1].artifact_kind == "semantic_grounded_document_draft"


def test_build_agent_task_context_for_verify_semantic_grounded_document_state() -> None:
    now = datetime.now(UTC)
    draft_task_id = uuid4()
    verify_task_id = uuid4()
    verification_id = uuid4()
    artifact_id = uuid4()
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
    verify_task = AgentTask(
        id=verify_task_id,
        task_type="verify_semantic_grounded_document",
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
    draft_context_artifact = build_context_artifact(
        task_id=draft_task_id,
        payload=build_task_context_payload(
            task_id=draft_task_id,
            task_type="draft_semantic_grounded_document",
            output_schema_name="draft_semantic_grounded_document_output",
            output=draft_grounded_document_output(
                brief_task_id=uuid4(),
                artifact_id=uuid4(),
            ),
            updated_at=now,
        ),
    )
    verification_row = AgentTaskVerification(
        id=verification_id,
        target_task_id=draft_task_id,
        verification_task_id=verify_task_id,
        verifier_type="semantic_grounded_document_gate",
        outcome="passed",
        metrics_json={"claim_count": 1},
        reasons_json=[],
        details_json={},
        created_at=now,
        completed_at=now,
    )
    verify_artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=verify_task_id,
        attempt_id=None,
        artifact_kind="semantic_grounded_document_verification",
        storage_path="/tmp/semantic_grounded_document_verification.json",
        payload_json={"summary": {"claim_count": 1}},
        created_at=now,
    )
    dependency = AgentTaskDependency(
        task_id=verify_task_id,
        depends_on_task_id=draft_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    verify_output = {
        "draft": draft_grounded_document_output(
            brief_task_id=uuid4(),
            artifact_id=uuid4(),
        )["draft"],
        "summary": {
            "claim_count": 1,
            "unsupported_claim_count": 0,
            "required_concept_coverage_ratio": 1.0,
        },
        "success_metrics": [],
        "verification": {
            "verification_id": str(verification_id),
            "target_task_id": str(draft_task_id),
            "verification_task_id": str(verify_task_id),
            "verifier_type": "semantic_grounded_document_gate",
            "outcome": "passed",
            "metrics": {"claim_count": 1},
            "reasons": [],
            "details": {},
            "created_at": now.isoformat(),
            "completed_at": now.isoformat(),
        },
        "artifact_id": str(artifact_id),
        "artifact_kind": "semantic_grounded_document_verification",
        "artifact_path": "/tmp/semantic_grounded_document_verification.json",
    }

    context = build_agent_task_context(
        FakeSession(
            tasks={draft_task_id: draft_task, verify_task_id: verify_task},
            artifacts={
                draft_context_artifact.id: draft_context_artifact,
                artifact_id: verify_artifact,
            },
            dependencies={uuid4(): dependency},
            verifications={verification_id: verification_row},
        ),
        verify_task,
        {"payload": verify_output},
    )

    assert context is not None
    assert context.summary.verification_state == "passed"
    assert context.refs[0].ref_key == "draft_task_output"


def test_build_agent_task_context_for_claim_support_judge_eval_includes_audit_ref() -> None:
    now = datetime.now(UTC)
    task_id = uuid4()
    task = AgentTask(
        id=task_id,
        task_type="evaluate_claim_support_judge",
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
    output = claim_support_judge_evaluation_output_payload()
    artifact_id = UUID(output["artifact_id"])
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="claim_support_judge_evaluation",
        storage_path=output["artifact_path"],
        payload_json=output,
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(tasks={task_id: task}, artifacts={artifact_id: artifact}),
        task,
        {"payload": output},
    )

    assert context.summary.verification_state == "passed"
    assert context.summary.next_action == (
        "Use verify_technical_report with support judgments enabled."
    )
    assert context.summary.metrics["fixture_set_sha256"] == "fixture-set-sha"
    assert context.refs[0].ref_key == "claim_support_judge_evaluation_artifact"
    assert context.refs[0].artifact_kind == "claim_support_judge_evaluation"


def test_build_agent_task_context_for_failed_claim_support_judge_eval_blocks_promotion() -> None:
    now = datetime.now(UTC)
    task_id = uuid4()
    task = AgentTask(
        id=task_id,
        task_type="evaluate_claim_support_judge",
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
    output = claim_support_judge_evaluation_output_payload(
        gate_outcome="failed",
        failed_case_count=1,
    )

    context = build_agent_task_context(
        FakeSession(tasks={task_id: task}), task, {"payload": output}
    )

    assert context.summary.verification_state == "failed"
    assert context.summary.problem == "Overall accuracy 0.0000 is below 1.0000."
    assert context.summary.next_action == (
        "Inspect failed case_results and rerun evaluate_claim_support_judge."
    )
    assert context.summary.metrics["failed_case_count"] == 1
    assert context.refs == []
