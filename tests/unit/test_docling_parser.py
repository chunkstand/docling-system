from __future__ import annotations

from types import SimpleNamespace

from app.services.docling_parser import (
    DoclingParser,
    ParsedTable,
    ParsedTableSegment,
    TableSupplementRule,
    _apply_registered_table_supplements,
    _apply_table_family_overlays,
    _build_logical_tables,
    _group_tables_by_upc_510_family,
    _load_table_supplement_registry,
    _meaningful_table_segments,
    _normalize_chunks,
    _snapshot_items,
)


class FakeDocument:
    def __init__(self) -> None:
        self.name = "sample"

    def iterate_items(self):
        yield (
            SimpleNamespace(
                text="701.1 Applicability",
                level=1,
                label="section_header",
                prov=[SimpleNamespace(page_no=1)],
            ),
            0,
        )
        yield (
            SimpleNamespace(
                text="First paragraph", label="text", prov=[SimpleNamespace(page_no=1)]
            ),
            1,
        )
        yield (
            SimpleNamespace(
                label="picture", self_ref="#/pictures/0", prov=[SimpleNamespace(page_no=1)]
            ),
            1,
        )
        yield (
            SimpleNamespace(
                text="UpCodes Diagram (1)", label="text", prov=[SimpleNamespace(page_no=1)]
            ),
            1,
        )
        yield (
            SimpleNamespace(
                text="Island Fixture Venting (UPC)", label="text", prov=[SimpleNamespace(page_no=1)]
            ),
            1,
        )
        yield (
            SimpleNamespace(text="TABLE 701.2", label="caption", prov=[SimpleNamespace(page_no=2)]),
            1,
        )
        yield (
            SimpleNamespace(
                text="MATERIALS FOR DRAIN, WASTE, VENT PIPE AND FITTINGS",
                level=1,
                label="section_header",
                prov=[SimpleNamespace(page_no=2)],
            ),
            1,
        )
        yield (SimpleNamespace(label="table", prov=[SimpleNamespace(page_no=2)]), 1)
        yield (SimpleNamespace(label="table", prov=[SimpleNamespace(page_no=3)]), 1)
        yield (
            SimpleNamespace(
                text="701.3 Drainage Fittings",
                level=1,
                label="section_header",
                prov=[SimpleNamespace(page_no=4)],
            ),
            0,
        )
        yield (
            SimpleNamespace(
                text="Second paragraph", label="text", prov=[SimpleNamespace(page_no=4)]
            ),
            1,
        )
        yield (
            SimpleNamespace(
                label="picture", self_ref="#/pictures/1", prov=[SimpleNamespace(page_no=4)]
            ),
            1,
        )

    def export_to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": "docling",
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "text": "Fixture Venting Diagram",
                }
            ],
            "pictures": [
                {
                    "self_ref": "#/pictures/0",
                    "label": "picture",
                    "captions": [],
                    "references": [],
                    "footnotes": [],
                    "annotations": [],
                    "prov": [
                        {
                            "page_no": 1,
                            "bbox": {
                                "l": 10,
                                "t": 20,
                                "r": 30,
                                "b": 40,
                                "coord_origin": "BOTTOMLEFT",
                            },
                            "charspan": [0, 0],
                        }
                    ],
                },
                {
                    "self_ref": "#/pictures/1",
                    "label": "picture",
                    "captions": ["#/texts/0"],
                    "references": [],
                    "footnotes": [],
                    "annotations": [],
                    "prov": [
                        {
                            "page_no": 4,
                            "bbox": {
                                "l": 11,
                                "t": 21,
                                "r": 31,
                                "b": 41,
                                "coord_origin": "BOTTOMLEFT",
                            },
                            "charspan": [0, 0],
                        }
                    ],
                },
            ],
            "tables": [
                {
                    "self_ref": "#/tables/0",
                    "data": {
                        "num_rows": 2,
                        "num_cols": 2,
                        "grid": [
                            [{"text": "Fixture"}, {"text": "DFU"}],
                            [{"text": "Sink"}, {"text": "2"}],
                        ],
                    },
                },
                {
                    "self_ref": "#/tables/1",
                    "data": {
                        "num_rows": 2,
                        "num_cols": 2,
                        "grid": [
                            [{"text": "Fixture"}, {"text": "DFU"}],
                            [{"text": "Lavatory"}, {"text": "1"}],
                        ],
                    },
                },
            ],
        }

    def num_pages(self) -> int:
        return 4


class FakeConverter:
    def convert(self, source_path):
        return SimpleNamespace(document=FakeDocument())


class FakeTitlelessDocument:
    def __init__(self) -> None:
        self.name = "12345678-1234-1234-1234-1234567890ab"

    def iterate_items(self):
        yield (
            SimpleNamespace(
                text="The Bitter Lesson",
                label="text",
                prov=[SimpleNamespace(page_no=1)],
            ),
            0,
        )
        yield (
            SimpleNamespace(
                text="Rich Sutton",
                label="text",
                prov=[SimpleNamespace(page_no=1)],
            ),
            1,
        )
        yield (
            SimpleNamespace(
                text="General methods that leverage computation are ultimately the most effective.",
                label="text",
                prov=[SimpleNamespace(page_no=1)],
            ),
            2,
        )

    def export_to_dict(self) -> dict:
        return {"name": self.name, "kind": "docling", "texts": [], "pictures": [], "tables": []}

    def num_pages(self) -> int:
        return 1


class FakeTitlelessConverter:
    def convert(self, source_path):
        return SimpleNamespace(document=FakeTitlelessDocument())


def test_normalize_chunks_keeps_structural_heading_not_table_heading() -> None:
    snapshots = _snapshot_items(FakeDocument())
    chunks = _normalize_chunks(snapshots)

    assert len(chunks) == 6
    assert chunks[0].heading == "701.1 Applicability"
    assert chunks[1].heading == "701.1 Applicability"
    assert chunks[-1].heading == "701.3 Drainage Fittings"


def test_docling_parser_returns_serialized_document_and_merged_table() -> None:
    parser = DoclingParser(converter=FakeConverter())

    parsed = parser.parse_pdf(source_path=None)  # type: ignore[arg-type]

    assert parsed.title == "701.1 Applicability"
    assert parsed.page_count == 4
    assert parsed.yaml_text.startswith("name: sample")
    assert "kind: docling" in parsed.yaml_text
    assert '"name": "sample"' in parsed.docling_json
    assert len(parsed.chunks) == 6
    assert len(parsed.tables) == 1
    assert len(parsed.figures) == 2
    assert (
        parsed.tables[0].title == "TABLE 701.2 MATERIALS FOR DRAIN, WASTE, VENT PIPE AND FITTINGS"
    )
    assert parsed.tables[0].row_count == 3
    assert parsed.tables[0].metadata["header_rows_removed_count"] == 1
    assert "Lavatory" in parsed.tables[0].search_text
    assert parsed.figures[0].caption == "UpCodes Diagram (1) Island Fixture Venting (UPC)"
    assert parsed.figures[0].metadata["caption_resolution_source"] == "nearby_group_label"
    assert parsed.figures[0].metadata["provenance"][0]["bbox"]["coord_origin"] == "BOTTOMLEFT"
    assert parsed.figures[1].caption == "Fixture Venting Diagram"
    assert parsed.figures[1].metadata["caption_resolution_source"] == "explicit_ref"


def test_docling_parser_uses_first_meaningful_text_for_title_when_headings_are_absent() -> None:
    parser = DoclingParser(converter=FakeTitlelessConverter())

    parsed = parser.parse_pdf(source_path=None)  # type: ignore[arg-type]

    assert parsed.title == "The Bitter Lesson"


def test_build_logical_tables_merges_same_title_adjacent_segments_with_shape_drift() -> None:
    first = ParsedTableSegment(
        segment_index=0,
        segment_order=10,
        source_table_ref="#/tables/0",
        title="TABLE 313.3 HANGERS AND SUPPORTS",
        heading="313.2 Material",
        page_from=35,
        page_to=35,
        row_count=2,
        col_count=4,
        rows=[
            ["Material", "Type", "Horizontal", "Vertical"],
            ["Cast Iron", "Lead", "5 feet", "Base and each floor"],
        ],
        metadata={"title_source": "caption", "header_rows_removed": 0, "header_rows_retained": 3},
    )
    second = ParsedTableSegment(
        segment_index=1,
        segment_order=11,
        source_table_ref="#/tables/1",
        title="TABLE 313.3 HANGERS AND SUPPORTS",
        heading="313.2 Material",
        page_from=36,
        page_to=36,
        row_count=2,
        col_count=5,
        rows=[
            ["Material", "Type", "Horizontal", "Vertical", "Support"],
            ["PEX", "Compression", "4 feet", "4 feet", "Base and each floor"],
        ],
        metadata={"title_source": "caption", "header_rows_removed": 0, "header_rows_retained": 3},
    )

    tables = _build_logical_tables([first, second])

    assert len(tables) == 1
    assert tables[0].page_from == 35
    assert tables[0].page_to == 36
    assert tables[0].metadata["is_merged"] is True
    assert tables[0].metadata["merge_reason"] == "adjacent_same_title_heading_continuation"
    assert tables[0].metadata["merge_confidence"] == 0.8


def test_meaningful_table_segments_drops_empty_spacer_and_allows_continuation_merge() -> None:
    first = ParsedTableSegment(
        segment_index=0,
        segment_order=10,
        source_table_ref="#/tables/0",
        title="TABLE 510.1.2(2) TYPE B DOUBLE-WALL GAS VENT [NFPA 54: TABLE 13.1(b)]*",
        heading="510.1.2 Elbows",
        page_from=109,
        page_to=109,
        row_count=2,
        col_count=3,
        rows=[
            ["Vent Height", "Fan", "Nat"],
            ["6", "2838", "1660"],
        ],
        metadata={"title_source": "caption", "header_rows_removed": 0, "header_rows_retained": 3},
    )
    spacer = ParsedTableSegment(
        segment_index=1,
        segment_order=11,
        source_table_ref="#/tables/1",
        title="TABLE 510.1.2(2) TYPE B DOUBLE-WALL GAS VENT [NFPA 54: TABLE 13.1(b)]* NUMBER OF",
        heading="510.1.2 Elbows",
        page_from=110,
        page_to=110,
        row_count=0,
        col_count=0,
        rows=[],
        metadata={
            "title_source": "caption+title_hint",
            "header_rows_removed": 0,
            "header_rows_retained": 0,
        },
    )
    second = ParsedTableSegment(
        segment_index=2,
        segment_order=12,
        source_table_ref="#/tables/2",
        title=None,
        heading="510.1.2 Elbows",
        page_from=111,
        page_to=111,
        row_count=2,
        col_count=4,
        rows=[
            ["20", "0", "35", "96"],
            ["2", "37", "74", "50"],
        ],
        metadata={"title_source": "inferred", "header_rows_removed": 0, "header_rows_retained": 3},
    )

    segments = _meaningful_table_segments([first, spacer, second])
    tables = _build_logical_tables(segments)

    assert [segment.segment_index for segment in segments] == [0, 2]
    assert len(tables) == 1
    assert tables[0].title == first.title
    assert tables[0].page_from == 109
    assert tables[0].page_to == 111
    assert tables[0].metadata["is_merged"] is True


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
        supplement_filename="510.1.2.pdf",
    )

    assert len(result) == 2
    assert result[0].metadata["overlay_applied"] is True
    assert result[0].metadata["overlay_original_table_indices"] == [0]
    assert result[1].title == chapter_tables[1].title
    assert result[1].metadata.get("overlay_applied") is None


def test_group_tables_by_upc_510_family_keeps_titled_continued_fragment() -> None:
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

    grouped = _group_tables_by_upc_510_family(tables)

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
    matcher: upc_510_family
    overlay_type: clean_pdf_family_replacement
    description: Example rule
""".strip()
    )

    rules = _load_table_supplement_registry(str(registry_path))

    assert len(rules) == 1
    assert rules[0].document_filenames == ("UPC_CH_5.pdf", "UPC_CH_6.pdf")
    assert rules[0].supplement_filename == "510.1.2.pdf"
    assert rules[0].matcher == "upc_510_family"
    assert rules[0].overlay_type == "clean_pdf_family_replacement"
    assert rules[0].description == "Example rule"


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
            matcher="upc_510_family",
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
            matcher="upc_510_family",
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
