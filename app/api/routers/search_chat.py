from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import require_api_capability, require_api_key_for_mutations
from app.api.errors import api_error
from app.api.routers.search_route_services import resolve_search_service
from app.db.session import get_db_session
from app.schemas.chat import (
    ChatAnswerFeedbackCreateRequest,
    ChatAnswerFeedbackResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.capabilities import retrieval

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]

answer_question = retrieval.answer_question
record_chat_answer_feedback = retrieval.record_chat_answer_feedback


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.CHAT_QUERY)),
    ],
)
def chat_with_corpus(
    request: ChatRequest,
    session: DbSession,
) -> ChatResponse:
    try:
        response = resolve_search_service("answer_question", answer_question)(
            session,
            request,
        )
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_chat_request",
            str(exc),
        ) from exc
    session.commit()
    return response


@router.post(
    "/chat/answers/{chat_answer_id}/feedback",
    response_model=ChatAnswerFeedbackResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.CHAT_FEEDBACK)),
    ],
)
def create_chat_answer_feedback(
    chat_answer_id: UUID,
    payload: ChatAnswerFeedbackCreateRequest,
    session: DbSession,
) -> ChatAnswerFeedbackResponse:
    response = resolve_search_service(
        "record_chat_answer_feedback",
        record_chat_answer_feedback,
    )(session, chat_answer_id, payload)
    session.commit()
    return response


__all__ = ["router"]
