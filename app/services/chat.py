from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import HTTPException, status
from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import ChatAnswerFeedback, ChatAnswerRecord
from app.schemas.chat import (
    ChatAnswerFeedbackCreateRequest,
    ChatAnswerFeedbackResponse,
    ChatCitation,
    ChatRequest,
    ChatResponse,
)
from app.schemas.search import SearchFilters, SearchRequest, SearchResult
from app.services.search import execute_search

MAX_CONTEXT_EXCERPT_CHARS = 700
FALLBACK_CITATION_COUNT = 3

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _page_label(page_from: int | None, page_to: int | None) -> str:
    if page_from is None and page_to is None:
        return "unknown pages"
    if page_from == page_to or page_to is None:
        return f"page {page_from}"
    if page_from is None:
        return f"page {page_to}"
    return f"pages {page_from}-{page_to}"


def _collapse_whitespace(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _result_label(result: SearchResult) -> str:
    if result.result_type == "table":
        return (
            _collapse_whitespace(result.table_title)
            or _collapse_whitespace(result.table_heading)
            or f"Table on {_page_label(result.page_from, result.page_to)}"
        )
    return (
        _collapse_whitespace(result.heading)
        or f"Chunk on {_page_label(result.page_from, result.page_to)}"
    )


def _result_excerpt(result: SearchResult) -> str:
    source_text = result.table_preview if result.result_type == "table" else result.chunk_text
    excerpt = _collapse_whitespace(source_text)
    if len(excerpt) <= MAX_CONTEXT_EXCERPT_CHARS:
        return excerpt
    return f"{excerpt[: MAX_CONTEXT_EXCERPT_CHARS - 3].rstrip()}..."


@dataclass
class AnswerContext:
    citation_index: int
    citation: ChatCitation


class AnswerGenerator:
    model: str | None = None

    def generate_answer(self, *, question: str, contexts: list[AnswerContext]) -> str:
        raise NotImplementedError


class OpenAIAnswerGenerator(AnswerGenerator):
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_answer(self, *, question: str, contexts: list[AnswerContext]) -> str:
        context_blocks = []
        for item in contexts:
            citation = item.citation
            context_blocks.append(
                "\n".join(
                    [
                        f"[{item.citation_index}] {citation.label}",
                        f"Source: {citation.source_filename}",
                        f"Location: {_page_label(citation.page_from, citation.page_to)}",
                        f"Type: {citation.result_type}",
                        f"Excerpt: {citation.excerpt}",
                    ]
                )
            )

        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            max_completion_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer questions using only the supplied corpus context. "
                        "Cite supporting snippets inline with bracketed references like [1]. "
                        "If the context is insufficient, say so clearly and do not guess."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        "Retrieved context:\n"
                        f"{'\n\n'.join(context_blocks)}"
                    ),
                },
            ],
        )
        message = completion.choices[0].message.content or ""
        return message.strip()


@lru_cache(maxsize=1)
def get_answer_generator() -> AnswerGenerator | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAIAnswerGenerator(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
    )


def _build_citations(results: list[SearchResult]) -> list[ChatCitation]:
    citations: list[ChatCitation] = []
    for index, result in enumerate(results, start=1):
        citations.append(
            ChatCitation(
                citation_index=index,
                result_type=result.result_type,
                document_id=result.document_id,
                run_id=result.run_id,
                source_filename=result.source_filename,
                page_from=result.page_from,
                page_to=result.page_to,
                label=_result_label(result),
                excerpt=_result_excerpt(result),
                score=result.score,
            )
        )
    return citations


def _fallback_answer(question: str, citations: list[ChatCitation]) -> str:
    if not citations:
        return "I couldn't find relevant support for that question in the ingested corpus."

    lines = [
        (
            "I found relevant material in the ingested corpus, but I couldn't produce "
            "a model-backed synthesis."
        ),
        "Start with these retrieved passages:",
    ]
    for citation in citations[:FALLBACK_CITATION_COUNT]:
        lines.append(
            f"[{citation.citation_index}] {citation.label} "
            f"({citation.source_filename}, {_page_label(citation.page_from, citation.page_to)}): "
            f"{citation.excerpt}"
        )
    return "\n".join(lines)


def answer_question(
    session: Session,
    request: ChatRequest,
    *,
    answer_generator: AnswerGenerator | None = None,
) -> ChatResponse:
    filters = SearchFilters(document_id=request.document_id) if request.document_id else None
    search_request = SearchRequest(
        query=request.question,
        mode=request.mode,
        filters=filters,
        limit=request.top_k,
        harness_name=request.harness_name,
    )
    execution = execute_search(session, search_request, origin="chat")
    citations = _build_citations(execution.results)

    if not citations:
        response = ChatResponse(
            answer=_fallback_answer(request.question, citations),
            citations=[],
            mode=request.mode,
            search_request_id=execution.request_id,
            harness_name=execution.harness_name,
            reranker_name=execution.reranker_name,
            reranker_version=execution.reranker_version,
            retrieval_profile_name=execution.retrieval_profile_name,
            used_fallback=True,
        )
        return _persist_chat_answer(session, request=request, response=response)

    generator = answer_generator if answer_generator is not None else get_answer_generator()
    if generator is None:
        response = ChatResponse(
            answer=_fallback_answer(request.question, citations),
            citations=citations,
            mode=request.mode,
            search_request_id=execution.request_id,
            harness_name=execution.harness_name,
            reranker_name=execution.reranker_name,
            reranker_version=execution.reranker_version,
            retrieval_profile_name=execution.retrieval_profile_name,
            used_fallback=True,
            warning="OpenAI is not configured, so the answer is extractive rather than generated.",
        )
        return _persist_chat_answer(session, request=request, response=response)

    contexts = [
        AnswerContext(citation_index=item.citation_index, citation=item)
        for item in citations
    ]
    try:
        answer = generator.generate_answer(question=request.question, contexts=contexts)
    except Exception as exc:
        logger.warning("chat_answer_generation_failed", error=str(exc))
        response = ChatResponse(
            answer=_fallback_answer(request.question, citations),
            citations=citations,
            mode=request.mode,
            search_request_id=execution.request_id,
            harness_name=execution.harness_name,
            reranker_name=execution.reranker_name,
            reranker_version=execution.reranker_version,
            retrieval_profile_name=execution.retrieval_profile_name,
            model=generator.model,
            used_fallback=True,
            warning=(
                "Model-backed answering failed, so the UI is showing retrieved evidence instead."
            ),
        )
        return _persist_chat_answer(session, request=request, response=response)

    response = ChatResponse(
        answer=answer or _fallback_answer(request.question, citations),
        citations=citations,
        mode=request.mode,
        search_request_id=execution.request_id,
        harness_name=execution.harness_name,
        reranker_name=execution.reranker_name,
        reranker_version=execution.reranker_version,
        retrieval_profile_name=execution.retrieval_profile_name,
        model=generator.model,
        used_fallback=False,
    )
    return _persist_chat_answer(session, request=request, response=response)


def _persist_chat_answer(
    session: Session,
    *,
    request: ChatRequest,
    response: ChatResponse,
) -> ChatResponse:
    answer_row = ChatAnswerRecord(
        id=uuid.uuid4(),
        search_request_id=response.search_request_id,
        document_id=request.document_id,
        question_text=request.question,
        mode=request.mode,
        answer_text=response.answer,
        model=response.model,
        used_fallback=response.used_fallback,
        warning=response.warning,
        citations_json=[citation.model_dump(mode="json") for citation in response.citations],
        harness_name=response.harness_name,
        reranker_name=response.reranker_name or "unknown",
        reranker_version=response.reranker_version or "unknown",
        retrieval_profile_name=response.retrieval_profile_name or "unknown",
        created_at=_utcnow(),
    )
    session.add(answer_row)
    session.flush()
    return response.model_copy(update={"chat_answer_id": answer_row.id})


def _answer_not_found(chat_answer_id) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Chat answer not found: {chat_answer_id}",
    )


def record_chat_answer_feedback(
    session: Session,
    chat_answer_id,
    payload: ChatAnswerFeedbackCreateRequest,
) -> ChatAnswerFeedbackResponse:
    answer_row = session.get(ChatAnswerRecord, chat_answer_id)
    if answer_row is None:
        raise _answer_not_found(chat_answer_id)

    feedback = ChatAnswerFeedback(
        id=uuid.uuid4(),
        chat_answer_id=answer_row.id,
        feedback_type=payload.feedback_type,
        note=payload.note,
        created_at=_utcnow(),
    )
    session.add(feedback)
    session.flush()
    return ChatAnswerFeedbackResponse(
        feedback_id=feedback.id,
        chat_answer_id=feedback.chat_answer_id,
        feedback_type=feedback.feedback_type,
        note=feedback.note,
        created_at=feedback.created_at,
    )
