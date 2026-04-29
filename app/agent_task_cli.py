from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

import yaml

from app.db.models import AgentTask
from app.db.session import get_session_factory
from app.schemas.agent_tasks import (
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskOutcomeCreateRequest,
    AgentTaskRejectionRequest,
)
from app.services.agent_task_artifacts import (
    get_agent_task_artifact,
    list_agent_task_artifacts,
)
from app.services.agent_task_context import get_agent_task_context
from app.services.agent_task_verifications import get_agent_task_verifications
from app.services.agent_tasks import (
    approve_agent_task,
    create_agent_task,
    create_agent_task_outcome,
    export_agent_task_traces,
    get_agent_approval_trends,
    get_agent_task_analytics_summary,
    get_agent_task_cost_summary,
    get_agent_task_cost_trends,
    get_agent_task_decision_signals,
    get_agent_task_detail,
    get_agent_task_performance_summary,
    get_agent_task_performance_trends,
    get_agent_task_recommendation_summary,
    get_agent_task_recommendation_trends,
    get_agent_task_trends,
    get_agent_task_value_density,
    get_agent_verification_trends,
    list_agent_task_action_definitions,
    list_agent_task_outcomes,
    list_agent_task_workflow_summaries,
    list_agent_tasks,
    reject_agent_task,
)


def _parse_json_arg(raw_json: str) -> dict:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("JSON payload must be an object.")
    return payload


def run_agent_task_actions() -> None:
    parser = argparse.ArgumentParser(description="List supported agent task action definitions.")
    parser.parse_args()

    payload = list_agent_task_action_definitions()
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_create() -> None:
    parser = argparse.ArgumentParser(description="Create one agent task.")
    parser.add_argument("task_type", help="Registered agent task type.")
    parser.add_argument(
        "--input-json",
        default="{}",
        help="JSON object payload for the registered task input.",
    )
    parser.add_argument("--priority", type=int, default=100, help="Task priority.")
    parser.add_argument(
        "--workflow-version",
        default="v1",
        help="Workflow version label to persist with the task.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type=args.task_type,
                input=_parse_json_arg(args.input_json),
                priority=args.priority,
                workflow_version=args.workflow_version,
            ),
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_list() -> None:
    parser = argparse.ArgumentParser(description="List agent tasks.")
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="Optional task status filter. Can be passed multiple times.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of tasks to return.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_agent_tasks(session, statuses=args.statuses, limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_show() -> None:
    parser = argparse.ArgumentParser(description="Show one agent task in detail.")
    parser.add_argument("task_id", help="Agent task UUID.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_detail(session, UUID(args.task_id))
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_context() -> None:
    parser = argparse.ArgumentParser(description="Show one agent task context artifact.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--format", choices=["json", "yaml"], default="json")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_context(session, UUID(args.task_id))
    payload_json = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    if args.format == "yaml":
        print(yaml.safe_dump(payload_json, sort_keys=False, allow_unicode=True))
        return
    print(json.dumps(payload_json))


def run_agent_task_outcomes() -> None:
    parser = argparse.ArgumentParser(description="List outcome labels for one agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum outcome rows to return.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_agent_task_outcomes(session, UUID(args.task_id), limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_label() -> None:
    parser = argparse.ArgumentParser(description="Record one outcome label for a terminal task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument(
        "--outcome-label",
        required=True,
        choices=["useful", "not_useful", "correct", "incorrect"],
        help="Outcome label to record.",
    )
    parser.add_argument("--created-by", required=True, help="Operator identifier.")
    parser.add_argument("--note", default=None, help="Optional note.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = create_agent_task_outcome(
            session,
            UUID(args.task_id),
            AgentTaskOutcomeCreateRequest(
                outcome_label=args.outcome_label,
                created_by=args.created_by,
                note=args.note,
            ),
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_artifacts() -> None:
    parser = argparse.ArgumentParser(description="List artifact records for one agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum artifact rows to return.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_agent_task_artifacts(session, UUID(args.task_id), limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_artifact() -> None:
    parser = argparse.ArgumentParser(description="Show one agent task artifact payload.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("artifact_id", help="Artifact UUID.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        artifact = get_agent_task_artifact(session, UUID(args.task_id), UUID(args.artifact_id))
    if artifact.storage_path and Path(artifact.storage_path).exists():
        print(Path(artifact.storage_path).read_text())
        return
    print(json.dumps(artifact.payload_json or {}))


def run_agent_task_verifications() -> None:
    parser = argparse.ArgumentParser(description="List verifier records for one agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum verification rows to return.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_verifications(session, UUID(args.task_id), limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_failure_artifact() -> None:
    parser = argparse.ArgumentParser(description="Show one agent task failure artifact payload.")
    parser.add_argument("task_id", help="Agent task UUID.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        task = session.get(AgentTask, UUID(args.task_id))
        if task is None:
            raise SystemExit(f"Agent task not found: {args.task_id}")
        if task.failure_artifact_path is None or not Path(task.failure_artifact_path).exists():
            raise SystemExit(f"Failure artifact not found for agent task: {args.task_id}")
        print(Path(task.failure_artifact_path).read_text())


def run_agent_task_approve() -> None:
    parser = argparse.ArgumentParser(description="Approve one approval-gated agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--approved-by", required=True, help="Approval actor identifier.")
    parser.add_argument("--approval-note", default=None, help="Optional approval note.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = approve_agent_task(
            session,
            UUID(args.task_id),
            AgentTaskApprovalRequest(
                approved_by=args.approved_by,
                approval_note=args.approval_note,
            ),
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_reject() -> None:
    parser = argparse.ArgumentParser(description="Reject one approval-gated agent task.")
    parser.add_argument("task_id", help="Agent task UUID.")
    parser.add_argument("--rejected-by", required=True, help="Rejection actor identifier.")
    parser.add_argument("--rejection-note", default=None, help="Optional rejection note.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = reject_agent_task(
            session,
            UUID(args.task_id),
            AgentTaskRejectionRequest(
                rejected_by=args.rejected_by,
                rejection_note=args.rejection_note,
            ),
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_analytics() -> None:
    parser = argparse.ArgumentParser(description="Show aggregate agent task analytics.")
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_analytics_summary(session)
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_trends() -> None:
    parser = argparse.ArgumentParser(description="Show time-bucketed agent task trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_verification_trends() -> None:
    parser = argparse.ArgumentParser(description="Show time-bucketed verifier trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_verification_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_approval_trends() -> None:
    parser = argparse.ArgumentParser(
        description="Show time-bucketed approval and rejection trends."
    )
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_approval_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_recommendation_summary() -> None:
    parser = argparse.ArgumentParser(description="Show recommendation success summary.")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_recommendation_summary(
            session,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_recommendation_trends() -> None:
    parser = argparse.ArgumentParser(description="Show recommendation success trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_recommendation_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_cost_summary() -> None:
    parser = argparse.ArgumentParser(description="Show agent task cost summary.")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_cost_summary(
            session,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_cost_trends() -> None:
    parser = argparse.ArgumentParser(description="Show agent task cost trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_cost_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_performance_summary() -> None:
    parser = argparse.ArgumentParser(description="Show agent task performance summary.")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_performance_summary(
            session,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_performance_trends() -> None:
    parser = argparse.ArgumentParser(description="Show agent task performance trends.")
    parser.add_argument("--bucket", choices=["day", "week"], default="day")
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--workflow-version", default=None)
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_performance_trends(
            session,
            bucket=args.bucket,
            task_type=args.task_type,
            workflow_version=args.workflow_version,
        )
    print(json.dumps(payload.model_dump(mode="json")))


def run_agent_task_value_density() -> None:
    parser = argparse.ArgumentParser(description="Show agent workflow value-density summaries.")
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_value_density(session)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_decision_signals() -> None:
    parser = argparse.ArgumentParser(description="Show workflow decision signals.")
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = get_agent_task_decision_signals(session)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_workflow_versions() -> None:
    parser = argparse.ArgumentParser(
        description="Show agent task analytics grouped by workflow version."
    )
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_agent_task_workflow_summaries(session)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_agent_task_export_traces() -> None:
    parser = argparse.ArgumentParser(description="Export durable agent task traces.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum tasks to export.")
    parser.add_argument(
        "--workflow-version",
        default=None,
        help="Optional workflow version filter.",
    )
    parser.add_argument("--task-type", default=None, help="Optional task type filter.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = export_agent_task_traces(
            session,
            limit=args.limit,
            workflow_version=args.workflow_version,
            task_type=args.task_type,
        )
    print(json.dumps(payload.model_dump(mode="json")))
