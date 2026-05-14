from __future__ import annotations

from typing import Protocol

from app.schemas.agent_task_core import AgentTaskActionDefinitionResponse


class AgentOrchestrationActionsCapability(Protocol):
    def list_agent_task_action_definitions(self) -> list[AgentTaskActionDefinitionResponse]: ...

    def run_worker_loop(self) -> None: ...
