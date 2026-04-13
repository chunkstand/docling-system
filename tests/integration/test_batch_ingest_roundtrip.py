from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedFigure,
    ParsedTable,
    ParsedTableSegment,
)
from app.services.ingest_batches import get_ingest_batch_detail, queue_local_ingest_directory

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


class StubParser:
    def __init__(self, parsed_document: ParsedDocument) -> None:
        self.parsed_document = parsed_document

    def parse_pdf(self, source_path, *, source_filename=None) -> ParsedDocument:
        assert source_path.exists()
        assert source_filename
        return self.parsed_document


def _build_parsed_document(*, title: str = "Batch Integration Report") -> ParsedDocument:
    chunk_text = "Batch integration keeps multiple queued runs visible and traceable."
    rows = [["Name", "Value"], ["alpha", "batch integration"]]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title="Batch Integration Table",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(rows),
        col_count=2,
        rows=rows,
        metadata={
            "caption": "Batch Integration Table",
            "title_hint": None,
            "segment_label": "table",
            "title_source": "caption",
            "header_rows_retained": 1,
            "header_rows_removed": 0,
            "source_artifact_sha256": "segment-sha",
        },
    )
    table = ParsedTable(
        table_index=0,
        title="Batch Integration Table",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(rows),
        col_count=2,
        rows=rows,
        search_text="Batch Integration Table alpha batch integration",
        preview_text="Name | Value\nalpha | batch integration",
        metadata={
            "is_merged": False,
            "source_segment_count": 1,
            "segment_count": 1,
            "merge_reason": "single_segment",
            "merge_confidence": 1.0,
            "continuation_candidate": False,
            "ambiguous_continuation_candidate": False,
            "repeated_header_rows_removed": False,
            "header_rows_removed_count": 0,
            "title_resolution_source": "caption",
            "merge_sanity_passed": True,
            "header_removal_passed": True,
            "source_segment_indices": [0],
            "source_titles": ["Batch Integration Table"],
        },
        segments=[segment],
    )
    figure = ParsedFigure(
        figure_index=0,
        source_figure_ref="figure-0",
        caption="Batch integration figure",
        heading="Section 1",
        page_from=1,
        page_to=1,
        confidence=0.95,
        metadata={
            "caption_resolution_source": "explicit_ref",
            "caption_candidates": ["Batch integration figure"],
            "caption_attachment_confidence": 1.0,
            "source_confidence": 0.95,
            "annotations": [],
            "provenance": [
                {
                    "page_no": 1,
                    "bbox": {"l": 0, "t": 0, "r": 1, "b": 1, "coord_origin": "TOPLEFT"},
                    "charspan": [0, 1],
                }
            ],
            "source_artifact_sha256": "figure-sha",
        },
    )
    exported_payload = {
        "name": title,
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [{"self_ref": "figure-0", "captions": ["caption-0"], "prov": []}],
    }
    return ParsedDocument(
        title=title,
        page_count=1,
        yaml_text="document: batch-integration\n",
        docling_json=json.dumps(exported_payload, indent=2),
        chunks=[
            ParsedChunk(
                chunk_index=0,
                text=chunk_text,
                heading="Section 1",
                page_from=1,
                page_to=1,
                metadata={"label": "text"},
            )
        ],
        tables=[table],
        raw_table_segments=[segment],
        figures=[figure],
    )


def test_queue_local_directory_ingest_creates_durable_batch_and_tracks_run_progress(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "a.pdf").write_bytes(b"%PDF-1.7\nbatch-a")
    (nested / "b.PDF").write_bytes(b"%PDF-1.7\nbatch-b")
    (root / "ignore.txt").write_text("not a pdf")

    allowed_root = root.resolve()
    monkeypatch.setattr(
        "app.services.ingest_batches._allowed_ingest_roots",
        lambda: [allowed_root],
    )
    monkeypatch.setattr(
        "app.services.documents._allowed_ingest_roots",
        lambda: [allowed_root],
    )
    monkeypatch.setattr(
        "app.services.documents.get_settings",
        lambda: SimpleNamespace(local_ingest_max_file_bytes=1024 * 1024, local_ingest_max_pages=10),
    )
    monkeypatch.setattr("app.services.documents._pdf_page_count", lambda _path: 1)

    with postgres_integration_harness.session_factory() as session:
        batch = queue_local_ingest_directory(
            session,
            root,
            postgres_integration_harness.storage_service,
            recursive=True,
        )

    assert batch.source_type == "local_directory"
    assert batch.status == "running"
    assert batch.completed_at is None
    assert batch.file_count == 2
    assert batch.queued_count == 2
    assert batch.failed_count == 0
    assert batch.run_status_counts == {"queued": 2}
    assert [item.relative_path for item in batch.items] == ["a.pdf", "nested/b.PDF"]
    assert all(item.run_id is not None for item in batch.items)
    assert all(item.current_run_status == "queued" for item in batch.items)

    parser = StubParser(_build_parsed_document())
    postgres_integration_harness.process_next_run(parser)
    postgres_integration_harness.process_next_run(parser)

    with postgres_integration_harness.session_factory() as session:
        refreshed = get_ingest_batch_detail(session, batch.batch_id)

    assert refreshed.status == "completed"
    assert refreshed.completed_at is not None
    assert refreshed.run_status_counts == {"completed": 2}
    assert all(item.current_run_status == "completed" for item in refreshed.items)


class FailingParser:
    def parse_pdf(self, source_path, *, source_filename=None):
        assert source_path.exists()
        assert source_filename
        raise ValueError("Intentional parse failure")


def test_queue_local_directory_ingest_reports_completed_with_errors_when_runs_fail(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "a.pdf").write_bytes(b"%PDF-1.7\nbatch-a")
    (root / "b.pdf").write_bytes(b"%PDF-1.7\nbatch-b")

    allowed_root = root.resolve()
    monkeypatch.setattr(
        "app.services.ingest_batches._allowed_ingest_roots",
        lambda: [allowed_root],
    )
    monkeypatch.setattr(
        "app.services.documents._allowed_ingest_roots",
        lambda: [allowed_root],
    )
    monkeypatch.setattr(
        "app.services.documents.get_settings",
        lambda: SimpleNamespace(local_ingest_max_file_bytes=1024 * 1024, local_ingest_max_pages=10),
    )
    monkeypatch.setattr("app.services.documents._pdf_page_count", lambda _path: 1)

    with postgres_integration_harness.session_factory() as session:
        batch = queue_local_ingest_directory(
            session,
            root,
            postgres_integration_harness.storage_service,
        )

    assert batch.status == "running"
    assert batch.completed_at is None
    assert batch.run_status_counts == {"queued": 2}

    postgres_integration_harness.process_next_run(FailingParser())
    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document(title="Recovered")))

    with postgres_integration_harness.session_factory() as session:
        refreshed = get_ingest_batch_detail(session, batch.batch_id)

    assert refreshed.status == "completed_with_errors"
    assert refreshed.completed_at is not None
    assert refreshed.run_status_counts == {"completed": 1, "failed": 1}


def test_queue_local_directory_ingest_marks_batch_failed_when_directory_scan_errors(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "corpus"
    root.mkdir()

    allowed_root = root.resolve()
    monkeypatch.setattr(
        "app.services.ingest_batches._allowed_ingest_roots",
        lambda: [allowed_root],
    )
    monkeypatch.setattr(
        "app.services.ingest_batches._iter_directory_children",
        lambda _directory_path: (_ for _ in ()).throw(PermissionError("scan denied")),
    )

    with postgres_integration_harness.session_factory() as session:
        batch = queue_local_ingest_directory(
            session,
            root,
            postgres_integration_harness.storage_service,
        )

    assert batch.status == "failed"
    assert batch.file_count == 0
    assert batch.completed_at is not None
    assert batch.error_message == "Directory scan failed: scan denied"
