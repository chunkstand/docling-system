from __future__ import annotations

from typing import Protocol

from app.services.capabilities.agent_orchestration_approval_contract import (
    AgentOrchestrationApprovalCapability,
)
from app.services.capabilities.agent_orchestration_context_artifact_contract import (
    AgentOrchestrationContextArtifactCapability,
)
from app.services.capabilities.agent_orchestration_lifecycle_contract import (
    AgentOrchestrationLifecycleCapability,
)


class AgentOrchestrationTaskCapability(
    AgentOrchestrationLifecycleCapability,
    AgentOrchestrationContextArtifactCapability,
    AgentOrchestrationApprovalCapability,
    Protocol,
):
    pass
