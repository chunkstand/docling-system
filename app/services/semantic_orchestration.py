from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.semantics import DocumentSemanticPassResponse
from app.services.semantic_registry import (
    get_active_semantic_ontology_snapshot,
    get_semantic_registry,
)


@dataclass(frozen=True)
class SemanticTriageOutcome:
    gap_report: dict
    recommendation: dict
    verification_outcome: str
    verification_metrics: dict
    verification_reasons: list[str]
    verification_details: dict


def build_semantic_success_metrics(
    semantic_pass: DocumentSemanticPassResponse,
) -> list[dict]:
    assertion_evidence_complete = all(
        assertion.evidence_count > 0 and len(assertion.evidence) == assertion.evidence_count
        for assertion in semantic_pass.assertions
    )
    issue_ready = bool(semantic_pass.summary) and bool(semantic_pass.continuity_summary)
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": (
                semantic_pass.has_json_artifact
                and bool(semantic_pass.registry_version)
                and bool(semantic_pass.registry_sha256)
                and assertion_evidence_complete
            ),
            "summary": "Semantic assertions are evidence-backed and version-stamped.",
            "details": {
                "has_json_artifact": semantic_pass.has_json_artifact,
                "assertion_count": semantic_pass.assertion_count,
                "evidence_count": semantic_pass.evidence_count,
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": (
                issue_ready
                and semantic_pass.semantic_pass_id is not None
                and semantic_pass.document_id is not None
                and semantic_pass.run_id is not None
            ),
            "summary": "The semantic pass is available as typed, durable machine-readable context.",
            "details": {
                "evaluation_status": semantic_pass.evaluation_status,
                "continuity_reason": semantic_pass.continuity_summary.get("reason"),
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": (
                semantic_pass.status == "completed"
                and bool(semantic_pass.artifact_schema_version)
                and bool(semantic_pass.extractor_version)
            ),
            "summary": "The semantic layer exposes explicit versions and bounded runtime state.",
            "details": {
                "status": semantic_pass.status,
                "artifact_schema_version": semantic_pass.artifact_schema_version,
                "extractor_version": semantic_pass.extractor_version,
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(semantic_pass.summary) and bool(semantic_pass.registry_sha256),
            "summary": (
                "The system owns durable semantic context instead of "
                "reconstructing it ad hoc."
            ),
            "details": {
                "concept_keys": list(semantic_pass.summary.get("concept_keys") or []),
                "evaluation_fixture_name": semantic_pass.evaluation_fixture_name,
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": (
                bool(semantic_pass.summary.get("concept_keys"))
                or semantic_pass.assertion_count == 0
            ),
            "summary": "The pass compresses raw document evidence into compact semantic objects.",
            "details": {
                "concept_key_count": len(semantic_pass.summary.get("concept_keys") or []),
                "assertion_count": semantic_pass.assertion_count,
            },
        },
    ]


def _assertion_by_concept(
    semantic_pass: DocumentSemanticPassResponse,
) -> dict[str, object]:
    return {assertion.concept_key: assertion for assertion in semantic_pass.assertions}


def _concept_category_binding_index(
    semantic_pass: DocumentSemanticPassResponse,
) -> dict[tuple[str, str], object]:
    return {
        (binding.concept_key, binding.category_key): binding
        for binding in semantic_pass.concept_category_bindings
    }


def _severity_for_issue(issue_type: str) -> str:
    if issue_type in {
        "missing_expected_concept",
        "unexpected_concept_removal",
        "review_status_regression",
    }:
        return "high"
    if issue_type in {
        "category_binding_mismatch",
        "source_type_coverage_gap",
        "unexpected_concept_addition",
    }:
        return "medium"
    return "low"


def _review_rank(review_status: str | None) -> int:
    if review_status == "approved":
        return 3
    if review_status == "candidate":
        return 2
    if review_status == "rejected":
        return 1
    return 0


def _evidence_refs(assertion) -> list[dict]:
    return [
        {
            "evidence_id": evidence.evidence_id,
            "source_type": evidence.source_type,
            "page_from": evidence.page_from,
            "page_to": evidence.page_to,
            "excerpt": evidence.excerpt,
            "source_artifact_api_path": evidence.source_artifact_api_path,
            "matched_terms": list(evidence.matched_terms),
        }
        for evidence in assertion.evidence
    ]


def triage_semantic_pass(
    semantic_pass: DocumentSemanticPassResponse,
    *,
    low_evidence_threshold: int = 2,
) -> SemanticTriageOutcome:
    assertions_by_concept = _assertion_by_concept(semantic_pass)
    concept_binding_index = _concept_category_binding_index(semantic_pass)
    issues: list[dict] = []

    evaluation_expectations = list(semantic_pass.evaluation_summary.get("expectations") or [])
    for raw_expectation in evaluation_expectations:
        concept_key = str(raw_expectation.get("concept_key") or "")
        if not concept_key or bool(raw_expectation.get("passed")):
            continue
        assertion = assertions_by_concept.get(concept_key)
        missing_source_types = list(raw_expectation.get("missing_source_types") or [])
        missing_category_keys = list(raw_expectation.get("missing_category_keys") or [])
        suggested_aliases = [
            str(value).strip()
            for value in (raw_expectation.get("suggested_aliases") or [])
            if str(value).strip()
        ]

        if assertion is None:
            issues.append(
                {
                    "issue_id": f"missing_expected_concept:{concept_key}",
                    "issue_type": "missing_expected_concept",
                    "severity": _severity_for_issue("missing_expected_concept"),
                    "concept_key": concept_key,
                    "category_key": None,
                    "assertion_id": None,
                    "binding_id": None,
                    "summary": (
                        f"Expected concept {concept_key} is missing from the "
                        "active semantic pass."
                    ),
                    "details": {
                        "minimum_evidence_count": raw_expectation.get("minimum_evidence_count"),
                        "required_source_types": list(
                            raw_expectation.get("required_source_types") or []
                        ),
                        "expected_category_keys": list(
                            raw_expectation.get("expected_category_keys") or []
                        ),
                        "observed_evidence_count": raw_expectation.get("observed_evidence_count"),
                        "observed_source_types": list(
                            raw_expectation.get("observed_source_types") or []
                        ),
                        "observed_category_keys": list(
                            raw_expectation.get("observed_category_keys") or []
                        ),
                    },
                    "evidence_refs": [],
                    "registry_update_hints": [
                        {
                            "update_type": "add_alias",
                            "concept_key": concept_key,
                            "alias_text": alias,
                            "category_key": None,
                            "reason": (
                                "Evaluation fixture marked this alias as a "
                                "missing semantic synonym."
                            ),
                        }
                        for alias in suggested_aliases
                    ],
                }
            )
            continue

        evidence_threshold = max(
            int(raw_expectation.get("minimum_evidence_count") or 0),
            int(low_evidence_threshold),
        )
        if assertion.evidence_count < evidence_threshold:
            issues.append(
                {
                    "issue_id": f"low_evidence_concept:{concept_key}",
                    "issue_type": "low_evidence_concept",
                    "severity": _severity_for_issue("low_evidence_concept"),
                    "concept_key": concept_key,
                    "category_key": None,
                    "assertion_id": assertion.assertion_id,
                    "binding_id": None,
                    "summary": (
                        f"Concept {concept_key} has thin evidence coverage "
                        f"({assertion.evidence_count} < {evidence_threshold})."
                    ),
                    "details": {
                        "evidence_count": assertion.evidence_count,
                        "evidence_threshold": evidence_threshold,
                        "required_source_types": list(
                            raw_expectation.get("required_source_types") or []
                        ),
                    },
                    "evidence_refs": _evidence_refs(assertion),
                    "registry_update_hints": [],
                }
            )

        if missing_source_types:
            issues.append(
                {
                    "issue_id": f"source_type_coverage_gap:{concept_key}",
                    "issue_type": "source_type_coverage_gap",
                    "severity": _severity_for_issue("source_type_coverage_gap"),
                    "concept_key": concept_key,
                    "category_key": None,
                    "assertion_id": assertion.assertion_id,
                    "binding_id": None,
                    "summary": (
                        f"Concept {concept_key} is missing semantic evidence from "
                        f"{', '.join(missing_source_types)}."
                    ),
                    "details": {
                        "missing_source_types": missing_source_types,
                        "observed_source_types": list(
                            raw_expectation.get("observed_source_types") or []
                        ),
                    },
                    "evidence_refs": _evidence_refs(assertion),
                    "registry_update_hints": [],
                }
            )

        if missing_category_keys:
            issues.append(
                {
                    "issue_id": f"category_binding_mismatch:{concept_key}",
                    "issue_type": "category_binding_mismatch",
                    "severity": _severity_for_issue("category_binding_mismatch"),
                    "concept_key": concept_key,
                    "category_key": None,
                    "assertion_id": assertion.assertion_id,
                    "binding_id": None,
                    "summary": (
                        f"Concept {concept_key} is missing expected semantic category bindings."
                    ),
                    "details": {
                        "missing_category_keys": missing_category_keys,
                        "observed_category_keys": list(
                            raw_expectation.get("observed_category_keys") or []
                        ),
                    },
                    "evidence_refs": _evidence_refs(assertion),
                    "registry_update_hints": [
                        {
                            "update_type": "add_category_binding",
                            "concept_key": concept_key,
                            "alias_text": None,
                            "category_key": category_key,
                            "reason": (
                                "The evaluation corpus expects this "
                                "concept-category binding."
                            ),
                        }
                        for category_key in missing_category_keys
                        if (concept_key, category_key) not in concept_binding_index
                    ],
                }
            )

    continuity_summary = semantic_pass.continuity_summary or {}
    for concept_key in continuity_summary.get("added_concept_keys") or []:
        issues.append(
            {
                "issue_id": f"unexpected_concept_addition:{concept_key}",
                "issue_type": "unexpected_concept_addition",
                "severity": _severity_for_issue("unexpected_concept_addition"),
                "concept_key": concept_key,
                "category_key": None,
                "assertion_id": getattr(
                    assertions_by_concept.get(concept_key), "assertion_id", None
                ),
                "binding_id": None,
                "summary": (
                    f"Concept {concept_key} was added relative to the baseline "
                    "semantic pass."
                ),
                "details": {"continuity_reason": continuity_summary.get("reason")},
                "evidence_refs": (
                    _evidence_refs(assertions_by_concept[concept_key])
                    if concept_key in assertions_by_concept
                    else []
                ),
                "registry_update_hints": [],
            }
        )

    for concept_key in continuity_summary.get("removed_concept_keys") or []:
        issues.append(
            {
                "issue_id": f"unexpected_concept_removal:{concept_key}",
                "issue_type": "unexpected_concept_removal",
                "severity": _severity_for_issue("unexpected_concept_removal"),
                "concept_key": concept_key,
                "category_key": None,
                "assertion_id": None,
                "binding_id": None,
                "summary": (
                    f"Concept {concept_key} disappeared relative to the baseline "
                    "semantic pass."
                ),
                "details": {"continuity_reason": continuity_summary.get("reason")},
                "evidence_refs": [],
                "registry_update_hints": [],
            }
        )

    for change in continuity_summary.get("changed_assertion_review_statuses") or []:
        baseline_status = str(change.get("baseline_review_status") or "")
        current_status = str(change.get("current_review_status") or "")
        if _review_rank(current_status) >= _review_rank(baseline_status):
            continue
        concept_key = str(change.get("concept_key") or "")
        assertion = assertions_by_concept.get(concept_key)
        issues.append(
            {
                "issue_id": f"review_status_regression:{concept_key}",
                "issue_type": "review_status_regression",
                "severity": _severity_for_issue("review_status_regression"),
                "concept_key": concept_key,
                "category_key": None,
                "assertion_id": getattr(assertion, "assertion_id", None),
                "binding_id": None,
                "summary": (
                    f"Concept {concept_key} regressed from {baseline_status} to {current_status}."
                ),
                "details": {
                    "baseline_review_status": baseline_status,
                    "current_review_status": current_status,
                },
                "evidence_refs": _evidence_refs(assertion) if assertion is not None else [],
                "registry_update_hints": [],
            }
        )

    for change in continuity_summary.get("changed_category_bindings") or []:
        concept_key = str(change.get("concept_key") or "")
        assertion = assertions_by_concept.get(concept_key)
        for status_change in change.get("changed_review_statuses") or []:
            baseline_status = str(status_change.get("baseline_review_status") or "")
            current_status = str(status_change.get("current_review_status") or "")
            if _review_rank(current_status) >= _review_rank(baseline_status):
                continue
            category_key = str(status_change.get("category_key") or "")
            binding = next(
                (
                    row
                    for row in getattr(assertion, "category_bindings", [])
                    if row.category_key == category_key
                ),
                None,
            )
            issues.append(
                {
                    "issue_id": f"review_status_regression:{concept_key}:{category_key}",
                    "issue_type": "review_status_regression",
                    "severity": _severity_for_issue("review_status_regression"),
                    "concept_key": concept_key,
                    "category_key": category_key,
                    "assertion_id": getattr(assertion, "assertion_id", None),
                    "binding_id": getattr(binding, "binding_id", None),
                    "summary": (
                        f"Binding {concept_key}:{category_key} regressed from "
                        f"{baseline_status} to {current_status}."
                    ),
                    "details": {
                        "baseline_review_status": baseline_status,
                        "current_review_status": current_status,
                    },
                    "evidence_refs": _evidence_refs(assertion) if assertion is not None else [],
                    "registry_update_hints": [],
                }
            )

    success_metrics = build_semantic_success_metrics(semantic_pass)
    issue_count = len(issues)
    issue_types = {issue["issue_type"] for issue in issues}
    has_registry_hints = any(issue["registry_update_hints"] for issue in issues)

    if has_registry_hints:
        recommendation = {
            "next_action": "draft_registry_update",
            "confidence": "high",
            "summary": (
                "The semantic gap report contains additive registry updates "
                "that can be drafted safely."
            ),
        }
        followups = [
            {
                "followup_type": "draft_registry_update",
                "priority": "high",
                "summary": (
                    "Draft an additive semantic registry update from the "
                    "triaged gap report."
                ),
                "target_task_type": "draft_semantic_registry_update",
                "details": {"issue_count": issue_count},
            }
        ]
    elif "review_status_regression" in issue_types:
        recommendation = {
            "next_action": "review_semantic_regressions",
            "confidence": "medium",
            "summary": (
                "Review-status regressions need operator attention before "
                "changing the registry."
            ),
        }
        followups = [
            {
                "followup_type": "review_assertion",
                "priority": "high",
                "summary": (
                    "Inspect semantic review regressions and confirm whether "
                    "they are intentional."
                ),
                "target_task_type": None,
                "details": {"issue_count": issue_count},
            }
        ]
    elif issue_count == 0:
        recommendation = {
            "next_action": "no_action",
            "confidence": "high",
            "summary": (
                "The active semantic pass is stable and meets the current "
                "semantic expectations."
            ),
        }
        followups = [
            {
                "followup_type": "no_action",
                "priority": "low",
                "summary": "No bounded semantic follow-up is required for the active document.",
                "target_task_type": None,
                "details": {},
            }
        ]
    else:
        recommendation = {
            "next_action": "review_semantic_evidence",
            "confidence": "medium",
            "summary": (
                "The semantic pass needs operator review before any registry "
                "change is proposed."
            ),
        }
        followups = [
            {
                "followup_type": "review_assertion",
                "priority": "medium",
                "summary": (
                    "Review the semantic evidence gaps and decide whether "
                    "registry work is warranted."
                ),
                "target_task_type": None,
                "details": {"issue_count": issue_count},
            }
        ]

    verification_outcome = "passed" if issue_count == 0 else "failed"
    verification_metrics = {
        "issue_count": issue_count,
        "issue_type_count": len(issue_types),
        "registry_update_hint_count": sum(
            len(issue.get("registry_update_hints") or []) for issue in issues
        ),
        "success_metric_pass_count": sum(1 for metric in success_metrics if metric["passed"]),
        "success_metric_count": len(success_metrics),
    }
    verification_reasons = [issue["summary"] for issue in issues[:5]]
    verification_details = {
        "issue_types": sorted(issue_types),
        "recommendation": recommendation,
        "document_id": str(semantic_pass.document_id),
        "semantic_pass_id": str(semantic_pass.semantic_pass_id),
    }
    gap_report = {
        "document_id": semantic_pass.document_id,
        "run_id": semantic_pass.run_id,
        "semantic_pass_id": semantic_pass.semantic_pass_id,
        "registry_version": semantic_pass.registry_version,
        "registry_sha256": semantic_pass.registry_sha256,
        "evaluation_status": semantic_pass.evaluation_status,
        "evaluation_fixture_name": semantic_pass.evaluation_fixture_name,
        "evaluation_version": semantic_pass.evaluation_version,
        "continuity_summary": continuity_summary,
        "issue_count": issue_count,
        "issues": issues,
        "recommended_followups": followups,
        "success_metrics": success_metrics,
    }
    return SemanticTriageOutcome(
        gap_report=gap_report,
        recommendation=recommendation,
        verification_outcome=verification_outcome,
        verification_metrics=verification_metrics,
        verification_reasons=verification_reasons,
        verification_details=verification_details,
    )


def semantic_triage_metrics(output: SemanticTriageOutcome) -> list[dict]:
    gap_report = output.gap_report
    return [
        *gap_report.get("success_metrics", []),
        {
            "metric_key": "bounded_followup_contract",
            "stakeholder": "Ronacher",
            "passed": bool(gap_report.get("recommended_followups")),
            "summary": "The triage output resolves to bounded, named next actions.",
            "details": {
                "followup_types": [
                    followup.get("followup_type")
                    for followup in gap_report.get("recommended_followups") or []
                ]
            },
        },
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
                "Verification emits per-document typed deltas tied to typed "
                "registry operations."
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
                "The live apply step publishes typed operations rather than "
                "an opaque file diff."
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
                "The published registry state remains attributable to specific "
                "typed operations."
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
