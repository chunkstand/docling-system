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
    SearchHarnessDescriptorResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSummaryResponse,
    SearchHarnessResponse,
    SearchReplayComparisonResponse,
    SearchReplayResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunRequest,
    SearchReplayRunSummaryResponse,
    SearchRequest,
    SearchRequestDetailResponse,
    SearchRequestExplanationResponse,
)
from app.services import (
    chat,
    eval_workbench,
    search,
    search_harness_evaluations,
    search_history,
    search_legibility,
    search_replays,
)


class RetrievalCapability(Protocol):
    def execute_search(
        self,
        session: Session,
        request: SearchRequest,
        *,
        origin: str,
        run_id: UUID | None = None,
        parent_search_request_id: UUID | None = None,
        evaluation_id: UUID | None = None,
    ) -> search.SearchExecution: ...

    def get_search_request_detail(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestDetailResponse: ...

    def get_search_request_explanation(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestExplanationResponse: ...

    def record_search_feedback(
        self,
        session: Session,
        search_request_id: UUID,
        payload: SearchFeedbackCreateRequest,
    ) -> SearchFeedbackResponse: ...

    def replay_search_request(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchReplayResponse: ...

    def list_search_replay_runs(
        self,
        session: Session,
    ) -> list[SearchReplayRunSummaryResponse]: ...

    def run_search_replay_suite(
        self,
        session: Session,
        payload: SearchReplayRunRequest,
    ) -> SearchReplayRunDetailResponse: ...

    def compare_search_replay_runs(
        self,
        session: Session,
        *,
        baseline_replay_run_id: UUID,
        candidate_replay_run_id: UUID,
    ) -> SearchReplayComparisonResponse: ...

    def get_search_replay_run_detail(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> SearchReplayRunDetailResponse: ...

    def explain_search_replay_run(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> dict: ...

    def list_search_harness_definitions(self) -> list[SearchHarnessResponse]: ...

    def get_search_harness_descriptor(
        self,
        harness_name: str,
    ) -> SearchHarnessDescriptorResponse: ...

    def list_search_harness_evaluations(
        self,
        session: Session,
        *,
        limit: int,
        candidate_harness_name: str | None = None,
    ) -> list[SearchHarnessEvaluationSummaryResponse]: ...

    def evaluate_search_harness(
        self,
        session: Session,
        payload: SearchHarnessEvaluationRequest,
    ) -> SearchHarnessEvaluationResponse: ...

    def get_search_harness_evaluation_detail(
        self,
        session: Session,
        evaluation_id: UUID,
    ) -> SearchHarnessEvaluationResponse: ...

    def answer_question(self, session: Session, request: ChatRequest) -> ChatResponse: ...

    def record_chat_answer_feedback(
        self,
        session: Session,
        chat_answer_id: UUID,
        payload: ChatAnswerFeedbackCreateRequest,
    ) -> ChatAnswerFeedbackResponse: ...


class ServicesRetrievalCapability:
    def execute_search(
        self,
        session: Session,
        request: SearchRequest,
        *,
        origin: str,
        run_id: UUID | None = None,
        parent_search_request_id: UUID | None = None,
        evaluation_id: UUID | None = None,
    ) -> search.SearchExecution:
        return search.execute_search(
            session,
            request,
            origin=origin,
            run_id=run_id,
            parent_request_id=parent_search_request_id,
            evaluation_id=evaluation_id,
        )

    def get_search_request_detail(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestDetailResponse:
        return search_history.get_search_request_detail(session, search_request_id)

    def get_search_request_explanation(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestExplanationResponse:
        return search_legibility.get_search_request_explanation(session, search_request_id)

    def record_search_feedback(
        self,
        session: Session,
        search_request_id: UUID,
        payload: SearchFeedbackCreateRequest,
    ) -> SearchFeedbackResponse:
        return search_history.record_search_feedback(session, search_request_id, payload)

    def replay_search_request(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchReplayResponse:
        return search_history.replay_search_request(session, search_request_id)

    def list_search_replay_runs(
        self,
        session: Session,
    ) -> list[SearchReplayRunSummaryResponse]:
        return search_replays.list_search_replay_runs(session)

    def run_search_replay_suite(
        self,
        session: Session,
        payload: SearchReplayRunRequest,
    ) -> SearchReplayRunDetailResponse:
        return search_replays.run_search_replay_suite(session, payload)

    def compare_search_replay_runs(
        self,
        session: Session,
        *,
        baseline_replay_run_id: UUID,
        candidate_replay_run_id: UUID,
    ) -> SearchReplayComparisonResponse:
        return search_replays.compare_search_replay_runs(
            session,
            baseline_replay_run_id=baseline_replay_run_id,
            candidate_replay_run_id=candidate_replay_run_id,
        )

    def get_search_replay_run_detail(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> SearchReplayRunDetailResponse:
        return search_replays.get_search_replay_run_detail(session, replay_run_id)

    def explain_search_replay_run(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> dict:
        return eval_workbench.explain_search_replay_run(session, replay_run_id)

    def list_search_harness_definitions(self) -> list[SearchHarnessResponse]:
        return search_harness_evaluations.list_search_harness_definitions()

    def get_search_harness_descriptor(
        self,
        harness_name: str,
    ) -> SearchHarnessDescriptorResponse:
        return search_legibility.get_search_harness_descriptor(harness_name)

    def list_search_harness_evaluations(
        self,
        session: Session,
        *,
        limit: int,
        candidate_harness_name: str | None = None,
    ) -> list[SearchHarnessEvaluationSummaryResponse]:
        return search_harness_evaluations.list_search_harness_evaluations(
            session,
            limit=limit,
            candidate_harness_name=candidate_harness_name,
        )

    def evaluate_search_harness(
        self,
        session: Session,
        payload: SearchHarnessEvaluationRequest,
    ) -> SearchHarnessEvaluationResponse:
        return search_harness_evaluations.evaluate_search_harness(session, payload)

    def get_search_harness_evaluation_detail(
        self,
        session: Session,
        evaluation_id: UUID,
    ) -> SearchHarnessEvaluationResponse:
        return search_harness_evaluations.get_search_harness_evaluation_detail(
            session,
            evaluation_id,
        )

    def answer_question(self, session: Session, request: ChatRequest) -> ChatResponse:
        return chat.answer_question(session, request)

    def record_chat_answer_feedback(
        self,
        session: Session,
        chat_answer_id: UUID,
        payload: ChatAnswerFeedbackCreateRequest,
    ) -> ChatAnswerFeedbackResponse:
        return chat.record_chat_answer_feedback(session, chat_answer_id, payload)


retrieval: RetrievalCapability = ServicesRetrievalCapability()
