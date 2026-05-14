from __future__ import annotations

from typing import Any as _Any

from app.schemas import agent_task_claim_support as _agent_task_claim_support
from app.schemas import agent_task_core as _agent_task_core
from app.schemas import agent_task_reports as _agent_task_reports
from app.schemas import agent_task_search_workflows as _agent_task_search_workflows
from app.schemas import agent_task_semantic_generation as _agent_task_semantic_generation
from app.schemas import agent_task_semantic_graph as _agent_task_semantic_graph
from app.schemas import agent_task_semantics as _agent_task_semantics

_OWNER_MODULES: tuple[object, ...] = (
    _agent_task_core,
    _agent_task_claim_support,
    _agent_task_reports,
    _agent_task_search_workflows,
    _agent_task_semantic_generation,
    _agent_task_semantic_graph,
    _agent_task_semantics,
)
_EXPORT_REGISTRY = {
    name: module for module in _OWNER_MODULES for name in getattr(module, "__all__", ())
}
__all__ = sorted(_EXPORT_REGISTRY)


def __getattr__(name: str) -> _Any:
    module = _EXPORT_REGISTRY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
