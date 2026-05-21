from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import app.services.agent_task_context as agent_task_context_module
from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact, AgentTaskDependency
from app.schemas.agent_task_core import ContextFreshnessStatus
from app.services.agent_task_context import (
    build_agent_task_context,
    get_agent_task_context_builder,
    list_agent_task_context_builder_names,
)
from app.services.agent_task_context_core import build_core_context_builders
from app.services.agent_task_context_registry import (
    compose_context_builder_registries,
)
from app.services.agent_task_context_search_harness import (
    build_search_harness_context_builders,
)
from app.services.agent_task_context_semantic import build_semantic_context_builders
from app.services.agent_task_context_semantic_governance import (
    build_semantic_governance_context_builders,
)
from app.services.agent_task_context_technical_reports import (
    build_technical_report_context_builders,
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


def test_context_builder_registry_is_composed_from_owner_modules() -> None:
    owner_builders = compose_context_builder_registries(
        build_core_context_builders(
            {"build_generic_task_context": agent_task_context_module.build_generic_task_context}
        ),
        build_semantic_context_builders(agent_task_context_module.__dict__),
        build_semantic_governance_context_builders(agent_task_context_module.__dict__),
        build_technical_report_context_builders(agent_task_context_module.__dict__),
        build_search_harness_context_builders(agent_task_context_module.__dict__),
    )

    assert set(owner_builders) == list_agent_task_context_builder_names()
    for builder_name, builder in owner_builders.items():
        assert get_agent_task_context_builder(builder_name) is builder


def test_build_agent_task_context_for_triage_semantic_pass_includes_target_and_artifact_refs() -> (
    None
):
    now = datetime.now(UTC)
    target_task_id = uuid4()
    triage_task_id = uuid4()
    verification_id = uuid4()
    artifact_id = uuid4()

    target_output = {
        "document_id": str(uuid4()),
        "semantic_pass": {
            "semantic_pass_id": str(uuid4()),
            "document_id": str(uuid4()),
            "run_id": str(uuid4()),
            "status": "completed",
            "registry_version": "semantics-layer-foundation-alpha.2",
            "registry_sha256": "registry-sha",
            "extractor_version": "semantics_sidecar_v2_1",
            "artifact_schema_version": "2.1",
            "baseline_run_id": None,
            "baseline_semantic_pass_id": None,
            "has_json_artifact": True,
            "has_yaml_artifact": True,
            "artifact_json_sha256": "json-sha",
            "artifact_yaml_sha256": "yaml-sha",
            "assertion_count": 0,
            "evidence_count": 0,
            "summary": {"concept_keys": []},
            "evaluation_status": "completed",
            "evaluation_fixture_name": "semantic_fixture",
            "evaluation_version": 2,
            "evaluation_summary": {"all_expectations_passed": False, "expectations": []},
            "continuity_summary": {"reason": "no_prior_active_run", "change_count": 0},
            "error_message": None,
            "created_at": "2026-04-15T00:00:00Z",
            "completed_at": "2026-04-15T00:00:00Z",
            "concept_category_bindings": [],
            "assertions": [],
        },
        "success_metrics": [],
    }
    target_context_payload = {
        "schema_name": "agent_task_context",
        "schema_version": "1.0",
        "task_id": str(target_task_id),
        "task_type": "get_latest_semantic_pass",
        "task_status": "completed",
        "workflow_version": "v1",
        "generated_at": "2026-04-15T00:00:00Z",
        "task_updated_at": "2026-04-15T00:00:00Z",
        "output_schema_name": "get_latest_semantic_pass_output",
        "output_schema_version": "1.0",
        "freshness_status": "fresh",
        "summary": {"headline": "semantic pass ready"},
        "refs": [],
        "output": target_output,
    }

    target_task = AgentTask(
        id=target_task_id,
        task_type="get_latest_semantic_pass",
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
    triage_task = AgentTask(
        id=triage_task_id,
        task_type="triage_semantic_pass",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={"target_task_id": str(target_task_id)},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    triage_dependency = AgentTaskDependency(
        id=uuid4(),
        task_id=triage_task_id,
        depends_on_task_id=target_task_id,
        dependency_kind="target_task",
        created_at=now,
    )
    verification_row = type(
        "VerificationRow",
        (),
        {
            "id": verification_id,
            "target_task_id": target_task_id,
            "verification_task_id": triage_task_id,
            "verifier_type": "semantic_gap_gate",
            "outcome": "failed",
            "metrics_json": {"issue_count": 1},
            "reasons_json": ["missing concept"],
            "details_json": {"issue_types": ["missing_expected_concept"]},
            "created_at": now,
            "completed_at": now,
        },
    )()
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=triage_task_id,
        attempt_id=None,
        artifact_kind="semantic_gap_report",
        storage_path="/tmp/semantic_gap_report.json",
        payload_json={"issue_count": 1},
        created_at=now,
    )
    target_context_artifact = _build_context_artifact(
        task_id=target_task_id,
        payload=target_context_payload,
    )

    result = {
        "payload": {
            "document_id": target_output["document_id"],
            "run_id": target_output["semantic_pass"]["run_id"],
            "semantic_pass_id": target_output["semantic_pass"]["semantic_pass_id"],
            "registry_version": "semantics-layer-foundation-alpha.2",
            "evaluation_fixture_name": "semantic_fixture",
            "evaluation_status": "completed",
            "gap_report": {
                "document_id": target_output["semantic_pass"]["document_id"],
                "run_id": target_output["semantic_pass"]["run_id"],
                "semantic_pass_id": target_output["semantic_pass"]["semantic_pass_id"],
                "registry_version": "semantics-layer-foundation-alpha.2",
                "registry_sha256": "registry-sha",
                "evaluation_status": "completed",
                "evaluation_fixture_name": "semantic_fixture",
                "evaluation_version": 2,
                "continuity_summary": {"reason": "no_prior_active_run", "change_count": 0},
                "issue_count": 1,
                "issues": [],
                "recommended_followups": [],
                "success_metrics": [],
            },
            "verification": {
                "verification_id": str(verification_id),
                "target_task_id": str(target_task_id),
                "verification_task_id": str(triage_task_id),
                "verifier_type": "semantic_gap_gate",
                "outcome": "failed",
                "metrics": {"issue_count": 1},
                "reasons": ["missing concept"],
                "details": {"issue_types": ["missing_expected_concept"]},
                "created_at": "2026-04-15T00:00:00Z",
                "completed_at": "2026-04-15T00:00:00Z",
            },
            "recommendation": {
                "next_action": "draft_registry_update",
                "confidence": "high",
                "summary": "draft registry update",
            },
            "artifact_id": str(artifact_id),
            "artifact_kind": "semantic_gap_report",
            "artifact_path": "/tmp/semantic_gap_report.json",
        }
    }

    context = build_agent_task_context(
        FakeSession(
            tasks={target_task_id: target_task, triage_task_id: triage_task},
            artifacts={target_context_artifact.id: target_context_artifact, artifact_id: artifact},
            dependencies={triage_dependency.id: triage_dependency},
            verifications={verification_id: verification_row},
        ),
        triage_task,
        result,
    )

    assert context is not None
    assert context.summary.next_action == "draft_registry_update"
    assert {row.ref_key for row in context.refs} == {
        "target_task_output",
        "verification_record",
        "semantic_gap_report_artifact",
    }
    assert context.freshness_status == ContextFreshnessStatus.FRESH
