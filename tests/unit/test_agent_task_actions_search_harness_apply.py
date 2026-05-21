from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_search_workflows import ApplyHarnessConfigUpdateTaskInput
from app.services.agent_actions.search_harness import _apply_harness_config_update_executor
from tests.unit.agent_task_actions_support import (
    _draft_output_payload,
    _resolve_payload_by_expected_type,
    _verification_output_payload,
)


def test_apply_harness_config_update_executor_persists_review_harness(
    monkeypatch,
    tmp_path,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
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

    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/applied_harness_config_update.json",
            },
        )(),
    )
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
            )
        ),
    }

    def fake_resolve(
        session,
        *,
        expected_task_type,
        **_kwargs,
    ):
        return _resolve_payload_by_expected_type(
            resolver_payloads,
            expected_task_type,
        )

    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    result = _apply_harness_config_update_executor(
        session=object(),
        task=apply_task,
        payload=ApplyHarnessConfigUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish review harness",
        ),
    )

    assert result["draft_harness_name"] == "wide_v2_review"
    assert result["applied_override"]["verification_task_id"] == str(verification_task_id)
    assert result["applied_override"]["applied_by"] == "operator@example.com"
    assert Path(result["config_path"]).exists()
    payload = json.loads(Path(result["config_path"]).read_text())
    assert payload["harnesses"]["wide_v2_review"]["base_harness_name"] == "wide_v2"


def test_apply_harness_config_update_executor_attaches_follow_up_evidence(
    monkeypatch,
    tmp_path,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
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
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    created_artifacts = []

    def fake_create_artifact(session, **kwargs):
        artifact = type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": f"/tmp/{kwargs['filename']}",
            },
        )()
        created_artifacts.append((kwargs["artifact_kind"], kwargs["payload"]))
        return artifact

    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.create_agent_task_artifact",
        fake_create_artifact,
    )
    verification_output = _verification_output_payload(
        verification_task_id=verification_task_id,
        draft_task_id=draft_task_id,
    )
    verification_output["comprehension_gate"] = {
        "comprehension_passed": True,
        "claim_evidence_alignment": "aligned",
        "change_justification": "publish review harness",
        "predicted_blast_radius": {"changed_scopes": ["reranker_overrides"]},
        "rollback_condition": "rollback on regression",
        "follow_up_plan": {
            "baseline_harness_name": "wide_v2",
            "candidate_harness_name": "wide_v2_review",
            "source_types": ["evaluation_queries"],
            "limit": 10,
        },
        "reasons": [],
    }
    verification_output["follow_up_plan"] = verification_output["comprehension_gate"][
        "follow_up_plan"
    ]
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(output=verification_output),
    }
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.evaluate_search_harness",
        lambda session, request: {
            "baseline_harness_name": request.baseline_harness_name,
            "candidate_harness_name": request.candidate_harness_name,
            "limit": request.limit,
            "total_shared_query_count": 10,
            "total_improved_count": 1,
            "total_regressed_count": 0,
            "total_unchanged_count": 9,
            "sources": [],
        },
    )

    result = _apply_harness_config_update_executor(
        session=object(),
        task=apply_task,
        payload=ApplyHarnessConfigUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish review harness",
        ),
    )

    assert result["follow_up_summary"]["recommendation"] == "keep_override"
    assert result["follow_up_artifact_kind"] == "follow_up_evaluation_summary"
    assert [kind for kind, _payload in created_artifacts] == [
        "follow_up_evaluation_summary",
        "applied_harness_config_update",
    ]


def test_apply_harness_config_update_executor_rejects_mismatched_verification_target(
    monkeypatch,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    other_draft_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
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
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=other_draft_task_id,
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except ValueError as exc:
        assert "does not target the requested draft task" in str(exc)
    else:
        raise AssertionError("Expected mismatched verifier target to be rejected")


def test_apply_harness_config_update_executor_rejects_failed_verification(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
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
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
                outcome="failed",
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except ValueError as exc:
        assert "Only passed draft harness verifications can be applied" in str(exc)
    else:
        raise AssertionError("Expected failed verification to be rejected")


def test_apply_harness_config_update_executor_bubbles_dependency_role_errors(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
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

    def fake_resolve(session, *, dependency_kind, **_kwargs):
        if dependency_kind == "draft_task":
            raise HTTPException(status_code=409, detail="wrong dependency kind")
        return SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
            )
        )

    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "wrong dependency kind"
    else:
        raise AssertionError("Expected dependency role validation to bubble")


def test_apply_harness_config_update_executor_bubbles_schema_errors(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
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

    def fake_resolve(session, *, dependency_kind, **_kwargs):
        if dependency_kind == "verification_task":
            raise HTTPException(status_code=409, detail="rerun required")
        return SimpleNamespace(output=_draft_output_payload(draft_task_id=draft_task_id))

    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "rerun required"
    else:
        raise AssertionError("Expected schema/rerun validation to bubble")


def test_apply_harness_config_update_executor_bubbles_missing_verification(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
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

    def fake_resolve(session, *, dependency_kind, depends_on_task_id, **_kwargs):
        if dependency_kind == "verification_task":
            raise HTTPException(
                status_code=404, detail=f"Target task not found: {depends_on_task_id}"
            )
        return SimpleNamespace(output=_draft_output_payload(draft_task_id=draft_task_id))

    monkeypatch.setattr(
        "app.services.agent_actions.search_harness.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert str(verification_task_id) in exc.detail
    else:
        raise AssertionError("Expected missing verification task to bubble")
