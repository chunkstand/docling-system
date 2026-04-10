from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

from app.services.docling_parser import ParsedChunk, ParsedDocument, ParsedFigure, ParsedTable, ParsedTableSegment
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
    def __init__(self, chunk_count, table_count, figure_count, persisted_tables, persisted_figures):
        self.results = [
            FakeScalarResult(chunk_count),
            FakeScalarResult(table_count),
            FakeScalarResult(figure_count),
            FakeRowsResult(persisted_tables),
            FakeRowsResult(persisted_figures),
        ]

    def execute(self, statement):
        return self.results.pop(0)


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
            "provenance": [{"page_no": 1, "bbox": {"l": 1, "t": 2, "r": 3, "b": 4, "coord_origin": "BOTTOMLEFT"}}],
        },
    )
    return ParsedDocument(
        title="Chapter 7",
        page_count=4,
        yaml_text="name: sample",
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


def test_validate_persisted_run_passes_with_matching_counts_and_artifacts() -> None:
    parsed = _parsed_document()

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        doc_json = root / "document.json"
        doc_yaml = root / "document.yaml"
        table_json = root / "table.json"
        table_yaml = root / "table.yaml"
        figure_json = root / "figure.json"
        figure_yaml = root / "figure.yaml"
        for path in (doc_json, doc_yaml, table_json, table_yaml, figure_json, figure_yaml):
            path.write_text("ok")

        run = SimpleNamespace(
            id=uuid4(),
            docling_json_path=str(doc_json),
            yaml_path=str(doc_yaml),
        )
        document = SimpleNamespace(id=uuid4())
        persisted_table = SimpleNamespace(json_path=str(table_json), yaml_path=str(table_yaml))
        persisted_figure = SimpleNamespace(json_path=str(figure_json), yaml_path=str(figure_yaml))
        session = FakeSession(
            chunk_count=1,
            table_count=1,
            figure_count=1,
            persisted_tables=[persisted_table],
            persisted_figures=[persisted_figure],
        )

        report = validate_persisted_run(session, document, run, parsed)

    assert report.passed is True
    assert report.details["table_checks"]["detected_count_matches_persisted"] is True


def test_validate_persisted_run_fails_when_table_artifact_missing() -> None:
    parsed = _parsed_document()

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        doc_json = root / "document.json"
        doc_yaml = root / "document.yaml"
        table_json = root / "table.json"
        doc_json.write_text("ok")
        doc_yaml.write_text("ok")
        table_json.write_text("ok")

        run = SimpleNamespace(
            id=uuid4(),
            docling_json_path=str(doc_json),
            yaml_path=str(doc_yaml),
        )
        document = SimpleNamespace(id=uuid4())
        persisted_table = SimpleNamespace(json_path=str(table_json), yaml_path=str(root / "missing.yaml"))
        persisted_figure = SimpleNamespace(json_path=str(root / "figure.json"), yaml_path=str(root / "figure.yaml"))
        session = FakeSession(
            chunk_count=1,
            table_count=1,
            figure_count=1,
            persisted_tables=[persisted_table],
            persisted_figures=[persisted_figure],
        )

        report = validate_persisted_run(session, document, run, parsed)

    assert report.passed is False
    assert report.details["table_details"][0]["yaml_artifact_exists"] is False


def test_validate_persisted_run_fails_when_figure_artifact_missing() -> None:
    parsed = _parsed_document()

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        doc_json = root / "document.json"
        doc_yaml = root / "document.yaml"
        table_json = root / "table.json"
        table_yaml = root / "table.yaml"
        figure_json = root / "figure.json"
        for path in (doc_json, doc_yaml, table_json, table_yaml, figure_json):
            path.write_text("ok")

        run = SimpleNamespace(
            id=uuid4(),
            docling_json_path=str(doc_json),
            yaml_path=str(doc_yaml),
        )
        document = SimpleNamespace(id=uuid4())
        persisted_table = SimpleNamespace(json_path=str(table_json), yaml_path=str(table_yaml))
        persisted_figure = SimpleNamespace(json_path=str(figure_json), yaml_path=str(root / "missing-figure.yaml"))
        session = FakeSession(
            chunk_count=1,
            table_count=1,
            figure_count=1,
            persisted_tables=[persisted_table],
            persisted_figures=[persisted_figure],
        )

        report = validate_persisted_run(session, document, run, parsed)

    assert report.passed is False
    assert report.details["figure_details"][0]["yaml_artifact_exists"] is False
