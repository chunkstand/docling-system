from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import SemanticReviewStatus
from app.services import semantic_graph_core as _semantic_graph_core
from app.services import semantic_graph_support as _semantic_graph_support
from app.services.semantic_registry import semantic_registry_from_payload


def build_shadow_semantic_graph(
    session: Session,
    *,
    document_ids: list[UUID],
    relation_extractor_name: str,
    minimum_review_status: str,
    min_shared_documents: int,
    score_threshold: float,
    get_active_semantic_ontology_snapshot_fn,
    get_active_semantic_pass_detail_fn,
) -> dict[str, Any]:
    if not document_ids:
        raise ValueError("Shadow semantic graph build requires at least one document.")
    descriptor = _semantic_graph_core._extractor_descriptor(relation_extractor_name)
    ontology_snapshot = get_active_semantic_ontology_snapshot_fn(session)
    registry = semantic_registry_from_payload(ontology_snapshot.payload_json or {})
    unique_document_ids = list(dict.fromkeys(document_ids))
    nodes_by_key, edges_by_pair, document_refs = _semantic_graph_support._collect_graph_support(
        session,
        registry=registry,
        document_ids=unique_document_ids,
        minimum_review_status=minimum_review_status,
        get_active_semantic_pass_detail_fn=get_active_semantic_pass_detail_fn,
    )
    nodes = _semantic_graph_core._build_graph_nodes(nodes_by_key)
    edges = _semantic_graph_core._build_graph_edges(
        registry=registry,
        nodes_by_key=nodes_by_key,
        edges_by_pair=edges_by_pair,
        extractor_name=relation_extractor_name,
        min_shared_documents=min_shared_documents,
        score_threshold=score_threshold,
        shadow_mode=True,
        review_status=SemanticReviewStatus.CANDIDATE.value,
    )
    payload = {
        "graph_name": _semantic_graph_core.DEFAULT_GRAPH_NAME,
        "graph_version": (
            f"shadow:{ontology_snapshot.ontology_version}:{relation_extractor_name}:{len(unique_document_ids)}"
        ),
        "ontology_snapshot_id": ontology_snapshot.id,
        "ontology_version": ontology_snapshot.ontology_version,
        "ontology_sha256": ontology_snapshot.sha256,
        "upper_ontology_version": ontology_snapshot.upper_ontology_version,
        "extractor": {
            "extractor_name": descriptor.extractor_name,
            "backing_model": descriptor.backing_model,
            "match_strategy": descriptor.match_strategy,
            "shadow_mode": descriptor.shadow_mode,
            "provider_name": descriptor.provider_name,
        },
        "shadow_mode": True,
        "minimum_review_status": minimum_review_status,
        "document_ids": unique_document_ids,
        "document_count": len(unique_document_ids),
        "document_refs": document_refs,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "relation_key_counts": {
                relation_key: sum(1 for edge in edges if edge.get("relation_key") == relation_key)
                for relation_key in sorted(
                    {
                        str(edge.get("relation_key") or "")
                        for edge in edges
                        if str(edge.get("relation_key") or "")
                    }
                )
            },
            "traceable_edge_count": sum(1 for edge in edges if edge.get("support_refs")),
            "support_ref_count": sum(len(edge.get("support_refs") or []) for edge in edges),
        },
    }
    payload["success_metrics"] = _semantic_graph_core._graph_success_metrics(payload)
    return payload
