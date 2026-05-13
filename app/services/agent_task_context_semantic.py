from __future__ import annotations

from collections.abc import Mapping

from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    compose_context_builder_registries,
)
from app.services.agent_task_context_semantic_analysis import (
    build_semantic_analysis_context_builders,
)
from app.services.agent_task_context_semantic_drafting import (
    build_semantic_drafting_context_builders,
)
from app.services.agent_task_context_semantic_verification import (
    build_semantic_verification_context_builders,
)


def build_semantic_context_builders(
    available_symbols: Mapping[str, object] | None = None,
) -> dict[str, AgentTaskContextBuilder]:
    return compose_context_builder_registries(
        build_semantic_analysis_context_builders(available_symbols),
        build_semantic_drafting_context_builders(available_symbols),
        build_semantic_verification_context_builders(available_symbols),
    )
