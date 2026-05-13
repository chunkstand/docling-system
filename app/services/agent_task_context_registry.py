from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from app.schemas.agent_tasks import TaskContextEnvelope

AgentTaskContextBuilder = Callable[..., TaskContextEnvelope]


def compose_context_builder_registries(
    *registries: Mapping[str, AgentTaskContextBuilder],
) -> dict[str, AgentTaskContextBuilder]:
    composed: dict[str, AgentTaskContextBuilder] = {}
    for registry in registries:
        for builder_name, builder in registry.items():
            if builder_name in composed:
                raise ValueError(f"duplicate agent task context builder '{builder_name}'")
            composed[builder_name] = builder
    return composed


def resolve_context_builder_registry(
    available_symbols: Mapping[str, object],
    *,
    builder_symbols: Mapping[str, str],
    registry_name: str,
) -> dict[str, AgentTaskContextBuilder]:
    missing = [
        f"{builder_name}->{symbol_name}"
        for builder_name, symbol_name in builder_symbols.items()
        if symbol_name not in available_symbols
    ]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(
            f"{registry_name} context builder registry references missing symbols: "
            f"{missing_text}"
        )
    return {
        builder_name: cast(AgentTaskContextBuilder, available_symbols[symbol_name])
        for builder_name, symbol_name in builder_symbols.items()
    }
