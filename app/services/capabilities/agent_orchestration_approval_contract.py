from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.agent_tasks import (
    AgentTaskApprovalRequest,
    AgentTaskDetailResponse,
    AgentTaskRejectionRequest,
    AgentTaskVerificationResponse,
)


class AgentOrchestrationApprovalCapability(Protocol):
    def get_agent_task_verifications(
        self,
        session: Session,
        task_id: UUID,
        *,
        limit: int = 20,
    ) -> list[AgentTaskVerificationResponse]: ...

    def approve_agent_task(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskApprovalRequest,
    ) -> AgentTaskDetailResponse: ...

    def reject_agent_task(
        self,
        session: Session,
        task_id: UUID,
        payload: AgentTaskRejectionRequest,
    ) -> AgentTaskDetailResponse: ...
