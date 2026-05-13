from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.chat import ChatCitation, ChatResponse
from app.schemas.search import SearchResult, SearchScores
from app.services import evaluations
from app.services.evaluation_fixtures import (
    EvaluationAnswerCase,
    EvaluationQueryCase,
    load_evaluation_fixtures,
)
from app.services.evaluation_scoring import (
    _evaluate_answer_case,
    _evaluate_retrieval_case,
    _summarize_retrieval_rank_metrics,
    _summarize_structural_checks,
)

LEGACY_CORPUS_PATH = Path("tests") / "fixtures" / "evaluation_corpus.legacy.yaml"


def test_evaluations_facade_reexports_scoring_helpers() -> None:
    assert evaluations._evaluate_retrieval_case is _evaluate_retrieval_case
    assert evaluations._evaluate_answer_case is _evaluate_answer_case
    assert evaluations._summarize_structural_checks is _summarize_structural_checks


def test_summarize_structural_checks_passes_expected_overlay_merge(tmp_path) -> None:
    json_path = tmp_path / "figure.json"
    yaml_path = tmp_path / "figure.yaml"
    json_path.write_text("{}")
    yaml_path.write_text("caption: ok\n")

    fixture = next(
        fixture
        for fixture in load_evaluation_fixtures(LEGACY_CORPUS_PATH)
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
        for fixture in load_evaluation_fixtures(LEGACY_CORPUS_PATH)
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
        "app.services.evaluation_scoring.answer_question",
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
        "app.services.evaluation_scoring.answer_question",
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
