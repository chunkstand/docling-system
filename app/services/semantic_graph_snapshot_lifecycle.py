from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    SemanticGraphSnapshot,
    SemanticGraphSourceKind,
    WorkspaceSemanticGraphState,
)
from app.services import semantic_graph_core as _semantic_graph_core


def persist_semantic_graph_snapshot(
    session: Session,
    payload: dict[str, object],
    *,
    source_kind: str,
    source_task_id: UUID | None = None,
    source_task_type: str | None = None,
    parent_snapshot_id: UUID | None = None,
    activate: bool = False,
    workspace_graph_state_fn=_semantic_graph_core._workspace_graph_state,
    graph_payload_sha256_fn=_semantic_graph_core._graph_payload_sha256,
    record_semantic_graph_snapshot_governance_events_fn=None,
) -> SemanticGraphSnapshot:
    now = utcnow()
    graph_version = str(payload.get("graph_version") or "").strip()
    graph_name = (
        str(payload.get("graph_name") or _semantic_graph_core.DEFAULT_GRAPH_NAME).strip()
        or _semantic_graph_core.DEFAULT_GRAPH_NAME
    )
    if not graph_version:
        raise ValueError("Semantic graph payload requires graph_version.")
    incoming_sha256 = graph_payload_sha256_fn(payload)
    snapshot = (
        session.query(SemanticGraphSnapshot).filter_by(graph_version=graph_version).one_or_none()
    )
    if snapshot is None:
        snapshot = SemanticGraphSnapshot(
            graph_name=graph_name,
            graph_version=graph_version,
            ontology_snapshot_id=payload.get("ontology_snapshot_id"),
            source_kind=source_kind,
            source_task_id=source_task_id,
            source_task_type=source_task_type,
            parent_snapshot_id=parent_snapshot_id,
            payload_json=payload,
            sha256=incoming_sha256,
            created_at=now,
            activated_at=now if activate else None,
        )
        session.add(snapshot)
        session.flush()
    else:
        if snapshot.sha256 != incoming_sha256:
            raise ValueError(
                "Semantic graph snapshot versions are immutable once published; "
                "choose a new graph_version for changed payloads."
            )
        if activate:
            snapshot.activated_at = now
    if activate:
        state = workspace_graph_state_fn(session)
        if state is None:
            state = WorkspaceSemanticGraphState(
                workspace_key=_semantic_graph_core.WORKSPACE_SEMANTIC_GRAPH_STATE_KEY,
                active_graph_snapshot_id=snapshot.id,
                created_at=now,
                updated_at=now,
            )
            session.add(state)
        else:
            state.active_graph_snapshot_id = snapshot.id
            state.updated_at = now
        snapshot.activated_at = now
    record_semantic_graph_snapshot_governance_events_fn(
        session,
        snapshot,
        activated=activate,
    )
    session.flush()
    return snapshot


def apply_graph_promotions(
    session: Session,
    draft: dict[str, object],
    *,
    source_task_id: UUID,
    source_task_type: str,
    reason: str | None,
    workspace_graph_state_fn=_semantic_graph_core._workspace_graph_state,
    graph_payload_sha256_fn=_semantic_graph_core._graph_payload_sha256,
    record_semantic_graph_snapshot_governance_events_fn=None,
) -> dict[str, object]:
    base_snapshot_id = draft.get("base_snapshot_id")
    snapshot = persist_semantic_graph_snapshot(
        session,
        draft["effective_graph"],
        source_kind=SemanticGraphSourceKind.GRAPH_PROMOTION_APPLY.value,
        source_task_id=source_task_id,
        source_task_type=source_task_type,
        parent_snapshot_id=UUID(str(base_snapshot_id)) if base_snapshot_id else None,
        activate=True,
        workspace_graph_state_fn=workspace_graph_state_fn,
        graph_payload_sha256_fn=graph_payload_sha256_fn,
        record_semantic_graph_snapshot_governance_events_fn=record_semantic_graph_snapshot_governance_events_fn,
    )
    session.commit()
    return {
        "applied_snapshot_id": snapshot.id,
        "applied_graph_version": snapshot.graph_version,
        "applied_graph_sha256": snapshot.sha256,
        "ontology_snapshot_id": snapshot.ontology_snapshot_id,
        "reason": reason,
        "applied_edge_count": len((snapshot.payload_json or {}).get("edges") or []),
        "success_metrics": [
            {
                "metric_key": "owned_context",
                "stakeholder": "Jones",
                "passed": True,
                "summary": "Approved graph memory is now stored as a live workspace snapshot.",
                "details": {"applied_snapshot_id": str(snapshot.id)},
            },
            {
                "metric_key": "memory_compaction",
                "stakeholder": "Yegge",
                "passed": bool((snapshot.payload_json or {}).get("edges") is not None),
                "summary": "Approved graph edges are now reusable by downstream agents.",
                "details": {
                    "applied_edge_count": len((snapshot.payload_json or {}).get("edges") or [])
                },
            },
        ],
    }
