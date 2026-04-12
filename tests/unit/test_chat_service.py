from __future__ import annotations

from uuid import uuid4

from app.schemas.chat import ChatRequest
from app.schemas.search import SearchResult, SearchScores
from app.services.chat import AnswerGenerator, answer_question


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

    def fake_search_documents(session, request):
        captured["request"] = request
        return [result]

    monkeypatch.setattr("app.services.chat.search_documents", fake_search_documents)
    generator = FakeAnswerGenerator()

    response = answer_question(
        session=None,
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


def test_answer_question_falls_back_without_generator(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.chat.search_documents",
        lambda session, request: [_chunk_result()],
    )
    monkeypatch.setattr("app.services.chat.get_answer_generator", lambda: None)

    response = answer_question(
        session=None,
        request=ChatRequest(question="What does the corpus say about vent joints?"),
        answer_generator=None,
    )

    assert response.used_fallback is True
    assert (
        response.warning
        == "OpenAI is not configured, so the answer is extractive rather than generated."
    )
    assert "[1]" in response.answer
