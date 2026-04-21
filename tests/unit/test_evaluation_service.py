from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import yaml

from app.schemas.chat import ChatCitation, ChatResponse
from app.schemas.search import SearchResult, SearchScores
from app.services.evaluation_execution import execute_retrieval_queries
from app.services.evaluations import (
    AUTO_FIXTURE_KIND,
    DEFAULT_CORPUS_PATH,
    EvaluationAnswerCase,
    EvaluationQueryCase,
    _evaluate_answer_case,
    _evaluate_retrieval_case,
    _summarize_retrieval_rank_metrics,
    _summarize_structural_checks,
    build_auto_evaluation_fixture_document,
    ensure_auto_evaluation_fixture,
    evaluate_run,
    fixture_for_document,
    load_evaluation_fixtures,
    resolve_baseline_run_id,
)


def test_load_evaluation_fixtures_compiles_search_queries() -> None:
    fixtures = load_evaluation_fixtures(DEFAULT_CORPUS_PATH)

    born_digital = next(fixture for fixture in fixtures if fixture.name == "born_digital_simple")
    assert born_digital.source_filename == "UPC_Appendix_N.pdf"
    assert len(born_digital.queries) >= 3
    assert born_digital.queries[0].expected_result_type == "table"
    assert born_digital.queries[0].expected_top_n >= 1

    chapter_five = next(fixture for fixture in fixtures if fixture.name == "upc_ch5")
    assert len(chapter_five.queries) >= 4
    assert len(chapter_five.thresholds.expected_merged_tables) == 1
    assert (
        chapter_five.thresholds.expected_merged_tables[0].overlay_family_key == "TABLE 510.1.2(2)"
    )

    appendix_b = next(
        fixture for fixture in fixtures if fixture.name == "appendix_b_prose_guidance"
    )
    assert appendix_b.source_filename == "UPC_Appendix_B.pdf"
    assert appendix_b.thresholds.expected_logical_table_count == 0
    assert appendix_b.thresholds.expected_figure_count == 0
    assert all(query.expected_result_type == "chunk" for query in appendix_b.queries)
    assert any(query.mode == "keyword" for query in appendix_b.queries)

    chapter_seven = next(fixture for fixture in fixtures if fixture.name == "upc_ch7")
    assert chapter_seven.thresholds.expected_figure_count == 10
    assert chapter_seven.thresholds.minimum_captioned_figure_count == 10

    awkward = next(fixture for fixture in fixtures if fixture.name == "awkward_headers")
    assert awkward.thresholds.expected_figure_count == 29
    assert awkward.thresholds.minimum_figures_with_provenance == 29

    bitter_lesson = next(fixture for fixture in fixtures if fixture.name == "bitter_lesson_prose")
    assert bitter_lesson.source_filename == "The Bitter Lesson.pdf"
    assert bitter_lesson.thresholds.expected_logical_table_count == 0
    assert bitter_lesson.thresholds.expected_figure_count == 0
    assert len(bitter_lesson.queries) == 8
    assert all(query.expected_result_type == "chunk" for query in bitter_lesson.queries)
    assert any(query.mode == "keyword" for query in bitter_lesson.queries)
    assert any(
        query.query == "What does the essay say about methods that leverage computation?"
        and query.include_document_filter is False
        for query in bitter_lesson.queries
    )
    assert any(
        query.query == "What does the essay say about search and learning?"
        and query.include_document_filter is False
        for query in bitter_lesson.queries
    )
    assert any(
        query.query == "claim bitter lesson" and query.include_document_filter is False
        for query in bitter_lesson.queries
    )
    assert len(bitter_lesson.answer_queries) == 1
    assert bitter_lesson.answer_queries[0].expected_answer_contains == [
        "general methods",
        "computation",
    ]
    assert bitter_lesson.queries[-1].expected_source_filename == "The Bitter Lesson.pdf"
    assert bitter_lesson.queries[-1].expected_top_result_source_filename == "The Bitter Lesson.pdf"
    assert bitter_lesson.queries[-1].minimum_top_n_hits_from_expected_document == 2
    assert bitter_lesson.queries[-1].maximum_foreign_results_before_first_expected_hit == 0
    assert (
        bitter_lesson.answer_queries[0].expected_citation_source_filename == "The Bitter Lesson.pdf"
    )
    assert bitter_lesson.answer_queries[0].maximum_foreign_citations == 0

    test_pdf = next(fixture for fixture in fixtures if fixture.name == "test_pdf_prose")
    assert test_pdf.source_filename == "TEST_PDF.pdf"
    assert len(test_pdf.queries) == 7
    opportunity_due_date = next(
        query for query in test_pdf.queries if query.query == "What is the opportunity due date?"
    )
    assert opportunity_due_date.expected_source_filename == "TEST_PDF.pdf"
    assert opportunity_due_date.expected_top_result_source_filename == "TEST_PDF.pdf"
    assert opportunity_due_date.minimum_top_n_hits_from_expected_document == 2
    assert opportunity_due_date.maximum_foreign_results_before_first_expected_hit == 0
    assert opportunity_due_date.include_document_filter is False
    opportunity_due = next(
        query for query in test_pdf.queries if query.query == "When is the opportunity due?"
    )
    assert opportunity_due.expected_source_filename == "TEST_PDF.pdf"
    assert opportunity_due.expected_top_result_source_filename == "TEST_PDF.pdf"
    assert opportunity_due.minimum_top_n_hits_from_expected_document == 2
    assert opportunity_due.maximum_foreign_results_before_first_expected_hit == 0
    assert opportunity_due.include_document_filter is False
    assert len(test_pdf.answer_queries) == 2
    assert test_pdf.answer_queries[0].minimum_citation_count == 1
    assert test_pdf.answer_queries[0].expected_citation_source_filename == "TEST_PDF.pdf"
    assert test_pdf.answer_queries[0].maximum_foreign_citations == 0
    assert test_pdf.answer_queries[1].expect_no_answer is True
    assert test_pdf.answer_queries[1].maximum_citation_count == 0

    nsf = next(fixture for fixture in fixtures if fixture.name == "nsf_ai_ready_america_figures")
    assert nsf.thresholds.expected_figure_count == 6
    assert len(nsf.answer_queries) == 1

    spend_report = next(
        fixture for fixture in fixtures if fixture.name == "openrouter_spend_report_tables"
    )
    assert spend_report.thresholds.expected_logical_table_count == 3
    assert len(spend_report.answer_queries) == 1

    soil_report = next(
        fixture for fixture in fixtures if fixture.name == "tyler_kitchen_soil_report"
    )
    assert soil_report.source_filename == "20251217_TK_SoilReport.pdf"
    assert soil_report.thresholds.expected_logical_table_count == 12
    assert soil_report.thresholds.expected_figure_count == 2
    assert len(soil_report.answer_queries) == 1
    assert any(query.mode == "keyword" for query in soil_report.queries)

    transportation_report = next(
        fixture for fixture in fixtures if fixture.name == "tyler_kitchen_transportation_report"
    )
    assert transportation_report.source_filename == "20251216_TK_TransportationReport.pdf"
    assert transportation_report.thresholds.expected_logical_table_count == 8
    assert transportation_report.thresholds.expected_figure_count == 0
    assert len(transportation_report.queries) == 4
    assert len(transportation_report.answer_queries) == 1
    assert (
        transportation_report.queries[-1].expected_source_filename
        == "20251216_TK_TransportationReport.pdf"
    )
    assert transportation_report.queries[-1].expected_result_type == "table"
    assert (
        transportation_report.queries[-1].expected_top_result_source_filename
        == "20251216_TK_TransportationReport.pdf"
    )
    assert transportation_report.answer_queries[0].expected_citation_source_filename == (
        "20251216_TK_TransportationReport.pdf"
    )
    assert transportation_report.answer_queries[0].expected_result_type == "table"
    assert transportation_report.answer_queries[0].maximum_foreign_citations == 0

    wildlife_report = next(
        fixture for fixture in fixtures if fixture.name == "tyler_kitchen_wildlife_report"
    )
    assert wildlife_report.source_filename == "20251215_TK_WildlifeSpecReport.pdf"
    assert wildlife_report.thresholds.expected_logical_table_count == 18
    assert wildlife_report.thresholds.expected_figure_count == 2
    assert len(wildlife_report.queries) == 5
    assert len(wildlife_report.answer_queries) == 1
    assert (
        wildlife_report.queries[-1].expected_source_filename == "20251215_TK_WildlifeSpecReport.pdf"
    )
    assert wildlife_report.queries[-1].expected_result_type == "table"
    assert (
        wildlife_report.queries[-1].expected_top_result_source_filename
        == "20251215_TK_WildlifeSpecReport.pdf"
    )
    assert wildlife_report.queries[-1].minimum_top_n_hits_from_expected_document == 1
    assert wildlife_report.queries[-1].maximum_foreign_results_before_first_expected_hit == 0
    assert (
        wildlife_report.answer_queries[0].expected_citation_source_filename
        == "20251215_TK_WildlifeSpecReport.pdf"
    )
    assert wildlife_report.answer_queries[0].maximum_foreign_citations == 0
    assert wildlife_report.thresholds.expected_figure_captions_present == [
        "Tyler's Kitchen Fuels Reduction and Forest Health Project",
        (
            "Figure 1. Modeled fisher habitat in the Northern Rocky Mountains, "
            "from USFWS status assessment (2017)."
        ),
    ]


def test_fixture_for_document_matches_auto_fixture_by_source_filename(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    (storage_root / "evaluation_corpus.auto.yaml").write_text(
        """
documents:
  - name: auto_duplicate
    kind: auto_generated_document
    source_filename: duplicate.pdf
    thresholds: {}
"""
    )
    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    fixture = fixture_for_document(SimpleNamespace(source_filename="duplicate.pdf"))

    assert fixture is not None
    assert fixture.name == "auto_duplicate"


def test_fixture_for_document_does_not_match_manual_fixture_by_source_filename_by_default() -> None:
    document = SimpleNamespace(source_filename="UPC_Appendix_N.pdf")

    fixture = fixture_for_document(document)

    assert fixture is None


def test_fixture_for_document_can_opt_into_manual_filename_fallback() -> None:
    document = SimpleNamespace(source_filename="UPC_Appendix_N.pdf")

    fixture = fixture_for_document(
        document,
        corpus_path=DEFAULT_CORPUS_PATH,
        allow_manual_filename_fallback=True,
    )

    assert fixture is not None
    assert fixture.name == "born_digital_simple"


def test_fixture_for_document_matches_by_sha256_when_source_filename_collides(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    corpus_path = tmp_path / "evaluation_corpus.yaml"
    corpus_path.write_text(
        """
documents:
  - name: first_collision
    kind: prose
    source_filename: duplicate.pdf
    sha256: aaa111
    thresholds: {}
  - name: second_collision
    kind: prose
    source_filename: duplicate.pdf
    sha256: bbb222
    thresholds: {}
"""
    )
    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    fixture = fixture_for_document(
        SimpleNamespace(source_filename="duplicate.pdf", sha256="bbb222"),
        corpus_path=corpus_path,
    )

    assert fixture is not None
    assert fixture.name == "second_collision"
    assert fixture.document_sha256 == "bbb222"


def test_fixture_for_document_returns_none_for_ambiguous_source_filename_without_sha256(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    corpus_path = tmp_path / "evaluation_corpus.yaml"
    corpus_path.write_text(
        """
documents:
  - name: first_collision
    kind: prose
    source_filename: duplicate.pdf
    thresholds: {}
  - name: second_collision
    kind: prose
    source_filename: duplicate.pdf
    thresholds: {}
"""
    )
    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    fixture = fixture_for_document(
        SimpleNamespace(source_filename="duplicate.pdf"),
        corpus_path=corpus_path,
    )

    assert fixture is None


def test_load_evaluation_fixtures_uses_configured_manual_corpus_path(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    corpus_path = tmp_path / "configured_manual.yaml"
    corpus_path.write_text(
        """
documents:
  - name: configured_manual
    kind: prose
    source_filename: configured.pdf
    thresholds: {}
"""
    )
    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            manual_evaluation_corpus_path=corpus_path,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    fixtures = load_evaluation_fixtures()

    assert [fixture.name for fixture in fixtures] == ["configured_manual"]


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


def test_build_auto_evaluation_fixture_document_skips_numeric_table_text_fallbacks() -> None:
    fixture = build_auto_evaluation_fixture_document(
        "numeric_table_fallbacks.pdf",
        title="Landscape Study",
        chunks=[
            SimpleNamespace(
                heading=None,
                page_from=1,
                text="Landscape Study",
            )
        ],
        tables=[
            SimpleNamespace(
                title=None,
                heading=None,
                preview_text="1971 Experiments No. Observers | No. Slides",
                search_text="1971 Experiments No. Observers | No. Slides",
            ),
            SimpleNamespace(
                title="Reliability Analysis",
                heading=None,
                preview_text="Observer A | B | C",
                search_text="Reliability Analysis Observer A | B | C",
            ),
        ],
        figures=[],
    )

    table_queries = fixture["thresholds"]["expected_top_n_table_hit_queries"]
    assert [entry["query"] for entry in table_queries] == ["Reliability Analysis"]


def test_ensure_auto_evaluation_fixture_writes_auto_corpus_entry(monkeypatch, tmp_path) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    tables = [
        SimpleNamespace(
            title="Table 3 Transportation Mitigations",
            heading="Transportation mitigations",
            preview_text="Transportation mitigations by route segment.",
            search_text="Transportation mitigations by route segment.",
        )
    ]
    figures = [
        SimpleNamespace(
            caption="Figure 1. Proposed access route.",
            json_path="/tmp/figure.json",
            yaml_path="/tmp/figure.yaml",
            metadata_json={"provenance": [{"page_no": 2}]},
        )
    ]
    chunks = [
        SimpleNamespace(
            heading="Executive Summary",
            text="Transportation mitigation measures are required for the proposed route.",
        )
    ]

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeSession:
        def __init__(self):
            self._results = [tables, figures, chunks]
            self.calls = 0

        def execute(self, _query):
            rows = self._results[self.calls]
            self.calls += 1
            return FakeResult(rows)

    monkeypatch.setattr("app.services.evaluations.search_documents", lambda *args, **kwargs: [])

    fixture = ensure_auto_evaluation_fixture(
        FakeSession(),
        SimpleNamespace(
            id=uuid4(),
            source_filename="autogen_doc.pdf",
            sha256="abc123",
            title="Autogen Document",
        ),
        SimpleNamespace(id=uuid4()),
    )

    auto_corpus_path = storage_root / "evaluation_corpus.auto.yaml"
    assert auto_corpus_path.exists() is True
    assert fixture["source_filename"] == "autogen_doc.pdf"
    assert fixture["sha256"] == "abc123"
    assert fixture["thresholds"]["expected_logical_table_count"] == 1
    loaded = fixture_for_document(
        SimpleNamespace(source_filename="autogen_doc.pdf", sha256="abc123")
    )
    assert loaded is not None
    assert loaded.name == fixture["name"]


def test_ensure_auto_evaluation_fixture_keeps_only_retrieval_backed_queries(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    tables = [
        SimpleNamespace(
            title="Table 3 Transportation Mitigations",
            heading="Transportation mitigations",
            preview_text="Transportation mitigations by route segment.",
            search_text="Transportation mitigations by route segment.",
        )
    ]
    figures: list[object] = []
    chunks = [
        SimpleNamespace(
            heading="Executive Summary",
            text="Transportation mitigation measures are required for the proposed route.",
        )
    ]

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeSession:
        def __init__(self):
            self._results = [tables, figures, chunks]
            self.calls = 0

        def execute(self, _query):
            rows = self._results[self.calls]
            self.calls += 1
            return FakeResult(rows)

    def fake_search_documents(_session, request, *_args, **_kwargs):
        if request.query in {
            "Table 3 Transportation Mitigations",
            "Transportation Mitigations",
        }:
            return [
                SearchResult(
                    result_type="table",
                    document_id=uuid4(),
                    run_id=uuid4(),
                    score=0.9,
                    table_id=uuid4(),
                    table_title="Table 3 Transportation Mitigations",
                    table_heading="Transportation mitigations",
                    table_preview="Transportation mitigations by route segment.",
                    row_count=3,
                    col_count=2,
                    page_from=1,
                    page_to=1,
                    source_filename="autogen_doc.pdf",
                    scores=SearchScores(keyword_score=0.9, hybrid_score=0.9),
                )
            ]
        return [
            SearchResult(
                result_type="table",
                document_id=uuid4(),
                run_id=uuid4(),
                score=0.5,
                table_id=uuid4(),
                table_title="Table 3 Transportation Mitigations",
                table_heading="Transportation mitigations",
                table_preview="Transportation mitigations by route segment.",
                row_count=3,
                col_count=2,
                page_from=1,
                page_to=1,
                source_filename="autogen_doc.pdf",
                scores=SearchScores(keyword_score=0.5, hybrid_score=0.5),
            )
        ]

    monkeypatch.setattr("app.services.evaluations.search_documents", fake_search_documents)

    fixture = ensure_auto_evaluation_fixture(
        FakeSession(),
        SimpleNamespace(
            id=uuid4(),
            source_filename="autogen_doc.pdf",
            sha256="abc123",
            title="Autogen Document",
        ),
        SimpleNamespace(id=uuid4()),
    )

    thresholds = fixture["thresholds"]
    assert len(thresholds["expected_top_n_table_hit_queries"]) == 1
    assert thresholds["expected_top_n_table_hit_queries"][0]["query"] in {
        "Table 3 Transportation Mitigations",
        "Transportation Mitigations",
    }
    assert thresholds["expected_top_n_chunk_hit_queries"] == []


def test_fixture_for_document_prefers_auto_fixture_over_manual_filename_match(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )
    storage_root.mkdir(parents=True, exist_ok=True)
    (storage_root / "evaluation_corpus.auto.yaml").write_text(
        """
documents:
  - name: auto_test_pdf
    kind: auto_generated_document
    source_filename: TEST_PDF.pdf
    thresholds:
      expected_top_n_chunk_hit_queries:
        - query: Automatic query
"""
    )

    fixture = fixture_for_document(SimpleNamespace(source_filename="TEST_PDF.pdf"))

    assert fixture is not None
    assert fixture.name == "auto_test_pdf"


def test_ensure_auto_evaluation_fixture_keeps_other_same_filename_sha256_entries(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )
    storage_root.mkdir(parents=True, exist_ok=True)
    auto_corpus_path = storage_root / "evaluation_corpus.auto.yaml"
    auto_corpus_path.write_text(
        """
documents:
  - name: auto_duplicate_old
    kind: auto_generated_document
    source_filename: duplicate.pdf
    sha256: oldsha
    thresholds:
      expected_top_n_chunk_hit_queries:
        - query: Old query
"""
    )

    tables: list[object] = []
    figures: list[object] = []
    chunks = [SimpleNamespace(heading=None, text="Fresh duplicate document content.")]

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class FakeSession:
        def __init__(self):
            self._results = [tables, figures, chunks]
            self.calls = 0

        def execute(self, _query):
            rows = self._results[self.calls]
            self.calls += 1
            return FakeResult(rows)

    monkeypatch.setattr("app.services.evaluations.search_documents", lambda *args, **kwargs: [])

    fixture = ensure_auto_evaluation_fixture(
        FakeSession(),
        SimpleNamespace(
            id=uuid4(),
            source_filename="duplicate.pdf",
            sha256="newsha",
            title="New Duplicate",
        ),
        SimpleNamespace(id=uuid4()),
    )

    payload = yaml.safe_load(auto_corpus_path.read_text())
    documents = payload["documents"]

    assert fixture["sha256"] == "newsha"
    assert len(documents) == 2
    assert {document["sha256"] for document in documents} == {"oldsha", "newsha"}


def test_evaluate_run_refreshes_existing_auto_fixture(monkeypatch) -> None:
    run_id = uuid4()
    document_id = uuid4()
    evaluation_row = SimpleNamespace(
        id=uuid4(),
        fixture_name=None,
        status=None,
        summary_json=None,
        completed_at=None,
    )
    fixture = SimpleNamespace(
        name="auto_test_pdf",
        kind=AUTO_FIXTURE_KIND,
        queries=[],
        answer_queries=[],
        thresholds=SimpleNamespace(),
    )
    state = {"refresh_count": 0, "fixture_calls": 0}

    class FakeSession:
        def add(self, _row) -> None:
            return None

        def commit(self) -> None:
            return None

        def rollback(self) -> None:
            return None

    def fake_fixture_for_document(*_args, **_kwargs):
        state["fixture_calls"] += 1
        return fixture

    monkeypatch.setattr(
        "app.services.evaluations._upsert_evaluation_row", lambda *args, **kwargs: evaluation_row
    )
    monkeypatch.setattr("app.services.evaluations.fixture_for_document", fake_fixture_for_document)
    monkeypatch.setattr(
        "app.services.evaluations.ensure_auto_evaluation_fixture",
        lambda *args, **kwargs: state.__setitem__("refresh_count", state["refresh_count"] + 1),
    )
    monkeypatch.setattr(
        "app.services.evaluations._evaluate_structural_checks",
        lambda *args, **kwargs: {
            "check_count": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "passed": True,
            "checks": [],
        },
    )

    evaluation = evaluate_run(
        FakeSession(),
        document=SimpleNamespace(
            id=document_id,
            source_filename="TEST_PDF.pdf",
            active_run_id=run_id,
        ),
        run=SimpleNamespace(id=run_id, document_id=document_id),
    )

    assert state["refresh_count"] == 1
    assert state["fixture_calls"] == 2
    assert evaluation.fixture_name == "auto_test_pdf"
    assert evaluation.status == "completed"
    assert evaluation.summary_json["query_count"] == 0
    assert evaluation.summary_json["structural_passed"] is True


def test_evaluate_run_uses_auto_corpus_by_default(monkeypatch, tmp_path) -> None:
    storage_root = tmp_path / "storage"
    auto_corpus_path = storage_root.resolve() / "evaluation_corpus.auto.yaml"
    run_id = uuid4()
    document_id = uuid4()
    evaluation_row = SimpleNamespace(
        id=uuid4(),
        fixture_name=None,
        status=None,
        summary_json=None,
        error_message=None,
        completed_at=None,
    )
    fixture = SimpleNamespace(
        name="auto_generated",
        kind=AUTO_FIXTURE_KIND,
        queries=[],
        answer_queries=[],
        thresholds=SimpleNamespace(),
    )
    state = {"refreshed": False}
    seen_corpus_paths: list[Path | None] = []

    class FakeSession:
        def add(self, _row) -> None:
            return None

        def commit(self) -> None:
            return None

        def rollback(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.evaluations.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            manual_evaluation_corpus_path=None,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )
    monkeypatch.setattr(
        "app.services.evaluations._upsert_evaluation_row", lambda *args, **kwargs: evaluation_row
    )

    def fake_fixture_for_document(_document, corpus_path=None, **_kwargs):
        seen_corpus_paths.append(corpus_path)
        return fixture if state["refreshed"] else None

    monkeypatch.setattr("app.services.evaluations.fixture_for_document", fake_fixture_for_document)
    monkeypatch.setattr(
        "app.services.evaluations.ensure_auto_evaluation_fixture",
        lambda *args, **kwargs: state.__setitem__("refreshed", True),
    )
    monkeypatch.setattr(
        "app.services.evaluations._evaluate_structural_checks",
        lambda *args, **kwargs: {
            "check_count": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "passed": True,
            "checks": [],
        },
    )

    evaluation = evaluate_run(
        FakeSession(),
        document=SimpleNamespace(
            id=document_id,
            source_filename="new_document.pdf",
            active_run_id=run_id,
        ),
        run=SimpleNamespace(id=run_id, document_id=document_id),
    )

    assert seen_corpus_paths == [auto_corpus_path, auto_corpus_path]
    assert evaluation.fixture_name == "auto_generated"
    assert evaluation.status == "completed"


def test_evaluate_run_persists_failed_row_when_auto_fixture_refresh_raises(monkeypatch) -> None:
    run_id = uuid4()
    document_id = uuid4()
    pending_row = SimpleNamespace(
        id=uuid4(),
        fixture_name=None,
        status="pending",
        summary_json=None,
        error_message=None,
        completed_at=None,
    )
    failed_row = SimpleNamespace(
        id=uuid4(),
        fixture_name=None,
        status="pending",
        summary_json=None,
        error_message=None,
        completed_at=None,
    )
    rows = [pending_row, failed_row]

    class FakeSession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def add(self, _row) -> None:
            return None

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    monkeypatch.setattr(
        "app.services.evaluations._upsert_evaluation_row",
        lambda *args, **kwargs: rows.pop(0),
    )
    monkeypatch.setattr(
        "app.services.evaluations.fixture_for_document", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "app.services.evaluations.ensure_auto_evaluation_fixture",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fixture refresh failed")),
    )

    session = FakeSession()
    evaluation = evaluate_run(
        session,
        document=SimpleNamespace(
            id=document_id,
            source_filename="TEST_PDF.pdf",
            active_run_id=run_id,
        ),
        run=SimpleNamespace(id=run_id, document_id=document_id),
    )

    assert session.rollbacks == 1
    assert session.commits == 1
    assert evaluation is failed_row
    assert evaluation.status == "failed"
    assert evaluation.error_message == "fixture refresh failed"
    assert evaluation.summary_json["status"] == "failed"
    assert evaluation.summary_json["fixture_name"] is None


def test_resolve_baseline_run_id_prefers_prior_active_run_for_reprocess() -> None:
    candidate_run_id = uuid4()
    prior_active_run_id = uuid4()

    assert resolve_baseline_run_id(candidate_run_id, prior_active_run_id) == prior_active_run_id


def test_resolve_baseline_run_id_ignores_self_and_honors_explicit_override() -> None:
    candidate_run_id = uuid4()
    active_run_id = candidate_run_id
    explicit_baseline_run_id = uuid4()

    assert resolve_baseline_run_id(candidate_run_id, active_run_id) is None
    assert (
        resolve_baseline_run_id(
            candidate_run_id,
            active_run_id,
            explicit_baseline_run_id=explicit_baseline_run_id,
        )
        == explicit_baseline_run_id
    )


def test_summarize_structural_checks_passes_expected_overlay_merge(tmp_path) -> None:
    json_path = tmp_path / "figure.json"
    yaml_path = tmp_path / "figure.yaml"
    json_path.write_text("{}")
    yaml_path.write_text("caption: ok\n")

    fixture = next(
        fixture
        for fixture in load_evaluation_fixtures(DEFAULT_CORPUS_PATH)
        if fixture.name == "upc_ch5"
    )
    table = SimpleNamespace(
        title="TABLE 510.1.2 ( 2 ) TYPE B DOUBLE -WALL GAS VENT [ NFPA 54 : TABLE 13.1(b)]*",
        heading="510.1.2 Elbows",
        page_from=109,
        page_to=113,
        metadata_json={
            "is_merged": True,
            "source_segment_count": 5,
            "overlay_applied": True,
            "overlay_family_key": "TABLE 510.1.2(2)",
        },
    )
    figure = SimpleNamespace(
        caption="Example figure",
        json_path=str(json_path),
        yaml_path=str(yaml_path),
        metadata_json={"provenance": [{"page_no": 1}]},
    )

    summary = _summarize_structural_checks(
        tables=[table] * fixture.thresholds.expected_logical_table_count,
        figures=[figure] * fixture.thresholds.expected_figure_count,
        thresholds=fixture.thresholds,
    )

    assert summary["passed"] is True
    expected_merge_check = next(
        check for check in summary["checks"] if check["name"] == "expected_merged_tables"
    )
    assert expected_merge_check["passed"] is True
    assert expected_merge_check["actual_matched_count"] == 1


def test_summarize_structural_checks_flags_missing_expected_merge(tmp_path) -> None:
    json_path = tmp_path / "figure.json"
    yaml_path = tmp_path / "figure.yaml"
    json_path.write_text("{}")
    yaml_path.write_text("caption: ok\n")

    fixture = next(
        fixture
        for fixture in load_evaluation_fixtures(DEFAULT_CORPUS_PATH)
        if fixture.name == "upc_ch5"
    )
    table = SimpleNamespace(
        title="TABLE 510.1.2 ( 2 ) TYPE B DOUBLE -WALL GAS VENT [ NFPA 54 : TABLE 13.1(b)]*",
        heading="510.1.2 Elbows",
        page_from=109,
        page_to=113,
        metadata_json={"is_merged": False, "source_segment_count": 1},
    )
    figure = SimpleNamespace(
        caption="Example figure",
        json_path=str(json_path),
        yaml_path=str(yaml_path),
        metadata_json={"provenance": [{"page_no": 1}]},
    )

    summary = _summarize_structural_checks(
        tables=[table] * fixture.thresholds.expected_logical_table_count,
        figures=[figure] * fixture.thresholds.expected_figure_count,
        thresholds=fixture.thresholds,
    )

    assert summary["passed"] is False
    expected_merge_check = next(
        check for check in summary["checks"] if check["name"] == "expected_merged_tables"
    )
    assert expected_merge_check["passed"] is False
    assert "repaired TABLE 510.1.2(2) overlay family" in expected_merge_check["missing"]


def test_summarize_structural_checks_tolerates_non_string_figure_captions(tmp_path) -> None:
    json_path = tmp_path / "figure.json"
    yaml_path = tmp_path / "figure.yaml"
    json_path.write_text("{}")
    yaml_path.write_text("caption: ok\n")

    summary = _summarize_structural_checks(
        tables=[],
        figures=[
            SimpleNamespace(
                caption={"text": "Flood: M/P/E Systems"},
                json_path=str(json_path),
                yaml_path=str(yaml_path),
                metadata_json={"provenance": [{"page_no": 1}]},
            )
        ],
        thresholds=SimpleNamespace(
            expected_logical_table_count=None,
            logical_table_tolerance=0,
            expected_figure_count=1,
            figure_count_tolerance=0,
            minimum_captioned_figure_count=1,
            minimum_figures_with_provenance=1,
            minimum_figures_with_artifacts=1,
            expected_figure_captions_present=["Flood: M/P/E Systems"],
            maximum_unexpected_merges=0,
            maximum_unexpected_splits=0,
            expected_merged_tables=[],
            enforce_unexpected_merged_tables=False,
        ),
    )

    caption_check = next(
        check for check in summary["checks"] if check["name"] == "expected_figure_captions_present"
    )
    assert caption_check["passed"] is True


def test_evaluate_retrieval_case_flags_foreign_top_result_before_expected_hit() -> None:
    case = EvaluationQueryCase(
        query="What is the main claim of The Bitter Lesson?",
        mode="keyword",
        filters={},
        include_document_filter=True,
        expected_result_type="chunk",
        expected_top_n=3,
        expected_source_filename="The Bitter Lesson.pdf",
        expected_top_result_source_filename="The Bitter Lesson.pdf",
        minimum_top_n_hits_from_expected_document=2,
        maximum_foreign_results_before_first_expected_hit=0,
    )
    candidate_results = [
        SearchResult(
            result_type="chunk",
            document_id=uuid4(),
            run_id=uuid4(),
            score=0.95,
            chunk_id=uuid4(),
            chunk_text="Unrelated plumbing code result.",
            heading="UPC",
            page_from=1,
            page_to=1,
            source_filename="UPC_CH_5.pdf",
            scores=SearchScores(keyword_score=0.95),
        ),
        SearchResult(
            result_type="chunk",
            document_id=uuid4(),
            run_id=uuid4(),
            score=0.94,
            chunk_id=uuid4(),
            chunk_text="General methods that leverage computation win over hand-coded ones.",
            heading="The Bitter Lesson",
            page_from=2,
            page_to=2,
            source_filename="The Bitter Lesson.pdf",
            scores=SearchScores(keyword_score=0.94),
        ),
        SearchResult(
            result_type="chunk",
            document_id=uuid4(),
            run_id=uuid4(),
            score=0.90,
            chunk_id=uuid4(),
            chunk_text="Search and learning are central recurring themes.",
            heading="The Bitter Lesson",
            page_from=3,
            page_to=3,
            source_filename="The Bitter Lesson.pdf",
            scores=SearchScores(keyword_score=0.90),
        ),
    ]

    outcome = _evaluate_retrieval_case(
        case=case,
        filters_payload={"document_id": str(uuid4())},
        candidate_results=candidate_results,
        baseline_results=[],
    )

    assert outcome["passed"] is False
    assert outcome["candidate_rank"] == 2
    assert outcome["details_json"]["candidate_top_result_source_filename"] == "UPC_CH_5.pdf"
    assert outcome["details_json"]["candidate_result_count"] == 3
    assert outcome["details_json"]["candidate_reciprocal_rank"] == 0.5
    assert outcome["details_json"]["candidate_expected_hits_in_top_1"] == 0
    assert outcome["details_json"]["candidate_expected_hits_in_top_3"] == 2
    assert outcome["details_json"]["candidate_expected_hits_in_top_5"] == 2
    assert outcome["details_json"]["candidate_foreign_top_result"] is True
    assert outcome["details_json"]["candidate_expected_source_hit_count"] == 2
    assert outcome["details_json"]["candidate_foreign_results_before_first_expected_hit"] == 1
    assert outcome["details_json"]["candidate_failure_kind"] == "foreign_top_result"


def test_execute_retrieval_queries_can_skip_document_filter() -> None:
    captured_filters: list[dict] = []
    captured_run_ids: list[object] = []

    class FakeSession:
        def __init__(self) -> None:
            self.rows: list[object] = []

        def add(self, row) -> None:
            self.rows.append(row)

    def fake_search_documents(_session, request, *_args, **kwargs):
        captured_filters.append(
            request.filters.model_dump(mode="json", exclude_none=True) if request.filters else {}
        )
        captured_run_ids.append(kwargs.get("run_id"))
        return [
            SearchResult(
                result_type="chunk",
                document_id=uuid4(),
                run_id=uuid4(),
                score=0.91,
                chunk_id=uuid4(),
                chunk_text="The Bitter Lesson says general methods that leverage computation win.",
                heading="The Bitter Lesson",
                page_from=1,
                page_to=1,
                source_filename="The Bitter Lesson.pdf",
                scores=SearchScores(keyword_score=0.91),
            )
        ]

    batch = execute_retrieval_queries(
        FakeSession(),
        document=SimpleNamespace(id=uuid4(), source_filename="The Bitter Lesson.pdf"),
        run=SimpleNamespace(id=uuid4()),
        evaluation_id=uuid4(),
        baseline_run_id=None,
        queries=[
            EvaluationQueryCase(
                query="claim bitter lesson",
                mode="keyword",
                filters={},
                include_document_filter=False,
                expected_result_type="chunk",
                expected_top_n=3,
                expected_source_filename="The Bitter Lesson.pdf",
                expected_top_result_source_filename="The Bitter Lesson.pdf",
                minimum_top_n_hits_from_expected_document=1,
                maximum_foreign_results_before_first_expected_hit=0,
            )
        ],
        created_at=datetime.now(UTC),
        search_documents_fn=fake_search_documents,
        evaluate_retrieval_case_fn=_evaluate_retrieval_case,
    )

    assert captured_filters == [{}]
    assert captured_run_ids == [None]
    assert batch.query_count == 1
    assert batch.passed_retrieval_queries == 1


def test_evaluate_answer_case_flags_foreign_citations(monkeypatch) -> None:
    candidate_response = ChatResponse(
        answer=(
            "The essay argues that general methods powered by computation "
            "outperform hand-built approaches."
        ),
        citations=[
            ChatCitation(
                citation_index=1,
                result_type="chunk",
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="UPC_CH_5.pdf",
                page_from=1,
                page_to=1,
                label="UPC",
                excerpt="Unrelated plumbing text.",
                score=0.8,
            )
        ],
        mode="hybrid",
        used_fallback=False,
    )

    monkeypatch.setattr(
        "app.services.evaluations.answer_question",
        lambda *args, **kwargs: candidate_response if kwargs["run_id"] else None,
    )

    outcome = _evaluate_answer_case(
        session=None,
        document=SimpleNamespace(id=uuid4()),
        run_id=uuid4(),
        baseline_run_id=None,
        evaluation_id=uuid4(),
        case=EvaluationAnswerCase(
            question="What is the main claim of The Bitter Lesson?",
            mode="hybrid",
            filters={},
            include_document_filter=True,
            expected_answer_contains=["general methods", "computation"],
            minimum_citation_count=1,
            allow_fallback=False,
            top_k=4,
            expected_citation_source_filename="The Bitter Lesson.pdf",
            maximum_foreign_citations=0,
        ),
    )

    assert outcome["passed"] is False
    assert outcome["details_json"]["candidate_matching_citation_count"] == 0
    assert outcome["details_json"]["candidate_foreign_citation_count"] == 1


def test_evaluate_answer_case_supports_expected_no_answer(monkeypatch) -> None:
    candidate_response = ChatResponse(
        answer="I couldn't find relevant support for that question in the ingested corpus.",
        citations=[],
        mode="hybrid",
        used_fallback=True,
    )

    monkeypatch.setattr(
        "app.services.evaluations.answer_question",
        lambda *args, **kwargs: candidate_response if kwargs["run_id"] else None,
    )

    outcome = _evaluate_answer_case(
        session=None,
        document=SimpleNamespace(id=uuid4()),
        run_id=uuid4(),
        baseline_run_id=None,
        evaluation_id=uuid4(),
        case=EvaluationAnswerCase(
            question="What launch date does the opportunity screening memo announce?",
            mode="hybrid",
            filters={},
            include_document_filter=True,
            expected_answer_contains=[],
            minimum_citation_count=0,
            allow_fallback=True,
            top_k=4,
            expect_no_answer=True,
            maximum_citation_count=0,
        ),
    )

    assert outcome["passed"] is True
    assert outcome["details_json"]["expect_no_answer"] is True
    assert outcome["details_json"]["candidate_citation_count"] == 0
    assert outcome["details_json"]["candidate_used_fallback"] is True


def test_summarize_retrieval_rank_metrics_rolls_up_query_metrics() -> None:
    metrics = _summarize_retrieval_rank_metrics(
        [
            {
                "details_json": {
                    "candidate_reciprocal_rank": 1.0,
                    "baseline_reciprocal_rank": 0.5,
                    "candidate_expected_hits_in_top_1": 1,
                    "candidate_expected_hits_in_top_3": 2,
                    "candidate_expected_hits_in_top_5": 2,
                    "baseline_expected_hits_in_top_1": 0,
                    "baseline_expected_hits_in_top_3": 1,
                    "baseline_expected_hits_in_top_5": 1,
                    "candidate_zero_results": False,
                    "baseline_zero_results": False,
                    "candidate_foreign_top_result": False,
                    "baseline_foreign_top_result": True,
                    "candidate_failure_kind": None,
                    "baseline_failure_kind": "foreign_top_result",
                }
            },
            {
                "details_json": {
                    "candidate_reciprocal_rank": 0.0,
                    "baseline_reciprocal_rank": 0.0,
                    "candidate_expected_hits_in_top_1": 0,
                    "candidate_expected_hits_in_top_3": 0,
                    "candidate_expected_hits_in_top_5": 0,
                    "baseline_expected_hits_in_top_1": 0,
                    "baseline_expected_hits_in_top_3": 0,
                    "baseline_expected_hits_in_top_5": 0,
                    "candidate_zero_results": True,
                    "baseline_zero_results": False,
                    "candidate_foreign_top_result": False,
                    "baseline_foreign_top_result": False,
                    "candidate_failure_kind": "zero_results",
                    "baseline_failure_kind": "wrong_result",
                }
            },
        ]
    )

    assert metrics["candidate_mrr"] == 0.5
    assert metrics["baseline_mrr"] == 0.25
    assert metrics["candidate_top_1_hit_queries"] == 1
    assert metrics["candidate_top_3_hit_queries"] == 1
    assert metrics["candidate_top_5_hit_queries"] == 1
    assert metrics["baseline_top_1_hit_queries"] == 0
    assert metrics["baseline_top_3_hit_queries"] == 1
    assert metrics["baseline_top_5_hit_queries"] == 1
    assert metrics["candidate_zero_result_queries"] == 1
    assert metrics["candidate_wrong_result_queries"] == 0
    assert metrics["candidate_foreign_top_result_queries"] == 0
    assert metrics["baseline_zero_result_queries"] == 0
    assert metrics["baseline_wrong_result_queries"] == 1
    assert metrics["baseline_foreign_top_result_queries"] == 1
    assert metrics["candidate_failure_kind_counts"] == {"zero_results": 1}
    assert metrics["baseline_failure_kind_counts"] == {
        "foreign_top_result": 1,
        "wrong_result": 1,
    }
