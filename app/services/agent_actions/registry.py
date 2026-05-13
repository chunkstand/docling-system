from __future__ import annotations

from collections.abc import Mapping

from app.services.agent_actions.types import AgentTaskActionDefinition


def compose_action_registries(
    *registries: Mapping[str, AgentTaskActionDefinition],
) -> dict[str, AgentTaskActionDefinition]:
    composed: dict[str, AgentTaskActionDefinition] = {}
    seen_task_types: set[str] = set()
    for registry in registries:
        for registry_key, action in registry.items():
            if registry_key != action.task_type:
                raise ValueError(
                    "agent action registry key "
                    f"'{registry_key}' must match task_type '{action.task_type}'"
                )
            if registry_key in composed:
                raise ValueError(f"duplicate agent action registry key '{registry_key}'")
            if action.task_type in seen_task_types:
                raise ValueError(f"duplicate agent action task_type '{action.task_type}'")
            composed[registry_key] = action
            seen_task_types.add(action.task_type)
    return composed
