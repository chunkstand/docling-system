from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.agent_task_core import (
    AgentTaskCreateRequest,
    AgentTaskDetailResponse,
    AgentTaskOutcomeCreateRequest,
    AgentTaskOutcomeResponse,
    AgentTaskSummaryResponse,
)


class AgentOrchestrationLifecycleCapability(Protocol):
    def list_agent_tasks(
        self,
        session: Session,
        *,
        statuses: list[str] | None = None,
        limit: int = 50,
    ) -> list[AgentTaskSummaryResponse]: ...

    def create_agent_task(
        self,
        session: Session,
        payload: AgentTaskCreateRequest,
    ) -> AgentTaskDetailResponse: ...

    def get_agent_task_detail(self, session: Session, task_id: UUID) -> AgentTaskDetailResponse: ...

    def list_agent_task_outcomes(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskOutcomeResponse]: ...

    def create_agent_task_outcome(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskOutcomeCreateRequest,
    ) -> AgentTaskOutcomeResponse: ...
