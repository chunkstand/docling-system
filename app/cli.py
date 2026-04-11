from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from app.db.models import Document, DocumentRun
from app.db.session import get_session_factory
from app.services.documents import ingest_local_file
from app.services.evaluations import evaluate_run, fixture_for_document
from app.services.storage import StorageService


def run_ingest_file() -> None:
    parser = argparse.ArgumentParser(description="Queue one or more local PDFs for ingestion.")
    parser.add_argument("pdf_paths", nargs="+", help="One or more PDF file paths.")
    args = parser.parse_args()

    storage_service = StorageService()
    session_factory = get_session_factory()

    with session_factory() as session:
        for raw_path in args.pdf_paths:
            payload, status_code = ingest_local_file(session, Path(raw_path).expanduser().resolve(), storage_service)
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
                        "active_run_id": str(payload.active_run_id) if payload.active_run_id else None,
                        "active_run_status": payload.active_run_status,
                    }
                )
            )


def run_eval_run() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one persisted run against the evaluation corpus.")
    parser.add_argument("run_id", help="Document run UUID to evaluate.")
    parser.add_argument("--baseline-run-id", help="Optional baseline run UUID for rank-delta comparison.")
    args = parser.parse_args()

    session_factory = get_session_factory()
    with session_factory() as session:
        run = session.get(DocumentRun, UUID(args.run_id))
        if run is None:
            raise SystemExit(f"Run not found: {args.run_id}")
        document = session.get(Document, run.document_id)
        if document is None:
            raise SystemExit(f"Document not found for run: {args.run_id}")
        baseline_run_id = UUID(args.baseline_run_id) if args.baseline_run_id else None
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
    parser = argparse.ArgumentParser(description="Evaluate all active documents that match the evaluation corpus.")
    parser.parse_args()

    session_factory = get_session_factory()
    summaries: list[dict] = []
    with session_factory() as session:
        documents = session.query(Document).order_by(Document.updated_at.desc()).all()
        for document in documents:
            if document.active_run_id is None or fixture_for_document(document) is None:
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
