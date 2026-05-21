from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask
from app.db.public.ingest import Document, DocumentRun
from app.services.evidence_audit_views import get_agent_task_audit_bundle
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_records import (
    document_payload as _document_payload,
)
from app.services.evidence_records import (
    manifest_run_payload as _manifest_run_payload,
)
from app.services.evidence_records import (
    select_by_ids as _select_by_ids,
)
from app.services.evidence_semantic_trace import (
    report_evidence_card_source_records as _report_evidence_card_source_records,
)
from app.services.evidence_semantic_trace import (
    semantic_trace_payload as _semantic_trace_payload,
)
from app.services.evidence_semantic_trace import (
    source_record_payloads_from_semantic_trace as _source_record_payloads_from_semantic_trace,
)
from app.services.evidence_semantic_trace import (
    technical_report_provenance_edges as _technical_report_provenance_edges,
)
from app.services.evidence_technical_report_context import (
    verification_task_id_for_manifest as _verification_task_id_for_manifest,
)


def build_technical_report_evidence_manifest_payload(
    session: Session,
    task_id: UUID,
) -> dict[str, Any]:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    audit_bundle = get_agent_task_audit_bundle(
        session,
        verification_task_id,
        include_live_release_readiness_db_gate_links=False,
        include_live_claim_retrieval_feedback_links=False,
    )
    draft_payload = audit_bundle["draft"]
    evidence_cards = list(draft_payload.get("evidence_cards") or [])
    claims = list(draft_payload.get("claims") or [])
    evidence_exports = list(audit_bundle.get("evidence_package_exports") or [])
    source_evidence_closure = dict(audit_bundle.get("source_evidence_closure") or {})
    claim_derivations = list(audit_bundle.get("claim_derivations") or [])
    claim_retrieval_feedback = list(audit_bundle.get("claim_retrieval_feedback") or [])
    claim_retrieval_feedback_integrity = dict(
        audit_bundle.get("claim_retrieval_feedback_integrity") or {}
    )
    operator_runs = list(audit_bundle.get("operator_runs") or [])
    context_pack_audit = dict(audit_bundle.get("context_pack_audit") or {})
    document_ids = _uuid_values(
        [
            *[row.get("document_id") for row in draft_payload.get("document_refs") or []],
            *[card.get("document_id") for card in evidence_cards],
            *[
                document_id
                for claim in claims
                for document_id in (claim.get("source_document_ids") or [])
            ],
            *[
                document_id
                for export in evidence_exports
                for document_id in (export.get("document_ids") or [])
            ],
        ]
    )
    run_ids = _uuid_values(
        [
            *[row.get("run_id") for row in draft_payload.get("document_refs") or []],
            *[card.get("run_id") for card in evidence_cards],
            *[run_id for export in evidence_exports for run_id in (export.get("run_ids") or [])],
        ]
    )
    assertion_ids = _uuid_values(
        [
            *[
                assertion_id
                for card in evidence_cards
                for assertion_id in (card.get("assertion_ids") or [])
            ],
            *[
                assertion_id
                for claim in claims
                for assertion_id in (claim.get("assertion_ids") or [])
            ],
        ]
    )
    fact_ids = _uuid_values(
        [
            *[fact_id for card in evidence_cards for fact_id in (card.get("fact_ids") or [])],
            *[fact_id for claim in claims for fact_id in (claim.get("fact_ids") or [])],
        ]
    )
    evidence_ids = _uuid_values(
        evidence_id for card in evidence_cards for evidence_id in (card.get("evidence_ids") or [])
    )
    documents_by_id = _select_by_ids(session, Document, document_ids)
    runs_by_id = _select_by_ids(session, DocumentRun, run_ids)
    semantic_trace = _semantic_trace_payload(
        session,
        assertion_ids=assertion_ids,
        fact_ids=fact_ids,
        evidence_ids=evidence_ids,
    )
    source_documents = [
        _document_payload(row)
        for row in sorted(documents_by_id.values(), key=lambda item: str(item.id))
    ]
    document_runs = [
        _manifest_run_payload(row)
        for row in sorted(runs_by_id.values(), key=lambda item: str(item.id))
    ]
    source_records = [
        *_report_evidence_card_source_records(evidence_cards),
        *_source_record_payloads_from_semantic_trace(
            session,
            semantic_trace["assertion_evidence"],
        ),
    ]
    search_request_ids = _string_values(
        [
            *[row.get("search_request_id") for row in operator_runs],
            *[row.get("search_request_id") for row in evidence_exports],
        ]
    )
    operator_run_ids = _string_values(
        [
            *(row.get("operator_run_id") for row in operator_runs),
            *[
                operator_run_id
                for export in evidence_exports
                for operator_run_id in (export.get("operator_run_ids") or [])
            ],
        ]
    )
    source_snapshot_sha256s = _string_values(
        [
            *(draft_payload.get("source_snapshot_sha256s") or []),
            *[value for claim in claims for value in (claim.get("source_snapshot_sha256s") or [])],
            *[
                value
                for export in evidence_exports
                for value in (export.get("source_snapshot_sha256s") or [])
            ],
        ]
    )
    provenance_edges = _technical_report_provenance_edges(
        source_documents=source_documents,
        document_runs=document_runs,
        evidence_exports=evidence_exports,
        evidence_cards=evidence_cards,
        claims=claims,
        claim_derivations=claim_derivations,
        claim_retrieval_feedback=claim_retrieval_feedback,
        semantic_trace=semantic_trace,
        context_pack_audit=context_pack_audit,
    )
    checklist = {
        "has_source_documents": bool(source_documents),
        "all_source_documents_hashed": bool(source_documents)
        and all(document.get("sha256") for document in source_documents),
        "has_document_runs": bool(document_runs),
        "all_document_runs_validation_passed": bool(document_runs)
        and all(run.get("validation_status") == "passed" for run in document_runs),
        "has_evidence_cards": bool(evidence_cards),
        "has_claims": bool(claims),
        "has_claim_derivations": len(claim_derivations) == len(claims) and bool(claims),
        "has_claim_provenance_locks": bool(claims)
        and all(claim.get("provenance_lock_sha256") for claim in claims)
        and audit_bundle["audit_checklist"].get("all_claims_have_provenance_locks", False),
        "has_claim_support_judgments": bool(claims)
        and all(
            claim.get("support_verdict") == "supported"
            and claim.get("support_score") is not None
            and claim.get("support_judge_run_id")
            and claim.get("support_judgment_sha256")
            for claim in claims
        )
        and audit_bundle["audit_checklist"].get("all_claims_have_support_judgments", False)
        and audit_bundle["audit_checklist"].get(
            "claim_support_judgment_integrity_verified",
            False,
        ),
        "has_claim_source_search_results": bool(claims)
        and all(claim.get("source_search_request_result_ids") for claim in claims)
        and audit_bundle["audit_checklist"].get("all_claims_have_source_search_results", False),
        "has_claim_retrieval_feedback_ledger": audit_bundle["audit_checklist"].get(
            "has_claim_retrieval_feedback_ledger",
            False,
        ),
        "claim_retrieval_feedback_coverage_complete": audit_bundle["audit_checklist"].get(
            "claim_retrieval_feedback_coverage_complete",
            False,
        ),
        "claim_retrieval_feedback_integrity_verified": audit_bundle["audit_checklist"].get(
            "claim_retrieval_feedback_integrity_verified",
            False,
        ),
        "has_semantic_trace": bool(
            semantic_trace["assertions"]
            or semantic_trace["facts"]
            or draft_payload.get("graph_context")
        ),
        "has_generation_operator_run": audit_bundle["audit_checklist"].get(
            "has_generation_operator_run",
            False,
        ),
        "has_support_judge_operator_run": audit_bundle["audit_checklist"].get(
            "has_support_judge_operator_run",
            False,
        ),
        "has_verification_operator_run": audit_bundle["audit_checklist"].get(
            "has_verification_operator_run",
            False,
        ),
        "has_context_pack_artifact": audit_bundle["audit_checklist"].get(
            "has_context_pack_artifact",
            False,
        ),
        "has_context_pack_evaluation_artifact": audit_bundle["audit_checklist"].get(
            "has_context_pack_evaluation_artifact",
            False,
        ),
        "has_context_pack_verifier_record": audit_bundle["audit_checklist"].get(
            "has_context_pack_verifier_record",
            False,
        ),
        "has_context_pack_evaluation_operator_run": audit_bundle["audit_checklist"].get(
            "has_context_pack_evaluation_operator_run",
            False,
        ),
        "context_pack_evaluation_passed": audit_bundle["audit_checklist"].get(
            "context_pack_evaluation_passed",
            False,
        ),
        "context_pack_hash_verified": audit_bundle["audit_checklist"].get(
            "context_pack_hash_verified",
            False,
        ),
        "has_release_readiness_assessments": audit_bundle["audit_checklist"].get(
            "has_release_readiness_assessments",
            False,
        ),
        "release_readiness_assessments_cover_source_requests": audit_bundle["audit_checklist"].get(
            "release_readiness_assessments_cover_source_requests", False
        ),
        "release_readiness_assessments_ready": audit_bundle["audit_checklist"].get(
            "release_readiness_assessments_ready",
            False,
        ),
        "release_readiness_assessment_integrity_verified": audit_bundle["audit_checklist"].get(
            "release_readiness_assessment_integrity_verified", False
        ),
        "release_readiness_db_gate_verified": audit_bundle["audit_checklist"].get(
            "release_readiness_db_gate_verified",
            False,
        ),
        "release_readiness_db_gate_complete": audit_bundle["audit_checklist"].get(
            "release_readiness_db_gate_complete",
            False,
        ),
        "release_readiness_db_covers_source_requests": audit_bundle["audit_checklist"].get(
            "release_readiness_db_covers_source_requests", False
        ),
        "has_persisted_release_readiness_db_gate": audit_bundle["audit_checklist"].get(
            "has_persisted_release_readiness_db_gate",
            False,
        ),
        "persisted_release_readiness_db_gate_integrity_verified": audit_bundle[
            "audit_checklist"
        ].get("persisted_release_readiness_db_gate_integrity_verified", False),
        "verification_passed": audit_bundle["audit_checklist"].get(
            "verification_passed",
            False,
        ),
        "hash_integrity_verified": audit_bundle["audit_checklist"].get(
            "hash_integrity_verified",
            False,
        ),
        "has_frozen_source_evidence_packages": audit_bundle["audit_checklist"].get(
            "has_frozen_source_evidence_packages",
            False,
        ),
        "source_evidence_trace_integrity_verified": audit_bundle["audit_checklist"].get(
            "source_evidence_trace_integrity_verified",
            False,
        ),
        "generation_evidence_closed": audit_bundle["audit_checklist"].get(
            "generation_evidence_closed",
            False,
        ),
        "change_impact_clear": audit_bundle["audit_checklist"].get(
            "change_impact_clear",
            False,
        ),
        "replay_alert_waiver_closure_integrity_verified": audit_bundle["audit_checklist"].get(
            "replay_alert_waiver_closure_integrity_verified", False
        ),
        "replay_alert_waiver_lifecycle_clear": audit_bundle["audit_checklist"].get(
            "replay_alert_waiver_lifecycle_clear",
            False,
        ),
        "active_replay_alert_fixture_corpus_snapshot_id": audit_bundle["audit_checklist"].get(
            "active_replay_alert_fixture_corpus_snapshot_id"
        ),
        "active_replay_alert_fixture_corpus_sha256": audit_bundle["audit_checklist"].get(
            "active_replay_alert_fixture_corpus_sha256"
        ),
        "replay_alert_fixture_corpus_snapshot_governed": audit_bundle["audit_checklist"].get(
            "replay_alert_fixture_corpus_snapshot_governed", True
        ),
        "replay_alert_fixture_corpus_trace_complete": audit_bundle["audit_checklist"].get(
            "replay_alert_fixture_corpus_trace_complete", True
        ),
        "invalid_replay_alert_fixture_corpus_snapshot_governance_count": audit_bundle[
            "audit_checklist"
        ].get("invalid_replay_alert_fixture_corpus_snapshot_governance_count", 0),
        "incomplete_replay_alert_fixture_corpus_trace_count": audit_bundle["audit_checklist"].get(
            "incomplete_replay_alert_fixture_corpus_trace_count", 0
        ),
        "has_provenance_edges": bool(provenance_edges),
    }
    checklist["complete"] = all(value for value in checklist.values() if isinstance(value, bool))
    return {
        "schema_name": "technical_report_evidence_manifest",
        "schema_version": "1.0",
        "manifest_kind": "technical_report_court_evidence",
        "task": audit_bundle["task"],
        "draft_task": audit_bundle["draft_task"],
        "verification_task": audit_bundle["verification_task"],
        "source_documents": source_documents,
        "document_runs": document_runs,
        "source_records": source_records,
        "semantic_trace": semantic_trace,
        "retrieval_trace": {
            "search_request_ids": search_request_ids,
            "ranking_operator_runs": [
                row
                for row in operator_runs
                if row.get("operator_kind") in {"retrieve", "rerank", "judge"}
            ],
            "search_evidence_package_exports": [
                row for row in evidence_exports if row.get("package_kind") == "search_request"
            ],
            "search_evidence_package_trace_summaries": list(
                audit_bundle.get("search_evidence_package_traces") or []
            ),
            "source_evidence_closure": source_evidence_closure,
        },
        "report_trace": {
            "evidence_cards": evidence_cards,
            "claims": claims,
            "claim_derivations": claim_derivations,
            "claim_retrieval_feedback": claim_retrieval_feedback,
            "claim_retrieval_feedback_integrity": claim_retrieval_feedback_integrity,
            "evidence_package_exports": evidence_exports,
            "evidence_package_integrity": audit_bundle["integrity"],
            "verification": audit_bundle["verification_record"],
            "context_pack_audit": context_pack_audit,
            "operator_runs": operator_runs,
        },
        "provenance_edges": provenance_edges,
        "change_impact": audit_bundle["change_impact"],
        "audit_checklist": checklist,
        "source_snapshot_sha256s": source_snapshot_sha256s,
        "document_ids": _string_values(document_ids),
        "run_ids": _string_values(run_ids),
        "claim_ids": _string_values(claim.get("claim_id") for claim in claims),
        "search_request_ids": search_request_ids,
        "operator_run_ids": operator_run_ids,
    }
