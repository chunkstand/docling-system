from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.session import get_session_factory
from app.services.documents import ingest_local_file
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
