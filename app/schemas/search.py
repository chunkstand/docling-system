from __future__ import annotations

from typing import Any as _Any

from app.schemas import search_core as _search_core
from app.schemas import search_explanations as _search_explanations
from app.schemas import search_harness as _search_harness
from app.schemas import search_history as _search_history
from app.schemas import search_learning as _search_learning
from app.schemas import search_replays as _search_replays

_OWNER_MODULES: tuple[object, ...] = (
    _search_core,
    _search_history,
    _search_explanations,
    _search_replays,
    _search_harness,
    _search_learning,
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
