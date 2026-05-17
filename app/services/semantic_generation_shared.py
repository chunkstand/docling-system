from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.text import collapse_whitespace

DOCUMENT_KIND_KNOWLEDGE_BRIEF = "knowledge_brief"
TARGET_LENGTH_EVIDENCE_LIMIT = {
    "short": 2,
    "medium": 3,
    "long": 5,
}

TARGET_LENGTH_EVIDENCE_LIMIT = {
    "short": 2,
    "medium": 3,
    "long": 5,
}


def _graph_claim_summary(graph_edge: dict[str, Any]) -> str:
    relation_label = collapse_whitespace(str(graph_edge.get("relation_label") or ""))
    subject_label = str(graph_edge.get("subject_label") or "")
    object_label = str(graph_edge.get("object_label") or "")
    document_count = len(graph_edge.get("supporting_document_ids") or [])
    document_phrase = f"{document_count} document{'' if document_count == 1 else 's'}"
    if relation_label and relation_label != "Concept Related To Concept":
        return (
            f"{subject_label} is connected to {object_label} through the approved "
            f"{relation_label.lower()} relation across {document_phrase}."
        )
    return (
        f"{subject_label} is linked to {object_label} through approved "
        f"cross-document graph memory across {document_phrase}."
    )


@dataclass(frozen=True)
class SemanticGroundedDocumentVerificationOutcome:
    summary: dict[str, Any]
    success_metrics: list[dict[str, Any]]
    verification_outcome: str
    verification_metrics: dict[str, Any]
    verification_reasons: list[str]
    verification_details: dict[str, Any]


def _sorted_unique_strings(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _join_words(values: list[str]) -> str:
    ordered = [value for value in values if value]
    if not ordered:
        return "no sources"
    if len(ordered) == 1:
        return ordered[0]
    if len(ordered) == 2:
        return f"{ordered[0]} and {ordered[1]}"
    return f"{', '.join(ordered[:-1])}, and {ordered[-1]}"


def _document_label(document_ref: dict[str, Any]) -> str:
    return str(document_ref.get("title") or document_ref.get("source_filename") or "document")


def _page_label(page_from: int | None, page_to: int | None) -> str:
    if page_from is None and page_to is None:
        return "unknown pages"
    if page_from == page_to or page_to is None:
        return f"page {page_from}"
    if page_from is None:
        return f"page {page_to}"
    return f"pages {page_from}-{page_to}"


def _support_level(
    assertions: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    evidence_count: int,
) -> str:
    approved_count = sum(1 for row in assertions if row["review_status"] == "approved")
    approved_fact_count = sum(1 for row in facts if row["review_status"] == "approved")
    if (approved_count or approved_fact_count) and evidence_count >= 2:
        return "strong"
    if approved_count or approved_fact_count or facts or evidence_count >= 2:
        return "supported"
    return "provisional"


def _review_policy_projection(
    assertions: list[dict[str, Any]],
    *,
    review_policy: str,
) -> tuple[list[dict[str, Any]], str, str | None]:
    supported_assertions = [row for row in assertions if row["review_status"] != "rejected"]
    if review_policy == "approved_only":
        approved_assertions = [
            row for row in supported_assertions if row["review_status"] == "approved"
        ]
        disclosure_note = None
        return approved_assertions, "approved_only", disclosure_note

    approved_count = sum(1 for row in supported_assertions if row["review_status"] == "approved")
    candidate_count = sum(1 for row in supported_assertions if row["review_status"] == "candidate")
    if approved_count and candidate_count:
        return (
            supported_assertions,
            "mixed_support_disclosed",
            "This claim includes candidate semantic support and should be "
            "reviewed before publication.",
        )
    if candidate_count:
        return (
            supported_assertions,
            "candidate_disclosed",
            "This claim is backed by candidate semantic assertions and should "
            "be reviewed before publication.",
        )
    return supported_assertions, "approved_support", None


def _matches_filters(
    concept_key: str,
    category_keys: list[str],
    *,
    requested_concept_keys: set[str],
    requested_category_keys: set[str],
) -> bool:
    if requested_concept_keys and concept_key in requested_concept_keys:
        return True
    if (
        requested_concept_keys
        and concept_key not in requested_concept_keys
        and not requested_category_keys
    ):
        return False
    if requested_category_keys and set(category_keys).intersection(requested_category_keys):
        return True
    return not requested_concept_keys and not requested_category_keys


def _concept_sort_key(
    entry: dict[str, Any],
    *,
    requested_concept_order: dict[str, int],
) -> tuple[int, str]:
    concept_key = str(entry["concept_key"])
    preferred_label = collapse_whitespace(entry["preferred_label"]).lower()
    if concept_key in requested_concept_order:
        return requested_concept_order[concept_key], preferred_label
    return len(requested_concept_order) + 1000, preferred_label


def _primary_category(
    entry: dict[str, Any],
    *,
    requested_category_order: dict[str, int],
) -> tuple[str | None, str | None]:
    keys = list(entry["category_keys"])
    labels = dict(entry["category_labels"])
    if not keys:
        return None, None
    if requested_category_order:
        for category_key in requested_category_order:
            if category_key in keys:
                return category_key, labels.get(category_key)
    ordered = sorted(keys, key=lambda key: (labels.get(key, key).lower(), key))
    category_key = ordered[0]
    return category_key, labels.get(category_key)


def _build_claim_summary(
    concept_entry: dict[str, Any],
    *,
    document_refs_by_id: dict[UUID, dict[str, Any]],
) -> str:
    document_labels = [
        _document_label(document_refs_by_id[document_id])
        for document_id in concept_entry["document_ids"]
        if document_id in document_refs_by_id
    ]
    document_phrase = (
        document_labels[0]
        if len(document_labels) == 1
        else f"{len(document_labels)} documents ({', '.join(document_labels[:2])})"
    )
    source_phrase = _join_words(list(concept_entry["source_types"]))
    evidence_count = int(concept_entry["evidence_count"])
    evidence_phrase = "evidence item" if evidence_count == 1 else "evidence items"
    return (
        f"{concept_entry['preferred_label']} appears in {document_phrase} with "
        f"{evidence_count} {evidence_phrase} across {source_phrase} sources."
    )



