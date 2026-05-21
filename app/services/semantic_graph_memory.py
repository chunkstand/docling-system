from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.public.semantic_memory import SemanticReviewStatus


def graph_memory_for_brief(
    session: Session,
    *,
    document_ids: list[UUID],
    requested_concept_keys: set[str],
    available_concept_keys: set[str],
    get_active_semantic_graph_snapshot_fn,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], list[str]]:
    snapshot = get_active_semantic_graph_snapshot_fn(session)
    if snapshot is None:
        return [], [], {}, []
    payload = dict(snapshot.payload_json or {})
    warnings: list[str] = []
    edge_refs: list[dict[str, Any]] = []
    related_concept_keys: list[str] = []
    document_id_set = set(document_ids)
    for edge in payload.get("edges") or []:
        if edge.get("review_status") != SemanticReviewStatus.APPROVED.value:
            continue
        support_document_ids = {
            UUID(str(value)) for value in edge.get("supporting_document_ids") or []
        }
        if not support_document_ids.intersection(document_id_set):
            continue
        subject_concept_key = str(edge.get("subject_entity_key") or "").split("concept:", 1)[-1]
        object_concept_key = str(edge.get("object_entity_key") or "").split("concept:", 1)[-1]
        if (
            subject_concept_key not in available_concept_keys
            or object_concept_key not in available_concept_keys
        ):
            continue
        if requested_concept_keys and not {
            subject_concept_key,
            object_concept_key,
        }.intersection(requested_concept_keys):
            continue
        related_concept_keys.extend([subject_concept_key, object_concept_key])
        edge_refs.append(
            {
                "edge_id": edge["edge_id"],
                "graph_snapshot_id": snapshot.id,
                "graph_version": snapshot.graph_version,
                "relation_key": edge["relation_key"],
                "relation_label": edge["relation_label"],
                "subject_entity_key": edge["subject_entity_key"],
                "subject_label": edge["subject_label"],
                "object_entity_key": edge["object_entity_key"],
                "object_label": edge["object_label"],
                "review_status": edge["review_status"],
                "support_level": edge["support_level"],
                "extractor_score": edge["extractor_score"],
                "supporting_document_ids": list(edge.get("supporting_document_ids") or []),
                "support_ref_ids": [
                    ref.get("support_ref_id")
                    for ref in edge.get("support_refs") or []
                    if ref.get("support_ref_id")
                ],
            }
        )
    if edge_refs:
        warnings.append(
            f"{len(edge_refs)} approved graph edge"
            f"{'' if len(edge_refs) == 1 else 's'} were used to enrich the generation brief."
        )
    summary = {
        "graph_snapshot_id": str(snapshot.id),
        "graph_version": snapshot.graph_version,
        "edge_count": len(edge_refs),
    }
    return sorted(set(related_concept_keys)), edge_refs, summary, warnings

