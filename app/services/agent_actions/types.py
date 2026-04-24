from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskSideEffectLevel

AgentTaskExecutor = Callable[[Session, AgentTask, BaseModel], dict]
AGENT_ACTION_CAPABILITIES = frozenset(
    {
        "document_lifecycle",
        "evaluation",
        "retrieval",
        "semantic_memory",
        "technical_reports",
    }
)
AGENT_ACTION_DEFINITION_KINDS = frozenset(
    {
        "action",
        "draft",
        "promotion",
        "verifier",
        "workflow",
    }
)
AGENT_ACTION_SIDE_EFFECT_LEVELS = frozenset(item.value for item in AgentTaskSideEffectLevel)
AGENT_ACTION_KIND_SIDE_EFFECT_LEVELS = {
    "action": AgentTaskSideEffectLevel.READ_ONLY.value,
    "draft": AgentTaskSideEffectLevel.DRAFT_CHANGE.value,
    "promotion": AgentTaskSideEffectLevel.PROMOTABLE.value,
    "verifier": AgentTaskSideEffectLevel.READ_ONLY.value,
    "workflow": AgentTaskSideEffectLevel.READ_ONLY.value,
}


@dataclass(frozen=True)
class AgentTaskActionDefinition:
    task_type: str
    definition_kind: str
    description: str
    payload_model: type[BaseModel]
    executor: AgentTaskExecutor
    side_effect_level: str = AgentTaskSideEffectLevel.READ_ONLY.value
    requires_approval: bool = False
    output_model: type[BaseModel] | None = None
    output_schema_name: str | None = None
    output_schema_version: str | None = None
    input_example: dict[str, Any] | None = None
    context_builder_name: str = "generic"
    capability: str = "uncategorized"
