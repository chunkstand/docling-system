from __future__ import annotations

from types import SimpleNamespace

from app.services.docling_parser import (
    ParsedTable,
    ParsedTableSegment,
    TableFamilyMatcher,
    TableSupplementRule,
    _apply_registered_table_supplements,
    _apply_table_family_overlays,
    _group_tables_by_title_regex_family,
    _load_table_supplement_registry,
)

UPC_510_FAMILY_PATTERN = r"TABLE\s+510\.1\.2\s*(?:\(\s*\d+\s*\)|\d+)"


def _make_table(
    *,
    table_index: int,
    title: str | None,
    page_from: int,
    page_to: int,
    rows: list[list[str]],
    heading: str = "510.1.2 Elbows",
    segment_index: int | None = None,
) -> ParsedTable:
    resolved_segment_index = segment_index if segment_index is not None else table_index
    segment = ParsedTableSegment(
        segment_index=resolved_segment_index,
        segment_order=resolved_segment_index,
        source_table_ref=f"#/tables/{resolved_segment_index}",
        title=title,
        heading=heading,
        page_from=page_from,
        page_to=page_to,
        row_count=len(rows),
        col_count=max((len(row) for row in rows), default=0),
        rows=rows,
        metadata={"title_source": "caption", "header_rows_removed": 0, "header_rows_retained": 3},
    )
    return ParsedTable(
        table_index=table_index,
        title=title,
        heading=heading,
        page_from=page_from,
        page_to=page_to,
        row_count=len(rows),
        col_count=max((len(row) for row in rows), default=0),
        rows=rows,
        search_text="\n".join(" | ".join(row) for row in rows),
        preview_text="\n".join(" | ".join(row) for row in rows[:4]),
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
            "source_segment_indices": [resolved_segment_index],
            "source_titles": [title] if title else [],
        },
        segments=[segment],
    )


def _make_title_regex_matcher(
    *,
    family_key_pattern: str = UPC_510_FAMILY_PATTERN,
    continuation_title_pattern: str | None = r"\bcontinued\b",
    max_page_gap: int = 1,
    require_same_heading: bool = True,
) -> TableFamilyMatcher:
    return TableFamilyMatcher(
        kind="title_regex_family",
        family_key_pattern=family_key_pattern,
        continuation_title_pattern=continuation_title_pattern,
        max_page_gap=max_page_gap,
        require_same_heading=require_same_heading,
    )


def test_apply_table_family_overlays_replaces_corrupted_upc_family() -> None:
    corrupted_tables = [
        _make_table(
            table_index=0,
            title="TABLE 510.1.2(2) TYPE B DOUBLE-WALL GAS VENT [NFPA 54: TABLE 13.1(b)]*",
            page_from=109,
            page_to=111,
            rows=[["10", "2733029 1940"], ["15", "3062988 1910"]],
            segment_index=21,
        ),
        _make_table(
            table_index=1,
            title="TABLE 510.1.2(2)",
            page_from=112,
            page_to=112,
            rows=[["50", "N", "N"], ["100", "0", "1316"]],
            segment_index=24,
        ),
        _make_table(
            table_index=2,
            title=(
                "TABLE 510.1.2(5) SINGLE-WALL METAL PIPE OR TYPE B ASBESTOS-CEMENT "
                "VENT [NFPA 54: TABLE 13.1(e)]*"
            ),
            page_from=120,
            page_to=121,
            rows=[["10", "2", "216"], ["15", "2", "211"]],
            segment_index=36,
        ),
    ]

    supplement_tables = [
        _make_table(
            table_index=0,
            title="TABLE 510.1.2 ( 2 ) TYPE B DOUBLE-WALL GAS VENT [ NFPA 54 : TABLE 13.1(b)]*",
            page_from=4,
            page_to=5,
            rows=[["10", "273", "3029", "1940"], ["15", "306", "2988", "1910"]],
            segment_index=4,
        ),
        _make_table(
            table_index=1,
            title="TABLE 510.1.2 ( 2 ) -[ :",
            page_from=5,
            page_to=6,
            rows=[["10", "229", "645", "437"], ["15", "272", "630", "420"]],
            segment_index=5,
        ),
    ]

    result = _apply_table_family_overlays(
        corrupted_tables,
        supplement_tables,
        family_matcher=_make_title_regex_matcher(),
        supplement_filename="510.1.2.pdf",
    )

    assert len(result) == 2
    assert result[0].table_index == 0
    assert result[0].title == supplement_tables[0].title
    assert result[0].page_from == 109
    assert result[0].page_to == 112
    assert result[0].rows[0] == ["10", "273", "3029", "1940"]
    assert result[0].rows[-1] == ["15", "272", "630", "420"]
    assert result[0].metadata["overlay_applied"] is True
    assert result[0].metadata["overlay_source_filename"] == "510.1.2.pdf"
    assert result[0].metadata["overlay_family_key"] == "TABLE 510.1.2(2)"
    assert result[0].metadata["overlay_original_table_indices"] == [0, 1]
    assert result[0].metadata["overlay_source_table_indices"] == [0, 1]
    assert [segment.segment_index for segment in result[0].segments] == [21, 24]
    assert result[1].title == corrupted_tables[2].title


def test_apply_table_family_overlays_does_not_absorb_later_titled_tables() -> None:
    chapter_tables = [
        _make_table(
            table_index=0,
            title="TABLE 510.1.2(6) EXTERIOR MASONRY CHIMNEY [NFPA 54: TABLE 13.1(f)]1, 2",
            page_from=122,
            page_to=124,
            rows=[["5", "35", "67"], ["10", "30", "58"]],
            heading="510.1.2 Elbows",
            segment_index=38,
        ),
        _make_table(
            table_index=1,
            title="TABLE 509.4 TYPE OF VENTING SYSTEM TO BE USED [NFPA 54: TABLE 12.5.1]",
            page_from=125,
            page_to=125,
            rows=[["Listed Category I appliances", "Type B gas vent"]],
            heading="509.4 Type of Venting System",
            segment_index=41,
        ),
    ]
    supplement_tables = [
        _make_table(
            table_index=0,
            title="TABLE 510.1.2 ( 6 ) EXTERIOR MASONRY CHIMNEY [ NFPA 54 : TABLE 13.1(f)] 1, 2",
            page_from=11,
            page_to=12,
            rows=[["NUMBEROFAPPLIANCES:", "SINGLE"], ["5", "35"]],
            segment_index=11,
        )
    ]

    result = _apply_table_family_overlays(
        chapter_tables,
        supplement_tables,
        family_matcher=_make_title_regex_matcher(),
        supplement_filename="510.1.2.pdf",
    )

    assert len(result) == 2
    assert result[0].metadata["overlay_applied"] is True
    assert result[0].metadata["overlay_original_table_indices"] == [0]
    assert result[1].title == chapter_tables[1].title
    assert result[1].metadata.get("overlay_applied") is None


def test_group_tables_by_title_regex_family_keeps_titled_continued_fragment() -> None:
    tables = [
        _make_table(
            table_index=0,
            title="TABLE 510.1.2 ( 1 ) TYPE B DOUBLE-WALL GAS VENT [ NFPA 54 :",
            page_from=1,
            page_to=1,
            rows=[["a"]],
        ),
        _make_table(
            table_index=1,
            title="TABLE 13.1(a)] (continued)",
            page_from=2,
            page_to=2,
            rows=[["b"]],
        ),
        _make_table(
            table_index=2,
            title="TABLE 510.2(1) TYPE B DOUBLE-WALL VENT [NFPA 54: TABLE 13.2(a)]*",
            page_from=3,
            page_to=3,
            rows=[["c"]],
            heading="510.2 Multiple Appliance Vent Table 510.2(1) Through Table 510.2(9)",
        ),
        _make_table(
            table_index=3,
            title="OF BTU PER HOUR",
            page_from=4,
            page_to=4,
            rows=[["d"]],
            heading="510.2 Multiple Appliance Vent Table 510.2(1) Through Table 510.2(9)",
        ),
    ]

    grouped = _group_tables_by_title_regex_family(
        tables,
        matcher=_make_title_regex_matcher(),
    )

    assert list(grouped) == ["TABLE 510.1.2(1)"]
    assert [table.table_index for table in grouped["TABLE 510.1.2(1)"]] == [0, 1]


def test_load_table_supplement_registry_reads_rules(tmp_path) -> None:
    registry_path = tmp_path / "table_supplements.yaml"
    registry_path.write_text(
        """
rules:
  - document_filenames:
      - UPC_CH_5.pdf
      - nested/UPC_CH_6.pdf
    supplement_filename: UPC/510.1.2.pdf
    matcher: title_regex_family
    family_key_pattern: 'TABLE\\s+510\\.1\\.2\\s*(?:\\(\\s*\\d+\\s*\\)|\\d+)'
    continuation_title_pattern: '\\bcontinued\\b'
    overlay_type: clean_pdf_family_replacement
    description: Example rule
""".strip()
    )

    rules = _load_table_supplement_registry(str(registry_path))

    assert len(rules) == 1
    assert rules[0].document_filenames == ("UPC_CH_5.pdf", "UPC_CH_6.pdf")
    assert rules[0].supplement_filename == "510.1.2.pdf"
    assert rules[0].matcher.kind == "title_regex_family"
    assert rules[0].matcher.family_key_pattern == UPC_510_FAMILY_PATTERN
    assert rules[0].overlay_type == "clean_pdf_family_replacement"
    assert rules[0].description == "Example rule"


def test_load_table_supplement_registry_refreshes_when_file_changes(tmp_path) -> None:
    registry_path = tmp_path / "table_supplements.yaml"
    registry_path.write_text(
        """
rules:
  - document_filenames: first.pdf
    supplement_filename: clean/first.pdf
    matcher: title_regex_family
    family_key_pattern: 'FIRST'
""".strip()
    )

    first_rules = _load_table_supplement_registry(str(registry_path))

    registry_path.write_text(
        """
rules:
  - document_filenames: second.pdf
    supplement_filename: clean/second.pdf
    matcher: title_regex_family
    family_key_pattern: 'SECOND'
    description: Updated rule
""".strip()
    )

    second_rules = _load_table_supplement_registry(str(registry_path))

    assert first_rules[0].document_filenames == ("first.pdf",)
    assert second_rules[0].document_filenames == ("second.pdf",)
    assert second_rules[0].description == "Updated rule"


def test_apply_registered_table_supplements_uses_matching_rule(monkeypatch, tmp_path) -> None:
    chapter_tables = [
        _make_table(
            table_index=0,
            title="TABLE 510.1.2(2) TYPE B DOUBLE-WALL GAS VENT [NFPA 54: TABLE 13.1(b)]*",
            page_from=109,
            page_to=111,
            rows=[["10", "2733029 1940"]],
        )
    ]
    supplement_tables = [
        _make_table(
            table_index=0,
            title="TABLE 510.1.2 ( 2 ) TYPE B DOUBLE-WALL GAS VENT [ NFPA 54 : TABLE 13.1(b)]*",
            page_from=4,
            page_to=5,
            rows=[["10", "273", "3029", "1940"]],
        )
    ]

    class FakeParser:
        def parse_pdf(self, source_path, *, source_filename=None):  # noqa: ANN001, ANN202
            return SimpleNamespace(tables=supplement_tables)

    supplement_path = tmp_path / "510.1.2.pdf"
    supplement_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "app.services.docling_parser._resolve_table_supplement_path",
        lambda supplement_filename, *, source_path: supplement_path,
    )

    rules = (
        TableSupplementRule(
            document_filenames=("UPC_CH_5.pdf",),
            supplement_filename="510.1.2.pdf",
            matcher=_make_title_regex_matcher(),
            overlay_type="clean_pdf_family_replacement",
        ),
    )

    result = _apply_registered_table_supplements(
        tmp_path / "UPC_CH_5.pdf",
        chapter_tables,
        source_filename="UPC_CH_5.pdf",
        registry_rules=rules,
        parser=FakeParser(),
    )

    assert result[0].metadata["overlay_applied"] is True
    assert result[0].metadata["overlay_type"] == "clean_pdf_family_replacement"
    assert result[0].rows[0] == ["10", "273", "3029", "1940"]


def test_apply_registered_table_supplements_skips_non_matching_rule(tmp_path) -> None:
    chapter_tables = [
        _make_table(
            table_index=0,
            title="TABLE 510.1.2(2) TYPE B DOUBLE-WALL GAS VENT [NFPA 54: TABLE 13.1(b)]*",
            page_from=109,
            page_to=111,
            rows=[["10", "2733029 1940"]],
        )
    ]
    rules = (
        TableSupplementRule(
            document_filenames=("UPC_CH_6.pdf",),
            supplement_filename="510.1.2.pdf",
            matcher=_make_title_regex_matcher(),
            overlay_type="clean_pdf_family_replacement",
        ),
    )

    result = _apply_registered_table_supplements(
        tmp_path / "UPC_CH_5.pdf",
        chapter_tables,
        source_filename="UPC_CH_5.pdf",
        registry_rules=rules,
    )

    assert result == chapter_tables
