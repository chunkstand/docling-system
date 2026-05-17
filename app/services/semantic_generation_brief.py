from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.coercion import unique_uuids as _unique_uuids
from app.core.text import collapse_whitespace
from app.db.models import Document
from app.services import semantic_generation_shared as _semantic_generation_shared


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
            "summary": "Every brief claim is tied to version-stamped semantic sources "
            "and evidence.",
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
            "summary": "The generation brief exposes typed claims, sections, and "
            "evidence-pack labels.",
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
                brief.get("document_kind")
                == _semantic_generation_shared.DOCUMENT_KIND_KNOWLEDGE_BRIEF
                and brief.get("review_policy")
                in {"approved_only", "allow_candidate_with_disclosure"}
            ),
            "summary": "Document generation stays bounded to one explicit artifact type "
            "and policy.",
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
            "summary": "Shadow candidates stay additive and separate from the live semantic "
            "dossier.",
            "details": {
                "shadow_mode": brief.get("shadow_mode"),
                "shadow_candidate_count": len(shadow_candidates),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(semantic_dossier) and bool(evidence_pack),
            "summary": "The brief persists owned semantic context instead of reconstructing "
            "it ad hoc.",
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
            "summary": "The brief compresses corpus evidence into compact claims for "
            "downstream agents.",
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
    get_active_semantic_pass_detail_fn,
    list_document_semantic_facts_fn,
    graph_memory_for_brief_fn,
    collect_shadow_candidates_for_brief_fn,
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
        semantic_pass = get_active_semantic_pass_detail_fn(session, document_id)
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
            for fact in list_document_semantic_facts_fn(session, document_id)
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
                            "source_locator": str(
                                evidence.chunk_id or evidence.table_id or evidence.figure_id or ""
                            )
                            or None,
                            "chunk_id": evidence.chunk_id,
                            "table_id": evidence.table_id,
                            "figure_id": evidence.figure_id,
                            "page_from": evidence.page_from,
                            "page_to": evidence.page_to,
                            "excerpt": collapse_whitespace(evidence.excerpt),
                            "source_artifact_api_path": evidence.source_artifact_api_path,
                            "source_artifact_sha256": evidence.source_artifact_sha256,
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
        projected_assertions, review_policy_status, disclosure_note = (
            _semantic_generation_shared._review_policy_projection(
                list(bucket["assertions"]),
                review_policy=review_policy,
            )
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
            and (review_policy != "approved_only" or row["review_status"] == "approved")
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
        support_level = _semantic_generation_shared._support_level(
            projected_assertions, projected_facts, evidence_count
        )
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
                "source_types": _semantic_generation_shared._sorted_unique_strings(
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
        if _semantic_generation_shared._matches_filters(
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
        related_concept_keys, graph_edge_refs, graph_summary, graph_warnings = (
            graph_memory_for_brief_fn(
                session,
                document_ids=unique_document_ids,
                requested_concept_keys=requested_concept_keys
                or {entry["concept_key"] for entry in base_concept_entries},
                available_concept_keys={entry["concept_key"] for entry in raw_concept_entries},
            )
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
        key=lambda entry: _semantic_generation_shared._concept_sort_key(
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
        category_key, category_label = _semantic_generation_shared._primary_category(
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
    evidence_limit = _semantic_generation_shared.TARGET_LENGTH_EVIDENCE_LIMIT[target_length]
    for entry in concept_entries:
        category_key, _category_label = _semantic_generation_shared._primary_category(
            entry,
            requested_category_order=requested_category_order,
        )
        section_id = f"section:{category_key}" if category_key else "section:uncategorized"
        claim_id = f"claim:{entry['concept_key']}"
        claim_candidates.append(
            {
                "claim_id": claim_id,
                "section_id": section_id,
                "summary": _semantic_generation_shared._build_claim_summary(
                    entry, document_refs_by_id=document_refs_by_id
                ),
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
                    "summary": _semantic_generation_shared._graph_claim_summary(graph_edge),
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
        "document_kind": _semantic_generation_shared.DOCUMENT_KIND_KNOWLEDGE_BRIEF,
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
        shadow_candidates, shadow_candidate_summary = collect_shadow_candidates_for_brief_fn(
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
