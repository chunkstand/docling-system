from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.evaluations import (
    _summarize_structural_checks,
    fixture_for_document,
    load_evaluation_fixtures,
    resolve_baseline_run_id,
)


def test_load_evaluation_fixtures_compiles_search_queries() -> None:
    fixtures = load_evaluation_fixtures()

    born_digital = next(fixture for fixture in fixtures if fixture.name == "born_digital_simple")
    assert born_digital.path.endswith("UPC_Appendix_N.pdf")
    assert len(born_digital.queries) >= 3
    assert born_digital.queries[0].expected_result_type == "table"
    assert born_digital.queries[0].expected_top_n >= 1

    chapter_five = next(fixture for fixture in fixtures if fixture.name == "upc_ch5")
    assert len(chapter_five.queries) >= 4
    assert len(chapter_five.thresholds.expected_merged_tables) == 1
    assert (
        chapter_five.thresholds.expected_merged_tables[0].overlay_family_key
        == "TABLE 510.1.2(2)"
    )

    appendix_b = next(
        fixture for fixture in fixtures if fixture.name == "appendix_b_prose_guidance"
    )
    assert appendix_b.path.endswith("UPC_Appendix_B.pdf")
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
    assert bitter_lesson.path.endswith("The Bitter Lesson.pdf")
    assert bitter_lesson.thresholds.expected_logical_table_count == 0
    assert bitter_lesson.thresholds.expected_figure_count == 0
    assert all(query.expected_result_type == "chunk" for query in bitter_lesson.queries)
    assert any(query.mode == "keyword" for query in bitter_lesson.queries)
    assert len(bitter_lesson.answer_queries) == 1
    assert bitter_lesson.answer_queries[0].expected_answer_contains == [
        "general methods",
        "computation",
    ]

    test_pdf = next(fixture for fixture in fixtures if fixture.name == "test_pdf_prose")
    assert test_pdf.path.endswith("TEST_PDF.pdf")
    assert len(test_pdf.answer_queries) == 1
    assert test_pdf.answer_queries[0].minimum_citation_count == 1

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
    assert soil_report.path.endswith("20251217_TK_SoilReport.pdf")
    assert soil_report.thresholds.expected_logical_table_count == 12
    assert soil_report.thresholds.expected_figure_count == 2
    assert len(soil_report.answer_queries) == 1
    assert any(query.mode == "keyword" for query in soil_report.queries)

    transportation_report = next(
        fixture for fixture in fixtures if fixture.name == "tyler_kitchen_transportation_report"
    )
    assert transportation_report.path.endswith("20251216_TK_TransportationReport.pdf")
    assert transportation_report.thresholds.expected_logical_table_count == 8
    assert transportation_report.thresholds.expected_figure_count == 0
    assert len(transportation_report.answer_queries) == 1

    wildlife_report = next(
        fixture for fixture in fixtures if fixture.name == "tyler_kitchen_wildlife_report"
    )
    assert wildlife_report.path.endswith("20251215_TK_WildlifeSpecReport.pdf")
    assert wildlife_report.thresholds.expected_logical_table_count == 18
    assert wildlife_report.thresholds.expected_figure_count == 2
    assert len(wildlife_report.answer_queries) == 1
    assert wildlife_report.thresholds.expected_figure_captions_present == [
        "Tyler's Kitchen Fuels Reduction and Forest Health Project",
        (
            "Figure 1. Modeled fisher habitat in the Northern Rocky Mountains, "
            "from USFWS status assessment (2017)."
        ),
    ]


def test_fixture_for_document_matches_by_source_filename() -> None:
    document = SimpleNamespace(source_filename="UPC_Appendix_N.pdf")

    fixture = fixture_for_document(document)

    assert fixture is not None
    assert fixture.name == "born_digital_simple"


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

    fixture = next(fixture for fixture in load_evaluation_fixtures() if fixture.name == "upc_ch5")
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

    fixture = next(fixture for fixture in load_evaluation_fixtures() if fixture.name == "upc_ch5")
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
