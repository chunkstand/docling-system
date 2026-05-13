from __future__ import annotations

from collections.abc import Mapping

from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    resolve_context_builder_registry,
)

CORE_CONTEXT_BUILDER_SYMBOLS = {
    "generic": "build_generic_task_context",
}


def build_core_context_builders(
    available_symbols: Mapping[str, object],
) -> dict[str, AgentTaskContextBuilder]:
    return resolve_context_builder_registry(
        available_symbols,
        builder_symbols=CORE_CONTEXT_BUILDER_SYMBOLS,
        registry_name="core",
    )
