from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.services.evaluation_fixtures import (
    DEFAULT_CORPUS_PATH,
    build_auto_evaluation_fixture_document,
    fixture_for_document,
    load_evaluation_fixtures,
)

LEGACY_CORPUS_PATH = Path("tests") / "fixtures" / "evaluation_corpus.legacy.yaml"


def test_default_evaluation_corpus_requires_explicit_manual_path(monkeypatch, tmp_path) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
            manual_evaluation_corpus_path=None,
        ),
    )

    fixtures = load_evaluation_fixtures()

    assert fixtures == []

    manual_fixtures = load_evaluation_fixtures(DEFAULT_CORPUS_PATH)

    assert len(manual_fixtures) == 5
    assert {fixture.name for fixture in manual_fixtures} == {
        "regression_doc_03_blue_mesas_seed",
        "regression_doc_04_sage_creek_seed",
        "regression_doc_05_granite_pass_seed",
        "regression_doc_06_timber_basin_seed",
        "regression_doc_07_copper_ridge_seed",
    }
    fixture = manual_fixtures[0]
    assert fixture.name == "regression_doc_03_blue_mesas_seed"
    assert fixture.kind == "reviewed_regression_seed"
    assert fixture.source_filename == "regression_doc_03.pdf"
    assert fixture.document_sha256 == (
        "504afc31793c86eb31b71c129005ddde9bf22e97eaa4e736534439857265d88c"
    )
    assert fixture.thresholds.expected_logical_table_count == 1
    assert fixture.thresholds.expected_figure_count == 0
    assert len(fixture.queries) == 7
    assert len(fixture.answer_queries) == 1

    assert sum(len(row.queries) for row in manual_fixtures) == 35
    assert sum(len(row.answer_queries) for row in manual_fixtures) == 5

    cross_document_query = next(
        query
        for query in fixture.queries
        if query.query == "Blue Mesas readiness narrative explains how milestone six"
        and query.include_document_filter is False
    )
    assert cross_document_query.mode == "hybrid"
    assert cross_document_query.expected_result_type == "chunk"
    assert cross_document_query.expected_top_n == 3
    assert cross_document_query.expected_source_filename == "regression_doc_03.pdf"
    assert cross_document_query.expected_top_result_source_filename == "regression_doc_03.pdf"
    assert cross_document_query.minimum_top_n_hits_from_expected_document == 1
    assert cross_document_query.maximum_foreign_results_before_first_expected_hit == 0


def test_load_legacy_evaluation_fixture_compiles_search_queries() -> None:
    fixtures = load_evaluation_fixtures(LEGACY_CORPUS_PATH)

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
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    fixture = fixture_for_document(SimpleNamespace(source_filename="duplicate.pdf"))

    assert fixture is not None
    assert fixture.name == "auto_duplicate"


def test_fixture_for_document_does_not_match_manual_fixture_by_source_filename_by_default(
    monkeypatch, tmp_path
) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )
    document = SimpleNamespace(source_filename="UPC_Appendix_N.pdf")

    fixture = fixture_for_document(document)

    assert fixture is None


def test_fixture_for_document_can_opt_into_manual_filename_fallback(monkeypatch, tmp_path) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )
    document = SimpleNamespace(source_filename="UPC_Appendix_N.pdf")

    fixture = fixture_for_document(
        document,
        corpus_path=LEGACY_CORPUS_PATH,
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
        "app.services.evaluation_fixtures.get_settings",
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
        "app.services.evaluation_fixtures.get_settings",
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
        "app.services.evaluation_fixtures.get_settings",
        lambda: SimpleNamespace(
            storage_root=storage_root,
            manual_evaluation_corpus_path=corpus_path,
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    fixtures = load_evaluation_fixtures()

    assert [fixture.name for fixture in fixtures] == ["configured_manual"]


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
