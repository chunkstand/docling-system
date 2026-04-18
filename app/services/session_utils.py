from __future__ import annotations

from sqlalchemy.orm import Session


def uses_in_memory_session(session: object) -> bool:
    return not isinstance(session, Session)
