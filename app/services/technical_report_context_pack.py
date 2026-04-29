from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.coercion import unique_strings as _unique_strings
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.time import utcnow
from app.schemas.agent_tasks import (
    ContextFreshnessStatus,
    DocumentGenerationContextPackEvaluationPayload,
    DocumentGenerationContextPackPayload,
    ReportAgentHarnessPayload,
)
from app.services.report_shared import (
    release_readiness_assessment_ready as _release_readiness_assessment_ready,
)
from app.services.technical_report_shared import expert_alignment, success_metric


def _context_ref_freshness_summary(context_refs: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = {
        ContextFreshnessStatus.FRESH.value: 0,
        ContextFreshnessStatus.STALE.value: 0,
        ContextFreshnessStatus.MISSING.value: 0,
        ContextFreshnessStatus.SCHEMA_MISMATCH.value: 0,
        "unknown": 0,
    }
    for ref in context_refs:
        status = str(ref.get("freshness_status") or "unknown")
        status_counts[status if status in status_counts else "unknown"] += 1
    return {
        "context_ref_count": len(context_refs),
        "fresh_context_ref_count": status_counts[ContextFreshnessStatus.FRESH.value],
        "stale_context_ref_count": status_counts[ContextFreshnessStatus.STALE.value],
        "missing_context_ref_count": status_counts[ContextFreshnessStatus.MISSING.value],
        "schema_mismatch_context_ref_count": status_counts[
            ContextFreshnessStatus.SCHEMA_MISMATCH.value
        ],
        "unknown_context_ref_count": status_counts["unknown"],
    }


def _context_pack_without_hash(payload: dict[str, Any]) -> dict[str, Any]:
    without_hash = dict(payload)
    without_hash.pop("context_pack_sha256", None)
    return without_hash


def _claim_has_traceable_support(row: dict[str, Any]) -> bool:
    return bool(row.get("evidence_card_ids") or row.get("graph_edge_ids")) and not any(
        row.get(key)
        for key in (
            "missing_evidence_labels",
            "missing_graph_edge_ids",
            "missing_fact_ids",
            "missing_assertion_ids",
        )
    )


def _release_readiness_assessment_eval_summary(
    *,
    source_search_request_ids: list[str],
    refs: list[dict[str, Any]],
) -> dict[str, Any]:
    refs_by_request_id = {
        str(ref.get("search_request_id")): ref for ref in refs if ref.get("search_request_id")
    }
    ready_request_ids = {
        request_id
        for request_id, ref in refs_by_request_id.items()
        if _release_readiness_assessment_ready(ref)
    }
    missing_request_ids = [
        request_id
        for request_id in source_search_request_ids
        if request_id not in ready_request_ids
    ]
    failed_refs = [
        ref
        for ref in refs
        if ref.get("search_request_id") in source_search_request_ids
        and not _release_readiness_assessment_ready(ref)
    ]
    failed_status_counts: dict[str, int] = {}
    for ref in failed_refs:
        status = str(ref.get("selection_status") or "unknown")
        failed_status_counts[status] = failed_status_counts.get(status, 0) + 1
    return {
        "source_search_request_count": len(source_search_request_ids),
        "readiness_assessment_ref_count": len(refs),
        "ready_assessment_ref_count": len(ready_request_ids),
        "missing_source_search_request_ids": missing_request_ids,
        "failed_ref_count": len(failed_refs),
        "failed_selection_status_counts": failed_status_counts,
    }


def build_document_generation_context_pack(
    harness_payload: dict[str, Any],
    *,
    release_readiness_assessments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    harness = ReportAgentHarnessPayload.model_validate(harness_payload)
    workflow_state = dict(harness.workflow_state or {})
    context_refs = [ref.model_dump(mode="json") for ref in harness.context_refs]
    claim_contract = [dict(row) for row in harness.claim_contract]
    traceable_claim_count = sum(1 for row in claim_contract if _claim_has_traceable_support(row))
    claim_count = len(claim_contract)
    source_evidence_package_export_ids = _unique_strings(
        [
            str(export.get("evidence_package_export_id"))
            for export in harness.search_evidence_package_exports
            if export.get("evidence_package_export_id")
        ]
    )
    source_evidence_package_sha256s = _unique_strings(
        [
            str(export.get("package_sha256"))
            for export in harness.search_evidence_package_exports
            if export.get("package_sha256")
        ]
    )
    source_search_request_ids = _unique_strings(
        [
            str(export.get("search_request_id"))
            for export in harness.search_evidence_package_exports
            if export.get("search_request_id")
        ]
    )
    release_readiness_assessment_refs = list(
        release_readiness_assessments
        if release_readiness_assessments is not None
        else harness.release_readiness_assessments
    )
    release_readiness_assessment_ids = _unique_strings(
        [
            str(ref.get("assessment_id"))
            for ref in release_readiness_assessment_refs
            if ref.get("assessment_id")
        ]
    )
    release_readiness_assessment_sha256s = _unique_strings(
        [
            str(ref.get("assessment_payload_sha256"))
            for ref in release_readiness_assessment_refs
            if ref.get("assessment_payload_sha256")
        ]
    )
    release_readiness_summary = _release_readiness_assessment_eval_summary(
        source_search_request_ids=source_search_request_ids,
        refs=release_readiness_assessment_refs,
    )
    context_pack = {
        "context_pack_id": (
            f"document-generation-context-pack:"
            f"{workflow_state.get('harness_task_id', 'unknown')}:v1"
        ),
        "harness_task_id": workflow_state["harness_task_id"],
        "evidence_task_id": workflow_state["evidence_task_id"],
        "plan_task_id": workflow_state["plan_task_id"],
        "report_request": dict(harness.report_request),
        "workflow_state": workflow_state,
        "context_refs": context_refs,
        "retrieval_plan": list(harness.retrieval_plan),
        "evidence_cards": [card.model_dump(mode="json") for card in harness.evidence_cards],
        "search_evidence_package_exports": list(harness.search_evidence_package_exports),
        "graph_context": [edge.model_dump(mode="json") for edge in harness.graph_context],
        "claim_contract": claim_contract,
        "freshness_summary": _context_ref_freshness_summary(context_refs),
        "quality_contract": {
            "min_traceable_claim_ratio": 1.0,
            "min_context_ref_count": 1,
            "max_blocked_step_count": 0,
            "require_source_evidence_packages": True,
            "require_fresh_context": False,
            "traceable_claim_count": traceable_claim_count,
            "claim_count": claim_count,
            "traceable_claim_ratio": (traceable_claim_count / claim_count if claim_count else 1.0),
            "blocked_steps": list(workflow_state.get("blocked_steps") or []),
        },
        "audit_refs": {
            "source_search_request_ids": source_search_request_ids,
            "source_evidence_package_export_ids": source_evidence_package_export_ids,
            "source_evidence_package_sha256s": source_evidence_package_sha256s,
            "release_readiness_assessments": release_readiness_assessment_refs,
            "release_readiness_assessment_ids": release_readiness_assessment_ids,
            "release_readiness_assessment_sha256s": release_readiness_assessment_sha256s,
            "context_ref_sha256s": _unique_strings(
                [
                    str(ref.get("observed_sha256"))
                    for ref in context_refs
                    if ref.get("observed_sha256")
                ]
            ),
        },
        "warnings": list(harness.warnings),
        "expert_alignment": expert_alignment(),
    }
    context_pack["success_metrics"] = [
        success_metric(
            "context_pack_contract",
            "Jerry Liu",
            bool(context_refs) and bool(claim_contract) and bool(harness.evidence_cards),
            "The generation input is packaged as reusable data, not hidden prompt state.",
            {
                "context_ref_count": len(context_refs),
                "claim_contract_count": claim_count,
                "evidence_card_count": len(harness.evidence_cards),
            },
        ),
        success_metric(
            "retrieval_context_packaged",
            "Jon Bratseth",
            bool(harness.retrieval_plan) and bool(harness.search_evidence_package_exports),
            "Retrieval plan and frozen search evidence are carried into generation together.",
            {
                "retrieval_plan_count": len(harness.retrieval_plan),
                "source_evidence_package_export_count": len(
                    harness.search_evidence_package_exports
                ),
            },
        ),
        success_metric(
            "claim_support_inputs_traceable",
            "Omar Khattab",
            traceable_claim_count == claim_count,
            "Every planned claim has resolvable evidence-card or graph support before drafting.",
            {
                "traceable_claim_count": traceable_claim_count,
                "claim_count": claim_count,
            },
        ),
        success_metric(
            "semantic_context_attached",
            "Juan Sequeda",
            bool(harness.source_plan.required_concept_keys) or bool(harness.graph_context),
            "The pack preserves ontology-facing concepts and governed graph context.",
            {
                "required_concept_count": len(harness.source_plan.required_concept_keys),
                "graph_edge_count": len(harness.graph_context),
            },
        ),
        success_metric(
            "audit_refs_packaged",
            "Luc Moreau / James Cheney",
            bool(source_evidence_package_sha256s)
            and not release_readiness_summary["missing_source_search_request_ids"],
            (
                "The context pack records stable evidence package hashes and release-readiness "
                "assessment refs for later audit replay."
            ),
            {
                "source_evidence_package_export_count": len(source_evidence_package_export_ids),
                "source_evidence_package_sha256_count": len(source_evidence_package_sha256s),
                "release_readiness_assessment_count": len(release_readiness_assessment_ids),
            },
        ),
        success_metric(
            "release_readiness_assessments_bound",
            "Jon Bratseth",
            not release_readiness_summary["missing_source_search_request_ids"]
            and release_readiness_summary["failed_ref_count"] == 0,
            (
                "Every source search request is bound to a ready, integrity-complete release "
                "readiness assessment before generation."
            ),
            release_readiness_summary,
        ),
        success_metric(
            "governed_graph_lifecycle_visible",
            "Joshua Yu + Nicolas Figay",
            all(edge.review_status == "approved" for edge in harness.graph_context),
            "Graph context enters generation with review status visible.",
            {"graph_edge_count": len(harness.graph_context)},
        ),
        success_metric(
            "evaluation_boundary_available",
            "Rich Sutton",
            True,
            "The pack is a measurable artifact that can be evaluated before generation.",
            {"schema_name": "document_generation_context_pack"},
        ),
    ]
    validated_context_pack = DocumentGenerationContextPackPayload.model_validate(
        context_pack
    ).model_dump(mode="json")
    validated_context_pack["context_pack_sha256"] = _payload_sha256(
        _context_pack_without_hash(validated_context_pack)
    )
    return DocumentGenerationContextPackPayload.model_validate(validated_context_pack).model_dump(
        mode="json"
    )


def evaluate_document_generation_context_pack(
    context_pack_payload: dict[str, Any],
    *,
    target_task_id: UUID,
    min_traceable_claim_ratio: float = 1.0,
    min_context_ref_count: int = 1,
    max_blocked_step_count: int = 0,
    require_source_evidence_packages: bool = True,
    require_release_readiness_assessments: bool = True,
    require_fresh_context: bool = False,
) -> dict[str, Any]:
    context_pack = DocumentGenerationContextPackPayload.model_validate(context_pack_payload)
    freshness_summary = dict(context_pack.freshness_summary or {})
    quality_contract = dict(context_pack.quality_contract or {})
    traceable_claim_ratio = float(quality_contract.get("traceable_claim_ratio") or 0.0)
    context_ref_count = int(freshness_summary.get("context_ref_count") or 0)
    blocked_steps = list(quality_contract.get("blocked_steps") or [])
    source_search_request_ids = list(context_pack.audit_refs.get("source_search_request_ids") or [])
    source_package_count = len(context_pack.audit_refs.get("source_evidence_package_sha256s") or [])
    release_readiness_assessments = list(
        context_pack.audit_refs.get("release_readiness_assessments") or []
    )
    release_readiness_summary = _release_readiness_assessment_eval_summary(
        source_search_request_ids=source_search_request_ids,
        refs=release_readiness_assessments,
    )
    stale_count = int(freshness_summary.get("stale_context_ref_count") or 0)
    missing_count = int(freshness_summary.get("missing_context_ref_count") or 0)
    schema_mismatch_count = int(freshness_summary.get("schema_mismatch_context_ref_count") or 0)
    recomputed_sha = _payload_sha256(
        _context_pack_without_hash(context_pack.model_dump(mode="json"))
    )
    checks = [
        {
            "check_key": "context_pack_hash_integrity",
            "passed": context_pack.context_pack_sha256 == recomputed_sha,
            "observed": context_pack.context_pack_sha256,
            "expected": recomputed_sha,
        },
        {
            "check_key": "traceable_claim_ratio",
            "passed": traceable_claim_ratio >= min_traceable_claim_ratio,
            "observed": traceable_claim_ratio,
            "threshold": min_traceable_claim_ratio,
        },
        {
            "check_key": "context_ref_count",
            "passed": context_ref_count >= min_context_ref_count,
            "observed": context_ref_count,
            "threshold": min_context_ref_count,
        },
        {
            "check_key": "blocked_step_count",
            "passed": len(blocked_steps) <= max_blocked_step_count,
            "observed": len(blocked_steps),
            "threshold": max_blocked_step_count,
        },
        {
            "check_key": "source_evidence_packages",
            "passed": (source_package_count > 0 if require_source_evidence_packages else True),
            "observed": source_package_count,
            "required": require_source_evidence_packages,
        },
        {
            "check_key": "release_readiness_assessments",
            "passed": (
                not require_release_readiness_assessments
                or not source_search_request_ids
                or (
                    not release_readiness_summary["missing_source_search_request_ids"]
                    and release_readiness_summary["failed_ref_count"] == 0
                )
            ),
            "observed": release_readiness_summary,
            "required": require_release_readiness_assessments,
        },
        {
            "check_key": "freshness_blockers",
            "passed": missing_count == 0 and schema_mismatch_count == 0,
            "observed": {
                "missing_context_ref_count": missing_count,
                "schema_mismatch_context_ref_count": schema_mismatch_count,
            },
        },
        {
            "check_key": "stale_context",
            "passed": stale_count == 0 if require_fresh_context else True,
            "observed": stale_count,
            "required": require_fresh_context,
        },
    ]
    failed_checks = [check for check in checks if not check["passed"]]
    reasons = [
        f"{check['check_key']} failed: observed {check.get('observed')!r}."
        for check in failed_checks
    ]
    summary = {
        "gate_outcome": "failed" if failed_checks else "passed",
        "check_count": len(checks),
        "passed_check_count": len(checks) - len(failed_checks),
        "failed_check_count": len(failed_checks),
        "claim_count": int(quality_contract.get("claim_count") or 0),
        "traceable_claim_count": int(quality_contract.get("traceable_claim_count") or 0),
        "traceable_claim_ratio": traceable_claim_ratio,
        "context_ref_count": context_ref_count,
        "blocked_step_count": len(blocked_steps),
        "source_evidence_package_count": source_package_count,
        "release_readiness_assessment_ref_count": release_readiness_summary[
            "readiness_assessment_ref_count"
        ],
        "release_readiness_ready_ref_count": release_readiness_summary[
            "ready_assessment_ref_count"
        ],
        "release_readiness_failed_ref_count": release_readiness_summary["failed_ref_count"],
        "release_readiness_missing_source_request_count": len(
            release_readiness_summary["missing_source_search_request_ids"]
        ),
        "stale_context_ref_count": stale_count,
        "missing_context_ref_count": missing_count,
        "schema_mismatch_context_ref_count": schema_mismatch_count,
    }
    payload = {
        "target_task_id": target_task_id,
        "context_pack_id": context_pack.context_pack_id,
        "context_pack_sha256": context_pack.context_pack_sha256 or recomputed_sha,
        "evaluated_at": utcnow(),
        "gate_outcome": summary["gate_outcome"],
        "thresholds": {
            "min_traceable_claim_ratio": min_traceable_claim_ratio,
            "min_context_ref_count": min_context_ref_count,
            "max_blocked_step_count": max_blocked_step_count,
            "require_source_evidence_packages": require_source_evidence_packages,
            "require_release_readiness_assessments": require_release_readiness_assessments,
            "require_fresh_context": require_fresh_context,
        },
        "summary": summary,
        "checks": checks,
        "reasons": reasons,
        "trace": {
            "harness_task_id": str(context_pack.harness_task_id),
            "evidence_task_id": str(context_pack.evidence_task_id),
            "plan_task_id": str(context_pack.plan_task_id),
            "source_evidence_package_export_ids": list(
                context_pack.audit_refs.get("source_evidence_package_export_ids") or []
            ),
            "source_search_request_ids": list(source_search_request_ids),
            "release_readiness_assessments": release_readiness_assessments,
            "release_readiness_summary": release_readiness_summary,
        },
        "success_metrics": [
            success_metric(
                "context_pack_eval_gate",
                "Jerry Liu",
                not failed_checks,
                "The context pack can be evaluated before report drafting.",
                summary,
            ),
            success_metric(
                "audit_ready_context_refs",
                "Luc Moreau / James Cheney",
                bool(context_pack.audit_refs.get("source_evidence_package_sha256s"))
                and missing_count == 0
                and schema_mismatch_count == 0,
                "Context-pack audit refs are stable and freshness blockers are absent.",
                {
                    "source_evidence_package_count": source_package_count,
                    "missing_context_ref_count": missing_count,
                    "schema_mismatch_context_ref_count": schema_mismatch_count,
                    "release_readiness_assessment_ref_count": release_readiness_summary[
                        "readiness_assessment_ref_count"
                    ],
                },
            ),
            success_metric(
                "release_readiness_gate",
                "Jon Bratseth",
                not release_readiness_summary["missing_source_search_request_ids"]
                and release_readiness_summary["failed_ref_count"] == 0,
                "Source retrieval evidence is bound to ready release assessments.",
                release_readiness_summary,
            ),
        ],
    }
    return DocumentGenerationContextPackEvaluationPayload.model_validate(payload).model_dump(
        mode="json"
    )
