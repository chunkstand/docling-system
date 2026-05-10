from __future__ import annotations

import json
import sys
from types import SimpleNamespace

from app.agent_task_cli import (
    run_agent_task_analytics,
    run_agent_task_approval_trends,
    run_agent_task_cost_summary,
    run_agent_task_decision_signals,
    run_agent_task_export_traces,
    run_agent_task_performance_summary,
    run_agent_task_recommendation_summary,
    run_agent_task_trends,
    run_agent_task_value_density,
    run_agent_task_verification_trends,
    run_agent_task_workflow_versions,
)


def test_agent_task_analytics_cli_prints_summary(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-analytics"])
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_analytics_summary",
        lambda session: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_count": 4,
                "labeled_task_count": 2,
                "outcome_label_counts": {"useful": 1, "correct": 1},
            }
        ),
    )

    run_agent_task_analytics()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["task_count"] == 4
    assert output["labeled_task_count"] == 2


def test_agent_task_workflow_versions_cli_prints_rows(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-workflow-versions"])
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.list_agent_task_workflow_summaries",
        lambda session: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "workflow_version": "v1",
                    "task_count": 4,
                }
            )
        ],
    )

    run_agent_task_workflow_versions()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["workflow_version"] == "v1"
    assert output[0]["task_count"] == 4


def test_agent_task_export_traces_cli_prints_payload(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-export-traces",
            "--limit",
            "10",
            "--workflow-version",
            "v1",
        ],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.export_agent_task_traces",
        lambda session, limit=50, workflow_version=None, task_type=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "export_count": 1,
                "workflow_version": workflow_version,
                "task_type": task_type,
                "traces": [{"task_type": "triage_replay_regression"}],
            }
        ),
    )

    run_agent_task_export_traces()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["export_count"] == 1
    assert output["workflow_version"] == "v1"


def test_agent_task_trends_cli_prints_payload(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-trends", "--bucket", "week", "--workflow-version", "v1"],
    )
    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "bucket": bucket,
                "workflow_version": workflow_version,
                "series": [{"created_count": 1}],
            }
        ),
    )

    run_agent_task_trends()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["bucket"] == "week"
    assert output["workflow_version"] == "v1"


def test_agent_task_recommendation_and_cost_cli_print_payloads(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_recommendation_summary",
        lambda session, task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_type": task_type,
                "workflow_version": workflow_version,
                "downstream_improved_count": 1,
            }
        ),
    )
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_cost_summary",
        lambda session, task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {
                "task_type": task_type,
                "workflow_version": workflow_version,
                "estimated_usd_total": 0.0,
            }
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-agent-task-recommendation-summary",
            "--task-type",
            "triage_replay_regression",
        ],
    )
    run_agent_task_recommendation_summary()
    recommendation_output = json.loads(capsys.readouterr().out.strip())
    assert recommendation_output["downstream_improved_count"] == 1

    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-agent-task-cost-summary", "--workflow-version", "v1"],
    )
    run_agent_task_cost_summary()
    cost_output = json.loads(capsys.readouterr().out.strip())
    assert cost_output["workflow_version"] == "v1"


def test_agent_task_remaining_milestone9_clis_print_payloads(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.agent_task_cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_verification_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {"bucket": bucket, "series": [{"passed_count": 1}]}
        ),
    )
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_approval_trends",
        lambda session, bucket="day", task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {"bucket": bucket, "series": [{"approval_count": 1}]}
        ),
    )
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_performance_summary",
        lambda session, task_type=None, workflow_version=None: SimpleNamespace(
            model_dump=lambda mode="json": {"median_execution_latency_ms": 12.0}
        ),
    )
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_value_density",
        lambda session: [
            SimpleNamespace(
                model_dump=lambda mode="json": {"task_type": "triage_replay_regression"}
            )
        ],
    )
    monkeypatch.setattr(
        "app.agent_task_cli.get_agent_task_decision_signals",
        lambda session: [SimpleNamespace(model_dump=lambda mode="json": {"status": "healthy"})],
    )

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-verification-trends"])
    run_agent_task_verification_trends()
    assert json.loads(capsys.readouterr().out.strip())["series"][0]["passed_count"] == 1

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-approval-trends"])
    run_agent_task_approval_trends()
    assert json.loads(capsys.readouterr().out.strip())["series"][0]["approval_count"] == 1

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-performance-summary"])
    run_agent_task_performance_summary()
    assert json.loads(capsys.readouterr().out.strip())["median_execution_latency_ms"] == 12.0

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-value-density"])
    run_agent_task_value_density()
    assert json.loads(capsys.readouterr().out.strip())[0]["task_type"] == "triage_replay_regression"

    monkeypatch.setattr(sys, "argv", ["docling-system-agent-task-decision-signals"])
    run_agent_task_decision_signals()
    assert json.loads(capsys.readouterr().out.strip())[0]["status"] == "healthy"
