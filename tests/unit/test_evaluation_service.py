from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import SearchResult, SearchScores
from app.services.evaluation_execution import execute_retrieval_queries
from app.services.evaluations import (
    AUTO_FIXTURE_KIND,
    EvaluationQueryCase,
    _evaluate_retrieval_case,
    evaluate_run,
    resolve_baseline_run_id,
)


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
