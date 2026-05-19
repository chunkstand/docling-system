from __future__ import annotations

from app.services.docling_parser import (
    ParsedTableSegment,
    _build_logical_tables,
    _meaningful_table_segments,
)


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


def test_build_logical_tables_does_not_flag_repeated_numeric_rows_as_headers() -> None:
    first = ParsedTableSegment(
        segment_index=0,
        segment_order=10,
        source_table_ref="#/tables/0",
        title="RESOURCE OUTPUTS WITH THE PROPOSED ACTION",
        heading="Georgia",
        page_from=200,
        page_to=200,
        row_count=3,
        col_count=4,
        rows=[
            ["", "-1.", "", "-1."],
            ["", "!I l", "", "0."],
            ["", "-1.", "", "-1."],
        ],
        metadata={
            "title_source": "title_hint",
            "header_rows_removed": 0,
            "header_rows_retained": 0,
        },
    )
    second = ParsedTableSegment(
        segment_index=1,
        segment_order=11,
        source_table_ref="#/tables/1",
        title=None,
        heading="Georgia",
        page_from=201,
        page_to=201,
        row_count=2,
        col_count=4,
        rows=[
            ["", "0.", "", "0."],
            ["", "0.", "", "-1."],
        ],
        metadata={"title_source": "inferred", "header_rows_removed": 0, "header_rows_retained": 0},
    )

    tables = _build_logical_tables([first, second])

    assert len(tables) == 1
    assert tables[0].metadata["is_merged"] is True
    assert tables[0].metadata["header_removal_passed"] is True
    assert tables[0].metadata["repeated_header_rows_removed"] is False
