from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import (
    SemanticOntologySnapshot,
    SemanticReviewStatus,
)
from app.services import semantic_graph_core as _semantic_graph_core
from app.services.semantic_registry import (
    canonicalize_semantic_relation_endpoints,
    get_semantic_relation_definition,
    semantic_registry_from_payload,
    validate_semantic_relation_instance,
)


def _next_graph_version(base_graph_version: str | None, *, ontology_version: str) -> str:
    if not base_graph_version:
        return f"{ontology_version}.graph.1"
    match = _semantic_graph_core.GRAPH_VERSION_PATTERN.match(base_graph_version)
    if match is None:
        return f"{ontology_version}.graph.1"
    next_version = int(match.group("version")) + 1
    prefix = match.group("prefix")
    return f"{prefix}.graph.{next_version}"


def _merged_graph_payload(
    *,
    base_payload: dict[str, Any] | None,
    promoted_edges: list[dict[str, Any]],
    ontology_snapshot: SemanticOntologySnapshot,
    graph_version: str,
) -> dict[str, Any]:
    base_payload = dict(base_payload or {})
    existing_edges = {
        str(edge.get("edge_id")): dict(edge) for edge in (base_payload.get("edges") or [])
    }
    for edge in promoted_edges:
        existing_edges[str(edge["edge_id"])] = dict(edge)
    edges = sorted(existing_edges.values(), key=lambda row: str(row.get("edge_id") or ""))

    def _support_document_ids(edge: dict[str, Any]) -> set[Any]:
        return {
            document_id
            for document_id in edge.get("supporting_document_ids") or []
            if document_id is not None
        }

    def _support_source_types(edge: dict[str, Any]) -> set[str]:
        return {
            source_type
            for ref in edge.get("support_refs") or []
            for source_type in ref.get("source_types") or []
        }

    def _support_assertion_ids(edge: dict[str, Any]) -> set[Any]:
        return {
            assertion_id
            for ref in edge.get("support_refs") or []
            for assertion_id in ref.get("assertion_ids") or []
            if assertion_id is not None
        }

    def _support_evidence_ids(edge: dict[str, Any]) -> set[Any]:
        return {
            evidence_id
            for ref in edge.get("support_refs") or []
            for evidence_id in ref.get("evidence_ids") or []
            if evidence_id is not None
        }

    node_map: dict[str, dict[str, Any]] = {
        str(node.get("entity_key")): dict(node) for node in (base_payload.get("nodes") or [])
    }
    entity_support: dict[str, dict[str, set[Any] | str]] = {}
    entity_review_status_counts: dict[str, dict[str, int]] = {}
    for edge in edges:
        support_document_ids = _support_document_ids(edge)
        support_source_types = _support_source_types(edge)
        support_assertion_ids = _support_assertion_ids(edge)
        support_evidence_ids = _support_evidence_ids(edge)
        review_status = str(edge.get("review_status") or "")
        for entity_key, label in (
            (edge["subject_entity_key"], edge["subject_label"]),
            (edge["object_entity_key"], edge["object_label"]),
        ):
            support = entity_support.setdefault(
                entity_key,
                {
                    "preferred_label": label,
                    "document_ids": set(),
                    "source_types": set(),
                    "assertion_ids": set(),
                    "evidence_ids": set(),
                },
            )
            support["preferred_label"] = label
            support["document_ids"].update(support_document_ids)
            support["source_types"].update(support_source_types)
            support["assertion_ids"].update(support_assertion_ids)
            support["evidence_ids"].update(support_evidence_ids)
            if review_status:
                review_counts = entity_review_status_counts.setdefault(entity_key, {})
                review_counts[review_status] = review_counts.get(review_status, 0) + 1

    for entity_key, support in entity_support.items():
        node = node_map.setdefault(
            entity_key,
            {
                "entity_key": entity_key,
                "concept_key": entity_key.split("concept:", 1)[1]
                if "concept:" in entity_key
                else entity_key,
                "preferred_label": str(support["preferred_label"]),
                "category_keys": [],
                "document_ids": [],
                "document_count": 0,
                "source_types": [],
                "review_status_counts": {"approved": 1},
                "assertion_count": 0,
                "evidence_count": 0,
            },
        )
        node["preferred_label"] = str(support["preferred_label"])
        node["document_ids"] = sorted(
            set(node.get("document_ids") or []) | set(support["document_ids"]), key=str
        )
        node["document_count"] = len(node["document_ids"])
        node["source_types"] = sorted(
            set(node.get("source_types") or []) | set(support["source_types"])
        )
        existing_review_status_counts = {
            str(status): int(count)
            for status, count in dict(node.get("review_status_counts") or {}).items()
            if str(status)
        }
        for status, count in entity_review_status_counts.get(entity_key, {}).items():
            existing_review_status_counts[status] = max(
                existing_review_status_counts.get(status, 0),
                count,
            )
        if existing_review_status_counts:
            node["review_status_counts"] = dict(sorted(existing_review_status_counts.items()))
        node["assertion_count"] = max(
            int(node.get("assertion_count") or 0),
            len(set(support["assertion_ids"])),
        )
        node["evidence_count"] = max(
            int(node.get("evidence_count") or 0),
            len(set(support["evidence_ids"])),
        )
    payload = {
        "graph_name": _semantic_graph_core.DEFAULT_GRAPH_NAME,
        "graph_version": graph_version,
        "ontology_snapshot_id": ontology_snapshot.id,
        "ontology_version": ontology_snapshot.ontology_version,
        "ontology_sha256": ontology_snapshot.sha256,
        "upper_ontology_version": ontology_snapshot.upper_ontology_version,
        "extractor": {
            "extractor_name": "approved_graph_memory",
            "backing_model": "none",
            "match_strategy": "approved_promotion",
            "shadow_mode": False,
            "provider_name": None,
        },
        "shadow_mode": False,
        "minimum_review_status": SemanticReviewStatus.APPROVED.value,
        "document_ids": sorted(
            {
                document_id
                for edge in edges
                for document_id in edge.get("supporting_document_ids") or []
                if document_id is not None
            },
            key=str,
        ),
        "document_count": len(
            {
                document_id
                for edge in edges
                for document_id in edge.get("supporting_document_ids") or []
                if document_id is not None
            }
        ),
        "document_refs": [],
        "node_count": len(node_map),
        "edge_count": len(edges),
        "nodes": sorted(node_map.values(), key=lambda row: str(row.get("entity_key") or "")),
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


def draft_graph_promotions(
    session: Session,
    *,
    source_payload: dict[str, Any],
    source_task_id: UUID,
    source_task_type: str,
    proposed_graph_version: str | None,
    rationale: str | None,
    edge_ids: list[str],
    min_score: float,
    get_active_semantic_ontology_snapshot_fn,
    get_active_semantic_graph_snapshot_fn,
) -> dict[str, Any]:
    ontology_snapshot = get_active_semantic_ontology_snapshot_fn(session)
    registry = semantic_registry_from_payload(ontology_snapshot.payload_json or {})
    active_snapshot = get_active_semantic_graph_snapshot_fn(session)
    base_payload = dict(active_snapshot.payload_json or {}) if active_snapshot is not None else None

    def _canonicalized_edge_payload(edge: dict[str, Any]) -> dict[str, Any]:
        relation_key = str(edge.get("relation_key") or "")
        relation_label = _semantic_graph_core._relation_label_from_registry(registry, relation_key)
        subject_entity_key, subject_label, object_entity_key, object_label = (
            canonicalize_semantic_relation_endpoints(
                registry,
                relation_key=relation_key,
                subject_entity_key=str(edge.get("subject_entity_key") or ""),
                subject_label=str(edge.get("subject_label") or ""),
                object_entity_key=str(edge.get("object_entity_key") or ""),
                object_label=str(edge.get("object_label") or ""),
            )
        )
        canonical_subject_concept_key = str(subject_entity_key).split("concept:", 1)[-1]
        canonical_object_concept_key = str(object_entity_key).split("concept:", 1)[-1]
        details = dict(edge.get("details") or {})
        details["constraint_validation_errors"] = validate_semantic_relation_instance(
            registry,
            relation_key=relation_key,
            subject_entity_key=subject_entity_key,
            object_entity_key=object_entity_key,
        )
        return {
            **edge,
            "edge_id": _semantic_graph_core._edge_id(
                registry,
                relation_key=relation_key,
                subject_concept_key=canonical_subject_concept_key,
                object_concept_key=canonical_object_concept_key,
            ),
            "relation_label": relation_label,
            "subject_entity_key": subject_entity_key,
            "subject_label": subject_label,
            "object_entity_key": object_entity_key,
            "object_label": object_label,
            "details": details,
        }

    if source_task_type == "triage_semantic_graph_disagreements":
        source_edges = [
            _canonicalized_edge_payload(
                {
                    "edge_id": issue["edge_id"],
                    "relation_key": issue["relation_key"],
                    "relation_label": _semantic_graph_core._relation_label_from_registry(
                        registry,
                        str(issue.get("relation_key") or ""),
                    ),
                    "subject_entity_key": issue["subject_entity_key"],
                    "subject_label": issue["subject_label"],
                    "object_entity_key": issue["object_entity_key"],
                    "object_label": issue["object_label"],
                    "epistemic_status": "approved_graph",
                    "review_status": SemanticReviewStatus.APPROVED.value,
                    "support_level": "supported",
                    "extractor_name": _semantic_graph_core.DEFAULT_GRAPH_CANDIDATE_EXTRACTOR,
                    "extractor_score": issue["candidate_score"],
                    "supporting_document_ids": issue["supporting_document_ids"],
                    "supporting_document_count": len(issue["supporting_document_ids"]),
                    "supporting_assertion_count": sum(
                        len(ref.get("assertion_ids") or [])
                        for ref in issue.get("support_refs") or []
                    ),
                    "supporting_evidence_count": sum(
                        len(ref.get("evidence_ids") or [])
                        for ref in issue.get("support_refs") or []
                    ),
                    "shared_category_keys": sorted(
                        {
                            category_key
                            for ref in issue.get("support_refs") or []
                            for category_key in ref.get("shared_category_keys") or []
                        }
                    ),
                    "source_types": sorted(
                        {
                            source_type
                            for ref in issue.get("support_refs") or []
                            for source_type in ref.get("source_types") or []
                        }
                    ),
                    "support_refs": issue.get("support_refs") or [],
                    "details": {
                        "promoted_from": "graph_disagreement_triage",
                    },
                }
            )
            for issue in source_payload.get("issues") or []
            if not edge_ids or issue["edge_id"] in set(edge_ids)
        ]
    else:
        source_edges = [
            _canonicalized_edge_payload(
                {
                    **edge,
                    "epistemic_status": "approved_graph",
                    "review_status": SemanticReviewStatus.APPROVED.value,
                }
            )
            for edge in source_payload.get("edges") or []
            if (not edge_ids or edge["edge_id"] in set(edge_ids))
            and float(edge.get("extractor_score") or 0.0) >= min_score
        ]
    if not source_edges:
        raise ValueError("Graph promotion draft did not select any eligible edges.")
    graph_version = proposed_graph_version or _next_graph_version(
        active_snapshot.graph_version if active_snapshot is not None else None,
        ontology_version=ontology_snapshot.ontology_version,
    )
    effective_graph = _merged_graph_payload(
        base_payload=base_payload,
        promoted_edges=source_edges,
        ontology_snapshot=ontology_snapshot,
        graph_version=graph_version,
    )
    return {
        "base_snapshot_id": active_snapshot.id if active_snapshot is not None else None,
        "base_graph_version": active_snapshot.graph_version
        if active_snapshot is not None
        else None,
        "proposed_graph_version": graph_version,
        "ontology_snapshot_id": ontology_snapshot.id,
        "ontology_version": ontology_snapshot.ontology_version,
        "ontology_sha256": ontology_snapshot.sha256,
        "source_task_id": source_task_id,
        "source_task_type": source_task_type,
        "rationale": rationale,
        "promoted_edges": source_edges,
        "effective_graph": effective_graph,
        "success_metrics": [
            {
                "metric_key": "semantic_integrity",
                "stakeholder": "Figay",
                "passed": all(edge.get("support_refs") for edge in source_edges)
                and all(
                    not (edge.get("details") or {}).get("constraint_validation_errors")
                    for edge in source_edges
                ),
                "summary": "Draft promotions only contain traceable graph edges.",
                "details": {
                    "promoted_edge_count": len(source_edges),
                    "constraint_validation_failures": sum(
                        1
                        for edge in source_edges
                        if (edge.get("details") or {}).get("constraint_validation_errors")
                    ),
                },
            },
            {
                "metric_key": "explicit_control_surface",
                "stakeholder": "Ronacher",
                "passed": True,
                "summary": "Graph promotion remains a draft artifact until verification "
                "and approval.",
                "details": {"promoted_edge_count": len(source_edges)},
            },
        ],
    }


def verify_draft_graph_promotions(
    session: Session,
    draft: dict[str, Any],
    *,
    min_supporting_document_count: int,
    max_conflict_count: int,
    require_current_ontology_snapshot: bool,
    get_active_semantic_ontology_snapshot_fn,
) -> tuple[dict[str, Any], dict[str, Any], list[str], str, list[dict[str, Any]]]:
    current_ontology = get_active_semantic_ontology_snapshot_fn(session)
    registry = semantic_registry_from_payload(current_ontology.payload_json or {})

    def _effective_graph_conflict_count(edges: list[dict[str, Any]]) -> int:
        seen_pairs: dict[tuple[str, str, str], str] = {}
        conflict_edge_ids: set[str] = set()
        for edge in edges:
            relation_key = str(edge.get("relation_key") or "")
            relation = get_semantic_relation_definition(registry, relation_key)
            if relation is None:
                continue
            subject_entity_key, _subject_label, object_entity_key, _object_label = (
                canonicalize_semantic_relation_endpoints(
                    registry,
                    relation_key=relation_key,
                    subject_entity_key=str(edge.get("subject_entity_key") or ""),
                    subject_label=str(edge.get("subject_label") or ""),
                    object_entity_key=str(edge.get("object_entity_key") or ""),
                    object_label=str(edge.get("object_label") or ""),
                )
            )
            pair_key = (
                relation_key,
                subject_entity_key,
                object_entity_key,
            )
            current_edge_id = str(edge.get("edge_id") or "")
            if pair_key in seen_pairs:
                conflict_edge_ids.update({current_edge_id, seen_pairs[pair_key]})
                continue
            inverse_relation_key = relation.inverse_relation_key
            if inverse_relation_key:
                inverse_key = (
                    inverse_relation_key,
                    object_entity_key,
                    subject_entity_key,
                )
                if inverse_key in seen_pairs:
                    conflict_edge_ids.update({current_edge_id, seen_pairs[inverse_key]})
            seen_pairs[pair_key] = current_edge_id
        return len(conflict_edge_ids)

    reasons: list[str] = []
    promoted_edges = list(draft.get("promoted_edges") or [])
    stale_edge_count = 0
    unsupported_edge_count = 0
    conflict_count = 0
    ontology_mismatch_count = 0
    constraint_violation_count = 0
    supported_edge_count = 0
    seen_pairs: dict[tuple[str, str, str], str] = {}
    for edge in promoted_edges:
        if (
            require_current_ontology_snapshot
            and UUID(str(draft["ontology_snapshot_id"])) != current_ontology.id
        ):
            stale_edge_count += 1
            continue
        relation_key = str(edge.get("relation_key") or "")
        relation = get_semantic_relation_definition(registry, relation_key)
        if relation is None:
            ontology_mismatch_count += 1
            continue
        validation_errors = validate_semantic_relation_instance(
            registry,
            relation_key=relation_key,
            subject_entity_key=str(edge.get("subject_entity_key") or ""),
            object_entity_key=str(edge.get("object_entity_key") or ""),
        )
        if validation_errors:
            constraint_violation_count += 1
            continue
        support_refs = list(edge.get("support_refs") or [])
        if len(edge.get("supporting_document_ids") or []) < min_supporting_document_count:
            unsupported_edge_count += 1
            continue
        if not support_refs:
            unsupported_edge_count += 1
            continue
        canonical_subject_entity_key, _subject_label, canonical_object_entity_key, _object_label = (
            canonicalize_semantic_relation_endpoints(
                registry,
                relation_key=relation_key,
                subject_entity_key=str(edge.get("subject_entity_key") or ""),
                subject_label=str(edge.get("subject_label") or ""),
                object_entity_key=str(edge.get("object_entity_key") or ""),
                object_label=str(edge.get("object_label") or ""),
            )
        )
        if (
            canonical_subject_entity_key != str(edge.get("subject_entity_key") or "")
            or canonical_object_entity_key != str(edge.get("object_entity_key") or "")
        ) and relation.symmetric:
            conflict_count += 1
            continue
        pair_key = (
            relation_key,
            canonical_subject_entity_key,
            canonical_object_entity_key,
        )
        if pair_key in seen_pairs:
            conflict_count += 1
            continue
        inverse_relation_key = relation.inverse_relation_key
        if inverse_relation_key:
            inverse_key = (
                inverse_relation_key,
                canonical_object_entity_key,
                canonical_subject_entity_key,
            )
            if inverse_key in seen_pairs:
                conflict_count += 1
                continue
        seen_pairs[pair_key] = str(edge.get("edge_id") or "")
        supported_edge_count += 1

    effective_graph_edges = list((draft.get("effective_graph") or {}).get("edges") or [])
    conflict_count = max(conflict_count, _effective_graph_conflict_count(effective_graph_edges))

    if stale_edge_count:
        reasons.append("Draft graph promotions target a stale ontology snapshot.")
    if unsupported_edge_count:
        reasons.append("Draft graph promotions include unsupported or weakly-backed edges.")
    if ontology_mismatch_count:
        reasons.append("Draft graph promotions target a relation missing from the active ontology.")
    if constraint_violation_count:
        reasons.append("Draft graph promotions violate active ontology relation constraints.")
    if conflict_count > max_conflict_count:
        reasons.append("Draft graph promotions introduce conflicting graph edges.")
    if supported_edge_count == 0:
        reasons.append("Draft graph promotions do not contain any promotable edges.")
    outcome = "passed" if not reasons else "failed"
    summary = {
        "promoted_edge_count": len(promoted_edges),
        "supported_edge_count": supported_edge_count,
        "stale_edge_count": stale_edge_count,
        "unsupported_edge_count": unsupported_edge_count,
        "ontology_mismatch_count": ontology_mismatch_count,
        "constraint_violation_count": constraint_violation_count,
        "conflict_count": conflict_count,
        "traceable_edge_ratio": round(
            sum(1 for edge in promoted_edges if edge.get("support_refs")) / len(promoted_edges),
            4,
        )
        if promoted_edges
        else 1.0,
    }
    metrics = {
        "promoted_edge_count": len(promoted_edges),
        "supported_edge_count": supported_edge_count,
        "stale_edge_count": stale_edge_count,
        "unsupported_edge_count": unsupported_edge_count,
        "ontology_mismatch_count": ontology_mismatch_count,
        "constraint_violation_count": constraint_violation_count,
        "conflict_count": conflict_count,
    }
    success_metrics = [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": summary["traceable_edge_ratio"] == 1.0
            and unsupported_edge_count == 0
            and ontology_mismatch_count == 0
            and constraint_violation_count == 0,
            "summary": "Only fully traceable, supported graph edges pass verification.",
            "details": {
                "traceable_edge_ratio": summary["traceable_edge_ratio"],
                "unsupported_edge_count": unsupported_edge_count,
                "ontology_mismatch_count": ontology_mismatch_count,
                "constraint_violation_count": constraint_violation_count,
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": stale_edge_count == 0
            and conflict_count <= max_conflict_count
            and ontology_mismatch_count == 0
            and constraint_violation_count == 0,
            "summary": "Verification blocks stale graph state and conflicting promotions.",
            "details": {
                "stale_edge_count": stale_edge_count,
                "conflict_count": conflict_count,
                "ontology_mismatch_count": ontology_mismatch_count,
                "constraint_violation_count": constraint_violation_count,
            },
        },
    ]
    return summary, metrics, reasons, outcome, success_metrics
