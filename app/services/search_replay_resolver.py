from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any


def resolve_search_replays_service(name: str, fallback: Callable[..., Any]) -> Callable[..., Any]:
    parent_module = sys.modules.get("app.services.search_replays")
    if parent_module is None:
        return fallback
    return getattr(parent_module, name, fallback)
