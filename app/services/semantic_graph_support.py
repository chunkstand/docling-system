from __future__ import annotations

from itertools import combinations
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.db.public.semantic_memory import SemanticReviewStatus
from app.services import semantic_graph_core as _semantic_graph_core


def _collect_graph_support(
    session: Session,
    *,
    registry,
    document_ids: list[UUID],
    minimum_review_status: str,
    get_active_semantic_pass_detail_fn,
) -> tuple[
    dict[str, _semantic_graph_core._ConceptNodeBucket],
    dict[tuple[str, str, str], _semantic_graph_core._EdgeBucket],
    list[dict[str, Any]],
]:
    minimum_rank = _semantic_graph_core._minimum_review_rank(minimum_review_status)
    nodes_by_key: dict[str, _semantic_graph_core._ConceptNodeBucket] = {}
    edges_by_pair: dict[tuple[str, str, str], _semantic_graph_core._EdgeBucket] = {}
    document_refs: list[dict[str, Any]] = []

    for document_id in document_ids:
        semantic_pass = get_active_semantic_pass_detail_fn(session, document_id)
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
            if _semantic_graph_core._review_rank(binding.review_status) < minimum_rank:
                continue
            category_labels_by_concept.setdefault(binding.concept_key, set()).add(
                binding.category_key
            )

        for assertion in semantic_pass.assertions:
            if _semantic_graph_core._review_rank(assertion.review_status) < minimum_rank:
                continue
            category_keys = set(category_labels_by_concept.get(assertion.concept_key, set()))
            for binding in assertion.category_bindings:
                if _semantic_graph_core._review_rank(binding.review_status) >= minimum_rank:
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
                _semantic_graph_core._ConceptNodeBucket(
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
            canonical_subject_key, canonical_object_key = _semantic_graph_core._canonical_edge_key(
                registry,
                relation_key=_semantic_graph_core.DEFAULT_GRAPH_RELATION_KEY,
                subject_concept_key=subject_key,
                object_concept_key=object_key,
            )
            pair_key = (
                _semantic_graph_core.DEFAULT_GRAPH_RELATION_KEY,
                canonical_subject_key,
                canonical_object_key,
            )
            edge_bucket = edges_by_pair.setdefault(
                pair_key,
                _semantic_graph_core._EdgeBucket(
                    relation_key=_semantic_graph_core.DEFAULT_GRAPH_RELATION_KEY,
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
                        "graph_support:"
                        f"{pair_key[0]}:{pair_key[1]}:{pair_key[2]}:{document_id}"
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
            dependency_pairs = _semantic_graph_core._dependency_relation_pairs(
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
                    _semantic_graph_core.DEPENDENCY_GRAPH_RELATION_KEY,
                    dependency_subject_key,
                    dependency_object_key,
                )
                dependency_bucket = edges_by_pair.setdefault(
                    dependency_key,
                    _semantic_graph_core._EdgeBucket(
                        relation_key=_semantic_graph_core.DEPENDENCY_GRAPH_RELATION_KEY,
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
