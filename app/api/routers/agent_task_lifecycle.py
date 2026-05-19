from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import (
    require_api_capability,
    require_api_key_for_mutations,
    response_field,
)
from app.api.errors import api_error
from app.api.routers.agent_task_route_services import service_from_parent
from app.db.session import get_db_session
from app.schemas.agent_task_core import (
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskDetailResponse,
    AgentTaskOutcomeCreateRequest,
    AgentTaskOutcomeResponse,
    AgentTaskRejectionRequest,
    AgentTaskSummaryResponse,
    AgentTaskVerificationResponse,
)
from app.services.capabilities import agent_orchestration

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
TaskStatusQuery = Annotated[list[str] | None, Query(alias="status")]

list_agent_tasks = agent_orchestration.list_agent_tasks
create_agent_task = agent_orchestration.create_agent_task
get_agent_task_detail = agent_orchestration.get_agent_task_detail
list_agent_task_outcomes = agent_orchestration.list_agent_task_outcomes
create_agent_task_outcome = agent_orchestration.create_agent_task_outcome
get_agent_task_verifications = agent_orchestration.get_agent_task_verifications
approve_agent_task = agent_orchestration.approve_agent_task
reject_agent_task = agent_orchestration.reject_agent_task


@router.get(
    "/agent-tasks",
    response_model=list[AgentTaskSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_tasks(
    session: DbSession,
    task_status: TaskStatusQuery = None,
    limit: int = 50,
) -> list[AgentTaskSummaryResponse]:
    return service_from_parent("list_agent_tasks", list_agent_tasks)(
        session,
        statuses=task_status,
        limit=limit,
    )


@router.post(
    "/agent-tasks",
    response_model=AgentTaskDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def create_agent_task_route(
    response: Response,
    payload: AgentTaskCreateRequest,
    session: DbSession,
) -> AgentTaskDetailResponse:
    try:
        task_response = service_from_parent("create_agent_task", create_agent_task)(
            session,
            payload,
        )
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_agent_task_request",
            str(exc),
        ) from exc
    task_id = response_field(task_response, "task_id")
    if task_id is not None:
        response.headers["Location"] = f"/agent-tasks/{task_id}"
    return task_response


@router.get(
    "/agent-tasks/{task_id}",
    response_model=AgentTaskDetailResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_detail_route(
    task_id: UUID,
    session: DbSession,
) -> AgentTaskDetailResponse:
    return service_from_parent("get_agent_task_detail", get_agent_task_detail)(
        session,
        task_id,
    )


@router.get(
    "/agent-tasks/{task_id}/outcomes",
    response_model=list[AgentTaskOutcomeResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_outcomes(
    task_id: UUID,
    session: DbSession,
    limit: int = 20,
) -> list[AgentTaskOutcomeResponse]:
    return service_from_parent("list_agent_task_outcomes", list_agent_task_outcomes)(
        session,
        task_id,
        limit=limit,
    )


@router.post(
    "/agent-tasks/{task_id}/outcomes",
    response_model=AgentTaskOutcomeResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def create_agent_task_outcome_route(
    task_id: UUID,
    payload: AgentTaskOutcomeCreateRequest,
    session: DbSession,
) -> AgentTaskOutcomeResponse:
    return service_from_parent("create_agent_task_outcome", create_agent_task_outcome)(
        session,
        task_id,
        payload,
    )


@router.get(
    "/agent-tasks/{task_id}/verifications",
    response_model=list[AgentTaskVerificationResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_agent_task_verifications_route(
    task_id: UUID,
    session: DbSession,
    limit: int = 20,
) -> list[AgentTaskVerificationResponse]:
    return service_from_parent("get_agent_task_verifications", get_agent_task_verifications)(
        session,
        task_id,
        limit=limit,
    )


@router.post(
    "/agent-tasks/{task_id}/approve",
    response_model=AgentTaskDetailResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def approve_agent_task_route(
    task_id: UUID,
    payload: AgentTaskApprovalRequest,
    session: DbSession,
) -> AgentTaskDetailResponse:
    return service_from_parent("approve_agent_task", approve_agent_task)(
        session,
        task_id,
        payload,
    )


@router.post(
    "/agent-tasks/{task_id}/reject",
    response_model=AgentTaskDetailResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def reject_agent_task_route(
    task_id: UUID,
    payload: AgentTaskRejectionRequest,
    session: DbSession,
) -> AgentTaskDetailResponse:
    return service_from_parent("reject_agent_task", reject_agent_task)(
        session,
        task_id,
        payload,
    )
