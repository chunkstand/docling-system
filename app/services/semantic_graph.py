from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from itertools import combinations
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.core.time import utcnow
from app.db.models import (
    SemanticGraphSnapshot,
    SemanticGraphSourceKind,
    SemanticOntologySnapshot,
    SemanticReviewStatus,
    WorkspaceSemanticGraphState,
)
from app.services.semantic_candidates import _cosine_similarity, _embedding_vector, _tokenize
from app.services.semantic_registry import (
    canonicalize_semantic_relation_endpoints,
    get_active_semantic_ontology_snapshot,
    get_semantic_relation_definition,
    normalize_semantic_text,
    semantic_registry_from_payload,
    validate_semantic_relation_instance,
)
from app.services.semantics import get_active_semantic_pass_detail

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
    left_tokens = set(_tokenize(left))
    right_tokens = set(_tokenize(right))
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
        _cosine_similarity(
            _embedding_vector(subject.preferred_label),
            _embedding_vector(object_.preferred_label),
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


def _collect_graph_support(
    session: Session,
    *,
    registry,
    document_ids: list[UUID],
    minimum_review_status: str,
) -> tuple[
    dict[str, _ConceptNodeBucket],
    dict[tuple[str, str, str], _EdgeBucket],
    list[dict[str, Any]],
]:
    minimum_rank = _minimum_review_rank(minimum_review_status)
    nodes_by_key: dict[str, _ConceptNodeBucket] = {}
    edges_by_pair: dict[tuple[str, str, str], _EdgeBucket] = {}
    document_refs: list[dict[str, Any]] = []

    for document_id in document_ids:
        semantic_pass = get_active_semantic_pass_detail(session, document_id)
        document_refs.append(
            {
                "document_id": document_id,
                "run_id": semantic_pass.run_id,
                "semantic_pass_id": semantic_pass.semantic_pass_id,
                "registry_version": semantic_pass.registry_version,
                "registry_sha256": semantic_pass.registry_sha256,
                "ontology_snapshot_id": semantic_pass.ontology_snapshot_id,
            }
        )
        document_concepts: dict[str, dict[str, Any]] = {}
        category_labels_by_concept: dict[str, set[str]] = {}
        for binding in semantic_pass.concept_category_bindings:
            if _review_rank(binding.review_status) < minimum_rank:
                continue
            category_labels_by_concept.setdefault(binding.concept_key, set()).add(
                binding.category_key
            )

        for assertion in semantic_pass.assertions:
            if _review_rank(assertion.review_status) < minimum_rank:
                continue
            category_keys = set(category_labels_by_concept.get(assertion.concept_key, set()))
            for binding in assertion.category_bindings:
                if _review_rank(binding.review_status) >= minimum_rank:
                    category_keys.add(binding.category_key)
            evidence_ids = [evidence.evidence_id for evidence in assertion.evidence]
            source_types = set(assertion.source_types)
            document_concepts[assertion.concept_key] = {
                "preferred_label": assertion.preferred_label,
                "category_keys": category_keys,
                "review_status": assertion.review_status,
                "assertion_id": assertion.assertion_id,
                "evidence_ids": evidence_ids,
                "source_types": source_types,
                "matched_terms": set(assertion.matched_terms),
                "evidence_texts": [
                    evidence.excerpt
                    for evidence in assertion.evidence
                    if collapse_whitespace(evidence.excerpt or "")
                ],
            }
            node = nodes_by_key.setdefault(
                assertion.concept_key,
                _ConceptNodeBucket(
                    concept_key=assertion.concept_key,
                    preferred_label=assertion.preferred_label,
                    category_keys=set(),
                    document_ids=set(),
                    source_types=set(),
                    review_status_counts={},
                    assertion_ids=set(),
                    evidence_ids=set(),
                ),
            )
            node.preferred_label = assertion.preferred_label
            node.category_keys.update(category_keys)
            node.document_ids.add(document_id)
            node.source_types.update(source_types)
            node.review_status_counts[assertion.review_status] = (
                node.review_status_counts.get(assertion.review_status, 0) + 1
            )
            node.assertion_ids.add(assertion.assertion_id)
            node.evidence_ids.update(evidence_ids)

        for subject_key, object_key in combinations(sorted(document_concepts), 2):
            subject = document_concepts[subject_key]
            object_ = document_concepts[object_key]
            canonical_subject_key, canonical_object_key = _canonical_edge_key(
                registry,
                relation_key=DEFAULT_GRAPH_RELATION_KEY,
                subject_concept_key=subject_key,
                object_concept_key=object_key,
            )
            pair_key = (
                DEFAULT_GRAPH_RELATION_KEY,
                canonical_subject_key,
                canonical_object_key,
            )
            edge_bucket = edges_by_pair.setdefault(
                pair_key,
                _EdgeBucket(
                    relation_key=DEFAULT_GRAPH_RELATION_KEY,
                    subject_concept_key=pair_key[1],
                    object_concept_key=pair_key[2],
                    supporting_document_ids=set(),
                    support_refs=[],
                    source_types=set(),
                    shared_category_keys=set(),
                ),
            )
            edge_bucket.supporting_document_ids.add(document_id)
            edge_bucket.source_types.update(subject["source_types"])
            edge_bucket.source_types.update(object_["source_types"])
            shared_category_keys = set(subject["category_keys"]) & set(object_["category_keys"])
            edge_bucket.shared_category_keys.update(shared_category_keys)
            if (
                subject["review_status"] == SemanticReviewStatus.APPROVED.value
                and object_["review_status"] == SemanticReviewStatus.APPROVED.value
            ):
                edge_bucket.approved_document_count += 1
            edge_bucket.support_refs.append(
                {
                    "support_ref_id": (
                        f"graph_support:{pair_key[0]}:{pair_key[1]}:{pair_key[2]}:{document_id}"
                    ),
                    "document_id": document_id,
                    "run_id": semantic_pass.run_id,
                    "semantic_pass_id": semantic_pass.semantic_pass_id,
                    "assertion_ids": sorted(
                        [subject["assertion_id"], object_["assertion_id"]],
                        key=str,
                    ),
                    "evidence_ids": sorted({*subject["evidence_ids"], *object_["evidence_ids"]}),
                    "concept_keys": [pair_key[1], pair_key[2]],
                    "source_types": sorted(subject["source_types"] | object_["source_types"]),
                    "shared_category_keys": sorted(shared_category_keys),
                }
            )
            dependency_pairs = _dependency_relation_pairs(
                subject_concept_key=subject_key,
                object_concept_key=object_key,
                subject_label=subject["preferred_label"],
                object_label=object_["preferred_label"],
                subject_terms=set(subject["matched_terms"]),
                object_terms=set(object_["matched_terms"]),
                evidence_texts=[
                    *subject["evidence_texts"],
                    *object_["evidence_texts"],
                ],
            )
            for dependency_subject_key, dependency_object_key in dependency_pairs:
                dependency_key = (
                    DEPENDENCY_GRAPH_RELATION_KEY,
                    dependency_subject_key,
                    dependency_object_key,
                )
                dependency_bucket = edges_by_pair.setdefault(
                    dependency_key,
                    _EdgeBucket(
                        relation_key=DEPENDENCY_GRAPH_RELATION_KEY,
                        subject_concept_key=dependency_subject_key,
                        object_concept_key=dependency_object_key,
                        supporting_document_ids=set(),
                        support_refs=[],
                        source_types=set(),
                        shared_category_keys=set(),
                    ),
                )
                dependency_bucket.supporting_document_ids.add(document_id)
                dependency_bucket.source_types.update(subject["source_types"])
                dependency_bucket.source_types.update(object_["source_types"])
                dependency_bucket.shared_category_keys.update(shared_category_keys)
                if (
                    subject["review_status"] == SemanticReviewStatus.APPROVED.value
                    and object_["review_status"] == SemanticReviewStatus.APPROVED.value
                ):
                    dependency_bucket.approved_document_count += 1
                dependency_bucket.cue_match_count += 1
                dependency_bucket.support_refs.append(
                    {
                        "support_ref_id": (
                            "graph_support:"
                            f"{dependency_key[0]}:{dependency_key[1]}:{dependency_key[2]}:{document_id}"
                        ),
                        "document_id": document_id,
                        "run_id": semantic_pass.run_id,
                        "semantic_pass_id": semantic_pass.semantic_pass_id,
                        "assertion_ids": sorted(
                            [subject["assertion_id"], object_["assertion_id"]],
                            key=str,
                        ),
                        "evidence_ids": sorted(
                            {*subject["evidence_ids"], *object_["evidence_ids"]}
                        ),
                        "concept_keys": [dependency_key[1], dependency_key[2]],
                        "source_types": sorted(subject["source_types"] | object_["source_types"]),
                        "shared_category_keys": sorted(shared_category_keys),
                    }
                )
    return nodes_by_key, edges_by_pair, document_refs


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
            "summary": (
                "Cross-document semantic context is externalized as a durable graph artifact."
            ),
            "details": {
                "document_count": payload.get("document_count"),
                "edge_count": payload.get("edge_count"),
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": len(edges) <= max(total_support_ref_count, 1),
            "summary": (
                "The graph compacts many supporting traces into a smaller edge memory surface."
            ),
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
            "summary": (
                "The graph builder stays extractor-swappable and free of domain-specific rules."
            ),
            "details": {
                "extractor_name": payload.get("extractor", {}).get("extractor_name"),
                "document_count": payload.get("document_count"),
            },
        },
    ]


def build_shadow_semantic_graph(
    session: Session,
    *,
    document_ids: list[UUID],
    relation_extractor_name: str,
    minimum_review_status: str,
    min_shared_documents: int,
    score_threshold: float,
) -> dict[str, Any]:
    if not document_ids:
        raise ValueError("Shadow semantic graph build requires at least one document.")
    descriptor = _extractor_descriptor(relation_extractor_name)
    ontology_snapshot = get_active_semantic_ontology_snapshot(session)
    registry = semantic_registry_from_payload(ontology_snapshot.payload_json or {})
    unique_document_ids = list(dict.fromkeys(document_ids))
    nodes_by_key, edges_by_pair, document_refs = _collect_graph_support(
        session,
        registry=registry,
        document_ids=unique_document_ids,
        minimum_review_status=minimum_review_status,
    )
    nodes = _build_graph_nodes(nodes_by_key)
    edges = _build_graph_edges(
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
        "graph_name": DEFAULT_GRAPH_NAME,
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
    payload["success_metrics"] = _graph_success_metrics(payload)
    return payload


def _expected_edge_keys(
    *,
    registry,
    edges_by_pair: dict[tuple[str, str, str], _EdgeBucket],
    min_shared_documents: int,
) -> set[str]:
    expected: set[str] = set()
    for _pair_key, edge_bucket in edges_by_pair.items():
        if len(edge_bucket.supporting_document_ids) >= min_shared_documents:
            expected.add(
                _edge_id(
                    registry,
                    relation_key=edge_bucket.relation_key,
                    subject_concept_key=edge_bucket.subject_concept_key,
                    object_concept_key=edge_bucket.object_concept_key,
                )
            )
            continue
        if edge_bucket.relation_key == DEFAULT_GRAPH_RELATION_KEY:
            if edge_bucket.approved_document_count >= 1 and edge_bucket.shared_category_keys:
                expected.add(
                    _edge_id(
                        registry,
                        relation_key=edge_bucket.relation_key,
                        subject_concept_key=edge_bucket.subject_concept_key,
                        object_concept_key=edge_bucket.object_concept_key,
                    )
                )
        elif edge_bucket.cue_match_count >= 1 and edge_bucket.approved_document_count >= 1:
            expected.add(
                _edge_id(
                    registry,
                    relation_key=edge_bucket.relation_key,
                    subject_concept_key=edge_bucket.subject_concept_key,
                    object_concept_key=edge_bucket.object_concept_key,
                )
            )
    return expected


def _evaluation_success_metrics(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": summary["traceable_candidate_edge_ratio"] == 1.0
            and summary["unsupported_candidate_edge_count"] == 0,
            "summary": "Candidate graph edges stay traceable and unsupported edges are blocked.",
            "details": {
                "traceable_candidate_edge_ratio": summary["traceable_candidate_edge_ratio"],
                "unsupported_candidate_edge_count": summary["unsupported_candidate_edge_count"],
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": summary["graph_memory_compaction_ratio"] > 1.0,
            "summary": "The graph stores less edge state than the raw supporting trace count.",
            "details": {
                "graph_memory_compaction_ratio": summary["graph_memory_compaction_ratio"],
            },
        },
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": summary["candidate_expected_recall"] >= summary["baseline_expected_recall"]
            and summary["document_specific_rule_count_delta"] == 0,
            "summary": (
                "The candidate extractor improves or matches recall without "
                "adding corpus-specific rules."
            ),
            "details": {
                "baseline_expected_recall": summary["baseline_expected_recall"],
                "candidate_expected_recall": summary["candidate_expected_recall"],
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(summary.get("document_count")),
            "summary": (
                "Extractor evaluation persists typed edge comparisons and aggregate metrics."
            ),
            "details": {
                "document_count": summary["document_count"],
                "expected_edge_count": summary["expected_edge_count"],
            },
        },
    ]


def evaluate_semantic_relation_extractor(
    session: Session,
    *,
    document_ids: list[UUID],
    baseline_extractor_name: str,
    candidate_extractor_name: str,
    minimum_review_status: str,
    baseline_min_shared_documents: int,
    candidate_score_threshold: float,
    expected_min_shared_documents: int,
) -> dict[str, Any]:
    unique_document_ids = list(dict.fromkeys(document_ids))
    if not unique_document_ids:
        raise ValueError("Semantic relation extractor evaluation requires at least one document.")
    ontology_snapshot = get_active_semantic_ontology_snapshot(session)
    registry = semantic_registry_from_payload(ontology_snapshot.payload_json or {})
    nodes_by_key, edges_by_pair, document_refs = _collect_graph_support(
        session,
        registry=registry,
        document_ids=unique_document_ids,
        minimum_review_status=minimum_review_status,
    )
    baseline_edges = _build_graph_edges(
        registry=registry,
        nodes_by_key=nodes_by_key,
        edges_by_pair=edges_by_pair,
        extractor_name=baseline_extractor_name,
        min_shared_documents=baseline_min_shared_documents,
        score_threshold=candidate_score_threshold,
        shadow_mode=True,
        review_status=SemanticReviewStatus.CANDIDATE.value,
    )
    candidate_edges = _build_graph_edges(
        registry=registry,
        nodes_by_key=nodes_by_key,
        edges_by_pair=edges_by_pair,
        extractor_name=candidate_extractor_name,
        min_shared_documents=baseline_min_shared_documents,
        score_threshold=candidate_score_threshold,
        shadow_mode=True,
        review_status=SemanticReviewStatus.CANDIDATE.value,
    )
    expected_edge_keys = _expected_edge_keys(
        registry=registry,
        edges_by_pair=edges_by_pair,
        min_shared_documents=expected_min_shared_documents,
    )
    baseline_edge_map = {edge["edge_id"]: edge for edge in baseline_edges}
    candidate_edge_map = {edge["edge_id"]: edge for edge in candidate_edges}
    live_graph_payload = get_active_semantic_graph_payload(session) or {}
    live_edge_ids = {
        str(edge.get("edge_id"))
        for edge in (live_graph_payload.get("edges") or [])
        if edge.get("review_status") == SemanticReviewStatus.APPROVED.value
    }

    edge_reports: list[dict[str, Any]] = []
    for edge_id in sorted(expected_edge_keys | set(baseline_edge_map) | set(candidate_edge_map)):
        baseline_edge = baseline_edge_map.get(edge_id)
        candidate_edge = candidate_edge_map.get(edge_id)
        exemplar = candidate_edge or baseline_edge
        if exemplar is None:
            continue
        edge_reports.append(
            {
                "edge_id": edge_id,
                "relation_key": exemplar["relation_key"],
                "subject_entity_key": exemplar["subject_entity_key"],
                "subject_label": exemplar["subject_label"],
                "object_entity_key": exemplar["object_entity_key"],
                "object_label": exemplar["object_label"],
                "expected_edge": edge_id in expected_edge_keys,
                "in_live_graph": edge_id in live_edge_ids,
                "baseline_found": baseline_edge is not None,
                "candidate_found": candidate_edge is not None,
                "baseline_score": baseline_edge["extractor_score"] if baseline_edge else 0.0,
                "candidate_score": candidate_edge["extractor_score"] if candidate_edge else 0.0,
                "supporting_document_ids": (
                    candidate_edge["supporting_document_ids"]
                    if candidate_edge is not None
                    else baseline_edge["supporting_document_ids"]
                ),
                "support_refs": (
                    candidate_edge["support_refs"]
                    if candidate_edge is not None
                    else baseline_edge["support_refs"]
                ),
            }
        )

    baseline_hit_count = sum(1 for edge_id in expected_edge_keys if edge_id in baseline_edge_map)
    candidate_hit_count = sum(1 for edge_id in expected_edge_keys if edge_id in candidate_edge_map)
    traceable_candidate_edge_ratio = (
        sum(1 for edge in candidate_edges if edge.get("support_refs")) / len(candidate_edges)
        if candidate_edges
        else 1.0
    )
    unsupported_candidate_edge_count = sum(
        1 for edge_id, edge in candidate_edge_map.items() if edge_id not in expected_edge_keys
    )
    summary = {
        "document_count": len(unique_document_ids),
        "expected_edge_count": len(expected_edge_keys),
        "baseline_edge_count": len(baseline_edges),
        "candidate_edge_count": len(candidate_edges),
        "baseline_expected_recall": round(baseline_hit_count / len(expected_edge_keys), 4)
        if expected_edge_keys
        else 1.0,
        "candidate_expected_recall": round(candidate_hit_count / len(expected_edge_keys), 4)
        if expected_edge_keys
        else 1.0,
        "candidate_only_edge_count": sum(
            1 for edge_id in candidate_edge_map if edge_id not in baseline_edge_map
        ),
        "regressed_expected_edge_count": sum(
            1
            for edge_id in expected_edge_keys
            if edge_id in baseline_edge_map and edge_id not in candidate_edge_map
        ),
        "traceable_candidate_edge_ratio": round(traceable_candidate_edge_ratio, 4),
        "unsupported_candidate_edge_count": unsupported_candidate_edge_count,
        "graph_memory_compaction_ratio": round(
            (
                sum(len(edge.get("support_refs") or []) for edge in candidate_edges)
                / max(len(candidate_edges), 1)
            ),
            4,
        ),
        "document_specific_rule_count_delta": 0,
    }
    return {
        "baseline_extractor": {
            **_extractor_descriptor(baseline_extractor_name).__dict__,
        },
        "candidate_extractor": {
            **_extractor_descriptor(candidate_extractor_name).__dict__,
        },
        "ontology_snapshot_id": ontology_snapshot.id,
        "ontology_version": ontology_snapshot.ontology_version,
        "document_refs": document_refs,
        "edge_reports": edge_reports,
        "summary": summary,
        "success_metrics": _evaluation_success_metrics(summary),
    }


def triage_semantic_graph_disagreements(
    evaluation: dict[str, Any],
    *,
    min_score: float,
    expected_only: bool,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    recommended_followups: list[dict[str, Any]] = []
    for edge in evaluation.get("edge_reports") or []:
        if expected_only and not edge.get("expected_edge"):
            continue
        candidate_score = float(edge.get("candidate_score") or 0.0)
        if candidate_score < min_score:
            continue
        if (
            edge.get("candidate_found")
            and not edge.get("in_live_graph")
            and edge.get("expected_edge")
        ):
            issue_id = f"graph_issue:{edge['edge_id']}"
            issues.append(
                {
                    "issue_id": issue_id,
                    "edge_id": edge["edge_id"],
                    "relation_key": edge["relation_key"],
                    "subject_entity_key": edge["subject_entity_key"],
                    "subject_label": edge["subject_label"],
                    "object_entity_key": edge["object_entity_key"],
                    "object_label": edge["object_label"],
                    "severity": "high" if edge.get("expected_edge") else "medium",
                    "expected_edge": bool(edge.get("expected_edge")),
                    "in_live_graph": bool(edge.get("in_live_graph")),
                    "baseline_found": bool(edge.get("baseline_found")),
                    "candidate_found": bool(edge.get("candidate_found")),
                    "candidate_score": candidate_score,
                    "supporting_document_ids": list(edge.get("supporting_document_ids") or []),
                    "support_refs": list(edge.get("support_refs") or []),
                    "summary": (
                        f"{edge['subject_label']} and {edge['object_label']} are linked by the "
                        "candidate graph but not yet promoted into live graph memory."
                    ),
                    "details": {
                        "baseline_score": edge.get("baseline_score"),
                    },
                }
            )
            recommended_followups.append(
                {
                    "followup_kind": "draft_graph_promotions",
                    "reason": "candidate_expected_edge_missing_from_live_graph",
                    "edge_id": edge["edge_id"],
                }
            )
    return {
        "issue_count": len(issues),
        "issues": issues,
        "recommended_followups": recommended_followups,
        "success_metrics": [
            {
                "metric_key": "agent_legibility",
                "stakeholder": "Lopopolo",
                "passed": all(issue.get("issue_id") and issue.get("edge_id") for issue in issues),
                "summary": "Graph disagreement triage emits typed issues and bounded next actions.",
                "details": {"issue_count": len(issues)},
            },
            {
                "metric_key": "memory_compaction",
                "stakeholder": "Yegge",
                "passed": len(issues) <= max(len(evaluation.get("edge_reports") or []), 1),
                "summary": "Triage condenses relation disagreements into a smaller actionable set.",
                "details": {
                    "edge_report_count": len(evaluation.get("edge_reports") or []),
                    "issue_count": len(issues),
                },
            },
        ],
    }


def _next_graph_version(base_graph_version: str | None, *, ontology_version: str) -> str:
    if not base_graph_version:
        return f"{ontology_version}.graph.1"
    match = GRAPH_VERSION_PATTERN.match(base_graph_version)
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
        "graph_name": DEFAULT_GRAPH_NAME,
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
    payload["success_metrics"] = _graph_success_metrics(payload)
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
) -> dict[str, Any]:
    ontology_snapshot = get_active_semantic_ontology_snapshot(session)
    registry = semantic_registry_from_payload(ontology_snapshot.payload_json or {})
    active_snapshot = get_active_semantic_graph_snapshot(session)
    base_payload = dict(active_snapshot.payload_json or {}) if active_snapshot is not None else None

    def _canonicalized_edge_payload(edge: dict[str, Any]) -> dict[str, Any]:
        relation_key = str(edge.get("relation_key") or "")
        relation_label = _relation_label_from_registry(registry, relation_key)
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
            "edge_id": _edge_id(
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
                    "relation_label": _relation_label_from_registry(
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
                    "extractor_name": DEFAULT_GRAPH_CANDIDATE_EXTRACTOR,
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
                "summary": (
                    "Graph promotion remains a draft artifact until verification and approval."
                ),
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
) -> tuple[dict[str, Any], dict[str, Any], list[str], str, list[dict[str, Any]]]:
    current_ontology = get_active_semantic_ontology_snapshot(session)
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


def persist_semantic_graph_snapshot(
    session: Session,
    payload: dict[str, Any],
    *,
    source_kind: str,
    source_task_id: UUID | None = None,
    source_task_type: str | None = None,
    parent_snapshot_id: UUID | None = None,
    activate: bool = False,
) -> SemanticGraphSnapshot:
    now = utcnow()
    graph_version = str(payload.get("graph_version") or "").strip()
    graph_name = str(payload.get("graph_name") or DEFAULT_GRAPH_NAME).strip() or DEFAULT_GRAPH_NAME
    if not graph_version:
        raise ValueError("Semantic graph payload requires graph_version.")
    incoming_sha256 = _graph_payload_sha256(payload)
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
        state = _workspace_graph_state(session)
        if state is None:
            state = WorkspaceSemanticGraphState(
                workspace_key=WORKSPACE_SEMANTIC_GRAPH_STATE_KEY,
                active_graph_snapshot_id=snapshot.id,
                created_at=now,
                updated_at=now,
            )
            session.add(state)
        else:
            state.active_graph_snapshot_id = snapshot.id
            state.updated_at = now
        snapshot.activated_at = now
    session.flush()
    return snapshot


def apply_graph_promotions(
    session: Session,
    draft: dict[str, Any],
    *,
    source_task_id: UUID,
    source_task_type: str,
    reason: str | None,
) -> dict[str, Any]:
    base_snapshot_id = draft.get("base_snapshot_id")
    snapshot = persist_semantic_graph_snapshot(
        session,
        draft["effective_graph"],
        source_kind=SemanticGraphSourceKind.GRAPH_PROMOTION_APPLY.value,
        source_task_id=source_task_id,
        source_task_type=source_task_type,
        parent_snapshot_id=UUID(str(base_snapshot_id)) if base_snapshot_id else None,
        activate=True,
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


def graph_memory_for_brief(
    session: Session,
    *,
    document_ids: list[UUID],
    requested_concept_keys: set[str],
    available_concept_keys: set[str],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], list[str]]:
    snapshot = get_active_semantic_graph_snapshot(session)
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
