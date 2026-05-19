from __future__ import annotations

from types import SimpleNamespace

from app.services.evaluation_fixtures import build_auto_evaluation_fixture_document


def test_build_auto_evaluation_fixture_document_builds_specific_table_queries_from_pipe_cells() -> (
    None
):
    fixture = build_auto_evaluation_fixture_document(
        "K-003-55_12022025_TK_Kosterman, M. 2018..pdf",
        title="Canada lynx habitat relationships",
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Canada lynx habitat relationships",
            )
        ],
        tables=[
            SimpleNamespace(
                title=None,
                heading=None,
                preview_text=(
                    "Forest structure class. | Stand description | Relationship to snowshoe hares"
                ),
                search_text=(
                    "Forest structure class. | Stand description | Relationship to snowshoe hares"
                ),
            ),
            SimpleNamespace(
                title="Table 2. Survival of Young",
                heading="Chapter 3",
                preview_text=("Survival of Young | Management Considerations | Research Needs"),
                search_text=(
                    "Table 2. Survival of Young\nChapter 3\n"
                    "Survival of Young | Management Considerations | Research Needs"
                ),
            ),
        ],
        figures=[],
    )

    table_queries = fixture["thresholds"]["expected_top_n_table_hit_queries"]
    assert [entry["query"] for entry in table_queries] == [
        "Forest structure class Stand description",
        "Survival of Young Management Considerations",
    ]


def test_build_auto_evaluation_fixture_document_skips_generic_project_title_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "J6-01_20251016_TK_HydrologyReport_updated.pdf",
        title="Tylers Kitchen Project",
        chunks=[
            SimpleNamespace(heading=None, page_from=1, text="Tylers Kitchen Project"),
            SimpleNamespace(heading=None, page_from=1, text="Hydrology Resource Report"),
            SimpleNamespace(heading=None, page_from=1, text="Prepared by:"),
        ],
        tables=[
            SimpleNamespace(
                title="Table 2. Road density classification",
                heading=None,
                preview_text="Road Density | High | Moderate",
                search_text="Table 2. Road density classification\nRoad Density | High | Moderate",
            )
        ],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert [entry["query"] for entry in chunk_queries] == ["Hydrology Resource Report"]


def test_build_auto_evaluation_fixture_document_skips_field_label_chunk_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "J2-02_12032025_TK_UnitStandExams.pdf",
        title="STAND DIAGNOSIS MATRIX",
        chunks=[
            SimpleNamespace(heading=None, page_from=1, text='Total BA >5.0";'),
            SimpleNamespace(heading=None, page_from=1, text="PROJECT:"),
        ],
        tables=[
            SimpleNamespace(
                title="Trees/snags per acre based on Basal Area",
                heading=None,
                preview_text="Trees/snags per acre based on Basal Area",
                search_text="Trees/snags per acre based on Basal Area",
            )
        ],
        figures=[],
    )

    assert "expected_top_n_chunk_hit_queries" not in fixture["thresholds"]


def test_build_auto_evaluation_fixture_document_skips_citation_header_chunk_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "BoulangerEtal2013UseMultistateModelsGriz.pdf",
        title=None,
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Wildl. Biol. 19: 274-288 (2013) DOI: 10.2981/12-088",
            ),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Citation: Boulanger J, Stenhouse GB (2014) The Impact of Roads",
            ),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Use multistate models to investigate grizzly bear dynamics",
            ),
        ],
        tables=[
            SimpleNamespace(
                title="Table 1. Mean daily movement rates",
                heading=None,
                preview_text="Movement rates by season.",
                search_text="Movement rates by season.",
            )
        ],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert [entry["query"] for entry in chunk_queries] == [
        "Use multistate models to investigate grizzly bear dynamics"
    ]


def test_build_auto_evaluation_fixture_document_skips_unit_fragment_chunk_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "DomkeEtal_2023_GreenhouseGasEmissionsRemovals.pdf",
        title="2021 Estimates at a Glance",
        chunks=[
            SimpleNamespace(heading=None, page_from=1, text="MMT Co, Eq."),
            SimpleNamespace(heading=None, page_from=1, text="25-"),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text=(
                    "Greenhouse Gas Emissions and Removals From Forest Land, "
                    "Woodlands, Urban Trees, and Harvested Wood Products in the "
                    "United States, 1990-2021"
                ),
            ),
        ],
        tables=[
            SimpleNamespace(
                title="Table 1. Emissions and removals by land category",
                heading=None,
                preview_text="Emissions and removals by land category.",
                search_text="Emissions and removals by land category.",
            )
        ],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert [entry["query"] for entry in chunk_queries] == [
        "Greenhouse Gas Emissions and Removals From Forest Land"
    ]


def test_build_auto_evaluation_fixture_document_skips_generic_chapter_table_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "BPA_Powerline_EIS.pdf",
        title="Transmission System Vegetation Management Program",
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Transmission System Vegetation Management Program",
            )
        ],
        tables=[
            SimpleNamespace(
                title="CHAPTER I PURPOSE AND NEED",
                heading=None,
                preview_text="Transmission system vegetation management program overview.",
                search_text="Transmission system vegetation management program overview.",
            ),
            SimpleNamespace(
                title="Control Methods Appropriate to the Facility",
                heading=None,
                preview_text="Control methods by facility type.",
                search_text="Control methods by facility type.",
            ),
        ],
        figures=[],
    )

    table_queries = fixture["thresholds"]["expected_top_n_table_hit_queries"]
    assert [entry["query"] for entry in table_queries] == [
        "Transmission system vegetation management program overview",
        "Control Methods Appropriate to the Facility",
    ]


def test_build_auto_evaluation_fixture_document_skips_contents_pipe_table_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "Deblander2000ForestResourcesLolo.pdf",
        title="What Forest Resources Are at Risk?",
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="What Forest Resources Are at Risk?",
            )
        ],
        tables=[
            SimpleNamespace(
                title=None,
                heading=None,
                preview_text=(
                    "Contents | __________________________________ Page What forest resources are"
                ),
                search_text=(
                    "Contents | __________________________________ Page What forest resources are"
                ),
            ),
            SimpleNamespace(
                title="Forest Resources at Risk",
                heading=None,
                preview_text="Resource | Acres | Priority",
                search_text="Forest Resources at Risk\nResource | Acres | Priority",
            ),
        ],
        figures=[],
    )

    table_queries = fixture["thresholds"]["expected_top_n_table_hit_queries"]
    assert [entry["query"] for entry in table_queries] == ["Forest Resources at Risk"]


def test_build_auto_evaluation_fixture_document_skips_cfr_and_report_title_table_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "USFWS2014FedRegYellow-billedCuckoo.pdf",
        title="Yellow-billed Cuckoo Threatened Status",
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Yellow-billed Cuckoo Threatened Status",
            )
        ],
        tables=[
            SimpleNamespace(
                title=None,
                heading="50 CFR Part 17",
                preview_text=("Species | Historic Range | Critical habitat | Special rules"),
                search_text=(
                    "50 CFR Part 17\nSpecies | Historic Range | Critical habitat | Special rules"
                ),
            ),
            SimpleNamespace(
                title=None,
                heading="2022 FORESTRY BMP FIELD REVIEW REPORT",
                preview_text=(
                    "Page\nFigure 1: Application and Effectiveness of High Risk BMPs 1990-2022 | 19"
                ),
                search_text=(
                    "2022 FORESTRY BMP FIELD REVIEW REPORT\nPage\nFigure 1: "
                    "Application and Effectiveness of High Risk BMPs 1990-2022 | 19"
                ),
            ),
        ],
        figures=[],
    )

    table_queries = fixture["thresholds"]["expected_top_n_table_hit_queries"]
    assert [entry["query"] for entry in table_queries] == [
        "Historic Range Critical habitat",
    ]


def test_build_auto_evaluation_fixture_document_skips_stat_header_table_queries() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "Stagliano2023WesternPearlshellMusselPopulationsLolo.pdf",
        title="Western Pearlshell Mussel Populations",
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Western Pearlshell Mussel Populations",
            )
        ],
        tables=[
            SimpleNamespace(
                title="Table 2.",
                heading="2022 Howard Creek",
                preview_text=("WEPE Occupancy Pre- 2010 | 2022 # revisited | Δ Trend p-value"),
                search_text=(
                    "Table 2.\n2022 Howard Creek\nWEPE Occupancy Pre- 2010 | "
                    "2022 # revisited | Δ Trend p-value"
                ),
            ),
            SimpleNamespace(
                title=(
                    "Appendix A. Mussel survey population data and viability "
                    "ranks from pre-2010 and 2014."
                ),
                heading="2022 Howard Creek",
                preview_text=(
                    "4th_Code HUC | StreamName | Viability Rank pre-2010 | Viability Rank 2014"
                ),
                search_text=(
                    "Appendix A. Mussel survey population data and viability ranks "
                    "from pre-2010 and 2014.\n2022 Howard Creek\n4th_Code HUC | "
                    "StreamName | Viability Rank pre-2010 | Viability Rank 2014"
                ),
            ),
        ],
        figures=[],
    )

    table_queries = fixture["thresholds"]["expected_top_n_table_hit_queries"]
    assert [entry["query"] for entry in table_queries] == [
        "Mussel survey population data and viability ranks from",
    ]


def test_build_auto_evaluation_fixture_document_skips_author_bylines_and_pipe_rows() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "daniel_boster_1976.pdf",
        title="1971 Samples 1972 Samples",
        chunks=[
            SimpleNamespace(heading=None, page_from=1, text="Terry C. Daniel Ron S. Boster"),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text=(
                    "USDA Forest Service Research Paper RM-167 Rocky Mountain Forest "
                    "and Range Experiment Station"
                ),
            ),
            SimpleNamespace(heading=None, page_from=1, text="May 1976"),
            SimpleNamespace(
                heading=None,
                page_from=1,
                text=("Measuring Landscape Esthetics: The Scenic Beauty Estimation Method"),
            ),
        ],
        tables=[
            SimpleNamespace(
                title=None,
                heading=None,
                preview_text=("1 | LANDSCAPE EVALUATION: OVERVIEW 2 | What's in a Name?"),
                search_text=("1 | LANDSCAPE EVALUATION: OVERVIEW 2 | What's in a Name?"),
            ),
            SimpleNamespace(
                title=None,
                heading=None,
                preview_text="Observer | Observer | Observer A | B",
                search_text="Observer | Observer | Observer A | B",
            ),
            SimpleNamespace(
                title=None,
                heading="Landscape Experiments",
                preview_text="Observer A | B | C",
                search_text="Landscape Experiments Observer A | B | C",
            ),
        ],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    table_queries = fixture["thresholds"]["expected_top_n_table_hit_queries"]

    assert [entry["query"] for entry in chunk_queries] == [
        "Measuring Landscape Esthetics: The Scenic Beauty Estimation Method"
    ]
    assert [entry["query"] for entry in table_queries] == ["Landscape Experiments"]
