from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from app.db.models import Document, DocumentRun
from app.db.session import get_session_factory
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.schemas.search import SearchHarnessEvaluationRequest, SearchReplayRunRequest
from app.services.agent_tasks import (
    approve_agent_task,
    create_agent_task,
    get_agent_task_detail,
    list_agent_task_action_definitions,
    list_agent_tasks,
)
from app.services.audit import run_integrity_audit
from app.services.cleanup import backfill_legacy_run_audit_fields
from app.services.documents import ingest_local_file
from app.services.evaluations import evaluate_run, resolve_baseline_run_id
from app.services.quality import list_quality_eval_candidates
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_history import replay_search_request
from app.services.search_replays import (
    export_ranking_dataset,
    run_search_replay_suite,
)
from app.services.storage import StorageService


def _parse_json_arg(raw_json: str) -> dict:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON payload: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("JSON payload must be an object.")
    return payload


def run_ingest_file() -> None:
    parser = argparse.ArgumentParser(description="Queue one or more local PDFs for ingestion.")
    parser.add_argument("pdf_paths", nargs="+", help="One or more PDF file paths.")
    args = parser.parse_args()

    storage_service = StorageService()
    session_factory = get_session_factory()

    with session_factory() as session:
        for raw_path in args.pdf_paths:
            payload, status_code = ingest_local_file(
                session, Path(raw_path).expanduser().resolve(), storage_service
            )
            print(
                json.dumps(
                    {
                        "source_path": str(Path(raw_path).expanduser().resolve()),
                        "status_code": status_code,
                        "document_id": str(payload.document_id),
                        "run_id": str(payload.run_id) if payload.run_id else None,
                        "status": payload.status,
                        "duplicate": payload.duplicate,
                        "recovery_run": payload.recovery_run,
                        "active_run_id": str(payload.active_run_id)
                        if payload.active_run_id
                        else None,
                        "active_run_status": payload.active_run_status,
                    }
                )
            )


def run_eval_run() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate one persisted run against the evaluation corpus."
    )
    parser.add_argument("run_id", help="Document run UUID to evaluate.")
    parser.add_argument(
        "--baseline-run-id", help="Optional baseline run UUID for rank-delta comparison."
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        run = session.get(DocumentRun, UUID(args.run_id))
        if run is None:
            raise SystemExit(f"Run not found: {args.run_id}")
        document = session.get(Document, run.document_id)
        if document is None:
            raise SystemExit(f"Document not found for run: {args.run_id}")
        baseline_run_id = resolve_baseline_run_id(
            run.id,
            document.active_run_id,
            explicit_baseline_run_id=UUID(args.baseline_run_id) if args.baseline_run_id else None,
        )
        evaluation = evaluate_run(session, document, run, baseline_run_id=baseline_run_id)
        print(
            json.dumps(
                {
                    "run_id": str(run.id),
                    "document_id": str(document.id),
                    "source_filename": document.source_filename,
                    "status": evaluation.status,
                    "fixture_name": evaluation.fixture_name,
                    "summary": evaluation.summary_json,
                    "error_message": evaluation.error_message,
                }
            )
        )


def run_eval_corpus() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate all active documents that match the evaluation corpus."
    )
    parser.parse_args()

    session_factory = get_session_factory()
    summaries: list[dict] = []
    with session_factory() as session:
        documents = session.query(Document).order_by(Document.updated_at.desc()).all()
        for document in documents:
            if document.active_run_id is None:
                continue
            run = session.get(DocumentRun, document.active_run_id)
            if run is None:
                continue
            evaluation = evaluate_run(session, document, run)
            summaries.append(
                {
                    "run_id": str(run.id),
                    "document_id": str(document.id),
                    "source_filename": document.source_filename,
                    "status": evaluation.status,
                    "fixture_name": evaluation.fixture_name,
                    "summary": evaluation.summary_json,
                }
            )
    print(json.dumps(summaries))


def run_audit() -> None:
    parser = argparse.ArgumentParser(
        description="Audit durable run and promotion invariants across the local corpus."
    )
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        summary = run_integrity_audit(session)
    print(json.dumps(summary))


def run_backfill_legacy_audit() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill legacy run audit fields so historical rows satisfy current invariants."
        )
    )
    parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        summary = backfill_legacy_run_audit_fields(session)
    print(json.dumps(summary))


def run_replay_search() -> None:
    parser = argparse.ArgumentParser(
        description="Replay one persisted search request against the current search stack."
    )
    parser.add_argument("search_request_id", help="Persisted search request UUID to replay.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = replay_search_request(session, UUID(args.search_request_id))
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


def run_eval_candidates() -> None:
    parser = argparse.ArgumentParser(
        description="List mined evaluation candidates from failed evals and live search gaps."
    )
    parser.add_argument("--limit", type=int, default=12, help="Maximum number of candidates.")
    parser.add_argument(
        "--include-resolved",
        action="store_true",
        help="Include candidates that later evidence has already resolved.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = list_quality_eval_candidates(
            session,
            limit=args.limit,
            include_resolved=args.include_resolved,
        )
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_replay_suite() -> None:
    parser = argparse.ArgumentParser(
        description="Run a persisted replay suite over evaluation queries, live gaps, or feedback."
    )
    parser.add_argument(
        "source_type",
        choices=[
            "evaluation_queries",
            "live_search_gaps",
            "feedback",
            "cross_document_prose_regressions",
        ],
        help="Replay source to execute.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    parser.add_argument(
        "--harness-name",
        default=None,
        help="Optional search harness name for replay execution.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = run_search_replay_suite(
            session,
            SearchReplayRunRequest(
                source_type=args.source_type,
                limit=args.limit,
                harness_name=args.harness_name,
            ),
        )
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


def run_export_ranking_dataset() -> None:
    parser = argparse.ArgumentParser(
        description="Export labeled ranking data from search feedback and replay deltas."
    )
    parser.add_argument("--limit", type=int, default=200, help="Maximum rows per source set.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = export_ranking_dataset(session, limit=args.limit)
    print(json.dumps(payload))


def run_eval_reranker() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a candidate search harness against replay and corpus query sets."
    )
    parser.add_argument("candidate_harness_name", help="Candidate search harness name.")
    parser.add_argument(
        "--baseline-harness-name",
        default="default_v1",
        help="Baseline harness name to compare against.",
    )
    parser.add_argument(
        "--source-type",
        action="append",
        dest="source_types",
        choices=[
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ],
        help="Replay source type to include. Can be passed multiple times.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of queries.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        payload = evaluate_search_harness(
            session,
            SearchHarnessEvaluationRequest(
                candidate_harness_name=args.candidate_harness_name,
                baseline_harness_name=args.baseline_harness_name,
                source_types=args.source_types
                or [
                    "evaluation_queries",
                    "feedback",
                    "live_search_gaps",
                    "cross_document_prose_regressions",
                ],
                limit=args.limit,
            ),
        )
        session.commit()
    print(json.dumps(payload.model_dump(mode="json")))


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
