from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

import yaml

from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedFigure,
    ParsedTable,
    ParsedTableSegment,
)
from app.services.validation import validate_persisted_run


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeRowsResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(
        self,
        chunk_rows,
        table_rows,
        segment_rows,
        figure_rows,
    ):
        self.results = [
            FakeScalarResult(len(chunk_rows)),
            FakeScalarResult(len(table_rows)),
            FakeScalarResult(len(figure_rows)),
            FakeRowsResult(chunk_rows),
            FakeRowsResult(table_rows),
            FakeRowsResult(segment_rows),
            FakeRowsResult(figure_rows),
        ]

    def execute(self, statement):
        return self.results.pop(0)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _parsed_document() -> ParsedDocument:
    table_segment = ParsedTableSegment(
        segment_index=0,
        segment_order=1,
        source_table_ref="#/tables/0",
        title="TABLE 1",
        heading="701.2 Drainage Piping",
        page_from=1,
        page_to=1,
        row_count=2,
        col_count=2,
        rows=[["Fixture", "DFU"], ["Sink", "2"]],
        metadata={},
    )
    table = ParsedTable(
        table_index=0,
        title="TABLE 1",
        heading="701.2 Drainage Piping",
        page_from=1,
        page_to=1,
        row_count=2,
        col_count=2,
        rows=[["Fixture", "DFU"], ["Sink", "2"]],
        search_text="TABLE 1\nFixture | DFU\nSink | 2",
        preview_text="Fixture | DFU",
        metadata={"merge_sanity_passed": True, "header_removal_passed": True},
        segments=[table_segment],
    )
    figure = ParsedFigure(
        figure_index=0,
        source_figure_ref="#/pictures/0",
        caption="Fixture Venting Diagram",
        heading="Chapter 7",
        page_from=1,
        page_to=1,
        confidence=0.9,
        metadata={
            "caption_resolution_source": "explicit_ref",
            "caption_attachment_confidence": 1.0,
            "source_confidence": None,
            "provenance": [
                {
                    "page_no": 1,
                    "bbox": {"l": 1, "t": 2, "r": 3, "b": 4, "coord_origin": "BOTTOMLEFT"},
                }
            ],
        },
    )
    return ParsedDocument(
        title="Chapter 7",
        page_count=4,
        yaml_text="name: sample\n",
        docling_json='{"name":"sample"}',
        chunks=[
            ParsedChunk(
                chunk_index=0,
                text="Body text",
                heading="Chapter 7",
                page_from=1,
                page_to=1,
                metadata={},
            )
        ],
        tables=[table],
        raw_table_segments=[table_segment],
        figures=[figure],
    )


@contextmanager
def _build_validation_fixture():
    parsed = _parsed_document()
    document_id = uuid4()
    run_id = uuid4()
    table_id = uuid4()
    figure_id = uuid4()
    created_at = datetime.now(UTC)

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        doc_json = root / "docling.json"
        doc_yaml = root / "document.yaml"
        table_json = root / "table.json"
        table_yaml = root / "table.yaml"
        figure_json = root / "figure.json"
        figure_yaml = root / "figure.yaml"

        doc_json.write_text(parsed.docling_json)
        doc_yaml.write_text(parsed.yaml_text)

        table_payload = parsed.tables[0].artifact_payload(
            document_id=str(document_id),
            run_id=str(run_id),
            table_id=str(table_id),
            logical_table_key=None,
            created_at=created_at.isoformat(),
        )
        table_json_bytes = json.dumps(table_payload, indent=2).encode("utf-8")
        table_yaml_bytes = yaml.safe_dump(
            table_payload,
            sort_keys=False,
            allow_unicode=True,
        ).encode("utf-8")
        table_json.write_bytes(table_json_bytes)
        table_yaml.write_bytes(table_yaml_bytes)

        table_audit = {
            "extractor_version": "docling",
            "profile_name": "standard_pdf",
            "fallback_used": False,
            "source_segment_refs": [segment.source_table_ref for segment in parsed.tables[0].segments],
            "page_from": parsed.tables[0].page_from,
            "page_to": parsed.tables[0].page_to,
            "json_artifact_sha256": _sha256_bytes(table_json_bytes),
            "yaml_artifact_sha256": _sha256_bytes(table_yaml_bytes),
            "search_text_sha256": hashlib.sha256(
                parsed.tables[0].search_text.encode("utf-8")
            ).hexdigest(),
            "merge_metadata_sha256": hashlib.sha256(
                json.dumps(parsed.tables[0].metadata, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }
        parsed.tables[0].metadata = {**parsed.tables[0].metadata, "audit": table_audit}

        figure_payload = parsed.figures[0].artifact_payload(
            document_id=str(document_id),
            run_id=str(run_id),
            figure_id=str(figure_id),
            created_at=created_at.isoformat(),
        )
        figure_json_bytes = json.dumps(figure_payload, indent=2).encode("utf-8")
        figure_yaml_bytes = yaml.safe_dump(
            figure_payload,
            sort_keys=False,
            allow_unicode=True,
        ).encode("utf-8")
        figure_json.write_bytes(figure_json_bytes)
        figure_yaml.write_bytes(figure_yaml_bytes)

        figure_audit = {
            "extractor_version": "docling",
            "profile_name": "standard_pdf",
            "fallback_used": False,
            "page_from": parsed.figures[0].page_from,
            "page_to": parsed.figures[0].page_to,
            "json_artifact_sha256": _sha256_bytes(figure_json_bytes),
            "yaml_artifact_sha256": _sha256_bytes(figure_yaml_bytes),
        }
        parsed.figures[0].metadata = {**parsed.figures[0].metadata, "audit": figure_audit}

        document = SimpleNamespace(id=document_id)
        run = SimpleNamespace(
            id=run_id,
            docling_json_path=str(doc_json),
            yaml_path=str(doc_yaml),
        )
        chunk_row = SimpleNamespace(
            chunk_index=0,
            text=parsed.chunks[0].text,
            heading=parsed.chunks[0].heading,
            page_from=parsed.chunks[0].page_from,
            page_to=parsed.chunks[0].page_to,
            metadata_json=parsed.chunks[0].metadata,
            embedding=parsed.chunks[0].embedding,
        )
        table_row = SimpleNamespace(
            id=table_id,
            document_id=document_id,
            run_id=run_id,
            table_index=parsed.tables[0].table_index,
            title=parsed.tables[0].title,
            logical_table_key=None,
            heading=parsed.tables[0].heading,
            page_from=parsed.tables[0].page_from,
            page_to=parsed.tables[0].page_to,
            row_count=parsed.tables[0].row_count,
            col_count=parsed.tables[0].col_count,
            search_text=parsed.tables[0].search_text,
            preview_text=parsed.tables[0].preview_text,
            metadata_json=parsed.tables[0].metadata,
            embedding=parsed.tables[0].embedding,
            json_path=str(table_json),
            yaml_path=str(table_yaml),
            created_at=created_at,
        )
        segment_row = SimpleNamespace(
            table_id=table_id,
            segment_index=parsed.tables[0].segments[0].segment_index,
            source_table_ref=parsed.tables[0].segments[0].source_table_ref,
            page_from=parsed.tables[0].segments[0].page_from,
            page_to=parsed.tables[0].segments[0].page_to,
            segment_order=parsed.tables[0].segments[0].segment_order,
            metadata_json=parsed.tables[0].segments[0].metadata,
        )
        figure_row = SimpleNamespace(
            id=figure_id,
            document_id=document_id,
            run_id=run_id,
            figure_index=parsed.figures[0].figure_index,
            source_figure_ref=parsed.figures[0].source_figure_ref,
            caption=parsed.figures[0].caption,
            heading=parsed.figures[0].heading,
            page_from=parsed.figures[0].page_from,
            page_to=parsed.figures[0].page_to,
            confidence=parsed.figures[0].confidence,
            metadata_json=parsed.figures[0].metadata,
            json_path=str(figure_json),
            yaml_path=str(figure_yaml),
            created_at=created_at,
        )
        session = FakeSession(
            chunk_rows=[chunk_row],
            table_rows=[table_row],
            segment_rows=[segment_row],
            figure_rows=[figure_row],
        )

        yield {
            "parsed": parsed,
            "document": document,
            "run": run,
            "session": session,
            "rows": {
                "chunk": chunk_row,
                "table": table_row,
                "segment": segment_row,
                "figure": figure_row,
            },
            "paths": {
                "doc_json": doc_json,
                "doc_yaml": doc_yaml,
                "table_json": table_json,
                "table_yaml": table_yaml,
                "figure_json": figure_json,
                "figure_yaml": figure_yaml,
            },
        }


def test_validate_persisted_run_passes_with_matching_counts_and_artifacts() -> None:
    with _build_validation_fixture() as fixture:
        report = validate_persisted_run(
            fixture["session"],
            fixture["document"],
            fixture["run"],
            fixture["parsed"],
        )

        assert report.passed is True
        assert report.warning_count == 0
        assert report.details["document_checks"]["docling_json_matches"] is True
        assert report.details["chunk_checks"]["all_chunk_checks_passed"] is True
        assert report.details["table_details"][0]["json_artifact_hash_matches"] is True
        assert report.details["figure_details"][0]["json_artifact_content_matches"] is True


def test_validate_persisted_run_fails_when_document_artifact_content_is_corrupted() -> None:
    with _build_validation_fixture() as fixture:
        fixture["paths"]["doc_json"].write_text('{"corrupted": true}')

        report = validate_persisted_run(
            fixture["session"],
            fixture["document"],
            fixture["run"],
            fixture["parsed"],
        )

        assert report.passed is False
        assert report.details["document_checks"]["docling_json_matches"] is False


def test_validate_persisted_run_fails_when_table_artifact_is_corrupted() -> None:
    with _build_validation_fixture() as fixture:
        fixture["paths"]["table_json"].write_text('{"not":"the expected table"}')

        report = validate_persisted_run(
            fixture["session"],
            fixture["document"],
            fixture["run"],
            fixture["parsed"],
        )

        assert report.passed is False
        assert report.details["table_details"][0]["json_artifact_hash_matches"] is False
        assert report.details["table_details"][0]["json_artifact_content_matches"] is False


def test_validate_persisted_run_fails_when_figure_artifact_missing() -> None:
    with _build_validation_fixture() as fixture:
        fixture["paths"]["figure_yaml"].unlink()

        report = validate_persisted_run(
            fixture["session"],
            fixture["document"],
            fixture["run"],
            fixture["parsed"],
        )

        assert report.passed is False
        assert report.details["figure_details"][0]["yaml_artifact_exists"] is False


def test_validate_persisted_run_allows_ambiguous_table_merge_issue_as_warning() -> None:
    with _build_validation_fixture() as fixture:
        fixture["parsed"].tables[0].metadata["ambiguous_continuation_candidate"] = True
        fixture["parsed"].tables[0].metadata["merge_confidence"] = 0.8
        fixture["parsed"].tables[0].metadata["header_removal_passed"] = False
        table_row = fixture["rows"]["table"]
        table_payload = {
            "schema_version": "1.0",
            "document_id": str(fixture["document"].id),
            "run_id": str(fixture["run"].id),
            "table_id": str(table_row.id),
            "table_index": fixture["parsed"].tables[0].table_index,
            "logical_table_key": table_row.logical_table_key,
            "title": fixture["parsed"].tables[0].title,
            "heading": fixture["parsed"].tables[0].heading,
            "page_from": fixture["parsed"].tables[0].page_from,
            "page_to": fixture["parsed"].tables[0].page_to,
            "row_count": fixture["parsed"].tables[0].row_count,
            "col_count": fixture["parsed"].tables[0].col_count,
            "created_at": table_row.created_at.isoformat(),
            "search_text": fixture["parsed"].tables[0].search_text,
            "preview_text": fixture["parsed"].tables[0].preview_text,
            "metadata": {
                key: value
                for key, value in fixture["parsed"].tables[0].metadata.items()
                if key != "audit"
            },
            "rows": fixture["parsed"].tables[0].rows,
            "segments": [
                {
                    "segment_index": segment.segment_index,
                    "segment_order": segment.segment_order,
                    "source_table_ref": segment.source_table_ref,
                    "title": segment.title,
                    "heading": segment.heading,
                    "page_from": segment.page_from,
                    "page_to": segment.page_to,
                    "row_count": segment.row_count,
                    "col_count": segment.col_count,
                    "metadata": segment.metadata,
                }
                for segment in fixture["parsed"].tables[0].segments
            ],
        }
        table_json_bytes = json.dumps(table_payload, indent=2).encode("utf-8")
        table_yaml_bytes = yaml.safe_dump(
            table_payload,
            sort_keys=False,
            allow_unicode=True,
        ).encode("utf-8")
        fixture["paths"]["table_json"].write_bytes(table_json_bytes)
        fixture["paths"]["table_yaml"].write_bytes(table_yaml_bytes)
        updated_audit = {
            **fixture["parsed"].tables[0].metadata["audit"],
            "json_artifact_sha256": _sha256_bytes(table_json_bytes),
            "yaml_artifact_sha256": _sha256_bytes(table_yaml_bytes),
            "merge_metadata_sha256": hashlib.sha256(
                json.dumps(
                    {
                        key: value
                        for key, value in fixture["parsed"].tables[0].metadata.items()
                        if key != "audit"
                    },
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest(),
        }
        fixture["parsed"].tables[0].metadata = {
            **fixture["parsed"].tables[0].metadata,
            "audit": updated_audit,
        }
        table_row.metadata_json = fixture["parsed"].tables[0].metadata

        report = validate_persisted_run(
            fixture["session"],
            fixture["document"],
            fixture["run"],
            fixture["parsed"],
        )

        assert report.passed is True
        assert report.warning_count == 1
        assert report.summary == "Validation passed with warnings."
        assert report.details["table_details"][0]["warning_checks"] == [
            "repeated_header_row_removal_sane"
        ]
