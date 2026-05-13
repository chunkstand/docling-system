from __future__ import annotations

from app.services.agent_task_context import (
    get_agent_task_context_builder,
    list_agent_task_context_builder_names,
)
from app.services.agent_task_context_registry import (
    compose_context_builder_registries,
)
from app.services.agent_task_context_semantic import build_semantic_context_builders
from app.services.agent_task_context_semantic_analysis import (
    build_semantic_analysis_context_builders,
)
from app.services.agent_task_context_semantic_drafting import (
    build_semantic_drafting_context_builders,
)
from app.services.agent_task_context_semantic_verification import (
    build_semantic_verification_context_builders,
)


def test_semantic_context_builders_are_composed_from_owner_modules() -> None:
    owner_builders = compose_context_builder_registries(
        build_semantic_analysis_context_builders(),
        build_semantic_drafting_context_builders(),
        build_semantic_verification_context_builders(),
    )
    semantic_builders = build_semantic_context_builders()

    assert set(semantic_builders) == set(owner_builders)
    for builder_name, owner_builder in owner_builders.items():
        assert semantic_builders[builder_name] is owner_builder
        assert builder_name in list_agent_task_context_builder_names()
        assert get_agent_task_context_builder(builder_name) is owner_builder
