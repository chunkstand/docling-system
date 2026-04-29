from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import (
    require_api_capability,
    require_api_key_for_mutations,
    response_field,
)
from app.api.errors import api_error
from app.api.routers.search_route_services import resolve_search_service
from app.db.session import get_db_session
from app.schemas.search import (
    SearchReplayComparisonResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunRequest,
    SearchReplayRunSummaryResponse,
)
from app.services.capabilities import retrieval

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]

list_search_replay_runs = retrieval.list_search_replay_runs
run_search_replay_suite = retrieval.run_search_replay_suite
compare_search_replay_runs = retrieval.compare_search_replay_runs
get_search_replay_run_detail = retrieval.get_search_replay_run_detail
explain_search_replay_run = retrieval.explain_search_replay_run


@router.get(
    "/search/replays",
    response_model=list[SearchReplayRunSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_REPLAY))],
)
def read_search_replays(
    session: DbSession,
) -> list[SearchReplayRunSummaryResponse]:
    return resolve_search_service("list_search_replay_runs", list_search_replay_runs)(session)


@router.post(
    "/search/replays",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_REPLAY)),
    ],
)
def create_search_replay_run(
    response: Response,
    payload: SearchReplayRunRequest,
    session: DbSession,
) -> SearchReplayRunDetailResponse:
    try:
        replay_run = resolve_search_service(
            "run_search_replay_suite",
            run_search_replay_suite,
        )(session, payload)
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
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_REPLAY))],
)
def read_search_replay_comparison(
    baseline_replay_run_id: UUID,
    candidate_replay_run_id: UUID,
    session: DbSession,
) -> SearchReplayComparisonResponse:
    return resolve_search_service(
        "compare_search_replay_runs",
        compare_search_replay_runs,
    )(
        session,
        baseline_replay_run_id=baseline_replay_run_id,
        candidate_replay_run_id=candidate_replay_run_id,
    )


@router.get(
    "/search/replays/{replay_run_id}",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_REPLAY))],
)
def read_search_replay_run(
    replay_run_id: UUID,
    session: DbSession,
) -> SearchReplayRunDetailResponse:
    return resolve_search_service(
        "get_search_replay_run_detail",
        get_search_replay_run_detail,
    )(session, replay_run_id)


@router.get(
    "/search/replays/{replay_run_id}/explain",
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_REPLAY))],
)
def explain_search_replay_run_route(
    replay_run_id: UUID,
    session: DbSession,
) -> dict:
    return resolve_search_service("explain_search_replay_run", explain_search_replay_run)(
        session,
        replay_run_id,
    )


__all__ = ["router"]
