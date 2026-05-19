from __future__ import annotations

from dataclasses import dataclass

from app.schemas.semantics import DocumentSemanticPassResponse


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
                "The system owns durable semantic context instead of reconstructing it ad hoc."
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


def _semantic_review_rank(review_status: str | None) -> int:
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
                        f"Expected concept {concept_key} is missing from the active semantic pass."
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
                                "The evaluation corpus expects this concept-category binding."
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
                    f"Concept {concept_key} was added relative to the baseline semantic pass."
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
                    f"Concept {concept_key} disappeared relative to the baseline semantic pass."
                ),
                "details": {"continuity_reason": continuity_summary.get("reason")},
                "evidence_refs": [],
                "registry_update_hints": [],
            }
        )

    for change in continuity_summary.get("changed_assertion_review_statuses") or []:
        baseline_status = str(change.get("baseline_review_status") or "")
        current_status = str(change.get("current_review_status") or "")
        if _semantic_review_rank(current_status) >= _semantic_review_rank(baseline_status):
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
            if _semantic_review_rank(current_status) >= _semantic_review_rank(baseline_status):
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
                    "Draft an additive semantic registry update from the triaged gap report."
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
                "Review-status regressions need operator attention before changing the registry."
            ),
        }
        followups = [
            {
                "followup_type": "review_assertion",
                "priority": "high",
                "summary": (
                    "Inspect semantic review regressions and confirm whether they are intentional."
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
                "The active semantic pass is stable and meets the current semantic expectations."
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
                "The semantic pass needs operator review before any registry change is proposed."
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
