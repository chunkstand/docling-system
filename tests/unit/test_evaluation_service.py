from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.schemas.chat import ChatCitation, ChatResponse
from app.schemas.search import SearchResult, SearchScores
from app.services.evaluations import (
    AUTO_FIXTURE_KIND,
    EvaluationAnswerCase,
    EvaluationQueryCase,
    _evaluate_answer_case,
    _evaluate_retrieval_case,
    _summarize_retrieval_rank_metrics,
    _summarize_structural_checks,
    build_auto_evaluation_fixture_document,
    ensure_auto_evaluation_fixture,
    fixture_for_document,
    load_evaluation_fixtures,
    resolve_baseline_run_id,
)


def test_load_evaluation_fixtures_compiles_search_queries() -> None:
    fixtures = load_evaluation_fixtures()

    born_digital = next(fixture for fixture in fixtures if fixture.name == "born_digital_simple")
    assert born_digital.source_filename == "UPC_Appendix_N.pdf"
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
    assert all(query.expected_result_type == "chunk" for query in bitter_lesson.queries)
    assert any(query.mode == "keyword" for query in bitter_lesson.queries)
    assert len(bitter_lesson.answer_queries) == 1
    assert bitter_lesson.answer_queries[0].expected_answer_contains == [
        "general methods",
        "computation",
    ]
    assert bitter_lesson.queries[-1].expected_source_filename == "The Bitter Lesson.pdf"
    assert (
        bitter_lesson.queries[-1].expected_top_result_source_filename == "The Bitter Lesson.pdf"
    )
    assert bitter_lesson.queries[-1].minimum_top_n_hits_from_expected_document == 2
    assert bitter_lesson.queries[-1].maximum_foreign_results_before_first_expected_hit == 0
    assert (
        bitter_lesson.answer_queries[0].expected_citation_source_filename
        == "The Bitter Lesson.pdf"
    )
    assert bitter_lesson.answer_queries[0].maximum_foreign_citations == 0

    test_pdf = next(fixture for fixture in fixtures if fixture.name == "test_pdf_prose")
    assert test_pdf.source_filename == "TEST_PDF.pdf"
    assert len(test_pdf.queries) == 5
    assert test_pdf.queries[-1].expected_source_filename == "TEST_PDF.pdf"
    assert test_pdf.queries[-1].expected_top_result_source_filename == "TEST_PDF.pdf"
    assert test_pdf.queries[-1].minimum_top_n_hits_from_expected_document == 1
    assert test_pdf.queries[-1].maximum_foreign_results_before_first_expected_hit == 0
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
    assert (
        transportation_report.queries[-1].expected_top_result_source_filename
        == "20251216_TK_TransportationReport.pdf"
    )
    assert transportation_report.answer_queries[0].expected_citation_source_filename == (
        "20251216_TK_TransportationReport.pdf"
    )
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
        wildlife_report.queries[-1].expected_source_filename
        == "20251215_TK_WildlifeSpecReport.pdf"
    )
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


def test_fixture_for_document_matches_by_source_filename() -> None:
    document = SimpleNamespace(source_filename="UPC_Appendix_N.pdf")

    fixture = fixture_for_document(document)

    assert fixture is not None
    assert fixture.name == "born_digital_simple"


def test_build_auto_evaluation_fixture_document_generates_structural_queries() -> None:
    run_id = uuid4()

    fixture = build_auto_evaluation_fixture_document(
        "auto_generated_report.pdf",
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
        chunks=[],
        tables=[],
        figures=[],
    )

    chunk_queries = fixture["thresholds"]["expected_top_n_chunk_hit_queries"]
    assert chunk_queries[0]["query"] == "TK SoilReport"


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

    fixture = ensure_auto_evaluation_fixture(
        FakeSession(),
        SimpleNamespace(id=uuid4(), source_filename="autogen_doc.pdf", title="Autogen Document"),
        SimpleNamespace(id=uuid4()),
    )

    auto_corpus_path = storage_root / "evaluation_corpus.auto.yaml"
    assert auto_corpus_path.exists() is True
    assert fixture["source_filename"] == "autogen_doc.pdf"
    assert fixture["thresholds"]["expected_logical_table_count"] == 1
    loaded = fixture_for_document(SimpleNamespace(source_filename="autogen_doc.pdf"))
    assert loaded is not None
    assert loaded.name == fixture["name"]


def test_fixture_for_document_prefers_manual_fixture_over_auto(monkeypatch, tmp_path) -> None:
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
    assert fixture.name == "test_pdf_prose"


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


def test_evaluate_retrieval_case_flags_foreign_top_result_before_expected_hit() -> None:
    case = EvaluationQueryCase(
        query="What is the main claim of The Bitter Lesson?",
        mode="keyword",
        filters={},
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
