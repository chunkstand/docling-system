from __future__ import annotations

import sys
from collections.abc import Callable


def service_from_parent(name: str, fallback: Callable) -> Callable:
    parent_module = sys.modules.get("app.api.routers.agent_tasks")
    if parent_module is None:
        return fallback
    return getattr(parent_module, name, fallback)


__all__ = ["service_from_parent"]
