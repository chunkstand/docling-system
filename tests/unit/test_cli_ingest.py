from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.cli import (
    run_ingest_batch_list,
    run_ingest_batch_show,
    run_ingest_dir,
    run_ingest_file,
)


def test_ingest_file_cli_prints_ingest_result(monkeypatch, capsys) -> None:
    document_id = uuid4()
    run_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-file", "/tmp/example.pdf"])
    monkeypatch.setattr(
        "app.cli.ingest_commands.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr("app.cli.ingest_commands.StorageService", lambda: object())
    monkeypatch.setattr(
        "app.cli.ingest_commands.ingest_local_file",
        lambda session, file_path, storage_service: (
            SimpleNamespace(
                document_id=document_id,
                run_id=run_id,
                status="queued",
                duplicate=False,
                recovery_run=False,
                active_run_id=None,
                active_run_status=None,
            ),
            202,
        ),
    )

    run_ingest_file()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["document_id"] == str(document_id)
    assert output["run_id"] == str(run_id)
    assert output["status"] == "queued"


def test_ingest_dir_cli_prints_batch_summary(monkeypatch, capsys) -> None:
    batch_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-dir", "/tmp/corpus", "--recursive"])
    monkeypatch.setattr(
        "app.cli.ingest_commands.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr("app.cli.ingest_commands.StorageService", lambda: object())
    monkeypatch.setattr(
        "app.cli.ingest_commands.queue_local_ingest_directory",
        lambda session, directory_path, storage_service, recursive: SimpleNamespace(
            model_dump=lambda mode="json", exclude=None: {
                "batch_id": str(batch_id),
                "source_type": "local_directory",
                "status": "completed",
                "root_path": str(directory_path),
                "recursive": recursive,
                "file_count": 2,
                "queued_count": 2,
                "recovery_queued_count": 0,
                "duplicate_count": 0,
                "failed_count": 0,
                "run_status_counts": {"queued": 2},
                "error_message": None,
                "created_at": "2026-04-14T00:00:00Z",
                "completed_at": "2026-04-14T00:00:01Z",
            }
        ),
    )

    run_ingest_dir()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["batch_id"] == str(batch_id)
    assert output["recursive"] is True
    assert output["file_count"] == 2


def test_ingest_batch_list_cli_prints_batches(monkeypatch, capsys) -> None:
    batch_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-batch-list", "--limit", "5"])
    monkeypatch.setattr(
        "app.cli.ingest_commands.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr(
        "app.cli.ingest_commands.list_ingest_batches",
        lambda session, limit: [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "batch_id": str(batch_id),
                    "status": "completed",
                    "file_count": 2,
                }
            )
        ],
    )

    run_ingest_batch_list()

    output = json.loads(capsys.readouterr().out.strip())
    assert output[0]["batch_id"] == str(batch_id)
    assert output[0]["file_count"] == 2


def test_ingest_batch_show_cli_prints_detail(monkeypatch, capsys) -> None:
    batch_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-batch-show", str(batch_id)])
    monkeypatch.setattr(
        "app.cli.ingest_commands.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr(
        "app.cli.ingest_commands.get_ingest_batch_detail",
        lambda session, requested_batch_id: SimpleNamespace(
            model_dump=lambda mode="json": {
                "batch_id": str(requested_batch_id),
                "status": "completed",
                "items": [
                    {
                        "relative_path": "doc.pdf",
                        "status": "queued",
                    }
                ],
            }
        ),
    )

    run_ingest_batch_show()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["batch_id"] == str(batch_id)
    assert output["items"][0]["relative_path"] == "doc.pdf"


def test_ingest_console_scripts_still_target_app_cli_facade() -> None:
    script_targets = tomllib.loads(Path("pyproject.toml").read_text())["project"]["scripts"]

    assert script_targets["docling-system-ingest-file"] == "app.cli:run_ingest_file"
    assert script_targets["docling-system-ingest-dir"] == "app.cli:run_ingest_dir"
    assert script_targets["docling-system-ingest-batch-list"] == "app.cli:run_ingest_batch_list"
    assert script_targets["docling-system-ingest-batch-show"] == "app.cli:run_ingest_batch_show"
    assert run_ingest_file.__module__ == "app.cli"
    assert run_ingest_dir.__module__ == "app.cli"
    assert run_ingest_batch_list.__module__ == "app.cli"
    assert run_ingest_batch_show.__module__ == "app.cli"
