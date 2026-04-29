from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.coercion import unique_strings as _unique_strings
from app.core.coercion import unique_uuids as _unique_uuids
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.text import collapse_whitespace
from app.core.time import utcnow
from app.schemas.agent_tasks import (
    ContextFreshnessStatus,
    ContextRef,
    ReportAgentHarnessPayload,
    TechnicalReportDraftPayload,
    TechnicalReportEvidenceBundlePayload,
    TechnicalReportEvidenceCard,
    TechnicalReportPlanPayload,
)
from app.services import technical_report_planning
from app.services.evidence import (
    apply_technical_report_derivation_links,
    build_technical_report_derivation_package,
)
from app.services.report_shared import source_evidence_match_status as _source_evidence_match_status
from app.services.semantic_generation import prepare_semantic_generation_brief
from app.services.technical_report_claim_support import (
    CLAIM_SUPPORT_VERDICTS,
    apply_technical_report_claim_support_judgments,
    claim_support_judgment_contract_mismatches,
    judge_technical_report_claim_support,
)
from app.services.technical_report_context_pack import (
    build_document_generation_context_pack,
    evaluate_document_generation_context_pack,
)
from app.services.technical_report_harness import (
    prepare_report_agent_harness,
)
from app.services.technical_report_shared import (
    TechnicalReportVerificationOutcome,
    card_requires_source_match,
    claim_provenance_lock_contract_mismatches,
    expert_alignment,
    success_metric,
)

__all__ = [
    "TechnicalReportVerificationOutcome",
    "apply_technical_report_claim_support_judgments",
    "build_document_generation_context_pack",
    "build_report_evidence_cards",
    "draft_technical_report",
    "evaluate_document_generation_context_pack",
    "judge_technical_report_claim_support",
    "plan_technical_report",
    "prepare_semantic_generation_brief",
    "prepare_report_agent_harness",
    "task_output_context_ref",
    "verify_technical_report",
]


def plan_technical_report(*args, **kwargs) -> dict[str, Any]:
    original_builder = technical_report_planning.prepare_semantic_generation_brief
    technical_report_planning.prepare_semantic_generation_brief = prepare_semantic_generation_brief
    try:
        return technical_report_planning.plan_technical_report(*args, **kwargs)
    finally:
        technical_report_planning.prepare_semantic_generation_brief = original_builder


def build_report_evidence_cards(
    plan_payload: dict[str, Any],
    *,
    plan_task_id: UUID,
) -> dict[str, Any]:
    plan = TechnicalReportPlanPayload.model_validate(plan_payload)
    brief = plan.semantic_brief
    claims = list(brief.claim_candidates)
    evidence_cards: list[dict[str, Any]] = []
    card_id_by_evidence_label: dict[str, str] = {}
    card_ids_by_evidence_id: dict[UUID, list[str]] = {}
    card_ids_by_fact_id: dict[UUID, list[str]] = {}
    card_ids_by_assertion_id: dict[UUID, list[str]] = {}
    card_id_by_graph_edge_id: dict[str, str] = {}
    warnings = list(plan.warnings)
    next_card_index = 1

    for evidence in brief.evidence_pack:
        card_id = f"EC{next_card_index}"
        next_card_index += 1
        related_claims = [
            claim for claim in claims if evidence.citation_label in claim.evidence_labels
        ]
        concept_keys = _unique_strings(
            [concept_key for claim in related_claims for concept_key in claim.concept_keys]
        )
        assertion_ids = _unique_uuids(
            [assertion_id for claim in related_claims for assertion_id in claim.assertion_ids]
        )
        fact_ids = _unique_uuids(
            [fact_id for claim in related_claims for fact_id in claim.fact_ids]
        )
        card = TechnicalReportEvidenceCard(
            evidence_card_id=card_id,
            evidence_kind="source_evidence",
            source_type=evidence.source_type,
            source_locator=evidence.source_locator,
            chunk_id=evidence.chunk_id,
            table_id=evidence.table_id,
            figure_id=evidence.figure_id,
            citation_label=evidence.citation_label,
            document_id=evidence.document_id,
            run_id=evidence.run_id,
            semantic_pass_id=evidence.semantic_pass_id,
            source_document_ids=[evidence.document_id],
            source_filename=evidence.source_filename,
            page_from=evidence.page_from,
            page_to=evidence.page_to,
            excerpt=evidence.excerpt,
            source_artifact_api_path=evidence.source_artifact_api_path,
            source_artifact_sha256=evidence.source_artifact_sha256,
            evidence_ids=[evidence.evidence_id],
            fact_ids=fact_ids,
            assertion_ids=assertion_ids,
            concept_keys=concept_keys,
            support_level="source",
            review_status=evidence.review_status,
            metadata={
                "matched_terms": list(evidence.matched_terms),
                "source_locator": evidence.source_locator,
                "chunk_id": str(evidence.chunk_id) if evidence.chunk_id else None,
                "table_id": str(evidence.table_id) if evidence.table_id else None,
                "figure_id": str(evidence.figure_id) if evidence.figure_id else None,
                "source_artifact_sha256": evidence.source_artifact_sha256,
            },
        )
        evidence_cards.append(card.model_dump(mode="json"))
        card_id_by_evidence_label[evidence.citation_label] = card_id
        card_ids_by_evidence_id.setdefault(evidence.evidence_id, []).append(card_id)
        for fact_id in fact_ids:
            card_ids_by_fact_id.setdefault(fact_id, []).append(card_id)
        for assertion_id in assertion_ids:
            card_ids_by_assertion_id.setdefault(assertion_id, []).append(card_id)

    for concept in brief.semantic_dossier:
        for fact in concept.facts:
            matched_card_ids = [
                card_id
                for evidence_id in fact.evidence_ids
                for card_id in card_ids_by_evidence_id.get(evidence_id, [])
            ]
            if matched_card_ids:
                for card in evidence_cards:
                    if card["evidence_card_id"] in matched_card_ids:
                        card["fact_ids"] = _unique_strings(
                            [*card.get("fact_ids", []), str(fact.fact_id)]
                        )
                        if fact.assertion_id:
                            card["assertion_ids"] = _unique_strings(
                                [
                                    *card.get("assertion_ids", []),
                                    str(fact.assertion_id),
                                ]
                            )
                card_ids_by_fact_id.setdefault(fact.fact_id, []).extend(matched_card_ids)
                if fact.assertion_id:
                    card_ids_by_assertion_id.setdefault(fact.assertion_id, []).extend(
                        matched_card_ids
                    )
                continue
            card_id = f"EC{next_card_index}"
            next_card_index += 1
            card = TechnicalReportEvidenceCard(
                evidence_card_id=card_id,
                evidence_kind="semantic_fact",
                source_type="semantic_fact",
                document_id=fact.document_id,
                run_id=fact.run_id,
                semantic_pass_id=fact.semantic_pass_id,
                source_document_ids=[fact.document_id],
                excerpt=fact.object_label or fact.object_value_text,
                evidence_ids=list(fact.evidence_ids),
                fact_ids=[fact.fact_id],
                assertion_ids=[fact.assertion_id] if fact.assertion_id else [],
                concept_keys=[concept.concept_key],
                support_level=concept.support_level,
                review_status=fact.review_status,
                relation_key=fact.relation_key,
                metadata={
                    "relation_label": fact.relation_label,
                    "subject_entity_key": fact.subject_entity_key,
                    "object_entity_key": fact.object_entity_key,
                },
            )
            evidence_cards.append(card.model_dump(mode="json"))
            card_ids_by_fact_id.setdefault(fact.fact_id, []).append(card_id)
            if fact.assertion_id:
                card_ids_by_assertion_id.setdefault(fact.assertion_id, []).append(card_id)

    for graph_edge in brief.graph_index:
        if graph_edge.review_status != "approved":
            warnings.append(
                f"{graph_edge.edge_id} is present in graph context with "
                f"review_status={graph_edge.review_status!r}; verifier approval is required."
            )
        card_id = f"EC{next_card_index}"
        next_card_index += 1
        concept_keys = [
            str(graph_edge.subject_entity_key).split("concept:", 1)[-1],
            str(graph_edge.object_entity_key).split("concept:", 1)[-1],
        ]
        card = TechnicalReportEvidenceCard(
            evidence_card_id=card_id,
            evidence_kind="approved_graph_edge",
            source_type="semantic_graph",
            source_document_ids=list(graph_edge.supporting_document_ids),
            excerpt=(
                f"{graph_edge.subject_label} -> {graph_edge.relation_label} -> "
                f"{graph_edge.object_label}"
            ),
            graph_edge_ids=[graph_edge.edge_id],
            concept_keys=concept_keys,
            support_level=graph_edge.support_level,
            review_status=graph_edge.review_status,
            relation_key=graph_edge.relation_key,
            metadata={
                "graph_snapshot_id": str(graph_edge.graph_snapshot_id),
                "graph_version": graph_edge.graph_version,
                "support_ref_ids": list(graph_edge.support_ref_ids),
            },
        )
        evidence_cards.append(card.model_dump(mode="json"))
        card_id_by_graph_edge_id[graph_edge.edge_id] = card_id

    claim_evidence_map: list[dict[str, Any]] = []
    for claim in claims:
        source_card_ids = [
            card_id_by_evidence_label[label]
            for label in claim.evidence_labels
            if label in card_id_by_evidence_label
        ]
        graph_card_ids = [
            card_id_by_graph_edge_id[edge_id]
            for edge_id in claim.graph_edge_ids
            if edge_id in card_id_by_graph_edge_id
        ]
        fact_card_ids = [
            card_id
            for fact_id in claim.fact_ids
            for card_id in card_ids_by_fact_id.get(fact_id, [])
        ]
        assertion_card_ids = [
            card_id
            for assertion_id in claim.assertion_ids
            for card_id in card_ids_by_assertion_id.get(assertion_id, [])
        ]
        missing_evidence_labels = [
            label for label in claim.evidence_labels if label not in card_id_by_evidence_label
        ]
        missing_graph_edge_ids = [
            edge_id for edge_id in claim.graph_edge_ids if edge_id not in card_id_by_graph_edge_id
        ]
        missing_fact_ids = [
            str(fact_id) for fact_id in claim.fact_ids if fact_id not in card_ids_by_fact_id
        ]
        missing_assertion_ids = [
            str(assertion_id)
            for assertion_id in claim.assertion_ids
            if assertion_id not in card_ids_by_assertion_id
        ]
        if missing_evidence_labels:
            warnings.append(
                f"{claim.claim_id} references missing evidence labels: "
                f"{', '.join(missing_evidence_labels)}."
            )
        if missing_graph_edge_ids:
            warnings.append(
                f"{claim.claim_id} references missing graph edges: "
                f"{', '.join(missing_graph_edge_ids)}."
            )
        if missing_fact_ids:
            warnings.append(
                f"{claim.claim_id} references facts without evidence cards: "
                f"{', '.join(missing_fact_ids)}."
            )
        if missing_assertion_ids:
            warnings.append(
                f"{claim.claim_id} references assertions without evidence cards: "
                f"{', '.join(missing_assertion_ids)}."
            )
        evidence_card_ids = _unique_strings(
            [*source_card_ids, *graph_card_ids, *fact_card_ids, *assertion_card_ids]
        )
        if not evidence_card_ids and not claim.graph_edge_ids:
            warnings.append(f"{claim.claim_id} has no resolvable report evidence support.")
        claim_evidence_map.append(
            {
                "claim_id": claim.claim_id,
                "section_id": claim.section_id,
                "summary": claim.summary,
                "concept_keys": list(claim.concept_keys),
                "evidence_card_ids": evidence_card_ids,
                "graph_edge_ids": list(claim.graph_edge_ids),
                "fact_ids": [str(fact_id) for fact_id in claim.fact_ids],
                "assertion_ids": [str(assertion_id) for assertion_id in claim.assertion_ids],
                "missing_evidence_labels": missing_evidence_labels,
                "missing_graph_edge_ids": missing_graph_edge_ids,
                "missing_fact_ids": missing_fact_ids,
                "missing_assertion_ids": missing_assertion_ids,
                "source_document_ids": [
                    str(document_id) for document_id in claim.source_document_ids
                ],
                "support_level": claim.support_level,
                "review_policy_status": claim.review_policy_status,
                "disclosure_note": claim.disclosure_note,
            }
        )

    bundle = {
        "plan_task_id": plan_task_id,
        "plan": plan.model_dump(mode="json"),
        "evidence_cards": evidence_cards,
        "claim_evidence_map": claim_evidence_map,
        "retrieval_index": list(plan.retrieval_plan),
        "graph_context": [edge.model_dump(mode="json") for edge in brief.graph_index],
        "warnings": _unique_strings(warnings),
        "expert_alignment": expert_alignment(),
    }
    bundle["success_metrics"] = [
        success_metric(
            "evidence_cards_available",
            "Jerry Liu",
            bool(evidence_cards),
            "The report has stable evidence cards for agent-legible claim binding.",
            {"evidence_card_count": len(evidence_cards)},
        ),
        success_metric(
            "table_evidence_preserved",
            "Omar Khattab",
            sum(1 for row in brief.evidence_pack if row.source_type == "table")
            == sum(1 for card in evidence_cards if card.get("source_type") == "table"),
            "Typed table evidence remains distinguishable from prose evidence.",
            {
                "source_table_count": sum(
                    1 for row in brief.evidence_pack if row.source_type == "table"
                ),
                "table_card_count": sum(
                    1 for card in evidence_cards if card.get("source_type") == "table"
                ),
                "source_types": sorted({str(card.get("source_type")) for card in evidence_cards}),
            },
        ),
        success_metric(
            "claim_contract_bound",
            "Luc Moreau / James Cheney",
            all(
                (row["evidence_card_ids"] or row["graph_edge_ids"])
                and not row["missing_evidence_labels"]
                and not row["missing_graph_edge_ids"]
                and not row["missing_fact_ids"]
                and not row["missing_assertion_ids"]
                for row in claim_evidence_map
            ),
            "Every planned claim has explicit support or graph context before drafting.",
            {"claim_count": len(claim_evidence_map)},
        ),
    ]
    return TechnicalReportEvidenceBundlePayload.model_validate(bundle).model_dump(mode="json")


def draft_technical_report(
    harness_payload: dict[str, Any],
    *,
    harness_task_id: UUID,
    generator_mode: str = "structured_fallback",
    generator_model: str | None = None,
    llm_draft_markdown: str | None = None,
) -> dict[str, Any]:
    harness = ReportAgentHarnessPayload.model_validate(harness_payload)
    sections_by_id = {section.section_id: section for section in harness.source_plan.sections}
    section_claim_ids: dict[str, list[str]] = {section_id: [] for section_id in sections_by_id}
    cards_by_id = {card.evidence_card_id: card for card in harness.evidence_cards}
    claims: list[dict[str, Any]] = []
    blocked_claims: list[dict[str, Any]] = []

    for claim_contract in harness.claim_contract:
        evidence_card_ids = list(claim_contract.get("evidence_card_ids") or [])
        graph_edge_ids = list(claim_contract.get("graph_edge_ids") or [])
        fact_ids = [UUID(str(value)) for value in claim_contract.get("fact_ids") or []]
        assertion_ids = [UUID(str(value)) for value in claim_contract.get("assertion_ids") or []]
        source_document_ids = [
            UUID(str(value)) for value in claim_contract.get("source_document_ids") or []
        ]
        if not evidence_card_ids and not graph_edge_ids:
            blocked_claims.append(
                {
                    "claim_id": claim_contract["claim_id"],
                    "section_id": claim_contract["section_id"],
                    "reason": ("No evidence card or graph edge support was available."),
                    "fact_ids": [str(value) for value in fact_ids],
                    "assertion_ids": [str(value) for value in assertion_ids],
                }
            )
            continue
        rendered_text = str(claim_contract.get("summary") or "").strip()
        if claim_contract.get("disclosure_note"):
            rendered_text = f"{rendered_text} {claim_contract['disclosure_note']}"
        claim_cards = [
            cards_by_id[card_id] for card_id in evidence_card_ids if card_id in cards_by_id
        ]
        source_search_request_ids = _unique_uuids(
            [
                search_request_id
                for card in claim_cards
                for search_request_id in card.source_search_request_ids
            ]
        )
        source_evidence_package_export_ids = _unique_uuids(
            [
                export_id
                for card in claim_cards
                for export_id in card.source_evidence_package_export_ids
            ]
        )
        source_search_request_result_ids = _unique_uuids(
            [
                result_id
                for card in claim_cards
                for result_id in card.source_search_request_result_ids
            ]
        )
        source_evidence_package_sha256s = _unique_strings(
            [sha256 for card in claim_cards for sha256 in card.source_evidence_package_sha256s]
        )
        source_evidence_trace_sha256s = _unique_strings(
            [sha256 for card in claim_cards for sha256 in card.source_evidence_trace_sha256s]
        )
        source_evidence_match_keys = _unique_strings(
            [match_key for card in claim_cards for match_key in card.source_evidence_match_keys]
        )
        source_evidence_match_status = _source_evidence_match_status(
            [
                card.source_evidence_match_status
                for card in claim_cards
                if card_requires_source_match(card)
                if card.source_evidence_match_status
            ]
        )
        claims.append(
            {
                "claim_id": claim_contract["claim_id"],
                "section_id": claim_contract["section_id"],
                "rendered_text": rendered_text,
                "concept_keys": list(claim_contract.get("concept_keys") or []),
                "evidence_card_ids": evidence_card_ids,
                "graph_edge_ids": graph_edge_ids,
                "fact_ids": fact_ids,
                "assertion_ids": assertion_ids,
                "source_document_ids": source_document_ids,
                "support_level": claim_contract.get("support_level"),
                "review_policy_status": claim_contract.get("review_policy_status"),
                "disclosure_note": claim_contract.get("disclosure_note"),
                "source_search_request_ids": source_search_request_ids,
                "source_search_request_result_ids": source_search_request_result_ids,
                "source_evidence_package_export_ids": source_evidence_package_export_ids,
                "source_evidence_package_sha256s": source_evidence_package_sha256s,
                "source_evidence_trace_sha256s": source_evidence_trace_sha256s,
                "source_evidence_match_keys": source_evidence_match_keys,
                "source_evidence_match_status": source_evidence_match_status,
            }
        )
        section_claim_ids.setdefault(claim_contract["section_id"], []).append(
            claim_contract["claim_id"]
        )

    claims_by_section: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        claims_by_section.setdefault(claim["section_id"], []).append(claim)

    sections: list[dict[str, Any]] = []
    markdown_parts = [
        f"# {harness.report_request['title']}",
        "",
        str(harness.report_request["goal"]),
    ]
    if harness.report_request.get("audience"):
        markdown_parts.extend(["", f"Audience: {harness.report_request['audience']}"])
    for section_id, section_plan in sections_by_id.items():
        body_lines = [section_plan.purpose, ""]
        for claim in claims_by_section.get(section_id, []):
            evidence_refs = " ".join(f"[{card_id}]" for card_id in claim["evidence_card_ids"])
            graph_refs = " ".join(f"[{edge_id}]" for edge_id in claim["graph_edge_ids"])
            ref_text = collapse_whitespace(" ".join([evidence_refs, graph_refs]))
            suffix = f" Evidence: {ref_text}." if ref_text else ""
            body_lines.append(f"- {claim['rendered_text']}{suffix}")
        body_markdown = "\n".join(body_lines).strip()
        sections.append(
            {
                "section_id": section_id,
                "title": section_plan.title,
                "body_markdown": body_markdown,
                "claim_ids": list(section_claim_ids.get(section_id, [])),
            }
        )
        markdown_parts.extend(["", f"## {section_plan.title}", "", body_markdown])

    markdown_parts.extend(["", "## Evidence Cards", ""])
    for card in harness.evidence_cards:
        excerpt = collapse_whitespace(card.excerpt) or "No excerpt captured."
        markdown_parts.append(
            f"- [{card.evidence_card_id}] {card.evidence_kind}"
            f" ({card.source_type or 'source'}): {excerpt}"
        )
    markdown = llm_draft_markdown or ("\n".join(markdown_parts).strip() + "\n")
    warnings = list(harness.warnings)
    if generator_mode == "llm_adapter" and not llm_draft_markdown:
        warnings.append(
            "LLM adapter mode was requested without an adapter draft; "
            "structured fallback rendered the draft."
        )

    draft = {
        "title": harness.report_request["title"],
        "goal": harness.report_request["goal"],
        "audience": harness.report_request.get("audience"),
        "target_length": harness.report_request["target_length"],
        "harness_task_id": harness_task_id,
        "generator_mode": generator_mode,
        "generator_model": generator_model,
        "used_fallback": generator_mode != "llm_adapter" or not llm_draft_markdown,
        "llm_adapter_contract": dict(harness.llm_adapter_contract),
        "document_refs": [row.model_dump(mode="json") for row in harness.source_plan.document_refs],
        "required_concept_keys": list(harness.source_plan.required_concept_keys),
        "sections": sections,
        "claims": claims,
        "blocked_claims": blocked_claims,
        "evidence_cards": [card.model_dump(mode="json") for card in harness.evidence_cards],
        "source_evidence_package_exports": list(harness.search_evidence_package_exports),
        "graph_context": [edge.model_dump(mode="json") for edge in harness.graph_context],
        "markdown": markdown,
        "warnings": warnings,
    }
    derivation_package = apply_technical_report_derivation_links(draft)
    draft["success_metrics"] = [
        success_metric(
            "claim_binding_preserved",
            "Luc Moreau / James Cheney",
            all(claim["evidence_card_ids"] or claim["graph_edge_ids"] for claim in claims),
            "Rendered claims preserve evidence-card or graph-edge bindings.",
            {"claim_count": len(claims)},
        ),
        success_metric(
            "unsupported_claims_blocked",
            "Omar Khattab",
            True,
            "Claims without support are blocked instead of rendered as supported prose.",
            {"blocked_claim_count": len(blocked_claims)},
        ),
        success_metric(
            "llm_adapter_pluggable",
            "Jerry Liu",
            bool(harness.llm_adapter_contract),
            "The draft records the harness contract an external LLM adapter must consume.",
            {"generator_mode": generator_mode},
        ),
        success_metric(
            "claim_derivations_frozen",
            "Luc Moreau / James Cheney",
            bool(derivation_package.get("package_sha256"))
            and all(claim.get("derivation_sha256") for claim in draft["claims"]),
            "Each rendered claim is bound to a frozen derivation package hash.",
            {
                "evidence_package_sha256": derivation_package.get("package_sha256"),
                "claim_derivation_count": len(draft.get("claim_derivations") or []),
            },
        ),
    ]
    return TechnicalReportDraftPayload.model_validate(draft).model_dump(mode="json")


def _technical_report_verification_metrics(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        success_metric(
            "claim_traceability",
            "Luc Moreau / James Cheney",
            summary["traceable_claim_ratio"] == 1.0
            and summary["unresolved_evidence_card_ref_count"] == 0
            and summary["unresolved_graph_edge_ref_count"] == 0,
            "Every rendered claim resolves to evidence cards and approved graph context.",
            {
                "traceable_claim_ratio": summary["traceable_claim_ratio"],
                "unresolved_evidence_card_ref_count": summary["unresolved_evidence_card_ref_count"],
                "unresolved_graph_edge_ref_count": summary["unresolved_graph_edge_ref_count"],
            },
        ),
        success_metric(
            "explicit_context_gate",
            "Jerry Liu",
            summary["context_blocker_count"] == 0 and summary["missing_wake_context_count"] == 0,
            "Missing and schema-mismatched wake-up context is blocked by the verifier.",
            {
                "context_blocker_count": summary["context_blocker_count"],
                "missing_wake_context_count": summary["missing_wake_context_count"],
            },
        ),
        success_metric(
            "graph_memory_governed",
            "Joshua Yu + Nicolas Figay",
            summary["unapproved_graph_claim_count"] == 0,
            "Graph-backed claims use approved graph edges only.",
            {"graph_claim_count": summary["graph_claim_count"]},
        ),
        success_metric(
            "owned_wake_context",
            "Jerry Liu",
            summary["context_ref_count"] > 0 and summary["missing_wake_context_count"] == 0,
            "The draft is verified against the harness wake-up context.",
            {
                "context_ref_count": summary["context_ref_count"],
                "missing_wake_context_count": summary["missing_wake_context_count"],
            },
        ),
        success_metric(
            "durable_platform_loop",
            "Rich Sutton",
            summary["claim_count"] > 0 and summary["evidence_card_count"] > 0,
            "The report loop produces reusable durable artifacts rather than one-off prose.",
            {
                "claim_count": summary["claim_count"],
                "evidence_card_count": summary["evidence_card_count"],
            },
        ),
        success_metric(
            "frozen_evidence_package",
            "Luc Moreau / James Cheney",
            summary["claims_with_derivation_hash_count"] == summary["claim_count"]
            and summary["claims_with_evidence_package_hash_count"] == summary["claim_count"]
            and summary["draft_evidence_package_hash_present"]
            and summary["evidence_package_integrity_mismatch_count"] == 0
            and summary["derivation_integrity_mismatch_count"] == 0,
            (
                "Every claim is tied to a frozen evidence package and the frozen hashes "
                "match recomputation."
            ),
            {
                "claims_with_derivation_hash_count": summary["claims_with_derivation_hash_count"],
                "claims_with_evidence_package_hash_count": summary[
                    "claims_with_evidence_package_hash_count"
                ],
                "draft_evidence_package_hash_present": summary[
                    "draft_evidence_package_hash_present"
                ],
                "evidence_package_integrity_mismatch_count": summary[
                    "evidence_package_integrity_mismatch_count"
                ],
                "derivation_integrity_mismatch_count": summary[
                    "derivation_integrity_mismatch_count"
                ],
            },
        ),
        success_metric(
            "court_grade_claim_provenance_lock",
            "Luc Moreau / James Cheney",
            summary["claims_with_provenance_lock_count"] == summary["claim_count"]
            and summary["missing_provenance_lock_count"] == 0
            and summary["provenance_lock_integrity_mismatch_count"] == 0
            and summary["provenance_lock_contract_mismatch_count"] == 0
            and summary["claims_missing_source_search_request_result_count"] == 0,
            (
                "Every generated claim carries a recomputable provenance lock down to "
                "search result identifiers."
            ),
            {
                "claims_with_provenance_lock_count": summary["claims_with_provenance_lock_count"],
                "missing_provenance_lock_count": summary["missing_provenance_lock_count"],
                "provenance_lock_integrity_mismatch_count": summary[
                    "provenance_lock_integrity_mismatch_count"
                ],
                "provenance_lock_contract_mismatch_count": summary[
                    "provenance_lock_contract_mismatch_count"
                ],
                "claims_missing_source_search_request_result_count": summary[
                    "claims_missing_source_search_request_result_count"
                ],
            },
        ),
        success_metric(
            "court_grade_claim_support_gate",
            "Omar Khattab",
            summary["claims_with_support_judgment_count"] == summary["claim_count"]
            and summary["missing_support_judgment_count"] == 0
            and summary["support_judgment_integrity_mismatch_count"] == 0
            and summary["support_judgment_contract_mismatch_count"] == 0
            and summary["unsupported_support_judgment_count"] == 0
            and summary["claim_support_score_below_threshold_count"] == 0,
            (
                "Every generated claim carries an auditable support judgment that "
                "passes the groundedness threshold."
            ),
            {
                "claims_with_support_judgment_count": summary["claims_with_support_judgment_count"],
                "missing_support_judgment_count": summary["missing_support_judgment_count"],
                "support_judgment_integrity_mismatch_count": summary[
                    "support_judgment_integrity_mismatch_count"
                ],
                "support_judgment_contract_mismatch_count": summary[
                    "support_judgment_contract_mismatch_count"
                ],
                "unsupported_support_judgment_count": summary["unsupported_support_judgment_count"],
                "claim_support_score_below_threshold_count": summary[
                    "claim_support_score_below_threshold_count"
                ],
            },
        ),
    ]


def verify_technical_report(
    draft_payload: dict[str, Any],
    *,
    max_unsupported_claim_count: int = 0,
    require_full_claim_traceability: bool = True,
    require_full_concept_coverage: bool = True,
    require_graph_edges_approved: bool = True,
    block_stale_context: bool = False,
    require_claim_support_judgments: bool = True,
    min_claim_support_score: float = 0.34,
) -> TechnicalReportVerificationOutcome:
    draft = TechnicalReportDraftPayload.model_validate(draft_payload)
    recomputed_derivation_package = build_technical_report_derivation_package(
        draft.model_dump(mode="json")
    )
    expected_package_sha256 = str(recomputed_derivation_package.get("package_sha256") or "")
    expected_derivations_by_claim_id = {
        str(row.get("claim_id")): row
        for row in recomputed_derivation_package.get("claim_derivations", [])
        if row.get("claim_id")
    }
    card_ids = {card.evidence_card_id for card in draft.evidence_cards}
    graph_edges = {edge.edge_id: edge for edge in draft.graph_context}
    required_concept_keys = set(draft.required_concept_keys)
    supported_concept_keys: set[str] = set()
    resolved_claim_count = 0
    unsupported_claim_count = len(draft.blocked_claims)
    unapproved_graph_claim_count = 0
    unresolved_evidence_card_ref_count = 0
    unresolved_graph_edge_ref_count = 0
    missing_evidence_package_hash_count = 0
    missing_derivation_hash_count = 0
    missing_provenance_lock_count = 0
    provenance_lock_integrity_mismatch_count = 0
    provenance_lock_contract_mismatch_count = 0
    claims_missing_source_search_request_result_count = 0
    missing_support_judgment_count = 0
    support_judgment_integrity_mismatch_count = 0
    support_judgment_contract_mismatch_count = 0
    unsupported_support_judgment_count = 0
    claim_support_score_below_threshold_count = 0
    evidence_package_mismatch_count = 0
    evidence_package_integrity_mismatch_count = 0
    derivation_integrity_mismatch_count = 0
    reasons: list[str] = []
    stale_context_count = 0
    context_blocker_count = 0
    context_refs = []
    if draft.llm_adapter_contract.get("harness_context_refs"):
        context_refs = list(draft.llm_adapter_contract["harness_context_refs"])
    missing_wake_context_count = 0 if context_refs else 1

    for ref in context_refs:
        status = str(ref.get("freshness_status") or "")
        if status in {
            ContextFreshnessStatus.MISSING.value,
            ContextFreshnessStatus.SCHEMA_MISMATCH.value,
        }:
            context_blocker_count += 1
        elif status == ContextFreshnessStatus.STALE.value:
            stale_context_count += 1

    if not draft.evidence_package_sha256:
        reasons.append("The report draft is missing a frozen evidence package hash.")
    elif draft.evidence_package_sha256 != expected_package_sha256:
        evidence_package_integrity_mismatch_count += 1
        reasons.append(
            "Draft evidence package hash does not match recomputed derivation package hash."
        )

    for claim in draft.claims:
        if not claim.evidence_package_sha256:
            missing_evidence_package_hash_count += 1
            reasons.append(f"{claim.claim_id} is missing a frozen evidence package hash.")
        elif (
            draft.evidence_package_sha256
            and claim.evidence_package_sha256 != draft.evidence_package_sha256
        ):
            evidence_package_mismatch_count += 1
            reasons.append(
                f"{claim.claim_id} evidence package hash does not match the draft package hash."
            )
        if (
            claim.evidence_package_sha256
            and claim.evidence_package_sha256 != expected_package_sha256
        ):
            evidence_package_integrity_mismatch_count += 1
            reasons.append(
                f"{claim.claim_id} evidence package hash does not match recomputed package hash."
            )
        if not claim.derivation_sha256:
            missing_derivation_hash_count += 1
            reasons.append(f"{claim.claim_id} is missing a derivation hash.")
        else:
            expected_derivation = expected_derivations_by_claim_id.get(claim.claim_id)
            expected_derivation_sha256 = (
                str(expected_derivation.get("derivation_sha256") or "")
                if expected_derivation is not None
                else ""
            )
            if claim.derivation_sha256 != expected_derivation_sha256:
                derivation_integrity_mismatch_count += 1
                reasons.append(
                    f"{claim.claim_id} derivation hash does not match recomputed claim derivation."
                )
        expected_derivation = expected_derivations_by_claim_id.get(claim.claim_id)
        expected_provenance_lock_sha256 = (
            str(expected_derivation.get("provenance_lock_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if not claim.provenance_lock or not claim.provenance_lock_sha256:
            missing_provenance_lock_count += 1
            reasons.append(f"{claim.claim_id} is missing a provenance lock.")
        elif (
            claim.provenance_lock_sha256 != _payload_sha256(claim.provenance_lock)
            or claim.provenance_lock_sha256 != expected_provenance_lock_sha256
        ):
            provenance_lock_integrity_mismatch_count += 1
            reasons.append(f"{claim.claim_id} provenance lock hash does not match recomputation.")
        lock_contract_mismatches = claim_provenance_lock_contract_mismatches(claim)
        if lock_contract_mismatches:
            provenance_lock_contract_mismatch_count += 1
            reasons.append(
                f"{claim.claim_id} provenance lock does not match claim fields: "
                f"{', '.join(lock_contract_mismatches)}."
            )
        if (
            not claim.support_verdict
            or claim.support_score is None
            or not claim.support_judge_run_id
            or not claim.support_judgment
            or not claim.support_judgment_sha256
        ):
            missing_support_judgment_count += 1
            reasons.append(f"{claim.claim_id} is missing a claim support judgment from the judge.")
        else:
            if claim.support_verdict not in CLAIM_SUPPORT_VERDICTS:
                support_judgment_contract_mismatch_count += 1
                reasons.append(
                    f"{claim.claim_id} has an invalid support verdict '{claim.support_verdict}'."
                )
            if claim.support_judgment_sha256 != _payload_sha256(claim.support_judgment):
                support_judgment_integrity_mismatch_count += 1
                reasons.append(
                    f"{claim.claim_id} support judgment hash does not match recomputation."
                )
            support_contract_mismatches = claim_support_judgment_contract_mismatches(
                claim,
                min_claim_support_score=min_claim_support_score,
            )
            if support_contract_mismatches:
                support_judgment_contract_mismatch_count += 1
                reasons.append(
                    f"{claim.claim_id} support judgment does not match claim fields: "
                    f"{', '.join(support_contract_mismatches)}."
                )
            if claim.support_verdict != "supported":
                unsupported_support_judgment_count += 1
                reasons.append(
                    f"{claim.claim_id} support judge verdict is {claim.support_verdict}."
                )
            if float(claim.support_score) < min_claim_support_score:
                claim_support_score_below_threshold_count += 1
                reasons.append(
                    f"{claim.claim_id} support score {claim.support_score:.4f} is below "
                    f"the required threshold {min_claim_support_score:.4f}."
                )
        if not claim.source_search_request_result_ids:
            claims_missing_source_search_request_result_count += 1
            reasons.append(f"{claim.claim_id} is missing source search request result identifiers.")
        missing_evidence_card_ids = [
            card_id for card_id in claim.evidence_card_ids if card_id not in card_ids
        ]
        if missing_evidence_card_ids:
            unresolved_evidence_card_ref_count += len(missing_evidence_card_ids)
            reasons.append(
                f"{claim.claim_id} references missing evidence cards: "
                f"{', '.join(missing_evidence_card_ids)}."
            )
        evidence_resolved = bool(claim.evidence_card_ids) and all(
            card_id in card_ids for card_id in claim.evidence_card_ids
        )
        missing_graph_edge_ids = [
            edge_id for edge_id in claim.graph_edge_ids if edge_id not in graph_edges
        ]
        if missing_graph_edge_ids:
            unresolved_graph_edge_ref_count += len(missing_graph_edge_ids)
            reasons.append(
                f"{claim.claim_id} references missing graph edges: "
                f"{', '.join(missing_graph_edge_ids)}."
            )
        graph_refs = [
            graph_edges[edge_id] for edge_id in claim.graph_edge_ids if edge_id in graph_edges
        ]
        graph_resolved = bool(claim.graph_edge_ids) and len(graph_refs) == len(claim.graph_edge_ids)
        graph_approved = graph_resolved and all(
            edge.review_status == "approved" for edge in graph_refs
        )
        unapproved_graph_refs = [edge for edge in graph_refs if edge.review_status != "approved"]
        if unapproved_graph_refs and require_graph_edges_approved:
            unapproved_graph_claim_count += 1
            reasons.append(
                f"{claim.claim_id} references graph edges that are not approved: "
                f"{', '.join(edge.edge_id for edge in unapproved_graph_refs)}."
            )
        if evidence_resolved or graph_approved:
            resolved_claim_count += 1
            supported_concept_keys.update(claim.concept_keys)
        else:
            unsupported_claim_count += 1
            reasons.append(f"{claim.claim_id} does not resolve to allowed support.")

    claim_count = len(draft.claims)
    traceable_claim_ratio = resolved_claim_count / claim_count if claim_count else 0.0
    required_concept_count = len(required_concept_keys)
    covered_required_concept_count = len(required_concept_keys.intersection(supported_concept_keys))
    required_concept_coverage_ratio = (
        covered_required_concept_count / required_concept_count if required_concept_count else 1.0
    )
    graph_claim_count = sum(1 for claim in draft.claims if claim.graph_edge_ids)
    claims_with_evidence_package_hash_count = claim_count - missing_evidence_package_hash_count
    claims_with_derivation_hash_count = claim_count - missing_derivation_hash_count
    claims_with_provenance_lock_count = claim_count - missing_provenance_lock_count
    claims_with_support_judgment_count = claim_count - missing_support_judgment_count
    if unsupported_claim_count > max_unsupported_claim_count:
        reasons.append(
            f"Unsupported claim count {unsupported_claim_count} exceeds the allowed maximum "
            f"of {max_unsupported_claim_count}."
        )
    if require_full_claim_traceability and traceable_claim_ratio < 1.0:
        reasons.append("Not every rendered claim resolves to allowed report evidence.")
    if require_full_concept_coverage and required_concept_coverage_ratio < 1.0:
        reasons.append("The report does not cover every required concept from the harness.")
    if context_blocker_count:
        reasons.append("The report used missing or schema-mismatched wake-up context.")
    if missing_wake_context_count:
        reasons.append("The report draft does not carry refreshed wake-up context refs.")
    if require_full_claim_traceability and (
        missing_evidence_package_hash_count
        or missing_derivation_hash_count
        or evidence_package_mismatch_count
        or evidence_package_integrity_mismatch_count
        or derivation_integrity_mismatch_count
        or missing_provenance_lock_count
        or provenance_lock_integrity_mismatch_count
        or provenance_lock_contract_mismatch_count
        or claims_missing_source_search_request_result_count
    ):
        reasons.append(
            "Frozen evidence package, derivation hashes, provenance locks, and source "
            "search result identifiers are required and must match recomputation."
        )
    if require_claim_support_judgments and (
        missing_support_judgment_count
        or support_judgment_integrity_mismatch_count
        or support_judgment_contract_mismatch_count
        or unsupported_support_judgment_count
        or claim_support_score_below_threshold_count
    ):
        reasons.append(
            "Every generated claim must pass the claim support judge with a recomputable "
            "support judgment and score."
        )
    if block_stale_context and stale_context_count:
        reasons.append("The report used stale wake-up context while stale blocking was enabled.")

    summary = {
        "claim_count": claim_count,
        "section_count": len(draft.sections),
        "evidence_card_count": len(draft.evidence_cards),
        "graph_edge_count": len(draft.graph_context),
        "graph_claim_count": graph_claim_count,
        "resolved_claim_count": resolved_claim_count,
        "unsupported_claim_count": unsupported_claim_count,
        "claims_with_evidence_package_hash_count": claims_with_evidence_package_hash_count,
        "claims_with_derivation_hash_count": claims_with_derivation_hash_count,
        "claims_with_provenance_lock_count": claims_with_provenance_lock_count,
        "claims_with_support_judgment_count": claims_with_support_judgment_count,
        "draft_evidence_package_hash_present": bool(draft.evidence_package_sha256),
        "expected_evidence_package_sha256": expected_package_sha256,
        "missing_evidence_package_hash_count": missing_evidence_package_hash_count,
        "missing_derivation_hash_count": missing_derivation_hash_count,
        "missing_provenance_lock_count": missing_provenance_lock_count,
        "evidence_package_mismatch_count": evidence_package_mismatch_count,
        "evidence_package_integrity_mismatch_count": evidence_package_integrity_mismatch_count,
        "derivation_integrity_mismatch_count": derivation_integrity_mismatch_count,
        "provenance_lock_integrity_mismatch_count": (provenance_lock_integrity_mismatch_count),
        "provenance_lock_contract_mismatch_count": provenance_lock_contract_mismatch_count,
        "claims_missing_source_search_request_result_count": (
            claims_missing_source_search_request_result_count
        ),
        "missing_support_judgment_count": missing_support_judgment_count,
        "support_judgment_integrity_mismatch_count": (support_judgment_integrity_mismatch_count),
        "support_judgment_contract_mismatch_count": (support_judgment_contract_mismatch_count),
        "unsupported_support_judgment_count": unsupported_support_judgment_count,
        "claim_support_score_below_threshold_count": (claim_support_score_below_threshold_count),
        "min_claim_support_score": min_claim_support_score,
        "traceable_claim_ratio": traceable_claim_ratio,
        "required_concept_count": required_concept_count,
        "covered_required_concept_count": covered_required_concept_count,
        "required_concept_coverage_ratio": required_concept_coverage_ratio,
        "unapproved_graph_claim_count": unapproved_graph_claim_count,
        "unresolved_evidence_card_ref_count": unresolved_evidence_card_ref_count,
        "unresolved_graph_edge_ref_count": unresolved_graph_edge_ref_count,
        "context_ref_count": len(context_refs),
        "missing_wake_context_count": missing_wake_context_count,
        "context_blocker_count": context_blocker_count,
        "stale_context_count": stale_context_count,
    }
    success_metrics = _technical_report_verification_metrics(summary)
    return TechnicalReportVerificationOutcome(
        summary=summary,
        success_metrics=success_metrics,
        verification_outcome="failed" if reasons else "passed",
        verification_metrics=summary,
        verification_reasons=reasons,
        verification_details={
            "thresholds": {
                "max_unsupported_claim_count": max_unsupported_claim_count,
                "require_full_claim_traceability": require_full_claim_traceability,
                "require_full_concept_coverage": require_full_concept_coverage,
                "require_graph_edges_approved": require_graph_edges_approved,
                "block_stale_context": block_stale_context,
                "require_claim_support_judgments": require_claim_support_judgments,
                "min_claim_support_score": min_claim_support_score,
            }
        },
    )


def task_output_context_ref(
    *,
    ref_key: str,
    summary: str,
    task_id: UUID,
    schema_name: str | None,
    schema_version: str | None,
    output: dict[str, Any],
    source_updated_at,
    freshness_status: ContextFreshnessStatus | None,
) -> ContextRef:
    return ContextRef(
        ref_key=ref_key,
        ref_kind="task_output",
        summary=summary,
        task_id=task_id,
        schema_name=schema_name,
        schema_version=schema_version,
        observed_sha256=_payload_sha256(output),
        source_updated_at=source_updated_at,
        checked_at=utcnow(),
        freshness_status=freshness_status or ContextFreshnessStatus.FRESH,
    )
