from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: str = Field(default="hybrid", pattern="^(keyword|semantic|hybrid)$")
    document_id: UUID | None = None
    top_k: int = Field(default=6, ge=1, le=12)


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
    model: str | None = None
    used_fallback: bool = False
    warning: str | None = None
