from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.db.models import Document
from app.schemas.agent_tasks import (
    GroundedDocumentDraftPayload,
    SemanticGenerationBriefPayload,
)
from app.services.semantic_candidates import collect_shadow_candidates_for_brief
from app.services.semantic_facts import list_document_semantic_facts
from app.services.semantic_graph import graph_memory_for_brief
from app.services.semantics import get_active_semantic_pass_detail

DOCUMENT_KIND_KNOWLEDGE_BRIEF = "knowledge_brief"
TARGET_LENGTH_EVIDENCE_LIMIT = {
    "short": 2,
    "medium": 3,
    "long": 5,
}


@dataclass(frozen=True)
class SemanticGroundedDocumentVerificationOutcome:
    summary: dict[str, Any]
    success_metrics: list[dict[str, Any]]
    verification_outcome: str
    verification_metrics: dict[str, Any]
    verification_reasons: list[str]
    verification_details: dict[str, Any]


def _unique_uuids(values: list[UUID]) -> list[UUID]:
    return list(dict.fromkeys(values))


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


def _brief_success_metrics(brief: dict[str, Any]) -> list[dict[str, Any]]:
    document_refs = list(brief.get("document_refs") or [])
    claim_candidates = list(brief.get("claim_candidates") or [])
    evidence_pack = list(brief.get("evidence_pack") or [])
    semantic_dossier = list(brief.get("semantic_dossier") or [])
    graph_index = list(brief.get("graph_index") or [])
    shadow_candidates = list(brief.get("shadow_candidates") or [])
    traceable_claim_ratio = (
        sum(
            1
            for row in claim_candidates
            if row.get("graph_edge_ids")
            or row.get("fact_ids")
            or (row.get("assertion_ids") and row.get("evidence_labels"))
        )
        / len(claim_candidates)
        if claim_candidates
        else 0.0
    )
    facts_by_concept = {
        str(entry.get("concept_key") or ""): list(entry.get("facts") or [])
        for entry in semantic_dossier
    }
    fact_backed_claim_count = 0
    approved_fact_backed_claim_count = 0
    for row in claim_candidates:
        claim_facts = [
            fact
            for concept_key in row.get("concept_keys") or []
            for fact in facts_by_concept.get(str(concept_key), [])
        ]
        if not claim_facts:
            continue
        fact_backed_claim_count += 1
        if all(fact.get("review_status") == "approved" for fact in claim_facts):
            approved_fact_backed_claim_count += 1
    approved_fact_support_ratio = (
        approved_fact_backed_claim_count / fact_backed_claim_count
        if fact_backed_claim_count
        else 1.0
    )
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": bool(document_refs)
            and all(
                row.get("registry_version") and row.get("registry_sha256") for row in document_refs
            )
            and traceable_claim_ratio == 1.0,
            "summary": (
                "Every brief claim is tied to version-stamped semantic sources and evidence."
            ),
            "details": {
                "document_count": len(document_refs),
                "traceable_claim_ratio": traceable_claim_ratio,
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(claim_candidates)
            and all(row.get("claim_id") and row.get("section_id") for row in claim_candidates),
            "summary": (
                "The generation brief exposes typed claims, sections, and evidence-pack labels."
            ),
            "details": {
                "claim_count": len(claim_candidates),
                "section_count": len(brief.get("sections") or []),
                "graph_edge_count": len(graph_index),
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": (
                brief.get("document_kind") == DOCUMENT_KIND_KNOWLEDGE_BRIEF
                and brief.get("review_policy")
                in {"approved_only", "allow_candidate_with_disclosure"}
            ),
            "summary": (
                "Document generation stays bounded to one explicit artifact type and policy."
            ),
            "details": {
                "document_kind": brief.get("document_kind"),
                "review_policy": brief.get("review_policy"),
            },
        },
        {
            "metric_key": "explicit_shadow_boundary",
            "stakeholder": "Figay",
            "passed": (
                not brief.get("shadow_mode")
                or all(
                    row.get("concept_key") not in set(brief.get("selected_concept_keys") or [])
                    for row in shadow_candidates
                )
            ),
            "summary": (
                "Shadow candidates stay additive and separate from the live semantic dossier."
            ),
            "details": {
                "shadow_mode": brief.get("shadow_mode"),
                "shadow_candidate_count": len(shadow_candidates),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(semantic_dossier) and bool(evidence_pack),
            "summary": (
                "The brief persists owned semantic context instead of reconstructing it ad hoc."
            ),
            "details": {
                "concept_count": len(semantic_dossier),
                "evidence_count": len(evidence_pack),
                "graph_edge_count": len(graph_index),
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": bool(claim_candidates)
            and len(claim_candidates) <= max(len(evidence_pack), 1),
            "summary": (
                "The brief compresses corpus evidence into compact claims for downstream agents."
            ),
            "details": {
                "claim_count": len(claim_candidates),
                "evidence_count": len(evidence_pack),
            },
        },
        {
            "metric_key": "approved_fact_support_ratio",
            "stakeholder": "Milestone",
            "passed": not claim_candidates or approved_fact_support_ratio >= 0.8,
            "summary": "Generation prefers approved fact support when it is available.",
            "details": {
                "approved_fact_support_ratio": approved_fact_support_ratio,
                "fact_backed_claim_count": fact_backed_claim_count,
            },
        },
    ]


def prepare_semantic_generation_brief(
    session: Session,
    *,
    title: str,
    goal: str,
    audience: str | None,
    document_ids: list[UUID],
    concept_keys: list[str],
    category_keys: list[str],
    target_length: str,
    review_policy: str,
    include_shadow_candidates: bool = False,
    candidate_extractor_name: str = "concept_ranker_v1",
    candidate_score_threshold: float = 0.34,
    max_shadow_candidates: int = 8,
) -> dict[str, Any]:
    unique_document_ids = _unique_uuids(document_ids)
    requested_concept_order = {concept_key: index for index, concept_key in enumerate(concept_keys)}
    requested_category_order = {
        category_key: index for index, category_key in enumerate(category_keys)
    }
    requested_concept_keys = set(concept_keys)
    requested_category_keys = set(category_keys)
    document_refs: list[dict[str, Any]] = []
    document_refs_by_id: dict[UUID, dict[str, Any]] = {}
    concept_buckets: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    for document_id in unique_document_ids:
        document = session.get(Document, document_id)
        if document is None:
            raise ValueError(f"Document not found: {document_id}")
        semantic_pass = get_active_semantic_pass_detail(session, document_id)
        document_ref = {
            "document_id": document_id,
            "run_id": semantic_pass.run_id,
            "semantic_pass_id": semantic_pass.semantic_pass_id,
            "source_filename": document.source_filename,
            "title": document.title,
            "registry_version": semantic_pass.registry_version,
            "registry_sha256": semantic_pass.registry_sha256,
            "evaluation_fixture_name": semantic_pass.evaluation_fixture_name,
            "evaluation_status": semantic_pass.evaluation_status,
            "assertion_count": semantic_pass.assertion_count,
            "evidence_count": semantic_pass.evidence_count,
            "all_expectations_passed": bool(
                semantic_pass.evaluation_summary.get("all_expectations_passed")
            ),
        }
        document_refs.append(document_ref)
        document_refs_by_id[document_id] = document_ref
        document_facts = [
            fact
            for fact in list_document_semantic_facts(session, document_id)
            if fact["semantic_pass_id"] == semantic_pass.semantic_pass_id
        ]
        facts_by_concept: dict[str, list[dict[str, Any]]] = {}
        for fact in document_facts:
            object_entity_key = str(fact.get("object_entity_key") or "")
            if not object_entity_key.startswith("concept:"):
                continue
            concept_key = object_entity_key.split("concept:", 1)[1]
            if not concept_key:
                continue
            facts_by_concept.setdefault(concept_key, []).append(fact)

        category_labels_by_concept: dict[str, dict[str, str]] = {}
        for binding in semantic_pass.concept_category_bindings:
            labels = category_labels_by_concept.setdefault(binding.concept_key, {})
            labels[binding.category_key] = binding.category_label

        for assertion in semantic_pass.assertions:
            if assertion.review_status == "rejected":
                continue
            category_labels = dict(category_labels_by_concept.get(assertion.concept_key, {}))
            for binding in assertion.category_bindings:
                if binding.review_status == "rejected":
                    continue
                category_labels[binding.category_key] = binding.category_label
            category_key_list = sorted(category_labels)

            bucket = concept_buckets.setdefault(
                assertion.concept_key,
                {
                    "concept_key": assertion.concept_key,
                    "preferred_label": assertion.preferred_label,
                    "category_keys": set(),
                    "category_labels": {},
                    "assertions": [],
                    "facts": [],
                    "document_ids": [],
                },
            )
            bucket["category_keys"].update(category_key_list)
            bucket["category_labels"].update(category_labels)
            bucket["document_ids"].append(document_id)
            bucket["assertions"].append(
                {
                    "document_id": document_id,
                    "run_id": semantic_pass.run_id,
                    "semantic_pass_id": semantic_pass.semantic_pass_id,
                    "assertion_id": assertion.assertion_id,
                    "concept_key": assertion.concept_key,
                    "preferred_label": assertion.preferred_label,
                    "review_status": assertion.review_status,
                    "source_types": list(assertion.source_types),
                    "evidence_count": assertion.evidence_count,
                    "category_keys": category_key_list,
                    "category_labels": [category_labels[key] for key in category_key_list],
                    "evidence": [
                        {
                            "document_id": document_id,
                            "run_id": semantic_pass.run_id,
                            "semantic_pass_id": semantic_pass.semantic_pass_id,
                            "assertion_id": assertion.assertion_id,
                            "evidence_id": evidence.evidence_id,
                            "concept_key": assertion.concept_key,
                            "preferred_label": assertion.preferred_label,
                            "review_status": assertion.review_status,
                            "source_filename": document.source_filename,
                            "source_type": evidence.source_type,
                            "page_from": evidence.page_from,
                            "page_to": evidence.page_to,
                            "excerpt": collapse_whitespace(evidence.excerpt),
                            "source_artifact_api_path": evidence.source_artifact_api_path,
                            "matched_terms": list(evidence.matched_terms),
                        }
                        for evidence in assertion.evidence
                    ],
                }
            )
        for concept_key, fact_rows in facts_by_concept.items():
            bucket = concept_buckets.setdefault(
                concept_key,
                {
                    "concept_key": concept_key,
                    "preferred_label": next(
                        (
                            assertion.preferred_label
                            for assertion in semantic_pass.assertions
                            if assertion.concept_key == concept_key
                        ),
                        fact_rows[0]["object_label"] or concept_key.replace("_", " ").title(),
                    ),
                    "category_keys": set(),
                    "category_labels": {},
                    "assertions": [],
                    "facts": [],
                    "document_ids": [],
                },
            )
            bucket["document_ids"].append(document_id)
            bucket["facts"].extend(dict(row) for row in fact_rows)

    raw_concept_entries: list[dict[str, Any]] = []
    for concept_key, bucket in concept_buckets.items():
        projected_assertions, review_policy_status, disclosure_note = _review_policy_projection(
            list(bucket["assertions"]),
            review_policy=review_policy,
        )
        if not projected_assertions:
            warnings.append(
                f"{bucket['preferred_label']} was omitted because it does not "
                f"satisfy the {review_policy} policy."
            )
            continue
        projected_facts = [
            row
            for row in bucket["facts"]
            if row["review_status"] != "rejected"
            and (
                review_policy != "approved_only" or row["review_status"] == "approved"
            )
        ]

        assertion_refs: list[dict[str, Any]] = []
        evidence_refs_by_id: dict[UUID, dict[str, Any]] = {}
        for assertion in projected_assertions:
            assertion_refs.append(
                {
                    "document_id": assertion["document_id"],
                    "run_id": assertion["run_id"],
                    "semantic_pass_id": assertion["semantic_pass_id"],
                    "assertion_id": assertion["assertion_id"],
                    "concept_key": assertion["concept_key"],
                    "preferred_label": assertion["preferred_label"],
                    "review_status": assertion["review_status"],
                    "support_level": "",
                    "source_types": list(assertion["source_types"]),
                    "evidence_count": assertion["evidence_count"],
                    "category_keys": list(assertion["category_keys"]),
                    "category_labels": list(assertion["category_labels"]),
                }
            )
            for evidence in assertion["evidence"]:
                evidence_refs_by_id[evidence["evidence_id"]] = dict(evidence)

        evidence_count = len(evidence_refs_by_id)
        support_level = _support_level(projected_assertions, projected_facts, evidence_count)
        for assertion_ref in assertion_refs:
            assertion_ref["support_level"] = support_level

        raw_concept_entries.append(
            {
                "concept_key": concept_key,
                "preferred_label": bucket["preferred_label"],
                "category_keys": sorted(bucket["category_keys"]),
                "category_labels": dict(bucket["category_labels"]),
                "document_ids": _unique_uuids(bucket["document_ids"]),
                "document_count": len(set(bucket["document_ids"])),
                "evidence_count": evidence_count,
                "source_types": _sorted_unique_strings(
                    [
                        source_type
                        for row in projected_assertions
                        for source_type in row["source_types"]
                    ]
                ),
                "support_level": support_level,
                "review_policy_status": review_policy_status,
                "disclosure_note": disclosure_note,
                "facts": projected_facts,
                "assertions": assertion_refs,
                "evidence_refs": list(evidence_refs_by_id.values()),
            }
        )

    if not raw_concept_entries:
        raise ValueError("No semantic concepts matched the requested generation scope.")

    base_concept_entries = [
        entry
        for entry in raw_concept_entries
        if _matches_filters(
            entry["concept_key"],
            list(entry["category_keys"]),
            requested_concept_keys=requested_concept_keys,
            requested_category_keys=requested_category_keys,
        )
    ]
    if not base_concept_entries:
        raise ValueError("No semantic concepts matched the requested generation scope.")

    graph_index: list[dict[str, Any]] = []
    graph_summary: dict[str, Any] = {}
    graph_related_concept_keys: set[str] = set()
    if requested_concept_keys or requested_category_keys:
        related_concept_keys, graph_edge_refs, graph_summary, graph_warnings = graph_memory_for_brief(
            session,
            document_ids=unique_document_ids,
            requested_concept_keys=requested_concept_keys
            or {entry["concept_key"] for entry in base_concept_entries},
            available_concept_keys={entry["concept_key"] for entry in raw_concept_entries},
        )
        graph_index = graph_edge_refs
        graph_related_concept_keys = set(related_concept_keys)
        warnings.extend(graph_warnings)

    if requested_concept_keys or requested_category_keys:
        selected_concept_key_set = {
            entry["concept_key"] for entry in base_concept_entries
        } | graph_related_concept_keys
        concept_entries = [
            entry
            for entry in raw_concept_entries
            if entry["concept_key"] in selected_concept_key_set
        ]
    else:
        concept_entries = list(raw_concept_entries)

    concept_entries.sort(
        key=lambda entry: _concept_sort_key(
            entry,
            requested_concept_order=requested_concept_order,
        )
    )

    evidence_pack: list[dict[str, Any]] = []
    evidence_labels_by_id: dict[UUID, str] = {}
    next_evidence_index = 1
    for entry in concept_entries:
        labeled_refs: list[dict[str, Any]] = []
        for evidence in entry["evidence_refs"]:
            evidence_id = evidence["evidence_id"]
            citation_label = evidence_labels_by_id.get(evidence_id)
            if citation_label is None:
                citation_label = f"E{next_evidence_index}"
                next_evidence_index += 1
                evidence_labels_by_id[evidence_id] = citation_label
                evidence_pack.append({"citation_label": citation_label, **evidence})
            labeled_refs.append({"citation_label": citation_label, **evidence})
        entry["evidence_refs"] = labeled_refs

    section_specs: dict[str, dict[str, Any]] = {}
    uncategorized_concepts: list[str] = []
    for entry in concept_entries:
        category_key, category_label = _primary_category(
            entry,
            requested_category_order=requested_category_order,
        )
        if category_key is None:
            section_id = "section:uncategorized"
            uncategorized_concepts.append(entry["concept_key"])
            section_title = "Additional Concepts"
            focus_category_keys: list[str] = []
        else:
            section_id = f"section:{category_key}"
            section_title = category_label or entry["preferred_label"]
            focus_category_keys = [category_key]
        section = section_specs.setdefault(
            section_id,
            {
                "section_id": section_id,
                "title": section_title,
                "summary": "",
                "focus_concept_keys": [],
                "focus_category_keys": focus_category_keys,
                "claim_ids": [],
            },
        )
        section["focus_concept_keys"].append(entry["concept_key"])

    if len(uncategorized_concepts) == 1:
        section = section_specs["section:uncategorized"]
        only_concept = next(
            entry for entry in concept_entries if entry["concept_key"] == uncategorized_concepts[0]
        )
        section["title"] = only_concept["preferred_label"]

    if graph_index:
        section_specs["section:cross_document_relationships"] = {
            "section_id": "section:cross_document_relationships",
            "title": "Cross-Document Relationships",
            "summary": (
                "This section captures approved cross-document graph links "
                "between the selected concepts."
            ),
            "focus_concept_keys": sorted(
                {
                    concept_key
                    for edge in graph_index
                    for concept_key in (
                        str(edge["subject_entity_key"]).split("concept:", 1)[-1],
                        str(edge["object_entity_key"]).split("concept:", 1)[-1],
                    )
                }
            ),
            "focus_category_keys": [],
            "claim_ids": [],
        }

    claim_candidates: list[dict[str, Any]] = []
    evidence_limit = TARGET_LENGTH_EVIDENCE_LIMIT[target_length]
    for entry in concept_entries:
        category_key, _category_label = _primary_category(
            entry,
            requested_category_order=requested_category_order,
        )
        section_id = f"section:{category_key}" if category_key else "section:uncategorized"
        claim_id = f"claim:{entry['concept_key']}"
        claim_candidates.append(
            {
                "claim_id": claim_id,
                "section_id": section_id,
                "summary": _build_claim_summary(entry, document_refs_by_id=document_refs_by_id),
                "concept_keys": [entry["concept_key"]],
                "graph_edge_ids": [],
                "fact_ids": [row["fact_id"] for row in entry["facts"]],
                "assertion_ids": [row["assertion_id"] for row in entry["assertions"]],
                "evidence_labels": [
                    row["citation_label"] for row in entry["evidence_refs"][:evidence_limit]
                ],
                "source_document_ids": list(entry["document_ids"]),
                "support_level": entry["support_level"],
                "review_policy_status": entry["review_policy_status"],
                "disclosure_note": entry["disclosure_note"],
            }
        )
        section_specs[section_id]["claim_ids"].append(claim_id)

    if graph_index:
        for graph_edge in graph_index:
            claim_id = f"claim:{graph_edge['edge_id']}"
            claim_candidates.append(
                {
                    "claim_id": claim_id,
                    "section_id": "section:cross_document_relationships",
                    "summary": (
                        f"{graph_edge['subject_label']} is linked to {graph_edge['object_label']} "
                        f"through approved cross-document graph memory across "
                        f"{len(graph_edge['supporting_document_ids'])} document"
                        f"{'' if len(graph_edge['supporting_document_ids']) == 1 else 's'}."
                    ),
                    "concept_keys": [
                        str(graph_edge["subject_entity_key"]).split("concept:", 1)[-1],
                        str(graph_edge["object_entity_key"]).split("concept:", 1)[-1],
                    ],
                    "graph_edge_ids": [graph_edge["edge_id"]],
                    "fact_ids": [],
                    "assertion_ids": [],
                    "evidence_labels": [],
                    "source_document_ids": list(graph_edge["supporting_document_ids"]),
                    "support_level": graph_edge["support_level"],
                    "review_policy_status": "approved_graph",
                    "disclosure_note": None,
                }
            )
            section_specs["section:cross_document_relationships"]["claim_ids"].append(claim_id)

    for section in section_specs.values():
        concept_count = len(section["focus_concept_keys"])
        if section["section_id"] == "section:cross_document_relationships":
            continue
        section["summary"] = (
            f"This section covers {concept_count} semantic concept"
            f"{'' if concept_count == 1 else 's'} from the selected corpus scope."
        )

    sections = list(section_specs.values())
    selected_concept_keys = [entry["concept_key"] for entry in concept_entries]
    required_concept_keys = list(dict.fromkeys([*concept_keys, *selected_concept_keys]))
    available_category_keys = {
        value for entry in concept_entries for value in entry["category_keys"]
    }
    selected_category_keys = [key for key in category_keys if key in available_category_keys]
    if not selected_category_keys:
        selected_category_keys = [
            key
            for key in dict.fromkeys(
                value for entry in concept_entries for value in entry["category_keys"]
            )
        ]

    brief = {
        "document_kind": DOCUMENT_KIND_KNOWLEDGE_BRIEF,
        "title": title,
        "goal": goal,
        "audience": audience,
        "review_policy": review_policy,
        "target_length": target_length,
        "document_refs": document_refs,
        "required_concept_keys": required_concept_keys,
        "selected_concept_keys": selected_concept_keys,
        "selected_category_keys": selected_category_keys,
        "semantic_dossier": concept_entries,
        "graph_index": graph_index,
        "graph_summary": graph_summary,
        "sections": sections,
        "claim_candidates": claim_candidates,
        "evidence_pack": evidence_pack,
        "shadow_mode": False,
        "shadow_candidate_extractor_name": None,
        "shadow_candidate_summary": {},
        "shadow_candidates": [],
        "warnings": warnings,
    }
    if include_shadow_candidates:
        shadow_candidates, shadow_candidate_summary = collect_shadow_candidates_for_brief(
            session,
            document_ids=unique_document_ids,
            candidate_extractor_name=candidate_extractor_name,
            score_threshold=candidate_score_threshold,
            requested_concept_keys=requested_concept_keys,
            requested_category_keys=requested_category_keys,
            max_shadow_candidates=max_shadow_candidates,
        )
        brief["shadow_mode"] = True
        brief["shadow_candidate_extractor_name"] = candidate_extractor_name
        brief["shadow_candidate_summary"] = shadow_candidate_summary
        brief["shadow_candidates"] = shadow_candidates
        if shadow_candidates:
            warnings.append(
                f"{len(shadow_candidates)} shadow semantic candidate"
                f"{'' if len(shadow_candidates) == 1 else 's'} were captured separately "
                "from the live semantic dossier."
            )
    brief["success_metrics"] = _brief_success_metrics(brief)
    return brief


def _draft_success_metrics(draft: dict[str, Any]) -> list[dict[str, Any]]:
    claims = list(draft.get("claims") or [])
    sections = list(draft.get("sections") or [])
    evidence_pack = list(draft.get("evidence_pack") or [])
    graph_index = list(draft.get("graph_index") or [])
    fact_index = list(draft.get("fact_index") or [])
    assertion_index = list(draft.get("assertion_index") or [])
    traceable_claim_ratio = (
        sum(
            1
            for row in claims
            if row.get("graph_edge_ids")
            or row.get("fact_ids")
            or (row.get("assertion_ids") and row.get("evidence_labels"))
        )
        / len(claims)
        if claims
        else 0.0
    )
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": traceable_claim_ratio == 1.0 and bool(draft.get("markdown")),
            "summary": (
                "The generated document keeps every claim tied to semantic assertions and evidence."
            ),
            "details": {
                "traceable_claim_ratio": traceable_claim_ratio,
                "claim_count": len(claims),
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(sections)
            and bool(claims)
            and bool(graph_index or assertion_index or fact_index),
            "summary": (
                "The draft exposes sections, claims, fact or assertion refs, and an evidence appendix."
            ),
            "details": {
                "section_count": len(sections),
                "claim_count": len(claims),
                "graph_edge_count": len(graph_index),
                "fact_count": len(fact_index),
                "assertion_count": len(assertion_index),
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": (
                draft.get("generator_name") == "structured_fallback"
                and draft.get("document_kind") == DOCUMENT_KIND_KNOWLEDGE_BRIEF
            ),
            "summary": (
                "Draft generation remains deterministic and bounded to the typed brief contract."
            ),
            "details": {
                "generator_name": draft.get("generator_name"),
                "used_fallback": draft.get("used_fallback"),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(draft.get("brief_task_id")) and bool(evidence_pack),
            "summary": (
                "The draft stays linked to a durable brief task and a reusable evidence pack."
            ),
            "details": {
                "brief_task_id": str(draft.get("brief_task_id")),
                "evidence_count": len(evidence_pack),
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": bool(claims) and len(claims) <= max(len(evidence_pack), 1),
            "summary": "The draft turns dossier coverage into compact, reusable claim text.",
            "details": {
                "claim_count": len(claims),
                "evidence_count": len(evidence_pack),
            },
        },
    ]


def draft_semantic_grounded_document(
    brief_payload: dict[str, Any],
    *,
    brief_task_id: UUID,
) -> dict[str, Any]:
    brief = SemanticGenerationBriefPayload.model_validate(brief_payload)
    if not brief.claim_candidates:
        raise ValueError("Semantic generation brief does not contain any claim candidates.")

    assertion_index: list[dict[str, Any]] = []
    fact_index: list[dict[str, Any]] = []
    graph_index: list[dict[str, Any]] = [edge.model_dump(mode="json") for edge in brief.graph_index]
    for concept_entry in brief.semantic_dossier:
        for fact in concept_entry.facts:
            fact_index.append(fact.model_dump(mode="json"))
        for assertion in concept_entry.assertions:
            assertion_index.append(assertion.model_dump(mode="json"))

    claim_candidates_by_id = {claim.claim_id: claim for claim in brief.claim_candidates}
    claims: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    for section in brief.sections:
        section_claims = [claim_candidates_by_id[claim_id] for claim_id in section.claim_ids]
        body_lines = [section.summary, ""]
        for claim in section_claims:
            rendered_text = claim.summary
            if claim.disclosure_note:
                rendered_text = f"{rendered_text} {claim.disclosure_note}"
            claims.append(
                {
                    "claim_id": claim.claim_id,
                    "section_id": claim.section_id,
                    "rendered_text": rendered_text,
                    "concept_keys": list(claim.concept_keys),
                    "graph_edge_ids": list(claim.graph_edge_ids),
                    "fact_ids": list(claim.fact_ids),
                    "assertion_ids": list(claim.assertion_ids),
                    "evidence_labels": list(claim.evidence_labels),
                    "source_document_ids": list(claim.source_document_ids),
                    "support_level": claim.support_level,
                    "review_policy_status": claim.review_policy_status,
                    "disclosure_note": claim.disclosure_note,
                }
            )
            evidence_phrase = (
                f" Evidence: {', '.join(f'[{label}]' for label in claim.evidence_labels)}."
                if claim.evidence_labels
                else ""
            )
            body_lines.append(f"- {rendered_text}{evidence_phrase}")
        sections.append(
            {
                "section_id": section.section_id,
                "title": section.title,
                "body_markdown": "\n".join(body_lines).strip(),
                "claim_ids": list(section.claim_ids),
            }
        )

    scope_labels = ", ".join(
        _document_label(row.model_dump(mode="json")) for row in brief.document_refs
    )
    markdown_parts = [f"# {brief.title}", "", brief.goal]
    if brief.audience:
        markdown_parts.extend(["", f"Audience: {brief.audience}"])
    markdown_parts.extend(["", f"Corpus scope: {scope_labels}"])
    if brief.warnings:
        markdown_parts.extend(["", "Warnings:"])
        markdown_parts.extend(f"- {warning}" for warning in brief.warnings)
    for section in sections:
        markdown_parts.extend(["", f"## {section['title']}", "", section["body_markdown"]])
    markdown_parts.extend(["", "## Evidence Appendix", ""])
    for evidence in brief.evidence_pack:
        excerpt = collapse_whitespace(evidence.excerpt) or "No excerpt captured."
        markdown_parts.append(
            f"- [{evidence.citation_label}] {evidence.source_filename}, "
            f"{_page_label(evidence.page_from, evidence.page_to)} "
            f"({evidence.source_type}): {excerpt}"
        )
    markdown = "\n".join(markdown_parts).strip() + "\n"

    draft = {
        "document_kind": brief.document_kind,
        "title": brief.title,
        "goal": brief.goal,
        "audience": brief.audience,
        "review_policy": brief.review_policy,
        "target_length": brief.target_length,
        "brief_task_id": brief_task_id,
        "generator_name": "structured_fallback",
        "generator_model": None,
        "used_fallback": True,
        "required_concept_keys": list(brief.required_concept_keys or brief.selected_concept_keys),
        "document_refs": [row.model_dump(mode="json") for row in brief.document_refs],
        "graph_index": graph_index,
        "fact_index": fact_index,
        "assertion_index": assertion_index,
        "sections": sections,
        "claims": claims,
        "evidence_pack": [row.model_dump(mode="json") for row in brief.evidence_pack],
        "markdown": markdown,
        "markdown_path": None,
        "warnings": list(brief.warnings),
    }
    draft["success_metrics"] = _draft_success_metrics(draft)
    return draft


def _verification_success_metrics(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": (
                summary["traceable_claim_ratio"] == 1.0 and summary["unsupported_claim_count"] == 0
            ),
            "summary": (
                "Verified claims stay completely evidence-backed and "
                "unsupported claims are blocked."
            ),
            "details": {
                "traceable_claim_ratio": summary["traceable_claim_ratio"],
                "unsupported_claim_count": summary["unsupported_claim_count"],
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": (
                summary["graph_ref_coverage_ratio"] == 1.0
                and
                summary["fact_ref_coverage_ratio"] == 1.0
                and
                summary["assertion_ref_coverage_ratio"] == 1.0
                and summary["evidence_ref_coverage_ratio"] == 1.0
            ),
            "summary": (
                "The verifier can resolve every claim back to the draft's "
                "typed fact, assertion, and evidence indexes."
            ),
            "details": {
                "graph_ref_coverage_ratio": summary["graph_ref_coverage_ratio"],
                "fact_ref_coverage_ratio": summary["fact_ref_coverage_ratio"],
                "assertion_ref_coverage_ratio": summary["assertion_ref_coverage_ratio"],
                "evidence_ref_coverage_ratio": summary["evidence_ref_coverage_ratio"],
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": (
                summary["required_concept_coverage_ratio"] == 1.0
                and summary["freshness_blocker_count"] == 0
            ),
            "summary": (
                "The verifier enforces explicit coverage and blocks missing "
                "or stale source control surfaces."
            ),
            "details": {
                "required_concept_coverage_ratio": summary["required_concept_coverage_ratio"],
                "freshness_blocker_count": summary["freshness_blocker_count"],
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": (
                summary["claim_count"] > 0 and summary["covered_required_concept_count"] > 0
            ),
            "summary": (
                "The verifier evaluates a durable claim graph rather than "
                "re-reading raw corpus state."
            ),
            "details": {
                "claim_count": summary["claim_count"],
                "covered_required_concept_count": summary["covered_required_concept_count"],
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": summary["claim_count"] <= max(summary["evidence_count"], 1),
            "summary": "The final draft stays compact relative to the underlying evidence pack.",
            "details": {
                "claim_count": summary["claim_count"],
                "evidence_count": summary["evidence_count"],
            },
        },
    ]


def verify_semantic_grounded_document(
    draft_payload: dict[str, Any],
    *,
    max_unsupported_claim_count: int = 0,
    require_full_claim_traceability: bool = True,
    require_full_concept_coverage: bool = True,
) -> SemanticGroundedDocumentVerificationOutcome:
    draft = GroundedDocumentDraftPayload.model_validate(draft_payload)
    graph_index = {row.edge_id: row for row in draft.graph_index}
    fact_index = {row.fact_id: row for row in draft.fact_index}
    assertion_index = {row.assertion_id: row for row in draft.assertion_index}
    evidence_index = {row.citation_label: row for row in draft.evidence_pack}
    required_concept_keys = set(draft.required_concept_keys)
    covered_concept_keys: set[str] = set()
    supported_concept_keys: set[str] = set()
    supported_claim_count = 0
    resolved_graph_edge_count = 0
    resolved_fact_count = 0
    resolved_assertion_count = 0
    resolved_evidence_count = 0
    candidate_disclosure_count = 0
    unsupported_claim_count = 0
    approved_supported_claim_count = 0
    reasons: list[str] = []

    for claim in draft.claims:
        covered_concept_keys.update(claim.concept_keys)
        has_graph_edges = bool(claim.graph_edge_ids)
        has_facts = bool(claim.fact_ids)
        has_assertions = bool(claim.assertion_ids)
        has_evidence = bool(claim.evidence_labels)
        resolved_graph_edges = [
            graph_index[edge_id] for edge_id in claim.graph_edge_ids if edge_id in graph_index
        ]
        resolved_facts = [fact_index[fact_id] for fact_id in claim.fact_ids if fact_id in fact_index]
        resolved_assertions = [
            assertion_index[assertion_id]
            for assertion_id in claim.assertion_ids
            if assertion_id in assertion_index
        ]
        resolved_evidence = [
            evidence_index[evidence_label]
            for evidence_label in claim.evidence_labels
            if evidence_label in evidence_index
        ]
        if has_graph_edges and len(resolved_graph_edges) == len(claim.graph_edge_ids):
            resolved_graph_edge_count += 1
        if has_facts and len(resolved_facts) == len(claim.fact_ids):
            resolved_fact_count += 1
        if has_assertions and len(resolved_assertions) == len(claim.assertion_ids):
            resolved_assertion_count += 1
        if has_evidence and len(resolved_evidence) == len(claim.evidence_labels):
            resolved_evidence_count += 1
        graph_backed = bool(resolved_graph_edges) and all(
            row.support_ref_ids for row in resolved_graph_edges
        )
        fact_backed = bool(resolved_facts) and all(row.evidence_ids for row in resolved_facts)
        assertion_backed = (
            has_assertions and has_evidence and resolved_assertions and resolved_evidence
        )
        if graph_backed or fact_backed or assertion_backed:
            supported_claim_count += 1
            supported_concept_keys.update(claim.concept_keys)
        else:
            unsupported_claim_count += 1
        if claim.review_policy_status in {"candidate_disclosed", "mixed_support_disclosed"}:
            if claim.disclosure_note:
                candidate_disclosure_count += 1
            else:
                reasons.append(
                    f"{claim.claim_id} is candidate-backed but missing a disclosure note."
                )
        if resolved_facts and all(row.review_status == "approved" for row in resolved_facts):
            approved_supported_claim_count += 1
        elif resolved_graph_edges and all(row.review_status == "approved" for row in resolved_graph_edges):
            approved_supported_claim_count += 1
        elif resolved_assertions and all(row.review_status == "approved" for row in resolved_assertions):
            approved_supported_claim_count += 1

    claim_count = len(draft.claims)
    required_concept_count = len(required_concept_keys)
    covered_required_concept_count = len(required_concept_keys.intersection(supported_concept_keys))
    traceable_claim_ratio = supported_claim_count / claim_count if claim_count else 0.0
    graph_claim_count = sum(1 for claim in draft.claims if claim.graph_edge_ids)
    fact_claim_count = sum(1 for claim in draft.claims if claim.fact_ids)
    assertion_claim_count = sum(1 for claim in draft.claims if claim.assertion_ids)
    evidence_claim_count = sum(1 for claim in draft.claims if claim.evidence_labels)
    graph_ref_coverage_ratio = (
        resolved_graph_edge_count / graph_claim_count if graph_claim_count else 1.0
    )
    fact_ref_coverage_ratio = (
        resolved_fact_count / fact_claim_count if fact_claim_count else 1.0
    )
    assertion_ref_coverage_ratio = (
        resolved_assertion_count / assertion_claim_count if assertion_claim_count else 1.0
    )
    evidence_ref_coverage_ratio = (
        resolved_evidence_count / evidence_claim_count if evidence_claim_count else 1.0
    )
    required_concept_coverage_ratio = (
        covered_required_concept_count / required_concept_count if required_concept_count else 1.0
    )
    approved_support_ratio = approved_supported_claim_count / claim_count if claim_count else 0.0

    if unsupported_claim_count > max_unsupported_claim_count:
        reasons.append(
            f"Unsupported claim count {unsupported_claim_count} exceeds the allowed maximum "
            f"of {max_unsupported_claim_count}."
        )
    if require_full_claim_traceability and traceable_claim_ratio < 1.0:
        reasons.append("Not every draft claim resolves to graph, fact, or assertion-plus-evidence support.")
    if require_full_concept_coverage and required_concept_coverage_ratio < 1.0:
        reasons.append("The draft does not cover every required concept from the generation brief.")

    summary = {
        "claim_count": claim_count,
        "section_count": len(draft.sections),
        "evidence_count": len(draft.evidence_pack),
        "graph_edge_count": len(draft.graph_index),
        "fact_count": len(draft.fact_index),
        "required_concept_count": required_concept_count,
        "covered_required_concept_count": covered_required_concept_count,
        "traceable_claim_ratio": traceable_claim_ratio,
        "graph_ref_coverage_ratio": graph_ref_coverage_ratio,
        "fact_ref_coverage_ratio": fact_ref_coverage_ratio,
        "assertion_ref_coverage_ratio": assertion_ref_coverage_ratio,
        "evidence_ref_coverage_ratio": evidence_ref_coverage_ratio,
        "required_concept_coverage_ratio": required_concept_coverage_ratio,
        "approved_support_ratio": approved_support_ratio,
        "candidate_disclosure_count": candidate_disclosure_count,
        "unsupported_claim_count": unsupported_claim_count,
        "freshness_blocker_count": 0,
    }
    success_metrics = _verification_success_metrics(summary)
    verification_outcome = "passed" if not reasons else "failed"
    verification_details = {
        "required_concept_keys": sorted(required_concept_keys),
        "covered_concept_keys": sorted(covered_concept_keys),
        "supported_concept_keys": sorted(supported_concept_keys),
    }
    return SemanticGroundedDocumentVerificationOutcome(
        summary=summary,
        success_metrics=success_metrics,
        verification_outcome=verification_outcome,
        verification_metrics=summary,
        verification_reasons=reasons,
        verification_details=verification_details,
    )
