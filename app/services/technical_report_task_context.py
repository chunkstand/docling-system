from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.time import utcnow
from app.schemas.agent_task_core import ContextFreshnessStatus, ContextRef


def task_output_context_ref(
    *,
    ref_key: str,
    summary: str,
    task_id: UUID,
    schema_name: str | None,
    schema_version: str | None,
    output: dict[str, Any],
    source_updated_at,
    freshness_status: ContextFreshnessStatus | None,
) -> ContextRef:
    return ContextRef(
        ref_key=ref_key,
        ref_kind="task_output",
        summary=summary,
        task_id=task_id,
        schema_name=schema_name,
        schema_version=schema_version,
        observed_sha256=_payload_sha256(output),
        source_updated_at=source_updated_at,
        checked_at=utcnow(),
        freshness_status=freshness_status or ContextFreshnessStatus.FRESH,
    )
