from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import IngestBatch, RunStatus
from app.services.ingest_batches import (
    _derive_batch_status,
    _iter_local_pdf_files,
    _resolve_batch_item,
)


def test_iter_local_pdf_files_preserves_symlink_pdf_paths_and_skips_symlink_dirs(
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    nested = root / "nested"
    nested.mkdir(parents=True)

    direct_pdf = root / "a.pdf"
    direct_pdf.write_bytes(b"%PDF-1.7\ndirect")
    nested_pdf = nested / "b.pdf"
    nested_pdf.write_bytes(b"%PDF-1.7\nnested")

    linked_pdf = root / "linked.pdf"
    linked_pdf.symlink_to(nested_pdf)

    external = tmp_path / "external"
    external.mkdir()
    external_pdf = external / "outside.pdf"
    external_pdf.write_bytes(b"%PDF-1.7\noutside")
    linked_directory = root / "linked-dir"
    linked_directory.symlink_to(external, target_is_directory=True)

    discovered = _iter_local_pdf_files(root, recursive=True)

    assert discovered == [direct_pdf, linked_pdf, nested_pdf]
    assert all(path.parent != linked_directory for path in discovered)


def test_derive_batch_status_tracks_inflight_and_failed_runs() -> None:
    batch = IngestBatch(
        id=uuid4(),
        source_type="local_directory",
        status="completed",
        root_path="/tmp/corpus",
        recursive=True,
        file_count=2,
        queued_count=2,
        recovery_queued_count=0,
        duplicate_count=0,
        failed_count=0,
        created_at=datetime.now(UTC),
    )

    assert _derive_batch_status(batch, {"queued": 2}) == "running"
    assert _derive_batch_status(batch, {"completed": 2}) == "completed"
    assert _derive_batch_status(batch, {"completed": 1, "failed": 1}) == "completed_with_errors"

    batch.failed_count = 1
    assert _derive_batch_status(batch, {"completed": 1}) == "completed_with_errors"

    batch.status = "failed"
    assert _derive_batch_status(batch, {}) == "failed"


def test_derive_batch_status_prefers_resolution_counts_when_failures_are_recovered() -> None:
    batch = IngestBatch(
        id=uuid4(),
        source_type="local_directory",
        status="completed",
        root_path="/tmp/corpus",
        recursive=True,
        file_count=1,
        queued_count=1,
        recovery_queued_count=0,
        duplicate_count=0,
        failed_count=0,
        created_at=datetime.now(UTC),
    )

    assert (
        _derive_batch_status(
            batch,
            {"failed": 1},
            {"recovered": 1},
        )
        == "completed"
    )


def test_resolve_batch_item_marks_failed_run_with_later_success_as_recovered() -> None:
    document_id = uuid4()
    failed_run_id = uuid4()
    recovered_run_id = uuid4()
    now = datetime.now(UTC)
    item = SimpleNamespace(
        status="queued",
        duplicate=False,
        recovery_run=False,
        run_id=failed_run_id,
        document_id=document_id,
    )
    current_run = SimpleNamespace(
        id=failed_run_id,
        status=RunStatus.FAILED.value,
        completed_at=now,
    )
    document = SimpleNamespace(id=document_id)
    active_run = SimpleNamespace(
        id=recovered_run_id,
        status=RunStatus.COMPLETED.value,
        completed_at=now,
    )

    resolution = _resolve_batch_item(
        item,
        current_run=current_run,
        document=document,
        active_run=active_run,
        latest_run=active_run,
    )

    assert resolution.resolved_status == "recovered"
    assert resolution.resolved_run_id == recovered_run_id
    assert resolution.resolution_reason == "superseded_by_later_successful_run"


def test_resolve_batch_item_marks_rejected_item_as_recovered_when_same_document_exists() -> None:
    document_id = uuid4()
    recovered_run_id = uuid4()
    now = datetime.now(UTC)
    item = SimpleNamespace(
        status="failed",
        duplicate=False,
        recovery_run=False,
        run_id=None,
        document_id=None,
    )
    document = SimpleNamespace(id=document_id)
    active_run = SimpleNamespace(
        id=recovered_run_id,
        status=RunStatus.COMPLETED.value,
        completed_at=now,
    )

    resolution = _resolve_batch_item(
        item,
        current_run=None,
        document=document,
        active_run=active_run,
        latest_run=active_run,
    )

    assert resolution.resolved_status == "recovered"
    assert resolution.resolved_run_id == recovered_run_id
    assert resolution.resolution_reason == "matched_successful_document_by_checksum"
