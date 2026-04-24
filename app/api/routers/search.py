from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    enforce_search_rate_limit,
    require_api_capability,
    require_api_key_for_mutations,
    response_field,
)
from app.api.errors import api_error
from app.db.session import get_db_session
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
    SearchResult,
)
from app.services.chat import answer_question, record_chat_answer_feedback
from app.services.eval_workbench import (
    explain_search_harness_evaluation,
    explain_search_replay_run,
)
from app.services.search import execute_search
from app.services.search_harness_evaluations import (
    evaluate_search_harness,
    get_search_harness_evaluation_detail,
    list_search_harness_definitions,
    list_search_harness_evaluations,
)
from app.services.search_history import (
    get_search_request_detail,
    record_search_feedback,
    replay_search_request,
)
from app.services.search_legibility import (
    get_search_harness_descriptor,
    get_search_request_explanation,
)
from app.services.search_replays import (
    compare_search_replay_runs,
    get_search_replay_run_detail,
    list_search_replay_runs,
    run_search_replay_suite,
)

router = APIRouter()


@router.post(
    "/search",
    response_model=list[SearchResult],
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("search:query")),
        Depends(enforce_search_rate_limit),
    ],
)
def search_corpus(
    request: SearchRequest,
    response: Response,
    session: Session = Depends(get_db_session),
) -> list[SearchResult]:
    try:
        execution = execute_search(session, request, origin="api")
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_request",
            str(exc),
        ) from exc
    session.commit()
    if execution.request_id is not None:
        response.headers["X-Search-Request-Id"] = str(execution.request_id)
    return execution.results


@router.post(
    "/search/executions",
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("search:query")),
        Depends(enforce_search_rate_limit),
    ],
)
def execute_search_with_explanation_ref(
    request: SearchRequest,
    response: Response,
    session: Session = Depends(get_db_session),
) -> dict:
    try:
        execution = execute_search(session, request, origin="api")
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_request",
            str(exc),
        ) from exc
    session.commit()
    search_request_id = str(execution.request_id) if execution.request_id is not None else None
    if search_request_id is not None:
        response.headers["X-Search-Request-Id"] = search_request_id
    return {
        "schema_name": "search_execution",
        "schema_version": "1.0",
        "search_request_id": search_request_id,
        "explanation_api_path": (
            f"/search/requests/{search_request_id}/explain"
            if search_request_id is not None
            else None
        ),
        "results": [row.model_dump(mode="json") for row in execution.results],
    }


@router.get(
    "/search/requests/{search_request_id}",
    response_model=SearchRequestDetailResponse,
    dependencies=[Depends(require_api_capability("search:history:read"))],
)
def read_search_request(
    search_request_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchRequestDetailResponse:
    return get_search_request_detail(session, search_request_id)


@router.get(
    "/search/requests/{search_request_id}/explain",
    response_model=SearchRequestExplanationResponse,
    dependencies=[Depends(require_api_capability("search:history:read"))],
)
def explain_search_request(
    search_request_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchRequestExplanationResponse:
    return get_search_request_explanation(session, search_request_id)


@router.post(
    "/search/requests/{search_request_id}/feedback",
    response_model=SearchFeedbackResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("search:feedback")),
    ],
)
def create_search_feedback(
    search_request_id: UUID,
    payload: SearchFeedbackCreateRequest,
    session: Session = Depends(get_db_session),
) -> SearchFeedbackResponse:
    feedback = record_search_feedback(session, search_request_id, payload)
    session.commit()
    return feedback


@router.post(
    "/search/requests/{search_request_id}/replay",
    response_model=SearchReplayResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("search:replay")),
    ],
)
def replay_logged_search(
    search_request_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchReplayResponse:
    replay = replay_search_request(session, search_request_id)
    session.commit()
    return replay


@router.get(
    "/search/replays",
    response_model=list[SearchReplayRunSummaryResponse],
    dependencies=[Depends(require_api_capability("search:replay"))],
)
def read_search_replays(
    session: Session = Depends(get_db_session),
) -> list[SearchReplayRunSummaryResponse]:
    return list_search_replay_runs(session)


@router.get(
    "/search/harnesses",
    response_model=list[SearchHarnessResponse],
    dependencies=[Depends(require_api_capability("search:evaluate"))],
)
def read_search_harnesses() -> list[SearchHarnessResponse]:
    return list_search_harness_definitions()


@router.get(
    "/search/harnesses/{harness_name}/descriptor",
    response_model=SearchHarnessDescriptorResponse,
    dependencies=[Depends(require_api_capability("search:evaluate"))],
)
def read_search_harness_descriptor(harness_name: str) -> SearchHarnessDescriptorResponse:
    try:
        return get_search_harness_descriptor(harness_name)
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_not_found",
            str(exc),
            harness_name=harness_name,
        ) from exc


@router.get(
    "/search/harness-evaluations",
    response_model=list[SearchHarnessEvaluationSummaryResponse],
    dependencies=[Depends(require_api_capability("search:evaluate"))],
)
def read_search_harness_evaluations(
    limit: int = Query(default=20, ge=1, le=200),
    candidate_harness_name: str | None = None,
    session: Session = Depends(get_db_session),
) -> list[SearchHarnessEvaluationSummaryResponse]:
    return list_search_harness_evaluations(
        session,
        limit=limit,
        candidate_harness_name=candidate_harness_name,
    )


@router.post(
    "/search/harness-evaluations",
    response_model=SearchHarnessEvaluationResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("search:evaluate")),
    ],
)
def create_search_harness_evaluation(
    response: Response,
    payload: SearchHarnessEvaluationRequest,
    session: Session = Depends(get_db_session),
) -> SearchHarnessEvaluationResponse:
    try:
        evaluation = evaluate_search_harness(session, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_harness_evaluation",
            str(exc),
        ) from exc
    session.commit()
    evaluation_id = response_field(evaluation, "evaluation_id")
    if evaluation_id is not None:
        response.headers["Location"] = f"/search/harness-evaluations/{evaluation_id}"
    return evaluation


@router.get(
    "/search/harness-evaluations/{evaluation_id}",
    response_model=SearchHarnessEvaluationResponse,
    dependencies=[Depends(require_api_capability("search:evaluate"))],
)
def read_search_harness_evaluation(
    evaluation_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchHarnessEvaluationResponse:
    return get_search_harness_evaluation_detail(session, evaluation_id)


@router.get(
    "/search/harness-evaluations/{evaluation_id}/explain",
    dependencies=[Depends(require_api_capability("search:evaluate"))],
)
def explain_search_harness_evaluation_route(
    evaluation_id: UUID,
    session: Session = Depends(get_db_session),
) -> dict:
    return explain_search_harness_evaluation(session, evaluation_id)


@router.post(
    "/search/replays",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("search:replay")),
    ],
)
def create_search_replay_run(
    response: Response,
    payload: SearchReplayRunRequest,
    session: Session = Depends(get_db_session),
) -> SearchReplayRunDetailResponse:
    try:
        replay_run = run_search_replay_suite(session, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_replay_request",
            str(exc),
        ) from exc
    session.commit()
    replay_run_id = response_field(replay_run, "replay_run_id")
    if replay_run_id is not None:
        response.headers["Location"] = f"/search/replays/{replay_run_id}"
    return replay_run


@router.get(
    "/search/replays/compare",
    response_model=SearchReplayComparisonResponse,
    dependencies=[Depends(require_api_capability("search:replay"))],
)
def read_search_replay_comparison(
    baseline_replay_run_id: UUID,
    candidate_replay_run_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchReplayComparisonResponse:
    return compare_search_replay_runs(
        session,
        baseline_replay_run_id=baseline_replay_run_id,
        candidate_replay_run_id=candidate_replay_run_id,
    )


@router.get(
    "/search/replays/{replay_run_id}",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[Depends(require_api_capability("search:replay"))],
)
def read_search_replay_run(
    replay_run_id: UUID,
    session: Session = Depends(get_db_session),
) -> SearchReplayRunDetailResponse:
    return get_search_replay_run_detail(session, replay_run_id)


@router.get(
    "/search/replays/{replay_run_id}/explain",
    dependencies=[Depends(require_api_capability("search:replay"))],
)
def explain_search_replay_run_route(
    replay_run_id: UUID,
    session: Session = Depends(get_db_session),
) -> dict:
    return explain_search_replay_run(session, replay_run_id)


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability("chat:query")),
    ],
)
def chat_with_corpus(
    request: ChatRequest,
    session: Session = Depends(get_db_session),
) -> ChatResponse:
    try:
        response = answer_question(session, request)
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
        Depends(require_api_capability("chat:feedback")),
    ],
)
def create_chat_answer_feedback(
    chat_answer_id: UUID,
    payload: ChatAnswerFeedbackCreateRequest,
    session: Session = Depends(get_db_session),
) -> ChatAnswerFeedbackResponse:
    response = record_chat_answer_feedback(session, chat_answer_id, payload)
    session.commit()
    return response
