from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.chat import ChatCitation, ChatResponse
from app.schemas.search import SearchResult, SearchScores
from app.services.evaluation_execution import execute_retrieval_queries
from app.services.evaluations import (
    AUTO_FIXTURE_KIND,
    EvaluationAnswerCase,
    EvaluationQueryCase,
    _evaluate_answer_case,
    _evaluate_retrieval_case,
    _summarize_retrieval_rank_metrics,
    _summarize_structural_checks,
    evaluate_run,
    load_evaluation_fixtures,
    resolve_baseline_run_id,
)

LEGACY_CORPUS_PATH = Path("tests") / "fixtures" / "evaluation_corpus.legacy.yaml"


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


def test_evaluate_run_can_reuse_existing_auto_fixture(monkeypatch) -> None:
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
        refresh_auto_fixture=False,
    )

    assert state["refresh_count"] == 0
    assert state["fixture_calls"] == 1
    assert evaluation.fixture_name == "auto_test_pdf"
    assert evaluation.status == "completed"


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
        "app.services.evaluation_fixtures.get_settings",
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
