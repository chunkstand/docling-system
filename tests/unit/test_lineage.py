from __future__ import annotations

import hashlib
from types import SimpleNamespace
from uuid import uuid4

from app.services.docling_parser import ParsedDocument, ParsedTable, ParsedTableSegment
from app.services.runs import _build_lineage_assignments


class FakeScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, statement):
        return FakeScalarRows(self.rows)


def _table(title: str | None) -> ParsedTable:
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=1,
        source_table_ref="#/tables/0",
        title=title,
        heading="702.1 Trap Size",
        page_from=7,
        page_to=9,
        row_count=2,
        col_count=2,
        rows=[["A", "B"]],
        metadata={},
    )
    return ParsedTable(
        table_index=0,
        title=title,
        heading="702.1 Trap Size",
        page_from=7,
        page_to=9,
        row_count=2,
        col_count=2,
        rows=[["A", "B"]],
        search_text="TABLE",
        preview_text="A | B",
        metadata={},
        segments=[segment],
    )


def test_lineage_assignments_reuse_logical_key_on_rerun() -> None:
    source = "table 702.1 drainage fixture unit values (dfu)|702.1 trap size|2"
    logical_key = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    previous = SimpleNamespace(
        logical_table_key=logical_key,
        table_version=1,
        id=uuid4(),
        lineage_group=logical_key,
    )
    session = FakeSession([previous])
    document = SimpleNamespace(active_run_id=uuid4())
    parsed = ParsedDocument(
        title="doc",
        page_count=1,
        yaml_text="",
        docling_json="{}",
        chunks=[],
        tables=[_table("TABLE 702.1 DRAINAGE FIXTURE UNIT VALUES (DFU)")],
        raw_table_segments=[],
        figures=[],
    )

    assignments = _build_lineage_assignments(session, document, parsed)

    assert assignments[0]["logical_table_key"] == logical_key
    assert assignments[0]["table_version"] == 2


def test_lineage_assignments_leave_ambiguous_key_null() -> None:
    session = FakeSession([])
    document = SimpleNamespace(active_run_id=None)
    parsed = ParsedDocument(
        title="doc",
        page_count=1,
        yaml_text="",
        docling_json="{}",
        chunks=[],
        tables=[_table(None)],
        raw_table_segments=[],
        figures=[],
    )

    assignments = _build_lineage_assignments(session, document, parsed)

    assert assignments[0]["logical_table_key"] is None
