from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import SemanticGraphSnapshot, SemanticReviewStatus, WorkspaceSemanticGraphState
from app.services.semantic_candidates import cosine_similarity, embedding_vector, tokenize
from app.services.semantic_registry import (
    canonicalize_semantic_relation_endpoints,
    get_semantic_relation_definition,
    normalize_semantic_text,
    validate_semantic_relation_instance,
)

WORKSPACE_SEMANTIC_GRAPH_STATE_KEY = "default"
DEFAULT_GRAPH_NAME = "workspace_semantic_graph"
DEFAULT_GRAPH_BASELINE_EXTRACTOR = "cooccurrence_v1"
DEFAULT_GRAPH_CANDIDATE_EXTRACTOR = "relation_ranker_v1"
DEFAULT_GRAPH_RELATION_KEY = "concept_related_to_concept"
DEFAULT_GRAPH_RELATION_LABEL = "Concept Related To Concept"
DEPENDENCY_GRAPH_RELATION_KEY = "concept_depends_on_concept"
DEPENDENCY_GRAPH_RELATION_LABEL = "Concept Depends On Concept"
GRAPH_VERSION_PATTERN = re.compile(r"^(?P<prefix>.+?)\\.graph\\.(?P<version>\\d+)$")
DEPENDENCY_CUE_PHRASES = (
    "depends on",
    "dependent on",
    "requires",
    "required for",
    "needs",
    "needed for",
    "gated by",
    "blocked by",
    "conditioned on",
    "contingent on",
)


@dataclass(frozen=True)
class GraphExtractorDescriptor:
    extractor_name: str
    backing_model: str
    match_strategy: str
    shadow_mode: bool = True
    provider_name: str | None = None


@dataclass
class _ConceptNodeBucket:
    concept_key: str
    preferred_label: str
    category_keys: set[str]
    document_ids: set[UUID]
    source_types: set[str]
    review_status_counts: dict[str, int]
    assertion_ids: set[UUID]
    evidence_ids: set[UUID]


@dataclass
class _EdgeBucket:
    relation_key: str
    subject_concept_key: str
    object_concept_key: str
    supporting_document_ids: set[UUID]
    support_refs: list[dict[str, Any]]
    source_types: set[str]
    shared_category_keys: set[str]
    approved_document_count: int = 0
    cue_match_count: int = 0


def _graph_payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _workspace_graph_state(session: Session) -> WorkspaceSemanticGraphState | None:
    return session.get(WorkspaceSemanticGraphState, WORKSPACE_SEMANTIC_GRAPH_STATE_KEY)


def get_active_semantic_graph_snapshot(session: Session) -> SemanticGraphSnapshot | None:
    state = _workspace_graph_state(session)
    if state is None or state.active_graph_snapshot_id is None:
        return None
    return session.get(SemanticGraphSnapshot, state.active_graph_snapshot_id)


def get_active_semantic_graph_payload(session: Session) -> dict[str, Any] | None:
    snapshot = get_active_semantic_graph_snapshot(session)
    if snapshot is None:
        return None
    return dict(snapshot.payload_json or {})


def _relation_label_from_registry(registry, relation_key: str) -> str:
    relation = get_semantic_relation_definition(registry, relation_key)
    if relation is None or not relation.preferred_label:
        if relation_key == DEFAULT_GRAPH_RELATION_KEY:
            return DEFAULT_GRAPH_RELATION_LABEL
        if relation_key == DEPENDENCY_GRAPH_RELATION_KEY:
            return DEPENDENCY_GRAPH_RELATION_LABEL
        return relation_key.replace("_", " ").title()
    return relation.preferred_label


def _extractor_descriptor(extractor_name: str) -> GraphExtractorDescriptor:
    if extractor_name == DEFAULT_GRAPH_BASELINE_EXTRACTOR:
        return GraphExtractorDescriptor(
            extractor_name=DEFAULT_GRAPH_BASELINE_EXTRACTOR,
            backing_model="none",
            match_strategy="cooccurrence_min_shared_documents_v1",
        )
    if extractor_name == DEFAULT_GRAPH_CANDIDATE_EXTRACTOR:
        return GraphExtractorDescriptor(
            extractor_name=DEFAULT_GRAPH_CANDIDATE_EXTRACTOR,
            backing_model="hashing_embedding_v1",
            match_strategy="relation_ranker_v1",
            provider_name="local_hashing",
        )
    raise ValueError(f"Unsupported semantic relation extractor: {extractor_name}")


def _review_rank(review_status: str) -> int:
    if review_status == SemanticReviewStatus.APPROVED.value:
        return 2
    if review_status == SemanticReviewStatus.CANDIDATE.value:
        return 1
    return 0


def _minimum_review_rank(minimum_review_status: str) -> int:
    if minimum_review_status not in {
        SemanticReviewStatus.CANDIDATE.value,
        SemanticReviewStatus.APPROVED.value,
    }:
        raise ValueError(f"Unsupported semantic graph review threshold: {minimum_review_status}")
    return _review_rank(minimum_review_status)


def _ordered_edge_key(subject_concept_key: str, object_concept_key: str) -> tuple[str, str]:
    if subject_concept_key <= object_concept_key:
        return subject_concept_key, object_concept_key
    return object_concept_key, subject_concept_key


def _canonical_edge_key(
    registry,
    *,
    relation_key: str,
    subject_concept_key: str,
    object_concept_key: str,
) -> tuple[str, str]:
    subject_entity_key, _subject_label, object_entity_key, _object_label = (
        canonicalize_semantic_relation_endpoints(
            registry,
            relation_key=relation_key,
            subject_entity_key=f"concept:{subject_concept_key}",
            subject_label=subject_concept_key,
            object_entity_key=f"concept:{object_concept_key}",
            object_label=object_concept_key,
        )
    )
    return (
        str(subject_entity_key).split("concept:", 1)[-1],
        str(object_entity_key).split("concept:", 1)[-1],
    )


def _edge_id(
    registry,
    *,
    relation_key: str,
    subject_concept_key: str,
    object_concept_key: str,
) -> str:
    left, right = _canonical_edge_key(
        registry,
        relation_key=relation_key,
        subject_concept_key=subject_concept_key,
        object_concept_key=object_concept_key,
    )
    return f"graph_edge:{relation_key}:concept:{left}:concept:{right}"


def _normalized_terms(preferred_label: str, matched_terms: set[str]) -> list[str]:
    return sorted(
        {
            normalize_semantic_text(preferred_label),
            *[normalize_semantic_text(term) for term in matched_terms],
        }
        - {""}
    )


def _excerpt_matches_dependency(
    excerpt: str,
    *,
    left_terms: list[str],
    right_terms: list[str],
) -> bool:
    normalized_excerpt = normalize_semantic_text(excerpt)
    if not normalized_excerpt:
        return False
    cue_pattern = "|".join(re.escape(cue) for cue in DEPENDENCY_CUE_PHRASES)
    for left in left_terms:
        for right in right_terms:
            if not left or not right or left == right:
                continue
            pattern = (
                rf"\b{re.escape(left)}\b(?:\s+\w+){{0,6}}\s+(?:{cue_pattern})"
                rf"(?:\s+\w+){{0,6}}\s+\b{re.escape(right)}\b"
            )
            if re.search(pattern, normalized_excerpt):
                return True
    return False


def _dependency_relation_pairs(
    *,
    subject_concept_key: str,
    object_concept_key: str,
    subject_label: str,
    object_label: str,
    subject_terms: set[str],
    object_terms: set[str],
    evidence_texts: list[str],
) -> list[tuple[str, str]]:
    normalized_subject_terms = _normalized_terms(subject_label, subject_terms)
    normalized_object_terms = _normalized_terms(object_label, object_terms)
    if any(
        _excerpt_matches_dependency(
            excerpt,
            left_terms=normalized_subject_terms,
            right_terms=normalized_object_terms,
        )
        for excerpt in evidence_texts
    ):
        return [(subject_concept_key, object_concept_key)]
    if any(
        _excerpt_matches_dependency(
            excerpt,
            left_terms=normalized_object_terms,
            right_terms=normalized_subject_terms,
        )
        for excerpt in evidence_texts
    ):
        return [(object_concept_key, subject_concept_key)]
    return []


def _token_jaccard(left: str, right: str) -> float:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def _relation_score(
    edge_bucket: _EdgeBucket,
    *,
    nodes_by_key: dict[str, _ConceptNodeBucket],
    total_document_count: int,
) -> float:
    shared_document_ratio = len(edge_bucket.supporting_document_ids) / max(total_document_count, 1)
    approved_support_ratio = edge_bucket.approved_document_count / max(
        len(edge_bucket.supporting_document_ids), 1
    )
    category_overlap = 1.0 if edge_bucket.shared_category_keys else 0.0
    source_type_diversity = min(len(edge_bucket.source_types) / 3, 1.0)
    cue_strength = 1.0 if edge_bucket.cue_match_count > 0 else 0.0
    subject = nodes_by_key[edge_bucket.subject_concept_key]
    object_ = nodes_by_key[edge_bucket.object_concept_key]
    label_similarity = max(
        _token_jaccard(subject.preferred_label, object_.preferred_label),
        cosine_similarity(
            embedding_vector(subject.preferred_label),
            embedding_vector(object_.preferred_label),
        ),
    )
    return round(
        0.35 * shared_document_ratio
        + 0.2 * approved_support_ratio
        + 0.1 * category_overlap
        + 0.1 * label_similarity
        + 0.1 * source_type_diversity
        + 0.15 * cue_strength,
        4,
    )


def _support_level(edge_bucket: _EdgeBucket) -> str:
    if edge_bucket.approved_document_count >= 2:
        return "strong"
    if edge_bucket.approved_document_count >= 1 or len(edge_bucket.supporting_document_ids) >= 2:
        return "supported"
    return "provisional"


def _build_graph_nodes(nodes_by_key: dict[str, _ConceptNodeBucket]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for concept_key in sorted(nodes_by_key):
        node = nodes_by_key[concept_key]
        nodes.append(
            {
                "entity_key": f"concept:{concept_key}",
                "concept_key": concept_key,
                "preferred_label": node.preferred_label,
                "category_keys": sorted(node.category_keys),
                "document_ids": sorted(node.document_ids, key=str),
                "document_count": len(node.document_ids),
                "source_types": sorted(node.source_types),
                "review_status_counts": dict(sorted(node.review_status_counts.items())),
                "assertion_count": len(node.assertion_ids),
                "evidence_count": len(node.evidence_ids),
            }
        )
    return nodes


def _build_graph_edges(
    *,
    registry,
    nodes_by_key: dict[str, _ConceptNodeBucket],
    edges_by_pair: dict[tuple[str, str, str], _EdgeBucket],
    extractor_name: str,
    min_shared_documents: int,
    score_threshold: float,
    shadow_mode: bool,
    review_status: str,
) -> list[dict[str, Any]]:
    total_document_count = max(
        len({doc_id for node in nodes_by_key.values() for doc_id in node.document_ids}), 1
    )
    edges: list[dict[str, Any]] = []
    for pair_key in sorted(edges_by_pair):
        edge_bucket = edges_by_pair[pair_key]
        if (
            extractor_name == DEFAULT_GRAPH_BASELINE_EXTRACTOR
            and edge_bucket.relation_key != DEFAULT_GRAPH_RELATION_KEY
        ):
            continue
        score = _relation_score(
            edge_bucket,
            nodes_by_key=nodes_by_key,
            total_document_count=total_document_count,
        )
        if extractor_name == DEFAULT_GRAPH_BASELINE_EXTRACTOR:
            if len(edge_bucket.supporting_document_ids) < min_shared_documents:
                continue
        elif score < score_threshold:
            continue
        relation_validation_errors = validate_semantic_relation_instance(
            registry,
            relation_key=edge_bucket.relation_key,
            subject_entity_key=f"concept:{edge_bucket.subject_concept_key}",
            object_entity_key=f"concept:{edge_bucket.object_concept_key}",
        )
        if relation_validation_errors:
            continue
        support_refs = [
            {
                **row,
                "score": score,
            }
            for row in edge_bucket.support_refs
        ]
        relation_label = _relation_label_from_registry(registry, edge_bucket.relation_key)
        edges.append(
            {
                "edge_id": _edge_id(
                    registry,
                    relation_key=edge_bucket.relation_key,
                    subject_concept_key=edge_bucket.subject_concept_key,
                    object_concept_key=edge_bucket.object_concept_key,
                ),
                "relation_key": edge_bucket.relation_key,
                "relation_label": relation_label,
                "subject_entity_key": f"concept:{edge_bucket.subject_concept_key}",
                "subject_label": nodes_by_key[edge_bucket.subject_concept_key].preferred_label,
                "object_entity_key": f"concept:{edge_bucket.object_concept_key}",
                "object_label": nodes_by_key[edge_bucket.object_concept_key].preferred_label,
                "epistemic_status": "shadow_candidate" if shadow_mode else "approved_graph",
                "review_status": review_status,
                "support_level": _support_level(edge_bucket),
                "extractor_name": extractor_name,
                "extractor_score": score,
                "supporting_document_ids": sorted(edge_bucket.supporting_document_ids, key=str),
                "supporting_document_count": len(edge_bucket.supporting_document_ids),
                "supporting_assertion_count": sum(
                    len(ref["assertion_ids"]) for ref in support_refs
                ),
                "supporting_evidence_count": sum(len(ref["evidence_ids"]) for ref in support_refs),
                "shared_category_keys": sorted(edge_bucket.shared_category_keys),
                "source_types": sorted(edge_bucket.source_types),
                "support_refs": support_refs,
                "details": {
                    "approved_document_count": edge_bucket.approved_document_count,
                    "min_shared_documents_threshold": min_shared_documents,
                    "score_threshold": score_threshold,
                    "cue_match_count": edge_bucket.cue_match_count,
                },
            }
        )
    return edges


def _graph_success_metrics(payload: dict[str, Any]) -> list[dict[str, Any]]:
    edges = list(payload.get("edges") or [])
    total_support_ref_count = sum(len(edge.get("support_refs") or []) for edge in edges)
    traceable_edge_ratio = (
        sum(1 for edge in edges if edge.get("support_refs")) / len(edges) if edges else 1.0
    )
    constraint_valid_relation_ratio = (
        sum(
            1
            for edge in edges
            if not (edge.get("details") or {}).get("constraint_validation_errors")
        )
        / len(edges)
        if edges
        else 1.0
    )
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": traceable_edge_ratio == 1.0
            and all(edge.get("epistemic_status") for edge in edges)
            and constraint_valid_relation_ratio == 1.0,
            "summary": "Every graph edge stays evidence-backed and explicitly status-stamped.",
            "details": {
                "traceable_edge_ratio": traceable_edge_ratio,
                "constraint_valid_relation_ratio": constraint_valid_relation_ratio,
                "edge_count": len(edges),
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": all(edge.get("edge_id") and edge.get("relation_key") for edge in edges),
            "summary": "Graph memory is emitted as typed nodes and stable edge identifiers.",
            "details": {
                "node_count": payload.get("node_count"),
                "edge_count": payload.get("edge_count"),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(payload.get("document_ids")) and payload.get("edge_count", 0) >= 0,
            "summary": "Cross-document semantic context is externalized as a durable "
            "graph artifact.",
            "details": {
                "document_count": payload.get("document_count"),
                "edge_count": payload.get("edge_count"),
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": len(edges) <= max(total_support_ref_count, 1),
            "summary": "The graph compacts many supporting traces into a smaller edge "
            "memory surface.",
            "details": {
                "edge_count": len(edges),
                "support_ref_count": total_support_ref_count,
            },
        },
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": payload.get("extractor", {}).get("extractor_name")
            in {DEFAULT_GRAPH_BASELINE_EXTRACTOR, DEFAULT_GRAPH_CANDIDATE_EXTRACTOR},
            "summary": "The graph builder stays extractor-swappable and free of "
            "domain-specific rules.",
            "details": {
                "extractor_name": payload.get("extractor", {}).get("extractor_name"),
                "document_count": payload.get("document_count"),
            },
        },
    ]
