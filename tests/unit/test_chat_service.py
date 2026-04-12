from __future__ import annotations

from uuid import uuid4

from app.schemas.chat import ChatRequest
from app.schemas.search import SearchResult, SearchScores
from app.services.chat import AnswerGenerator, answer_question


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
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
