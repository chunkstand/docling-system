from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskVerification,
    SearchReplayRun,
)
from app.schemas.agent_tasks import ContextFreshnessStatus, ContextRef, TaskContextEnvelope
from app.services.agent_task_context import (
    build_agent_task_context,
    refresh_task_context_freshness,
    resolve_required_dependency_task_output_context,
    resolve_required_task_output_context,
)


def _payload_sha256(payload: dict) -> str:
    return (
        __import__("hashlib")
        .sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        )
        .hexdigest()
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
        if "agent_task_artifacts" in rendered:
            return FakeExecuteResult(self.artifacts.values())
        if "agent_task_dependencies" in rendered:
            return FakeExecuteResult(self.dependencies.values())
        raise AssertionError(f"Unexpected statement: {rendered}")


def _build_draft_task(*, task_id, updated_at) -> AgentTask:
    return AgentTask(
        id=task_id,
        task_type="draft_harness_config_update",
        status="completed",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=updated_at,
        updated_at=updated_at,
        completed_at=updated_at,
    )


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


def _build_replay_run(*, replay_run_id, source_type: str = "evaluation_queries") -> SearchReplayRun:
    now = datetime.now(UTC)
    return SearchReplayRun(
        id=replay_run_id,
        source_type=source_type,
        status="completed",
        harness_name="wide_v2",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="wide_v2",
        harness_config_json={"base_harness_name": "default_v1"},
        query_count=4,
        passed_count=4,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0}},
        created_at=now,
        completed_at=now,
    )


def _build_draft_context_payload(*, task_id, observed_sha256, ref_freshness="fresh") -> dict:
    return {
        "schema_name": "agent_task_context",
        "schema_version": "1.0",
        "task_id": str(task_id),
        "task_type": "draft_harness_config_update",
        "task_status": "completed",
        "workflow_version": "v1",
        "generated_at": "2026-04-15T00:00:00Z",
        "task_updated_at": "2026-04-15T00:00:00Z",
        "output_schema_name": "draft_harness_config_update_output",
        "output_schema_version": "1.0",
        "freshness_status": ref_freshness,
        "summary": {"headline": "Draft ready"},
        "refs": [
            {
                "ref_key": "source_task",
                "ref_kind": "task_output",
                "task_id": str(uuid4()),
                "observed_sha256": observed_sha256,
                "source_updated_at": "2026-04-15T00:00:00Z",
                "checked_at": "2026-04-15T00:00:00Z",
                "freshness_status": ref_freshness,
            }
        ],
        "output": {
            "draft": {
                "draft_harness_name": "wide_v2_review",
                "base_harness_name": "wide_v2",
                "source_task_id": None,
                "source_task_type": None,
                "rationale": "publish review harness",
                "override_spec": {
                    "base_harness_name": "wide_v2",
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(task_id),
                    "source_task_id": None,
                    "rationale": "publish review harness",
                },
                "effective_harness_config": {"base_harness_name": "wide_v2"},
            },
            "artifact_id": str(uuid4()),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    }


def test_refresh_task_context_freshness_marks_task_output_ref_fresh() -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    task = _build_draft_task(task_id=task_id, updated_at=now)
    output_payload = {
        "draft": {"draft_harness_name": "wide_v2_review"},
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft",
        "artifact_path": "/tmp/harness_config_draft.json",
    }
    artifact = _build_context_artifact(
        task_id=task_id,
        payload={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(task_id),
            "task_type": task.task_type,
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": "2026-04-15T00:00:00Z",
            "task_updated_at": "2026-04-15T00:00:00Z",
            "output_schema_name": "draft_harness_config_update_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {},
            "refs": [],
            "output": output_payload,
        },
    )
    envelope = TaskContextEnvelope(
        task_id=uuid4(),
        task_type="verify_draft_harness_config",
        task_status="completed",
        workflow_version="v1",
        generated_at=now,
        task_updated_at=now,
        refs=[
            ContextRef(
                ref_key="draft_task_output",
                ref_kind="task_output",
                task_id=task_id,
                schema_name="draft_harness_config_update_output",
                schema_version="1.0",
                observed_sha256=_payload_sha256(output_payload),
                source_updated_at=now,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        ],
    )

    refreshed = refresh_task_context_freshness(
        FakeSession(tasks={task_id: task}, artifacts={artifact.id: artifact}),
        envelope,
    )

    assert refreshed.refs[0].freshness_status == ContextFreshnessStatus.FRESH
    assert refreshed.freshness_status == ContextFreshnessStatus.FRESH


def test_build_agent_task_context_for_triage_semantic_pass_includes_target_and_artifact_refs(
) -> None:
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


def test_refresh_task_context_freshness_detects_stale_missing_and_schema_mismatch() -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    task = _build_draft_task(task_id=task_id, updated_at=now)
    fresh_output = {
        "draft": {"draft_harness_name": "wide_v2_review"},
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft",
        "artifact_path": "/tmp/harness_config_draft.json",
    }
    artifact = _build_context_artifact(
        task_id=task_id,
        payload={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(task_id),
            "task_type": task.task_type,
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": "2026-04-15T00:00:00Z",
            "task_updated_at": "2026-04-15T00:00:00Z",
            "output_schema_name": "draft_harness_config_update_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {},
            "refs": [],
            "output": fresh_output,
        },
    )
    stale_envelope = TaskContextEnvelope(
        task_id=uuid4(),
        task_type="verify_draft_harness_config",
        task_status="completed",
        workflow_version="v1",
        generated_at=now,
        task_updated_at=now,
        refs=[
            ContextRef(
                ref_key="draft_task_output",
                ref_kind="task_output",
                task_id=task_id,
                schema_name="draft_harness_config_update_output",
                schema_version="1.0",
                observed_sha256=_payload_sha256({"draft": {"draft_harness_name": "old"}}),
                source_updated_at=now,
                checked_at=now,
            )
        ],
    )
    refreshed_stale = refresh_task_context_freshness(
        FakeSession(tasks={task_id: task}, artifacts={artifact.id: artifact}),
        stale_envelope,
    )
    assert refreshed_stale.refs[0].freshness_status == ContextFreshnessStatus.STALE

    missing_envelope = stale_envelope.model_copy(deep=True)
    refreshed_missing = refresh_task_context_freshness(FakeSession(), missing_envelope)
    assert refreshed_missing.refs[0].freshness_status == ContextFreshnessStatus.MISSING

    mismatch_envelope = stale_envelope.model_copy(deep=True)
    mismatch_envelope.refs[0].schema_name = "wrong_schema"
    refreshed_mismatch = refresh_task_context_freshness(
        FakeSession(tasks={task_id: task}, artifacts={artifact.id: artifact}),
        mismatch_envelope,
    )
    assert refreshed_mismatch.refs[0].freshness_status == ContextFreshnessStatus.SCHEMA_MISMATCH


def test_required_task_output_context_blocks_missing_and_schema_mismatch() -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    task = _build_draft_task(task_id=task_id, updated_at=now)
    current_output = {
        "draft": {"draft_harness_name": "wide_v2_review"},
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft",
        "artifact_path": "/tmp/harness_config_draft.json",
    }
    stale_payload = {
        "schema_name": "agent_task_context",
        "schema_version": "1.0",
        "task_id": str(task_id),
        "task_type": task.task_type,
        "task_status": "completed",
        "workflow_version": "v1",
        "generated_at": "2026-04-15T00:00:00Z",
        "task_updated_at": "2026-04-15T00:00:00Z",
        "output_schema_name": "draft_harness_config_update_output",
        "output_schema_version": "1.0",
        "freshness_status": "fresh",
        "summary": {},
        "refs": [
            {
                "ref_key": "source_task",
                "ref_kind": "artifact",
                "artifact_id": str(uuid4()),
                "artifact_kind": "harness_config_draft",
                "observed_sha256": "old",
                "source_updated_at": "2026-04-15T00:00:00Z",
                "checked_at": "2026-04-15T00:00:00Z",
                "freshness_status": "stale",
            }
        ],
        "output": current_output,
    }
    stale_context = _build_context_artifact(task_id=task_id, payload=stale_payload)
    session = FakeSession(tasks={task_id: task}, artifacts={stale_context.id: stale_context})

    resolved = resolve_required_task_output_context(
        session,
        task_id=task_id,
        expected_task_type="draft_harness_config_update",
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        rerun_message="rerun required",
    )
    assert resolved.output["draft"]["draft_harness_name"] == "wide_v2_review"

    try:
        resolve_required_task_output_context(
            FakeSession(tasks={task_id: task}),
            task_id=task_id,
            expected_task_type="draft_harness_config_update",
            expected_schema_name="draft_harness_config_update_output",
            expected_schema_version="1.0",
            rerun_message="rerun required",
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "agent_task_context_output_missing"
        assert exc.detail["message"] == "rerun required"
    else:
        raise AssertionError("Expected missing context to block")

    mismatch_context = _build_context_artifact(
        task_id=task_id,
        payload={**stale_payload, "output_schema_name": "wrong_schema"},
    )
    try:
        resolve_required_task_output_context(
            FakeSession(tasks={task_id: task}, artifacts={mismatch_context.id: mismatch_context}),
            task_id=task_id,
            expected_task_type="draft_harness_config_update",
            expected_schema_name="draft_harness_config_update_output",
            expected_schema_version="1.0",
            rerun_message="rerun required",
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "agent_task_context_output_schema_mismatch"
        assert exc.detail["message"] == "rerun required"
    else:
        raise AssertionError("Expected schema mismatch to block")


def test_resolve_required_task_output_context_uses_structured_errors_for_task_state() -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    wrong_type_task = _build_draft_task(task_id=task_id, updated_at=now)
    wrong_type_task.task_type = "evaluate_search_harness"
    incomplete_task = _build_draft_task(task_id=task_id, updated_at=now)
    incomplete_task.status = "processing"

    try:
        resolve_required_task_output_context(
            FakeSession(),
            task_id=task_id,
            expected_task_type="draft_harness_config_update",
            expected_schema_name="draft_harness_config_update_output",
            expected_schema_version="1.0",
            rerun_message="rerun required",
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail["code"] == "agent_task_context_target_task_not_found"
        assert exc.detail["context"]["task_id"] == str(task_id)
    else:
        raise AssertionError("Expected missing task to block")

    try:
        resolve_required_task_output_context(
            FakeSession(tasks={task_id: wrong_type_task}),
            task_id=task_id,
            expected_task_type="draft_harness_config_update",
            expected_schema_name="draft_harness_config_update_output",
            expected_schema_version="1.0",
            rerun_message="rerun required",
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "agent_task_context_target_task_type_mismatch"
        assert exc.detail["context"]["actual_task_type"] == "evaluate_search_harness"
    else:
        raise AssertionError("Expected wrong task type to block")

    try:
        resolve_required_task_output_context(
            FakeSession(tasks={task_id: incomplete_task}),
            task_id=task_id,
            expected_task_type="draft_harness_config_update",
            expected_schema_name="draft_harness_config_update_output",
            expected_schema_version="1.0",
            rerun_message="rerun required",
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "agent_task_context_target_task_not_completed"
        assert exc.detail["context"]["task_status"] == "processing"
    else:
        raise AssertionError("Expected incomplete task to block")


def test_resolve_required_dependency_task_output_context_requires_matching_role() -> None:
    apply_task_id = uuid4()
    draft_task_id = uuid4()
    now = datetime.now(UTC)
    draft_task = _build_draft_task(task_id=draft_task_id, updated_at=now)
    current_output = {
        "draft": {"draft_harness_name": "wide_v2_review"},
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft",
        "artifact_path": "/tmp/harness_config_draft.json",
    }
    context_artifact = _build_context_artifact(
        task_id=draft_task_id,
        payload={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(draft_task_id),
            "task_type": draft_task.task_type,
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": "2026-04-15T00:00:00Z",
            "task_updated_at": "2026-04-15T00:00:00Z",
            "output_schema_name": "draft_harness_config_update_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {},
            "refs": [],
            "output": current_output,
        },
    )
    dependency_row = AgentTaskDependency(
        task_id=apply_task_id,
        depends_on_task_id=draft_task_id,
        dependency_kind="draft_task",
        created_at=now,
    )

    resolved = resolve_required_dependency_task_output_context(
        FakeSession(
            tasks={draft_task_id: draft_task},
            artifacts={context_artifact.id: context_artifact},
            dependencies={(apply_task_id, draft_task_id): dependency_row},
        ),
        task_id=apply_task_id,
        depends_on_task_id=draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_harness_config_update",
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        dependency_error_message="wrong dependency kind",
        rerun_message="rerun required",
    )
    assert resolved.output["draft"]["draft_harness_name"] == "wide_v2_review"

    wrong_kind_row = AgentTaskDependency(
        task_id=apply_task_id,
        depends_on_task_id=draft_task_id,
        dependency_kind="explicit",
        created_at=now,
    )
    try:
        resolve_required_dependency_task_output_context(
            FakeSession(
                tasks={draft_task_id: draft_task},
                artifacts={context_artifact.id: context_artifact},
                dependencies={(apply_task_id, draft_task_id): wrong_kind_row},
            ),
            task_id=apply_task_id,
            depends_on_task_id=draft_task_id,
            dependency_kind="draft_task",
            expected_task_type="draft_harness_config_update",
            expected_schema_name="draft_harness_config_update_output",
            expected_schema_version="1.0",
            dependency_error_message="wrong dependency kind",
            rerun_message="rerun required",
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "agent_task_context_dependency_mismatch"
        assert exc.detail["message"] == "wrong dependency kind"
    else:
        raise AssertionError("Expected mismatched dependency kind to block")


def test_refresh_task_context_freshness_marks_replay_run_refs_fresh() -> None:
    replay_run_id = uuid4()
    replay_run = _build_replay_run(replay_run_id=replay_run_id)
    replay_payload = {
        "replay_run_id": str(replay_run.id),
        "source_type": replay_run.source_type,
        "status": replay_run.status,
        "harness_name": replay_run.harness_name,
        "reranker_name": replay_run.reranker_name,
        "reranker_version": replay_run.reranker_version,
        "retrieval_profile_name": replay_run.retrieval_profile_name,
        "harness_config": replay_run.harness_config_json,
        "query_count": replay_run.query_count,
        "passed_count": replay_run.passed_count,
        "failed_count": replay_run.failed_count,
        "zero_result_count": replay_run.zero_result_count,
        "table_hit_count": replay_run.table_hit_count,
        "top_result_changes": replay_run.top_result_changes,
        "max_rank_shift": replay_run.max_rank_shift,
        "summary": replay_run.summary_json,
        "created_at": replay_run.created_at.isoformat(),
        "completed_at": replay_run.completed_at.isoformat(),
    }
    now = datetime.now(UTC)
    envelope = TaskContextEnvelope(
        task_id=uuid4(),
        task_type="evaluate_search_harness",
        task_status="completed",
        workflow_version="v1",
        generated_at=now,
        task_updated_at=now,
        refs=[
            ContextRef(
                ref_key="evaluation_queries_candidate_replay_run",
                ref_kind="replay_run",
                replay_run_id=replay_run_id,
                observed_sha256=_payload_sha256(replay_payload),
                source_updated_at=now,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        ],
    )

    refreshed = refresh_task_context_freshness(
        FakeSession(replay_runs={replay_run_id: replay_run}),
        envelope,
    )

    assert refreshed.refs[0].freshness_status == ContextFreshnessStatus.FRESH
    assert refreshed.freshness_status == ContextFreshnessStatus.FRESH


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


def test_build_agent_task_context_for_prepare_semantic_generation_brief_includes_artifact_ref(
) -> None:
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


def test_build_agent_task_context_for_draft_semantic_grounded_document_includes_target_ref(
) -> None:
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


def test_build_agent_task_context_for_verify_semantic_grounded_document_includes_verification_state(
) -> None:
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
