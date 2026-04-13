from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.db.models import IngestBatch
from app.services.ingest_batches import _derive_batch_status, _iter_local_pdf_files


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
