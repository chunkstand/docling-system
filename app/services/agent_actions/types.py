from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import AgentTask, AgentTaskSideEffectLevel

AgentTaskExecutor = Callable[[Session, AgentTask, BaseModel], dict]


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
