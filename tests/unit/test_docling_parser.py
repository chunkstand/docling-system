from __future__ import annotations

from types import SimpleNamespace

from app.services.docling_parser import (
    DoclingParser,
    ParsedTableSegment,
    _build_logical_tables,
    _normalize_chunks,
    _snapshot_items,
)


class FakeDocument:
    def __init__(self) -> None:
        self.name = "sample"

    def iterate_items(self):
        yield (
            SimpleNamespace(text="701.1 Applicability", level=1, label="section_header", prov=[SimpleNamespace(page_no=1)]),
            0,
        )
        yield (
            SimpleNamespace(text="First paragraph", label="text", prov=[SimpleNamespace(page_no=1)]),
            1,
        )
        yield (SimpleNamespace(label="picture", self_ref="#/pictures/0", prov=[SimpleNamespace(page_no=1)]), 1)
        yield (
            SimpleNamespace(text="UpCodes Diagram (1)", label="text", prov=[SimpleNamespace(page_no=1)]),
            1,
        )
        yield (
            SimpleNamespace(text="Island Fixture Venting (UPC)", label="text", prov=[SimpleNamespace(page_no=1)]),
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
            SimpleNamespace(text="701.3 Drainage Fittings", level=1, label="section_header", prov=[SimpleNamespace(page_no=4)]),
            0,
        )
        yield (
            SimpleNamespace(text="Second paragraph", label="text", prov=[SimpleNamespace(page_no=4)]),
            1,
        )
        yield (SimpleNamespace(label="picture", self_ref="#/pictures/1", prov=[SimpleNamespace(page_no=4)]), 1)

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
                            "bbox": {"l": 10, "t": 20, "r": 30, "b": 40, "coord_origin": "BOTTOMLEFT"},
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
                            "bbox": {"l": 11, "t": 21, "r": 31, "b": 41, "coord_origin": "BOTTOMLEFT"},
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
    assert parsed.tables[0].title == "TABLE 701.2 MATERIALS FOR DRAIN, WASTE, VENT PIPE AND FITTINGS"
    assert parsed.tables[0].row_count == 3
    assert parsed.tables[0].metadata["header_rows_removed_count"] == 1
    assert "Lavatory" in parsed.tables[0].search_text
    assert parsed.figures[0].caption == "UpCodes Diagram (1) Island Fixture Venting (UPC)"
    assert parsed.figures[0].metadata["caption_resolution_source"] == "nearby_group_label"
    assert parsed.figures[0].metadata["provenance"][0]["bbox"]["coord_origin"] == "BOTTOMLEFT"
    assert parsed.figures[1].caption == "Fixture Venting Diagram"
    assert parsed.figures[1].metadata["caption_resolution_source"] == "explicit_ref"


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
