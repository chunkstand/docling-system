from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session


def load_by_ids(session: Session, model: Any, ids: set[UUID]) -> dict[UUID, Any]:
    if not ids:
        return {}
    return {
        row.id: row
        for row in session.execute(select(model).where(model.id.in_(ids))).scalars().all()
    }
