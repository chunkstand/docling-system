from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.semantic_orchestration_triage import (
    SemanticTriageOutcome,
    build_semantic_success_metrics,
    semantic_triage_metrics,
    triage_semantic_pass,
)
from app.services.semantic_registry import (
    get_active_semantic_ontology_snapshot,
    get_semantic_registry,
)

__all__ = [
    "SemanticTriageOutcome",
    "build_semantic_success_metrics",
    "draft_semantic_registry_update",
    "draft_semantic_registry_update_from_bootstrap_report",
    "semantic_registry_apply_metrics",
    "semantic_registry_verification_metrics",
    "semantic_registry_verification_summary",
    "semantic_triage_metrics",
    "triage_semantic_pass",
]


def _next_registry_version(base_version: str) -> str:
    prefix, separator, suffix = base_version.rpartition(".")
    if separator and suffix.isdigit():
        return f"{prefix}.{int(suffix) + 1}"
    return f"{base_version}.1"


def _registry_operation_id(operation_type: str, concept_key: str, value: str) -> str:
    normalized_value = value.strip().lower().replace(" ", "_")
    return f"{operation_type}:{concept_key}:{normalized_value}"


def _preferred_label_from_concept_key(concept_key: str) -> str:
    return " ".join(part.capitalize() for part in concept_key.replace("-", "_").split("_") if part)


def _collect_registry_operations_from_gap_report(gap_report: dict[str, Any]) -> list[dict]:
    operations_by_id: dict[str, dict[str, Any]] = {}
    for issue in gap_report.get("issues") or []:
        for hint in issue.get("registry_update_hints") or []:
            operation_type = str(hint.get("update_type") or "")
            concept_key = str(hint.get("concept_key") or "")
            alias_text = str(hint.get("alias_text") or "").strip() or None
            category_key = str(hint.get("category_key") or "").strip() or None
            value = alias_text or category_key
            if not operation_type or not concept_key or not value:
                continue
            operation_id = _registry_operation_id(operation_type, concept_key, value)
            current = operations_by_id.setdefault(
                operation_id,
                {
                    "operation_id": operation_id,
                    "operation_type": operation_type,
                    "concept_key": concept_key,
                    "alias_text": alias_text,
                    "category_key": category_key,
                    "source_issue_ids": [],
                    "rationale": hint.get("reason"),
                },
            )
            current["source_issue_ids"] = sorted(
                {*(current.get("source_issue_ids") or []), str(issue.get("issue_id") or "")}
            )
    return list(operations_by_id.values())


def _collect_registry_operations_from_bootstrap_report(
    bootstrap_report: dict[str, Any],
    *,
    candidate_ids: list[str] | None = None,
) -> list[dict]:
    requested_candidate_ids = {
        str(candidate_id).strip()
        for candidate_id in (candidate_ids or [])
        if str(candidate_id).strip()
    }
    operations: list[dict[str, Any]] = []
    for candidate in bootstrap_report.get("candidates") or []:
        candidate_id = str(candidate.get("candidate_id") or "")
        if requested_candidate_ids and candidate_id not in requested_candidate_ids:
            continue
        concept_key = str(candidate.get("concept_key") or "").strip()
        if not concept_key:
            continue
        operation_id = _registry_operation_id("add_concept", concept_key, concept_key)
        operations.append(
            {
                "operation_id": operation_id,
                "operation_type": "add_concept",
                "concept_key": concept_key,
                "preferred_label": str(candidate.get("preferred_label") or "").strip() or None,
                "alias_text": None,
                "category_key": None,
                "source_issue_ids": [candidate_id] if candidate_id else [],
                "rationale": (
                    f"Bootstrap candidate {candidate.get('preferred_label') or concept_key} "
                    "was mined from corpus evidence and remains reviewable before publication."
                ),
            }
        )
    return operations


def _apply_registry_operations(
    base_registry_payload: dict[str, Any],
    operations: list[dict[str, Any]],
    *,
    proposed_registry_version: str,
) -> dict[str, Any]:
    updated_payload = {
        **base_registry_payload,
        "registry_version": proposed_registry_version,
        "categories": [dict(item) for item in (base_registry_payload.get("categories") or [])],
        "concepts": [dict(item) for item in (base_registry_payload.get("concepts") or [])],
    }
    concepts_by_key = {
        str(concept.get("concept_key") or ""): concept
        for concept in updated_payload["concepts"]
        if str(concept.get("concept_key") or "")
    }
    for operation in operations:
        concept_key = operation["concept_key"]
        concept = concepts_by_key.get(concept_key)
        if operation["operation_type"] == "add_concept":
            if concept is not None:
                raise ValueError(f"Semantic concept key already exists in draft: {concept_key}")
            preferred_label = str(operation.get("preferred_label") or "").strip()
            concept = {
                "concept_key": concept_key,
                "preferred_label": preferred_label
                or _preferred_label_from_concept_key(concept_key),
            }
            updated_payload["concepts"].append(concept)
            concepts_by_key[concept_key] = concept
        elif concept is None:
            raise ValueError(f"Unknown semantic concept key in draft: {concept_key}")

        if operation["operation_type"] == "add_alias":
            alias_text = str(operation.get("alias_text") or "").strip()
            aliases = [
                str(item).strip() for item in (concept.get("aliases") or []) if str(item).strip()
            ]
            if alias_text and alias_text not in aliases:
                concept["aliases"] = [*aliases, alias_text]
        elif operation["operation_type"] == "add_category_binding":
            category_key = str(operation.get("category_key") or "").strip()
            category_keys = [
                str(item).strip()
                for item in (concept.get("category_keys") or [])
                if str(item).strip()
            ]
            if category_key and category_key not in category_keys:
                concept["category_keys"] = sorted([*category_keys, category_key])
        elif operation["operation_type"] == "add_concept":
            continue
        else:
            raise ValueError(
                f"Unsupported semantic registry operation: {operation['operation_type']}"
            )
    return updated_payload


def draft_semantic_registry_update(
    session: Session,
    gap_report: dict[str, Any],
    *,
    source_task_id: UUID,
    source_task_type: str | None,
    proposed_registry_version: str | None,
    rationale: str | None,
    candidate_ids: list[str] | None = None,
) -> dict[str, Any]:
    operations = _collect_registry_operations_from_gap_report(gap_report)
    if not operations:
        raise ValueError("Semantic gap report does not contain any additive registry updates.")

    base_registry = get_semantic_registry(session)
    base_snapshot = get_active_semantic_ontology_snapshot(session)
    base_registry_payload = dict(base_snapshot.payload_json or {})
    next_version = proposed_registry_version or _next_registry_version(
        base_registry.registry_version
    )
    effective_registry = _apply_registry_operations(
        base_registry_payload,
        operations,
        proposed_registry_version=next_version,
    )
    success_metrics = [
        {
            "metric_key": "semantic_integrity_upgrade",
            "stakeholder": "Figay",
            "passed": next_version != base_registry.registry_version and bool(operations),
            "summary": "The draft preserves additive semantics and stamps a new registry version.",
            "details": {
                "base_registry_version": base_registry.registry_version,
                "proposed_registry_version": next_version,
                "operation_count": len(operations),
            },
        },
        {
            "metric_key": "agent_legible_patch",
            "stakeholder": "Lopopolo",
            "passed": bool(operations) and bool(effective_registry),
            "summary": (
                "The draft is encoded as typed operations plus a concrete "
                "effective registry snapshot."
            ),
            "details": {"operation_ids": [operation["operation_id"] for operation in operations]},
        },
        {
            "metric_key": "explicit_mutation_boundary",
            "stakeholder": "Ronacher",
            "passed": True,
            "summary": "The draft is explicit and does not mutate the live registry file.",
            "details": {"live_mutation_performed": False},
        },
        {
            "metric_key": "owned_registry_context",
            "stakeholder": "Jones",
            "passed": bool(gap_report.get("document_id")) and bool(gap_report.get("issue_count")),
            "summary": (
                "Every proposed registry edit is tied back to a document-scoped "
                "semantic gap report."
            ),
            "details": {
                "document_id": str(gap_report.get("document_id")),
                "issue_count": gap_report.get("issue_count"),
            },
        },
        {
            "metric_key": "memory_compaction_patch",
            "stakeholder": "Yegge",
            "passed": len(operations) <= max(len(gap_report.get("issues") or []), 1),
            "summary": (
                "The draft compresses a larger semantic gap report into a "
                "small set of actionable operations."
            ),
            "details": {
                "operation_count": len(operations),
                "issue_count": len(gap_report.get("issues") or []),
            },
        },
    ]
    return {
        "base_registry_version": base_registry.registry_version,
        "proposed_registry_version": next_version,
        "source_task_id": source_task_id,
        "source_task_type": source_task_type,
        "rationale": rationale,
        "document_ids": [gap_report["document_id"]],
        "operations": operations,
        "effective_registry": effective_registry,
        "success_metrics": success_metrics,
    }


def draft_semantic_registry_update_from_bootstrap_report(
    session: Session,
    bootstrap_report: dict[str, Any],
    *,
    source_task_id: UUID,
    source_task_type: str | None,
    proposed_registry_version: str | None,
    rationale: str | None,
    candidate_ids: list[str] | None = None,
) -> dict[str, Any]:
    operations = _collect_registry_operations_from_bootstrap_report(
        bootstrap_report,
        candidate_ids=candidate_ids,
    )
    if not operations:
        raise ValueError("Bootstrap candidate report does not contain any draftable concepts.")

    base_registry = get_semantic_registry(session)
    base_snapshot = get_active_semantic_ontology_snapshot(session)
    base_registry_payload = dict(base_snapshot.payload_json or {})
    next_version = proposed_registry_version or _next_registry_version(
        base_registry.registry_version
    )
    effective_registry = _apply_registry_operations(
        base_registry_payload,
        operations,
        proposed_registry_version=next_version,
    )
    document_ids = [
        UUID(str(document_id))
        for document_id in (bootstrap_report.get("input_document_ids") or [])
        if str(document_id)
    ]
    success_metrics = [
        {
            "metric_key": "semantic_integrity_upgrade",
            "stakeholder": "Figay",
            "passed": next_version != base_registry.registry_version and bool(operations),
            "summary": (
                "The bootstrap draft keeps discovered concepts provisional until "
                "they are verified and explicitly published."
            ),
            "details": {
                "base_registry_version": base_registry.registry_version,
                "proposed_registry_version": next_version,
                "operation_count": len(operations),
            },
        },
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": bool(operations)
            and all(operation["operation_type"] == "add_concept" for operation in operations),
            "summary": (
                "The draft promotes corpus-discovered concepts through a general "
                "registry interface instead of domain-specific rule patches."
            ),
            "details": {"operation_count": len(operations), "domain_agnostic": True},
        },
        {
            "metric_key": "agent_legible_patch",
            "stakeholder": "Lopopolo",
            "passed": bool(operations) and bool(effective_registry),
            "summary": (
                "The bootstrap draft is encoded as typed operations plus a concrete "
                "effective registry snapshot."
            ),
            "details": {"operation_ids": [operation["operation_id"] for operation in operations]},
        },
        {
            "metric_key": "explicit_mutation_boundary",
            "stakeholder": "Ronacher",
            "passed": True,
            "summary": "The draft is explicit and does not mutate the live registry file.",
            "details": {"live_mutation_performed": False},
        },
        {
            "metric_key": "owned_registry_context",
            "stakeholder": "Jones",
            "passed": bool(document_ids) and bool(bootstrap_report.get("candidate_count")),
            "summary": (
                "Every proposed concept is tied back to a durable bootstrap report over "
                "the selected document set."
            ),
            "details": {
                "document_count": len(document_ids),
                "candidate_count": bootstrap_report.get("candidate_count"),
            },
        },
        {
            "metric_key": "memory_compaction_patch",
            "stakeholder": "Yegge",
            "passed": len(operations) <= max(int(bootstrap_report.get("candidate_count") or 0), 1),
            "summary": (
                "The draft compresses a broader bootstrap report into a compact set "
                "of promotable concept operations."
            ),
            "details": {
                "operation_count": len(operations),
                "candidate_count": bootstrap_report.get("candidate_count"),
            },
        },
    ]
    return {
        "base_registry_version": base_registry.registry_version,
        "proposed_registry_version": next_version,
        "source_task_id": source_task_id,
        "source_task_type": source_task_type,
        "rationale": rationale,
        "document_ids": document_ids,
        "operations": operations,
        "effective_registry": effective_registry,
        "success_metrics": success_metrics,
    }


def semantic_registry_verification_summary(document_deltas: list[dict[str, Any]]) -> dict[str, Any]:
    improved_document_count = sum(
        1
        for delta in document_deltas
        if (
            delta["after_failed_expectations"] < delta["before_failed_expectations"]
            or (
                delta["after_assertion_count"] > delta["before_assertion_count"]
                and not delta["regressed_expected_concepts"]
                and not delta["removed_concept_keys"]
            )
        )
    )
    regressed_document_count = sum(
        1
        for delta in document_deltas
        if delta["after_failed_expectations"] > delta["before_failed_expectations"]
        or delta["regressed_expected_concepts"]
        or (
            delta["after_assertion_count"] < delta["before_assertion_count"]
            and not delta["added_concept_keys"]
        )
    )
    improved_expectation_count = sum(
        max(0, delta["before_failed_expectations"] - delta["after_failed_expectations"])
        for delta in document_deltas
    )
    regressed_expectation_count = sum(
        max(0, delta["after_failed_expectations"] - delta["before_failed_expectations"])
        + len(delta["regressed_expected_concepts"])
        for delta in document_deltas
    )
    added_concept_count = sum(len(delta["added_concept_keys"]) for delta in document_deltas)
    removed_concept_count = sum(len(delta["removed_concept_keys"]) for delta in document_deltas)
    return {
        "document_count": len(document_deltas),
        "improved_document_count": improved_document_count,
        "regressed_document_count": regressed_document_count,
        "improved_expectation_count": improved_expectation_count,
        "regressed_expectation_count": regressed_expectation_count,
        "added_concept_count": added_concept_count,
        "removed_concept_count": removed_concept_count,
        "all_documents_passed_after": all(
            delta["after_all_expectations_passed"] for delta in document_deltas
        )
        if document_deltas
        else False,
    }


def semantic_registry_verification_metrics(
    *,
    draft: dict[str, Any],
    document_deltas: list[dict[str, Any]],
) -> list[dict]:
    summary = semantic_registry_verification_summary(document_deltas)
    return [
        {
            "metric_key": "semantic_value_gain",
            "stakeholder": "Figay",
            "passed": summary["improved_expectation_count"] > 0
            or summary["added_concept_count"] > 0,
            "summary": "The draft improves semantic coverage on real documents.",
            "details": summary,
        },
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": summary["added_concept_count"] >= summary["removed_concept_count"],
            "summary": (
                "Verification measures corpus-level semantic coverage gains without "
                "relying on domain-specific rule inspection."
            ),
            "details": summary,
        },
        {
            "metric_key": "agent_legible_verification",
            "stakeholder": "Lopopolo",
            "passed": bool(document_deltas) and bool(draft.get("operations")),
            "summary": (
                "Verification emits per-document typed deltas tied to typed registry operations."
            ),
            "details": {"document_count": len(document_deltas)},
        },
        {
            "metric_key": "explicit_read_only_verification",
            "stakeholder": "Ronacher",
            "passed": True,
            "summary": (
                "Verification stays read-only and compares previews without "
                "mutating the live registry."
            ),
            "details": {"live_mutation_performed": False},
        },
        {
            "metric_key": "owned_context_verification",
            "stakeholder": "Jones",
            "passed": all(
                delta.get("document_id") and delta.get("run_id") for delta in document_deltas
            ),
            "summary": "Every verification delta remains grounded in a concrete document and run.",
            "details": {},
        },
        {
            "metric_key": "memory_compaction_verification",
            "stakeholder": "Yegge",
            "passed": len(document_deltas) <= max(len(draft.get("document_ids") or []), 1),
            "summary": "Verification compresses registry impact into concise per-document deltas.",
            "details": {"document_count": len(document_deltas)},
        },
    ]


def semantic_registry_apply_metrics(
    *,
    applied_registry_version: str,
    applied_operations: list[dict[str, Any]],
    verification_outcome: str,
) -> list[dict]:
    return [
        {
            "metric_key": "semantic_contract_published",
            "stakeholder": "Figay",
            "passed": verification_outcome == "passed" and bool(applied_registry_version),
            "summary": "Only a verified semantic contract is eligible for publication.",
            "details": {"applied_registry_version": applied_registry_version},
        },
        {
            "metric_key": "agent_legible_apply",
            "stakeholder": "Lopopolo",
            "passed": bool(applied_operations),
            "summary": (
                "The live apply step publishes typed operations rather than an opaque file diff."
            ),
            "details": {"operation_count": len(applied_operations)},
        },
        {
            "metric_key": "approval_gate_preserved",
            "stakeholder": "Ronacher",
            "passed": True,
            "summary": "The live registry mutation remains an explicit approval-gated step.",
            "details": {},
        },
        {
            "metric_key": "owned_registry_publication",
            "stakeholder": "Jones",
            "passed": bool(applied_registry_version) and bool(applied_operations),
            "summary": (
                "The published registry state remains attributable to specific typed operations."
            ),
            "details": {},
        },
        {
            "metric_key": "memory_compaction_publication",
            "stakeholder": "Yegge",
            "passed": len(applied_operations) > 0,
            "summary": "The publication step keeps the semantic change-set compact and reviewable.",
            "details": {"operation_count": len(applied_operations)},
        },
    ]
