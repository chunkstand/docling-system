from __future__ import annotations

import sys
from collections.abc import Callable


def resolve_search_service(name: str, fallback: Callable) -> Callable:
    parent_module = sys.modules.get("app.api.routers.search")
    if parent_module is None:
        return fallback
    return getattr(parent_module, name, fallback)


__all__ = ["resolve_search_service"]
