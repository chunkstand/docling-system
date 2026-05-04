from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.chat import (
    ChatAnswerFeedbackCreateRequest,
    ChatAnswerFeedbackResponse,
    ChatRequest,
    ChatResponse,
)
from app.schemas.search import (
    SearchFeedbackCreateRequest,
    SearchFeedbackResponse,
)


class RetrievalChatFeedbackCapability(Protocol):
    def record_search_feedback(
        self,
        session: Session,
        search_request_id: UUID,
        payload: SearchFeedbackCreateRequest,
    ) -> SearchFeedbackResponse: ...

    def answer_question(self, session: Session, request: ChatRequest) -> ChatResponse: ...

    def record_chat_answer_feedback(
        self,
        session: Session,
        chat_answer_id: UUID,
        payload: ChatAnswerFeedbackCreateRequest,
    ) -> ChatAnswerFeedbackResponse: ...
