from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.schemas.chat import ChatAnswerFeedbackCreateRequest, ChatRequest
from app.schemas.search import SearchResult, SearchScores
from app.services.chat import (
    AnswerGenerator,
    OpenAIAnswerGenerator,
    answer_question,
    record_chat_answer_feedback,
)


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        return None

    def get(self, model, row_id):
        return None


def _chunk_result() -> SearchResult:
    return SearchResult(
        result_type="chunk",
        document_id=uuid4(),
        run_id=uuid4(),
        score=0.88,
        chunk_id=uuid4(),
        chunk_text="Plastic vent joints shall be installed with approved fittings.",
        heading="701.1 Materials",
        page_from=15,
        page_to=15,
        source_filename="UPC_CH_5.pdf",
        scores=SearchScores(keyword_score=0.4, semantic_score=0.8, hybrid_score=0.88),
    )


def test_record_chat_answer_feedback_returns_structured_not_found() -> None:
    answer_id = uuid4()

    try:
        record_chat_answer_feedback(
            FakeSession(),
            answer_id,
            ChatAnswerFeedbackCreateRequest(feedback_type="helpful"),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail["code"] == "chat_answer_not_found"
        assert exc.detail["context"]["chat_answer_id"] == str(answer_id)
    else:
        raise AssertionError("Expected missing chat answer to be rejected")


def _memo_date_result() -> SearchResult:
    return SearchResult(
        result_type="chunk",
        document_id=uuid4(),
        run_id=uuid4(),
        score=0.9,
        chunk_id=uuid4(),
        chunk_text=(
            "Standing Framework - Government Contract Opportunity Screening (March 23, 2026)"
        ),
        heading=None,
        page_from=1,
        page_to=1,
        source_filename="TEST_PDF.pdf",
        scores=SearchScores(keyword_score=0.5, semantic_score=0.9, hybrid_score=0.9),
    )


def _due_date_result() -> SearchResult:
    return SearchResult(
        result_type="chunk",
        document_id=uuid4(),
        run_id=uuid4(),
        score=0.88,
        chunk_id=uuid4(),
        chunk_text=(
            "Data sources - Opportunities were found via publicly available solicitations. "
            "Due date: April 9 2026"
        ),
        heading=None,
        page_from=1,
        page_to=1,
        source_filename="TEST_PDF.pdf",
        scores=SearchScores(keyword_score=0.4, semantic_score=0.8, hybrid_score=0.88),
    )


class FakeAnswerGenerator(AnswerGenerator):
    model = "fake-model"

    def __init__(self) -> None:
        self.questions: list[str] = []

    def generate_answer(self, *, question: str, contexts) -> str:
        self.questions.append(question)
        assert contexts[0].citation.label == "701.1 Materials"
        return "Plastic vent joints require approved fittings [1]."


def test_answer_question_uses_retrieval_and_generator(monkeypatch) -> None:
    result = _chunk_result()
    captured = {}

    class FakeExecution:
        def __init__(self) -> None:
            self.results = [result]
            self.request_id = uuid4()
            self.harness_name = "wide_v2"
            self.reranker_name = "linear_feature_reranker"
            self.reranker_version = "v2"
            self.retrieval_profile_name = "wide_v2"

    def fake_execute_search(session, request, origin="api"):
        captured["request"] = request
        captured["origin"] = origin
        return FakeExecution()

    monkeypatch.setattr("app.services.chat.execute_search", fake_execute_search)
    generator = FakeAnswerGenerator()
    session = FakeSession()

    response = answer_question(
        session=session,
        request=ChatRequest(
            question="How should plastic vent joints be installed?",
            mode="hybrid",
            document_id=result.document_id,
            top_k=4,
        ),
        answer_generator=generator,
    )

    assert response.used_fallback is False
    assert response.model == "fake-model"
    assert response.answer == "Plastic vent joints require approved fittings [1]."
    assert response.citations[0].excerpt.startswith("Plastic vent joints shall be installed")
    assert captured["request"].filters.document_id == result.document_id
    assert captured["request"].limit == 4
    assert captured["request"].harness_name is None
    assert captured["origin"] == "chat"
    assert response.harness_name == "wide_v2"
    assert response.reranker_name == "linear_feature_reranker"
    assert response.reranker_version == "v2"
    assert response.retrieval_profile_name == "wide_v2"
    assert response.search_request_id is not None
    assert response.chat_answer_id is not None


def test_answer_question_falls_back_without_generator(monkeypatch) -> None:
    class FakeExecution:
        def __init__(self) -> None:
            self.results = [_chunk_result()]
            self.request_id = uuid4()
            self.harness_name = "default_v1"
            self.reranker_name = "linear_feature_reranker"
            self.reranker_version = "v1"
            self.retrieval_profile_name = "default_v1"

    monkeypatch.setattr(
        "app.services.chat.execute_search",
        lambda session, request, origin="api": FakeExecution(),
    )
    monkeypatch.setattr("app.services.chat.get_answer_generator", lambda: None)
    session = FakeSession()

    response = answer_question(
        session=session,
        request=ChatRequest(question="What does the corpus say about vent joints?"),
        answer_generator=None,
    )

    assert response.used_fallback is True
    assert (
        response.warning
        == "OpenAI is not configured, so the answer is extractive rather than generated."
    )
    assert "[1]" in response.answer
    assert response.harness_name == "default_v1"
    assert response.reranker_version == "v1"
    assert response.search_request_id is not None
    assert response.chat_answer_id is not None


def test_answer_question_falls_back_when_qualified_date_phrase_is_unsupported(
    monkeypatch,
) -> None:
    results = [_memo_date_result(), _due_date_result()]
    asked: list[str] = []

    class FakeExecution:
        def __init__(self) -> None:
            self.results = results
            self.request_id = uuid4()
            self.harness_name = "default_v1"
            self.reranker_name = "linear_feature_reranker"
            self.reranker_version = "v1"
            self.retrieval_profile_name = "default_v1"

    monkeypatch.setattr(
        "app.services.chat.execute_search",
        lambda session, request, origin="api", **kwargs: FakeExecution(),
    )

    class UnsupportedDateGenerator(AnswerGenerator):
        model = "fake-model"

        def generate_answer(self, *, question: str, contexts) -> str:
            asked.append(question)
            return "The opportunity screening memo announces a launch date of March 23, 2026 [1]."

    session = FakeSession()

    response = answer_question(
        session=session,
        request=ChatRequest(
            question="What launch date does the opportunity screening memo announce?",
            mode="hybrid",
            document_id=results[0].document_id,
            top_k=4,
        ),
        answer_generator=UnsupportedDateGenerator(),
    )

    assert response.used_fallback is True
    assert response.citations == []
    assert "launch date" in (response.warning or "")
    assert asked == []


def test_answer_question_allows_supported_qualified_date_phrase(
    monkeypatch,
) -> None:
    results = [_memo_date_result(), _due_date_result()]
    asked: list[str] = []

    class FakeExecution:
        def __init__(self) -> None:
            self.results = results
            self.request_id = uuid4()
            self.harness_name = "default_v1"
            self.reranker_name = "linear_feature_reranker"
            self.reranker_version = "v1"
            self.retrieval_profile_name = "default_v1"

    monkeypatch.setattr(
        "app.services.chat.execute_search",
        lambda session, request, origin="api", **kwargs: FakeExecution(),
    )

    class SupportedDateGenerator(AnswerGenerator):
        model = "fake-model"

        def generate_answer(self, *, question: str, contexts) -> str:
            asked.append(question)
            return "The due date is April 9, 2026 [2]."

    session = FakeSession()

    response = answer_question(
        session=session,
        request=ChatRequest(
            question="What is the due date in the opportunity screening memo?",
            mode="hybrid",
            document_id=results[0].document_id,
            top_k=4,
        ),
        answer_generator=SupportedDateGenerator(),
    )

    assert response.used_fallback is False
    assert asked == ["What is the due date in the opportunity screening memo?"]


def test_openai_answer_generator_configures_timeout_and_retries(monkeypatch) -> None:
    captured = {}

    def fake_openai(*, api_key: str, timeout: float, max_retries: int):
        captured["api_key"] = api_key
        captured["timeout"] = timeout
        captured["max_retries"] = max_retries
        return SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: None))
        )

    monkeypatch.setattr("app.services.chat.OpenAI", fake_openai)

    OpenAIAnswerGenerator(
        api_key="chat-key",
        model="gpt-4.1-mini",
        timeout_seconds=9.0,
        max_retries=3,
    )

    assert captured == {
        "api_key": "chat-key",
        "timeout": 9.0,
        "max_retries": 3,
    }


def test_answer_question_retries_with_normalized_query_when_initial_search_misses(
    monkeypatch,
) -> None:
    result = _chunk_result()
    queries: list[str] = []

    class FakeExecution:
        def __init__(self, results, request_id):
            self.results = results
            self.request_id = request_id
            self.harness_name = "default_v1"
            self.reranker_name = "linear_feature_reranker"
            self.reranker_version = "v1"
            self.retrieval_profile_name = "default_v1"

    def fake_execute_search(session, request, origin="api", parent_request_id=None):
        queries.append(request.query)
        if len(queries) == 1:
            return FakeExecution([], uuid4())
        return FakeExecution([result], uuid4())

    monkeypatch.setattr("app.services.chat.execute_search", fake_execute_search)
    generator = FakeAnswerGenerator()
    session = FakeSession()

    response = answer_question(
        session=session,
        request=ChatRequest(
            question="What is the main claim of The Bitter Lesson?",
            mode="keyword",
            document_id=result.document_id,
            top_k=4,
        ),
        answer_generator=generator,
    )

    assert len(queries) == 2
    assert queries[0] == "What is the main claim of The Bitter Lesson?"
    assert queries[1] == "claim bitter lesson"
    assert response.used_fallback is False
    assert response.chat_answer_id is not None


def test_answer_question_can_skip_persistence_for_evaluations(monkeypatch) -> None:
    result = _chunk_result()
    captured = {}
    evaluation_id = uuid4()

    class FakeExecution:
        def __init__(self) -> None:
            self.results = [result]
            self.request_id = uuid4()
            self.harness_name = "default_v1"
            self.reranker_name = "linear_feature_reranker"
            self.reranker_version = "v1"
            self.retrieval_profile_name = "default_v1"

    def fake_execute_search(
        session,
        request,
        origin="api",
        run_id=None,
        evaluation_id=None,
        parent_request_id=None,
    ):
        captured["origin"] = origin
        captured["run_id"] = run_id
        captured["evaluation_id"] = evaluation_id
        captured["parent_request_id"] = parent_request_id
        return FakeExecution()

    monkeypatch.setattr("app.services.chat.execute_search", fake_execute_search)
    generator = FakeAnswerGenerator()
    session = FakeSession()

    response = answer_question(
        session=session,
        request=ChatRequest(
            question="What is the main claim of The Bitter Lesson?",
            mode="hybrid",
            document_id=result.document_id,
            top_k=4,
        ),
        answer_generator=generator,
        run_id=result.run_id,
        origin="evaluation_answer_candidate",
        evaluation_id=evaluation_id,
        persist=False,
    )

    assert response.used_fallback is False
    assert response.chat_answer_id is None
    assert len(session.added) == 0
    assert captured["origin"] == "evaluation_answer_candidate"
    assert captured["run_id"] == result.run_id
    assert captured["evaluation_id"] == evaluation_id


def test_answer_question_retries_with_chunk_only_context_when_tables_dominate(
    monkeypatch,
) -> None:
    table_result = SearchResult(
        result_type="table",
        document_id=uuid4(),
        run_id=uuid4(),
        score=6.7,
        table_id=uuid4(),
        table_title="TABLE 510.1.2",
        table_heading="510.1.2 Elbows",
        table_preview="preview",
        row_count=10,
        col_count=3,
        page_from=10,
        page_to=11,
        source_filename="UPC_CH_5.pdf",
        scores=SearchScores(keyword_score=6.7, semantic_score=None, hybrid_score=None),
    )
    chunk_result = _chunk_result()
    calls: list[tuple[str | None, str]] = []

    class FakeExecution:
        def __init__(self, results, request_id):
            self.results = results
            self.request_id = request_id
            self.harness_name = "wide_v2"
            self.reranker_name = "linear_feature_reranker"
            self.reranker_version = "v2"
            self.retrieval_profile_name = "wide_v2"

    def fake_execute_search(
        session,
        request,
        origin="api",
        run_id=None,
        evaluation_id=None,
        parent_request_id=None,
    ):
        result_type = request.filters.result_type if request.filters else None
        calls.append((result_type, request.query))
        if result_type == "chunk":
            return FakeExecution([chunk_result], uuid4())
        return FakeExecution([table_result], uuid4())

    monkeypatch.setattr("app.services.chat.execute_search", fake_execute_search)
    generator = FakeAnswerGenerator()
    session = FakeSession()

    response = answer_question(
        session=session,
        request=ChatRequest(
            question="What does the corpus say about vent stacks?",
            mode="keyword",
            top_k=4,
            harness_name="wide_v2",
        ),
        answer_generator=generator,
    )

    assert calls == [
        (None, "What does the corpus say about vent stacks?"),
        ("chunk", "What does the corpus say about vent stacks?"),
    ]
    assert response.used_fallback is False
    assert response.citations[0].result_type == "chunk"
    assert response.chat_answer_id is not None
