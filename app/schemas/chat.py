from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: str = Field(default="hybrid", pattern="^(keyword|semantic|hybrid)$")
    document_id: UUID | None = None
    top_k: int = Field(default=6, ge=1, le=12)
    harness_name: str | None = None


class ChatCitation(BaseModel):
    citation_index: int
    result_type: str
    document_id: UUID
    run_id: UUID
    source_filename: str
    page_from: int | None = None
    page_to: int | None = None
    label: str
    excerpt: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation]
    mode: str
    chat_answer_id: UUID | None = None
    search_request_id: UUID | None = None
    harness_name: str = "default_v1"
    reranker_name: str | None = None
    reranker_version: str | None = None
    retrieval_profile_name: str | None = None
    model: str | None = None
    used_fallback: bool = False
    warning: str | None = None


class ChatAnswerFeedbackCreateRequest(BaseModel):
    feedback_type: str = Field(pattern="^(helpful|unhelpful|unsupported|incomplete)$")
    note: str | None = None


class ChatAnswerFeedbackResponse(BaseModel):
    feedback_id: UUID
    chat_answer_id: UUID
    feedback_type: str
    note: str | None = None
    created_at: datetime
