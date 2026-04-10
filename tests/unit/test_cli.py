from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli import run_ingest_file


def test_ingest_file_cli_prints_ingest_result(monkeypatch, capsys) -> None:
    document_id = uuid4()
    run_id = uuid4()

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(sys, "argv", ["docling-system-ingest-file", "/tmp/example.pdf"])
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())
    monkeypatch.setattr("app.cli.StorageService", lambda: object())
    monkeypatch.setattr(
        "app.cli.ingest_local_file",
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
