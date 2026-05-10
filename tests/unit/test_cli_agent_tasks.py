from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.agent_task_cli import (
    run_agent_task_actions,
    run_agent_task_approve,
    run_agent_task_artifact,
    run_agent_task_artifacts,
    run_agent_task_context,
    run_agent_task_create,
    run_agent_task_failure_artifact,
    run_agent_task_label,
    run_agent_task_list,
    run_agent_task_outcomes,
    run_agent_task_reject,
    run_agent_task_show,
    run_agent_task_verifications,
)


def test_agent_task_actions_cli_prints_action_catalog(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-actions"])
    monkeypatch.setattr(
        "app.agent_task_cli.list_agent_task_action_definitions",
        lambda: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "task_type": "get_latest_evaluation",
                    "description": "Fetch one latest evaluation.",
                }
            )
        ],
    )

    run_agent_task_actions()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["task_type"] == "get_latest_evaluation"


def test_agent_task_create_cli_prints_created_task(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-create",
            "list_quality_eval_candidates",
            "--input-json",
            '{"limit": 5}',
        ],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.create_agent_task",
        lambda session, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(task_id),
                "task_type": payload.task_type,
                "status": "queued",
                "input": payload.input,
            }
        ),
    )

    run_agent_task_create()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["task_type"] == "list_quality_eval_candidates"
    assert output["input"]["limit"] == 5


def test_agent_task_list_cli_prints_tasks(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-list", "--status", "queued", "--limit", "3"],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.list_agent_tasks",
        lambda session, statuses=None, limit=50: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "task_id": str(task_id),
                    "status": statuses[0],
                    "limit": limit,
                }
            )
        ],
    )

    run_agent_task_list()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["task_id"] == str(task_id)
    assert output[0]["status"] == "queued"
    assert output[0]["limit"] == 3


def test_agent_task_show_cli_prints_task_detail(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-show", str(task_id)])
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_detail",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "replay_search_request",
            }
        ),
    )

    run_agent_task_show()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["task_type"] == "replay_search_request"


def test_agent_task_context_cli_prints_json(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-context", str(task_id)])
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_context",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "draft_harness_config_update",
                "schema_name": "agent_task_context",
            }
        ),
    )

    run_agent_task_context()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["schema_name"] == "agent_task_context"


def test_agent_task_apply_cli_surfaces_consistent_applied_state(
    monkeypatch, capsys, tmp_path
) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    artifact_path = tmp_path / "applied_harness_config_update.json"
    artifact_path.write_text('{"draft_harness_name": "wide_v2_review"}')

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())

    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_detail",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "apply_harness_config_update",
                "result": {
                    "draft_harness_name": "wide_v2_review",
                    "artifact_id": str(artifact_id),
                },
                "context_summary": {"approval_state": "approved"},
            }
        ),
    )
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_context",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "apply_harness_config_update",
                "summary": {
                    "approval_state": "approved",
                    "verification_state": "passed",
                },
                "output": {"draft_harness_name": "wide_v2_review"},
            }
        ),
    )
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_artifact",
        lambda session, incoming_task_id, incoming_artifact_id: SimpleNamespace(
            task_id=incoming_task_id,
            id=incoming_artifact_id,
            storage_path=str(artifact_path),
            payload_json={"draft_harness_name": "wide_v2_review"},
        ),
    )
    monkeypatch.setattr(
        "app.agent_task_cli.export_agent_task_traces",
        lambda session, limit=50, workflow_version=None, task_type=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "export_count": 1,
                "workflow_version": workflow_version,
                "task_type": task_type,
                "traces": [
                    {
                        "task_type": "apply_harness_config_update",
                        "result": {"draft_harness_name": "wide_v2_review"},
                        "context_summary": {"approval_state": "approved"},
                    }
                ],
            }
        ),
    )

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-show", str(task_id)])
    run_agent_task_show()
    show_output = json.loads(capsys.readouterr().out.strip())
    assert show_output["result"]["draft_harness_name"] == "wide_v2_review"

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-context", str(task_id)])
    run_agent_task_context()
    context_output = json.loads(capsys.readouterr().out.strip())
    assert context_output["output"]["draft_harness_name"] == "wide_v2_review"

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-artifact", str(task_id), str(artifact_id)],
    )
    run_agent_task_artifact()
    artifact_output = json.loads(capsys.readouterr().out.strip())
    assert artifact_output["draft_harness_name"] == "wide_v2_review"


def test_agent_task_triage_context_cli_prints_recommendation(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-context", str(task_id)])
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_context",
        lambda session, incoming_task_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "task_type": "triage_replay_regression",
                "freshness_status": "fresh",
                "summary": {
                    "next_action": "candidate_ready_for_review",
                    "verification_state": "passed",
                },
            }
        ),
    )

    run_agent_task_context()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["freshness_status"] == "fresh"
    assert output["summary"]["next_action"] == "candidate_ready_for_review"


def test_agent_task_outcomes_cli_prints_rows(monkeypatch, capsys) -> None:
    task_id = uuid4()
    outcome_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-outcomes", str(task_id), "--limit", "5"],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.list_agent_task_outcomes",
        lambda session, incoming_task_id, limit=20: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "outcome_id": str(outcome_id),
                    "task_id": str(incoming_task_id),
                    "outcome_label": "useful",
                    "created_by": "operator@example.com",
                    "limit": limit,
                }
            )
        ],
    )

    run_agent_task_outcomes()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["outcome_id"] == str(outcome_id)
    assert output[0]["task_id"] == str(task_id)
    assert output[0]["limit"] == 5


def test_agent_task_label_cli_prints_row(monkeypatch, capsys) -> None:
    task_id = uuid4()
    outcome_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-label",
            str(task_id),
            "--outcome-label",
            "useful",
            "--created-by",
            "operator@example.com",
            "--note",
            "accurate recommendation",
        ],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.create_agent_task_outcome",
        lambda session, incoming_task_id, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "outcome_id": str(outcome_id),
                "task_id": str(incoming_task_id),
                "outcome_label": payload.outcome_label,
                "created_by": payload.created_by,
                "note": payload.note,
            }
        ),
    )

    run_agent_task_label()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["outcome_id"] == str(outcome_id)
    assert output["outcome_label"] == "useful"
    assert output["created_by"] == "operator@example.com"


def test_agent_task_artifacts_cli_prints_artifact_rows(monkeypatch, capsys) -> None:
    task_id = uuid4()
    artifact_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-artifacts", str(task_id), "--limit", "5"],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.list_agent_task_artifacts",
        lambda session, incoming_task_id, limit=20: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "artifact_id": str(artifact_id),
                    "task_id": str(incoming_task_id),
                    "artifact_kind": "triage_summary",
                    "limit": limit,
                }
            )
        ],
    )

    run_agent_task_artifacts()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["artifact_id"] == str(artifact_id)
    assert output[0]["task_id"] == str(task_id)
    assert output[0]["limit"] == 5


def test_agent_task_artifact_cli_prints_artifact_payload(monkeypatch, capsys, tmp_path) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    artifact_path = tmp_path / "triage_summary.json"
    artifact_path.write_text('{"shadow_mode": true, "triage_kind": "replay_regression"}')

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-artifact", str(task_id), str(artifact_id)],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_artifact",
        lambda session, incoming_task_id, incoming_artifact_id: SimpleNamespace(
            task_id=incoming_task_id,
            id=incoming_artifact_id,
            storage_path=str(artifact_path),
            payload_json={"shadow_mode": True},
        ),
    )

    run_agent_task_artifact()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["triage_kind"] == "replay_regression"


def test_agent_task_verifications_cli_prints_verification_rows(monkeypatch, capsys) -> None:
    task_id = uuid4()
    verification_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-verifications", str(task_id), "--limit", "5"],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_verifications",
        lambda session, incoming_task_id, limit=20: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "verification_id": str(verification_id),
                    "target_task_id": str(incoming_task_id),
                    "outcome": "passed",
                    "limit": limit,
                }
            )
        ],
    )

    run_agent_task_verifications()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["verification_id"] == str(verification_id)
    assert output[0]["target_task_id"] == str(task_id)
    assert output[0]["limit"] == 5


def test_agent_task_failure_artifact_cli_prints_failure_payload(
    monkeypatch, capsys, tmp_path
) -> None:
    task_id = uuid4()
    failure_path = tmp_path / "failure.json"
    failure_path.write_text('{"failure_type": "ValueError", "failure_stage": "execute"}')

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, model, key):
            return SimpleNamespace(failure_artifact_path=str(failure_path))

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-failure-artifact", str(task_id)],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())

    run_agent_task_failure_artifact()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["failure_type"] == "ValueError"
    assert output["failure_stage"] == "execute"


def test_agent_task_approve_cli_prints_updated_task(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-approve",
            str(task_id),
            "--approved-by",
            "operator@example.com",
            "--approval-note",
            "ok",
        ],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.approve_agent_task",
        lambda session, incoming_task_id, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "approved_by": payload.approved_by,
                "approval_note": payload.approval_note,
            }
        ),
    )

    run_agent_task_approve()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["approved_by"] == "operator@example.com"
    assert output["approval_note"] == "ok"


def test_agent_task_reject_cli_prints_updated_task(monkeypatch, capsys) -> None:
    task_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-reject",
            str(task_id),
            "--rejected-by",
            "reviewer@example.com",
            "--rejection-note",
            "not enough evidence",
        ],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.reject_agent_task",
        lambda session, incoming_task_id, payload: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_id": str(incoming_task_id),
                "rejected_by": payload.rejected_by,
                "rejection_note": payload.rejection_note,
                "status": "rejected",
            }
        ),
    )

    run_agent_task_reject()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_id"] == str(task_id)
    assert output["rejected_by"] == "reviewer@example.com"
    assert output["rejection_note"] == "not enough evidence"
    assert output["status"] == "rejected"
