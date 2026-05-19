from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.evaluation_fixtures import (
    AUTO_FIXTURE_KIND,
    build_auto_evaluation_fixture_document,
)


def test_build_auto_evaluation_fixture_document_generates_structural_queries() -> None:
    run_id = uuid4()

    fixture = build_auto_evaluation_fixture_document(
        "auto_generated_report.pdf",
        sha256="deadbeef",
        title="Forest Health Assessment",
        chunks=[
            SimpleNamespace(
                heading="Project Overview",
                text="The report summarizes forest health assessment methods and scope.",
            ),
            SimpleNamespace(
                heading="Drainage Analysis",
                text="Drainage and erosion considerations are evaluated for site access.",
            ),
        ],
        tables=[
            SimpleNamespace(
                title="Table 1 Soil Stability Measurements",
                heading="Slope stability results",
                preview_text="Soil stability measurements by slope segment.",
                search_text="Soil stability measurements by slope segment.",
            )
        ],
        figures=[
            SimpleNamespace(
                caption="Figure 1. Project area map.",
                json_path="/tmp/figure.json",
                yaml_path="/tmp/figure.yaml",
                metadata_json={"provenance": [{"page_no": 1}]},
            )
        ],
        run_id=run_id,
    )

    assert fixture["name"] == "auto_auto_generated_report"
    assert fixture["kind"] == AUTO_FIXTURE_KIND
    assert fixture["sha256"] == "deadbeef"
    assert fixture["generated_from_run_id"] == str(run_id)
    assert fixture["thresholds"]["expected_logical_table_count"] == 1
    assert fixture["thresholds"]["expected_figure_count"] == 1
    assert fixture["thresholds"]["minimum_captioned_figure_count"] == 1
    assert fixture["thresholds"]["minimum_figures_with_provenance"] == 1
    assert fixture["thresholds"]["minimum_figures_with_artifacts"] == 1
    assert fixture["thresholds"]["expected_top_n_table_hit_queries"][0]["query"] == (
        "Soil Stability Measurements"
    )
    assert fixture["thresholds"]["expected_top_n_chunk_hit_queries"][0]["query"] == (
        "Forest Health Assessment"
    )


def test_build_auto_evaluation_fixture_document_skips_low_signal_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "Standing Framework LLC - MT filed evidence.pdf",
        title=None,
        chunks=[
            SimpleNamespace(
                heading="February 18, 2026",
                text="Mitch Wilde fulfillment@zenbusiness.com",
            ),
            SimpleNamespace(
                heading=None,
                text="I, CHRISTI JACOBSEN, Secretary of State for the State of Montana.",
            ),
        ],
        tables=[],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert chunk_queries[0]["query"] == "Standing Framework LLC - MT filed evidence"
    assert chunk_queries[1]["query"] == "Standing Framework LLC"
    assert chunk_queries[2]["query"] == "MT filed evidence"
    assert all("@" not in entry["query"] for entry in chunk_queries)
    assert "February 18, 2026" not in {entry["query"] for entry in chunk_queries}
    assert not any("CHRISTI JACOBSEN" in entry["query"] for entry in chunk_queries)


def test_build_auto_evaluation_fixture_document_strips_date_prefix_from_filename() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "20251217_TK_SoilReport.pdf",
        title=None,
        chunks=[
            SimpleNamespace(
                heading=None,
                text="Prepared by:",
            )
        ],
        tables=[],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert chunk_queries[0]["query"] == "TK SoilReport"


def test_auto_fixture_skips_ambiguous_chunk_queries_when_tables_exist() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "TaylorParkRTC_Scoping.pdf",
        title="Table of Contents",
        chunks=[
            SimpleNamespace(
                heading=None,
                text="Table of Contents",
            ),
            SimpleNamespace(
                heading=None,
                text="Taylor Park Vegetation Management: Response to Scoping Comments",
            ),
        ],
        tables=[
            SimpleNamespace(
                title="Table of Contents Individuals",
                heading=None,
                preview_text="Air Quality | 3",
                search_text="Air Quality | 3",
            ),
            SimpleNamespace(
                title="Taylor Park Vegetation Management: Response to Scoping Comments",
                heading=None,
                preview_text="Comment Category | Comment | Remarks",
                search_text="Comment Category | Comment | Remarks",
            ),
        ],
        figures=[],
    )

    assert "expected_top_n_chunk_hit_queries" not in fixture["thresholds"]


def test_build_auto_evaluation_fixture_document_skips_cover_boilerplate_when_tables_exist() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "GMUG SUHFER EA_Tech Report_Climate Change_March 2026.pdf",
        title=(
            "Climate Change Technical Report for the South Uncompahgre Hazardous "
            "Fuels and Ecological Resiliency Project Environmental Assessment"
        ),
        chunks=[
            SimpleNamespace(
                heading=None,
                text=(
                    "Climate Change Technical Report for the South Uncompahgre "
                    "Hazardous Fuels and Ecological Resiliency Project Environmental "
                    "Assessment"
                ),
            ),
            SimpleNamespace(heading=None, text="Draft For Publication - March 2026"),
            SimpleNamespace(heading=None, text="Prepared for:"),
            SimpleNamespace(
                heading=None,
                text=(
                    "USDA Forest Service Grand Mesa, Uncompahgre and Gunnison "
                    "National Forests Norwood Ranger District"
                ),
            ),
            SimpleNamespace(heading=None, text="Prepared by:"),
            SimpleNamespace(heading=None, text="SE Group PO Box 2729 Frisco, CO 80443"),
            SimpleNamespace(heading=None, text="Table of Contents"),
            SimpleNamespace(heading=None, text="List of Figures and Exhibits"),
        ],
        tables=[
            SimpleNamespace(
                title="4.3.3 Cumulative Effects",
                heading=None,
                preview_text="Cumulative effects by resource.",
                search_text="Cumulative effects by resource.",
            )
        ],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert [entry["query"] for entry in chunk_queries] == [
        "Climate Change Technical Report for the South Uncompahgre"
    ]


def test_auto_fixture_uses_cover_title_when_metadata_title_is_heading() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "GMUG SUHFER EA_Biological Assessment_March 2026.pdf",
        title="1.0 Introduction",
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="SOUTH UNCOMPAHGRE HAZARDOUS FUELS AND ECOLOGICAL RESILIENCY PROJECT",
            ),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Biological Assessment",
            ),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Prepared by: Prepared For:",
            ),
            SimpleNamespace(
                heading="2.0 Purpose and Need",
                page_from=5,
                text="The purpose and need for the SUHFER project is to increase resilience.",
            ),
            SimpleNamespace(
                heading="3.0 Current Management Direction",
                page_from=6,
                text="Current management direction for the project area is summarized here.",
            ),
            SimpleNamespace(
                heading="4.1 Alternative 1 - No Action Alternative",
                page_from=7,
                text="The No Action Alternative provides a baseline for comparison.",
            ),
        ],
        tables=[
            SimpleNamespace(
                title="Table 1. Management Areas within the SUHFER project boundary.",
                heading=None,
                preview_text="Management areas across the project boundary.",
                search_text="Management areas across the project boundary.",
            )
        ],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert [entry["query"] for entry in chunk_queries] == [
        "SOUTH UNCOMPAHGRE HAZARDOUS FUELS AND ECOLOGICAL RESILIENCY PROJECT"
    ]


def test_build_auto_evaluation_fixture_document_skips_alternative_headings_when_tables_exist() -> (
    None
):
    fixture = build_auto_evaluation_fixture_document(
        "GMUG SUHFER EA_Biological Assessment_March 2026.pdf",
        title="1.0 Introduction",
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="SOUTH UNCOMPAHGRE HAZARDOUS FUELS AND ECOLOGICAL RESILIENCY PROJECT",
            ),
            SimpleNamespace(
                heading="2.0 Purpose and Need",
                page_from=5,
                text="The purpose and need for the SUHFER project is to increase resilience.",
            ),
            SimpleNamespace(
                heading="4.1 Alternative 1 - No Action Alternative",
                page_from=7,
                text="The No Action Alternative provides a baseline for comparison.",
            ),
            SimpleNamespace(
                heading="4.2 Alternative 2 - Proposed Action Alternative",
                page_from=7,
                text="The Proposed Action Alternative addresses the project's purpose and need.",
            ),
        ],
        tables=[
            SimpleNamespace(
                title="Table 1. Management Areas within the SUHFER project boundary.",
                heading=None,
                preview_text="Management areas across the project boundary.",
                search_text="Management areas across the project boundary.",
            )
        ],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert [entry["query"] for entry in chunk_queries] == [
        "SOUTH UNCOMPAHGRE HAZARDOUS FUELS AND ECOLOGICAL RESILIENCY PROJECT"
    ]


def test_auto_fixture_skips_forwarded_headers_and_project_report_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "Losensky1993HistoricalVegetationR1ByClimaticSection.pdf",
        title=None,
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text=(
                    ">>Message from Barry Bollenbacher:R01A; to b.bollenbacher; "
                    "autoforwarded on >>10/22/98 at 15:40:20."
                ),
            ),
            SimpleNamespace(heading=None, page_from=1, text="CEO document contents:"),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Project Report: NRGG_PR_BITLO_VMAP2016",
            ),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="HISTORICAL VEGETATION IN REGION ONE BY CLIMATIC SECTION",
            ),
        ],
        tables=[
            SimpleNamespace(
                title="Forest Types by Climatic Section",
                heading=None,
                preview_text="Section | Forest type | Acres",
                search_text="Forest Types by Climatic Section\nSection | Forest type | Acres",
            )
        ],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert [entry["query"] for entry in chunk_queries] == [
        "HISTORICAL VEGETATION IN REGION ONE BY CLIMATIC SECTION"
    ]


def test_build_auto_evaluation_fixture_document_skips_chunk_queries_for_figure_only_docs() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "J13-4_20250416_TK_BeeTeeGeeCulturalSurveyMap.pdf",
        title="Untitled document",
        chunks=[],
        tables=[],
        figures=[
            SimpleNamespace(
                caption=None,
                json_path="/tmp/figure.json",
                yaml_path="/tmp/figure.yaml",
                metadata_json={"provenance": [{"page_no": 1}]},
            )
        ],
    )

    assert "expected_top_n_chunk_hit_queries" not in fixture["thresholds"]


def test_build_auto_evaluation_fixture_document_skips_chunk_queries_for_zero_content_docs() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "J3-10_12032025_TK_FieldData_BKWhitetaleSaddle.pdf",
        title="Untitled document",
        chunks=[],
        tables=[],
        figures=[],
    )

    assert "expected_top_n_chunk_hit_queries" not in fixture["thresholds"]


def test_build_auto_evaluation_fixture_document_skips_duplicate_word_table_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "J14-07_20241213_TK_HeadwatersDemographics.pdf",
        title="A Demographic Profile",
        chunks=[
            SimpleNamespace(
                heading=None,
                text="A Demographic Profile",
            )
        ],
        tables=[
            SimpleNamespace(
                title="Population",
                heading=None,
                preview_text="Population " + ("." * 96) + " | 4",
                search_text="Population Population " + ("." * 96) + " | 4",
            ),
            SimpleNamespace(
                title="Age and Gender",
                heading=None,
                preview_text="Population (2022*) | 3,368 | 118,541 | 6,998",
                search_text="Age and Gender Population (2022*) | 3,368 | 118,541 | 6,998",
            ),
        ],
        figures=[],
    )

    table_queries = fixture["thresholds"]["expected_top_n_table_hit_queries"]
    assert [entry["query"] for entry in table_queries] == ["Age and Gender"]
