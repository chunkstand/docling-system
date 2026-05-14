from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskVerification,
)
from app.services.agent_task_context import (
    build_agent_task_context,
)


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def one(self):
        if len(self._rows) != 1:
            raise AssertionError("Expected one row")
        return self._rows[0]

    def all(self):
        return list(self._rows)


class FakeExecuteResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return FakeScalarResult(self._rows)


class FakeSession:
    def __init__(
        self,
        *,
        tasks=None,
        artifacts=None,
        dependencies=None,
        verifications=None,
        replay_runs=None,
    ) -> None:
        self.tasks = tasks or {}
        self.artifacts = artifacts or {}
        self.dependencies = dependencies or {}
        self.verifications = verifications or {}
        self.replay_runs = replay_runs or {}

    def get(self, model, key):
        if model.__name__ == "AgentTask":
            return self.tasks.get(key)
        if model.__name__ == "AgentTaskArtifact":
            return self.artifacts.get(key)
        if model.__name__ == "AgentTaskVerification":
            return self.verifications.get(key)
        if model.__name__ == "SearchReplayRun":
            return self.replay_runs.get(key)
        return None

    def execute(self, statement):
        rendered = str(statement)
        compiled = statement.compile()
        params = compiled.params
        if "agent_task_artifacts" in rendered:
            rows = list(self.artifacts.values())
            task_id = params.get("task_id_1")
            artifact_kind = params.get("artifact_kind_1")
            if task_id is not None:
                rows = [row for row in rows if row.task_id == task_id]
            if artifact_kind is not None:
                rows = [row for row in rows if row.artifact_kind == artifact_kind]
            return FakeExecuteResult(rows)
        if "agent_task_dependencies" in rendered:
            rows = list(self.dependencies.values())
            task_id = params.get("task_id_1")
            depends_on_task_id = params.get("depends_on_task_id_1")
            if task_id is not None:
                rows = [row for row in rows if row.task_id == task_id]
            if depends_on_task_id is not None:
                rows = [row for row in rows if row.depends_on_task_id == depends_on_task_id]
            return FakeExecuteResult(rows)
        raise AssertionError(f"Unexpected statement: {rendered}")


def _build_context_artifact(*, task_id, payload) -> AgentTaskArtifact:
    return AgentTaskArtifact(
        id=uuid4(),
        task_id=task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json=payload,
        created_at=datetime.now(UTC),
    )


def _prepare_generation_brief_output(*, task_id) -> dict:
    document_id = uuid4()
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
            "semantic_dossier": [],
            "sections": [
                {
                    "section_id": "section:integration_governance",
                    "title": "Integration Governance",
                    "summary": (
                        "This section covers one semantic concept from the selected corpus scope."
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
                    "summary": "Integration Threshold appears in Integration One.",
                    "concept_keys": ["integration_threshold"],
                    "assertion_ids": [str(uuid4())],
                    "evidence_labels": ["E1"],
                    "source_document_ids": [str(document_id)],
                    "support_level": "supported",
                    "review_policy_status": "candidate_disclosed",
                    "disclosure_note": "Candidate-backed support requires review.",
                }
            ],
            "evidence_pack": [],
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


def _draft_grounded_document_output(*, brief_task_id, artifact_id) -> dict:
    return {
        "draft": {
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
            "document_refs": [],
            "assertion_index": [],
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
                    "assertion_ids": [str(uuid4())],
                    "evidence_labels": ["E1"],
                    "source_document_ids": [str(uuid4())],
                    "support_level": "supported",
                    "review_policy_status": "candidate_disclosed",
                    "disclosure_note": "Candidate-backed support requires review.",
                }
            ],
            "evidence_pack": [],
            "markdown": "# Integration Governance Brief\n",
            "markdown_path": "/tmp/semantic_grounded_document.md",
            "warnings": [],
            "success_metrics": [
                {
                    "metric_key": "agent_legibility",
                    "stakeholder": "Lopopolo",
                    "passed": True,
                    "summary": "Typed draft ready",
                    "details": {},
                }
            ],
        },
        "artifact_id": str(artifact_id),
        "artifact_kind": "semantic_grounded_document_draft",
        "artifact_path": "/tmp/semantic_grounded_document_draft.json",
    }


def _claim_support_judge_evaluation_output_payload(
    *,
    artifact_id=None,
    gate_outcome: str = "passed",
    failed_case_count: int = 0,
) -> dict:
    evaluation_id = uuid4()
    artifact_id = artifact_id or uuid4()
    reasons = ["Overall accuracy 0.0000 is below 1.0000."] if gate_outcome == "failed" else []
    return {
        "evaluation_id": str(evaluation_id),
        "evaluation_name": "claim_support_judge_calibration",
        "fixture_set_name": "default_claim_support_v1",
        "fixture_set_sha256": "fixture-set-sha",
        "judge_name": "technical_report_claim_support_judge",
        "judge_version": "deterministic_claim_support_v1",
        "thresholds": {
            "min_overall_accuracy": 1.0,
            "min_verdict_precision": 1.0,
            "min_verdict_recall": 1.0,
            "min_support_score": 0.34,
        },
        "summary": {
            "case_count": 1,
            "passed_case_count": 1 - failed_case_count,
            "failed_case_count": failed_case_count,
            "overall_accuracy": 0.0 if gate_outcome == "failed" else 1.0,
            "gate_outcome": gate_outcome,
            "hard_case_kind_count": 1,
            "hard_case_kinds": ["exact_source_support"],
        },
        "verdict_metrics": {},
        "case_results": [],
        "reasons": reasons,
        "success_metrics": [],
        "operator_run_id": None,
        "artifact_id": str(artifact_id),
        "artifact_kind": "claim_support_judge_evaluation",
        "artifact_path": "/tmp/claim_support_judge_evaluation.json",
    }


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
    output = _prepare_generation_brief_output(task_id=task_id)
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
    brief_output = _prepare_generation_brief_output(task_id=brief_task_id)
    brief_context_artifact = _build_context_artifact(
        task_id=brief_task_id,
        payload={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(brief_task_id),
            "task_type": "prepare_semantic_generation_brief",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "prepare_semantic_generation_brief_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Brief ready"},
            "refs": [],
            "output": brief_output,
        },
    )
    draft_artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=draft_task_id,
        attempt_id=None,
        artifact_kind="semantic_grounded_document_draft",
        storage_path="/tmp/semantic_grounded_document_draft.json",
        payload_json=_draft_grounded_document_output(
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
            "payload": _draft_grounded_document_output(
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
    draft_context_artifact = _build_context_artifact(
        task_id=draft_task_id,
        payload={
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
            "output": _draft_grounded_document_output(
                brief_task_id=uuid4(),
                artifact_id=uuid4(),
            ),
        },
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
        "draft": _draft_grounded_document_output(
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
    output = _claim_support_judge_evaluation_output_payload()
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
    output = _claim_support_judge_evaluation_output_payload(
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
