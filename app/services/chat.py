from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from uuid import UUID

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
from app.services.search import _is_tabular_query, execute_search

MAX_CONTEXT_EXCERPT_CHARS = 700
FALLBACK_CITATION_COUNT = 3
QUALIFIED_DATE_PHRASE_PATTERN = re.compile(
    r"\b([a-z][a-z0-9]*(?:\s+[a-z][a-z0-9]*){0,2}\s+date)\b",
    re.IGNORECASE,
)
QUESTION_STOPWORDS = {
    "a",
    "about",
    "an",
    "are",
    "as",
    "at",
    "by",
    "can",
    "corpus",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "main",
    "me",
    "of",
    "on",
    "say",
    "says",
    "should",
    "tell",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}

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
    excerpt = _collapse_whitespace(result.chunk_text)
    return (
        _collapse_whitespace(result.heading)
        or excerpt[:80].rstrip(" .,;:")
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


def _normalize_question_query(question: str) -> str | None:
    tokens = re.findall(r"[A-Za-z0-9]+", question.lower())
    filtered: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in QUESTION_STOPWORDS or token in seen:
            continue
        seen.add(token)
        filtered.append(token)
    if not filtered:
        return None
    normalized = " ".join(filtered)
    if normalized == question.strip().lower():
        return None
    return normalized


def _missing_qualified_date_phrases(
    question: str, citations: list[ChatCitation]
) -> list[str]:
    citation_text = " ".join(
        _collapse_whitespace(f"{citation.label} {citation.excerpt}").lower()
        for citation in citations
    )
    missing: list[str] = []
    seen: set[str] = set()
    for match in QUALIFIED_DATE_PHRASE_PATTERN.finditer(question):
        tokens = _collapse_whitespace(match.group(1)).lower().split()
        while len(tokens) > 2 and tokens[0] in QUESTION_STOPWORDS:
            tokens.pop(0)
        phrase = " ".join(tokens)
        if phrase in seen:
            continue
        seen.add(phrase)
        if phrase not in citation_text:
            missing.append(phrase)
    return missing


def _execute_chat_search(
    session: Session,
    request: SearchRequest,
    *,
    origin: str,
    run_id: UUID | None = None,
    evaluation_id: UUID | None = None,
    parent_request_id: UUID | None = None,
):
    kwargs = {"origin": origin}
    if run_id is not None:
        kwargs["run_id"] = run_id
    if evaluation_id is not None:
        kwargs["evaluation_id"] = evaluation_id
    if parent_request_id is not None:
        kwargs["parent_request_id"] = parent_request_id
    return execute_search(session, request, **kwargs)


def _all_table_citations(citations: list[ChatCitation]) -> bool:
    return bool(citations) and all(item.result_type == "table" for item in citations)


def _chunk_only_filters(document_id: UUID | None) -> SearchFilters:
    return SearchFilters(document_id=document_id, result_type="chunk")


def answer_question(
    session: Session,
    request: ChatRequest,
    *,
    answer_generator: AnswerGenerator | None = None,
    run_id: UUID | None = None,
    origin: str = "chat",
    evaluation_id: UUID | None = None,
    persist: bool = True,
) -> ChatResponse:
    filters = SearchFilters(document_id=request.document_id) if request.document_id else None
    search_request = SearchRequest(
        query=request.question,
        mode=request.mode,
        filters=filters,
        limit=request.top_k,
        harness_name=request.harness_name,
    )
    execution = _execute_chat_search(
        session,
        search_request,
        origin=origin,
        run_id=run_id,
        evaluation_id=evaluation_id,
    )
    citations = _build_citations(execution.results)

    if not citations:
        normalized_query = _normalize_question_query(request.question)
        if normalized_query:
            retry_request = SearchRequest(
                query=normalized_query,
                mode=request.mode,
                filters=filters,
                limit=request.top_k,
                harness_name=request.harness_name,
            )
            retry_execution = _execute_chat_search(
                session,
                retry_request,
                origin=origin,
                run_id=run_id,
                evaluation_id=evaluation_id,
                parent_request_id=execution.request_id,
            )
            retry_citations = _build_citations(retry_execution.results)
            if retry_citations:
                execution = retry_execution
                citations = retry_citations

    if citations and not _is_tabular_query(request.question) and _all_table_citations(citations):
        chunk_retry_request = SearchRequest(
            query=request.question,
            mode=request.mode,
            filters=_chunk_only_filters(request.document_id),
            limit=request.top_k,
            harness_name=request.harness_name,
        )
        chunk_retry_execution = _execute_chat_search(
            session,
            chunk_retry_request,
            origin=origin,
            run_id=run_id,
            evaluation_id=evaluation_id,
            parent_request_id=execution.request_id,
        )
        chunk_retry_citations = _build_citations(chunk_retry_execution.results)
        if chunk_retry_citations:
            execution = chunk_retry_execution
            citations = chunk_retry_citations

    missing_date_phrases = _missing_qualified_date_phrases(request.question, citations)
    if missing_date_phrases:
        response = ChatResponse(
            answer=_fallback_answer(request.question, []),
            citations=[],
            mode=request.mode,
            search_request_id=execution.request_id,
            harness_name=execution.harness_name,
            reranker_name=execution.reranker_name,
            reranker_version=execution.reranker_version,
            retrieval_profile_name=execution.retrieval_profile_name,
            used_fallback=True,
            warning=(
                "Retrieved context does not explicitly support the requested date attribute: "
                + ", ".join(missing_date_phrases)
            ),
        )
        if persist:
            return _persist_chat_answer(session, request=request, response=response)
        return response

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
        if persist:
            return _persist_chat_answer(session, request=request, response=response)
        return response

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
        if persist:
            return _persist_chat_answer(session, request=request, response=response)
        return response

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
        if persist:
            return _persist_chat_answer(session, request=request, response=response)
        return response

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
    if persist:
        return _persist_chat_answer(session, request=request, response=response)
    return response


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
