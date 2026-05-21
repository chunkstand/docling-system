from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID

from app.cli_commands.common import lazy_service_attr
from app.db.session import get_session_factory
from app.services.storage import StorageService


def ingest_local_file(*args, **kwargs):
    return lazy_service_attr("app.services.documents", "ingest_local_file")(*args, **kwargs)


def queue_local_ingest_directory(*args, **kwargs):
    return lazy_service_attr("app.services.ingest_batches", "queue_local_ingest_directory")(
        *args,
        **kwargs,
    )


def list_ingest_batches(*args, **kwargs):
    return lazy_service_attr("app.services.ingest_batches", "list_ingest_batches")(
        *args,
        **kwargs,
    )


def get_ingest_batch_detail(*args, **kwargs):
    return lazy_service_attr("app.services.ingest_batches", "get_ingest_batch_detail")(
        *args,
        **kwargs,
    )


def run_ingest_file(
    *,
    ingest_local_file_func=None,
    session_factory_func=None,
    storage_service_factory=None,
) -> None:
    parser = argparse.ArgumentParser(description="Queue one or more local PDFs for ingestion.")
    parser.add_argument("pdf_paths", nargs="+", help="One or more PDF file paths.")
    args = parser.parse_args()

    ingest_local_file_func = ingest_local_file_func or ingest_local_file
    session_factory_func = session_factory_func or get_session_factory
    storage_service_factory = storage_service_factory or StorageService

    storage_service = storage_service_factory()
    session_factory = session_factory_func()

    with session_factory() as session:
        for raw_path in args.pdf_paths:
            resolved_path = Path(raw_path).expanduser().resolve()
            payload, status_code = ingest_local_file_func(
                session,
                resolved_path,
                storage_service,
            )
            print(
                json.dumps(
                    {
                        "source_path": str(resolved_path),
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


def run_ingest_dir(
    *,
    queue_local_ingest_directory_func=None,
    session_factory_func=None,
    storage_service_factory=None,
) -> None:
    parser = argparse.ArgumentParser(
        description="Queue all PDF files under one local directory for ingestion."
    )
    parser.add_argument("directory_path", help="Directory containing PDF files.")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into nested directories while collecting PDFs.",
    )
    args = parser.parse_args()

    queue_local_ingest_directory_func = (
        queue_local_ingest_directory_func or queue_local_ingest_directory
    )
    session_factory_func = session_factory_func or get_session_factory
    storage_service_factory = storage_service_factory or StorageService

    storage_service = storage_service_factory()
    session_factory = session_factory_func()

    with session_factory() as session:
        payload = queue_local_ingest_directory_func(
            session,
            Path(args.directory_path).expanduser().resolve(),
            storage_service,
            recursive=args.recursive,
        )
        print(json.dumps(payload.model_dump(mode="json", exclude={"items"})))


def run_ingest_batch_list(
    *,
    list_ingest_batches_func=None,
    session_factory_func=None,
) -> None:
    parser = argparse.ArgumentParser(description="List recent local ingest batches.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of batches.")
    args = parser.parse_args()

    list_ingest_batches_func = list_ingest_batches_func or list_ingest_batches
    session_factory_func = session_factory_func or get_session_factory

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = list_ingest_batches_func(session, limit=args.limit)
    print(json.dumps([row.model_dump(mode="json") for row in payload]))


def run_ingest_batch_show(
    *,
    get_ingest_batch_detail_func=None,
    session_factory_func=None,
) -> None:
    parser = argparse.ArgumentParser(description="Show one local ingest batch and its items.")
    parser.add_argument("batch_id", help="Ingest batch UUID.")
    args = parser.parse_args()

    get_ingest_batch_detail_func = get_ingest_batch_detail_func or get_ingest_batch_detail
    session_factory_func = session_factory_func or get_session_factory

    session_factory = session_factory_func()
    with session_factory() as session:
        payload = get_ingest_batch_detail_func(session, UUID(args.batch_id))
    print(json.dumps(payload.model_dump(mode="json")))
