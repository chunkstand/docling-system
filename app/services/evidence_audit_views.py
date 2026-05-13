# ruff: noqa: E501, F401, I001
from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    AgentTaskVerification,
    ClaimEvidenceDerivation,
    EvidenceManifest,
    EvidencePackageExport,
    KnowledgeOperatorRun,
    SemanticGovernanceEvent,
    TechnicalReportReleaseReadinessDbGate,
)
from app.services.evidence_claim_feedback import (
    claim_retrieval_feedback_payload as _claim_retrieval_feedback_payload,
    claim_retrieval_feedback_rows_for_verification_task as _claim_retrieval_feedback_rows_for_verification_task,
    technical_report_claim_feedback_integrity_payload as _technical_report_claim_feedback_integrity_payload,
)
from app.services.evidence_claim_support_impacts import (
    change_impact_payload as _change_impact_payload,
)
from app.services.evidence_common import int_or_none as _int_or_none
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe
from app.services.evidence_constants import RELEASE_READINESS_DB_GATE_CHECK_KEY
from app.services.evidence_provenance import (
    TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
    frozen_export_receipt as _frozen_export_receipt,
)
from app.services.evidence_records import (
    evidence_export_payload as _evidence_export_payload,
)
from app.services.evidence_technical_report_exports import (
    claim_derivation_payload as _claim_derivation_payload,
)
from app.services.evidence_release_readiness import (
    prov_export_receipt_integrity as _prov_export_receipt_integrity,
    technical_report_context_pack_audit_payload as _technical_report_context_pack_audit_payload,
    technical_report_readiness_db_gate_for_verification_task as _technical_report_readiness_db_gate_for_verification_task,
    with_release_readiness_db_gate_record as _with_release_readiness_db_gate_record,
)
from app.services.evidence_search_closure import technical_report_search_evidence_closure_payload
from app.services.evidence_semantic_trace import (
    technical_report_integrity_payload as _technical_report_integrity_payload,
)
from app.services.evidence_task_payloads import (
    artifact_payload as _artifact_payload,
    immutability_event_payload as _immutability_event_payload,
    operator_run_summary as _operator_run_summary,
    task_payload as _task_payload,
    verification_payload as _verification_payload,
)
from app.services.evidence_technical_report_context import (
    context_pack_eval_task_ids_for_harness as _context_pack_eval_task_ids_for_harness,
    context_pack_verification_rows as _context_pack_verification_rows,
    draft_task_id_for_audit as _draft_task_id_for_audit,
    technical_report_upstream_task_ids as _technical_report_upstream_task_ids,
)
from app.services.semantic_governance import (
    record_technical_report_release_readiness_db_gate_event,
    semantic_governance_chain_for_audit,
)

def _provenance_export_receipt_payload(row: AgentTaskArtifact) -> dict:
    payload = _json_payload(row.payload_json or {})
    frozen_export = payload.get("frozen_export") or {}
    receipt = _frozen_export_receipt(payload)
    return {
        "artifact_id": row.id,
        "task_id": row.task_id,
        "artifact_kind": row.artifact_kind,
        "storage_path": row.storage_path,
        "export_payload_sha256": frozen_export.get("export_payload_sha256"),
        "prov_hash_basis_sha256": frozen_export.get("prov_hash_basis_sha256"),
        "export_receipt": receipt,
        "receipt_integrity": _prov_export_receipt_integrity(payload),
    }

def _technical_report_context_pack_audit_for_verification_task(
    session: Session,
    verification_task_id: UUID,
) -> dict[str, Any]:
    verification_task = session.get(AgentTask, verification_task_id)
    if verification_task is None:
        raise ValueError(f"Agent task '{verification_task_id}' was not found.")
    draft_task_id = _draft_task_id_for_audit(verification_task)
    draft_task = session.get(AgentTask, draft_task_id)
    if draft_task is None:
        raise ValueError(f"Draft task '{draft_task_id}' was not found.")
    draft_payload = ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
    related_task_ids = [
        draft_task.id,
        *_technical_report_upstream_task_ids(session, draft_payload),
        verification_task_id,
    ]
    related_task_ids = list(dict.fromkeys(related_task_ids))
    artifacts = list(
        session.scalars(
            select(AgentTaskArtifact)
            .where(AgentTaskArtifact.task_id.in_(related_task_ids))
            .order_by(AgentTaskArtifact.created_at.asc())
        )
    )
    operator_runs = list(
        session.scalars(
            select(KnowledgeOperatorRun)
            .where(KnowledgeOperatorRun.agent_task_id.in_(related_task_ids))
            .order_by(KnowledgeOperatorRun.created_at.asc())
        )
    )
    harness_task_id = _uuid_or_none_safe(draft_payload.get("harness_task_id"))
    context_pack_eval_task_ids = (
        _context_pack_eval_task_ids_for_harness(session, harness_task_id)
        if harness_task_id is not None
        else []
    )
    context_pack_verifications = _context_pack_verification_rows(
        session,
        harness_task_id=harness_task_id,
        eval_task_ids=context_pack_eval_task_ids,
    )
    return _technical_report_context_pack_audit_payload(
        harness_task_id=harness_task_id,
        eval_task_ids=context_pack_eval_task_ids,
        artifacts=artifacts,
        verification_rows=context_pack_verifications,
        operator_runs=operator_runs,
    )


def _ensure_technical_report_release_readiness_db_gate_governance_event(
    session: Session,
    row: TechnicalReportReleaseReadinessDbGate,
) -> TechnicalReportReleaseReadinessDbGate:
    if row.evidence_manifest_id is None or row.prov_export_artifact_id is None:
        return row
    if row.semantic_governance_event_id is not None:
        event = session.get(SemanticGovernanceEvent, row.semantic_governance_event_id)
        if (
            event is not None
            and event.event_kind == "technical_report_readiness_db_gate_recorded"
            and event.evidence_manifest_id == row.evidence_manifest_id
            and event.agent_task_artifact_id == row.prov_export_artifact_id
        ):
            return row
    event = record_technical_report_release_readiness_db_gate_event(session, gate=row)
    row.semantic_governance_event_id = event.id
    row.updated_at = utcnow()
    session.flush()
    return row


def persist_technical_report_release_readiness_db_gate(
    session: Session,
    *,
    verification_task_id: UUID,
    evidence_manifest: EvidenceManifest | None = None,
    prov_export_artifact: AgentTaskArtifact | None = None,
) -> TechnicalReportReleaseReadinessDbGate | None:
    row = _technical_report_readiness_db_gate_for_verification_task(
        session,
        verification_task_id,
    )
    if row is not None:
        changed = False
        if evidence_manifest is not None and row.evidence_manifest_id != evidence_manifest.id:
            row.evidence_manifest_id = evidence_manifest.id
            changed = True
        if (
            prov_export_artifact is not None
            and row.prov_export_artifact_id != prov_export_artifact.id
        ):
            row.prov_export_artifact_id = prov_export_artifact.id
            changed = True
        if changed:
            row.updated_at = utcnow()
            session.flush()
        return _ensure_technical_report_release_readiness_db_gate_governance_event(
            session,
            row,
        )

    context_pack_audit = _technical_report_context_pack_audit_for_verification_task(
        session,
        verification_task_id,
    )
    gate_payload = _json_payload(context_pack_audit.get("release_readiness_db_gate") or {})
    source_verification_id = _uuid_or_none_safe(gate_payload.get("verification_id"))
    if source_verification_id is None:
        return None
    now = utcnow()
    row = TechnicalReportReleaseReadinessDbGate(
        id=uuid.uuid4(),
        technical_report_verification_task_id=verification_task_id,
        source_verification_id=source_verification_id,
        source_verification_task_id=_uuid_or_none_safe(gate_payload.get("verification_task_id")),
        harness_task_id=_uuid_or_none_safe(context_pack_audit.get("harness_task_id")),
        evidence_manifest_id=evidence_manifest.id if evidence_manifest is not None else None,
        prov_export_artifact_id=(
            prov_export_artifact.id if prov_export_artifact is not None else None
        ),
        check_key=RELEASE_READINESS_DB_GATE_CHECK_KEY,
        passed=gate_payload.get("passed") is True,
        required=gate_payload.get("required") if gate_payload.get("required") is not None else None,
        coverage_complete=gate_payload.get("coverage_complete") is True,
        complete=gate_payload.get("complete") is True,
        source_search_request_count=_int_or_none(
            gate_payload.get("source_search_request_count")
        )
        or 0,
        verified_request_count=_int_or_none(gate_payload.get("verified_request_count")) or 0,
        failure_count=_int_or_none(gate_payload.get("failure_count")) or 0,
        source_search_request_ids_json=_string_values(
            gate_payload.get("source_search_request_ids") or []
        ),
        verified_request_ids_json=_string_values(gate_payload.get("verified_request_ids") or []),
        missing_expected_request_ids_json=_string_values(
            gate_payload.get("missing_expected_request_ids") or []
        ),
        unexpected_verified_request_ids_json=_string_values(
            gate_payload.get("unexpected_verified_request_ids") or []
        ),
        summary_json=_json_payload(gate_payload.get("summary") or {}),
        gate_payload_json=gate_payload,
        gate_payload_sha256=str(payload_sha256(gate_payload)),
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    return _ensure_technical_report_release_readiness_db_gate_governance_event(
        session,
        row,
    )


def get_agent_task_audit_bundle(
    session: Session,
    task_id: UUID,
    *,
    include_live_release_readiness_db_gate_links: bool = True,
    include_live_claim_retrieval_feedback_links: bool = True,
) -> dict:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    draft_task_id = _draft_task_id_for_audit(task)
    draft_task = session.get(AgentTask, draft_task_id)
    if draft_task is None:
        raise ValueError(f"Draft task '{draft_task_id}' was not found.")

    verification_task = task if task.task_type == "verify_technical_report" else None
    verification_row = None
    if verification_task is not None:
        verification_row = session.scalar(
            select(AgentTaskVerification).where(
                AgentTaskVerification.verification_task_id == verification_task.id
            )
        )

    draft_payload = ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
    related_task_ids = [
        draft_task.id,
        *_technical_report_upstream_task_ids(session, draft_payload),
    ]
    if verification_task is not None:
        related_task_ids.append(verification_task.id)
    related_task_ids = list(dict.fromkeys(related_task_ids))

    artifacts = list(
        session.scalars(
            select(AgentTaskArtifact)
            .where(AgentTaskArtifact.task_id.in_(related_task_ids))
            .order_by(AgentTaskArtifact.created_at.asc())
        )
    )
    prov_export_artifacts = [
        row for row in artifacts if row.artifact_kind == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND
    ]
    prov_export_artifact_ids = [row.id for row in prov_export_artifacts]
    prov_export_receipts = [
        _provenance_export_receipt_payload(row) for row in prov_export_artifacts
    ]
    prov_export_immutability_events = (
        list(
            session.scalars(
                select(AgentTaskArtifactImmutabilityEvent)
                .where(AgentTaskArtifactImmutabilityEvent.artifact_id.in_(prov_export_artifact_ids))
                .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
            )
        )
        if prov_export_artifact_ids
        else []
    )
    evidence_manifests = list(
        session.scalars(
            select(EvidenceManifest)
            .where(
                or_(
                    EvidenceManifest.agent_task_id.in_(related_task_ids),
                    EvidenceManifest.draft_task_id.in_(related_task_ids),
                    EvidenceManifest.verification_task_id.in_(related_task_ids),
                )
            )
            .order_by(EvidenceManifest.created_at.asc())
        )
    )
    semantic_governance_chain = semantic_governance_chain_for_audit(
        session,
        task_ids=related_task_ids,
        artifact_ids=prov_export_artifact_ids,
        evidence_manifest_ids=[row.id for row in evidence_manifests],
        receipt_sha256s=[
            (row.get("export_receipt") or {}).get("receipt_sha256") for row in prov_export_receipts
        ],
    )
    exports = list(
        session.scalars(
            select(EvidencePackageExport)
            .where(EvidencePackageExport.agent_task_id.in_(related_task_ids))
            .order_by(EvidencePackageExport.created_at.asc())
        )
    )
    report_exports = [row for row in exports if row.package_kind == "technical_report_claims"]
    search_exports = [row for row in exports if row.package_kind == "search_request"]
    report_export_ids = [row.id for row in report_exports]
    derivations: list[ClaimEvidenceDerivation] = []
    if report_export_ids:
        derivations = list(
            session.scalars(
                select(ClaimEvidenceDerivation)
                .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(report_export_ids))
                .order_by(ClaimEvidenceDerivation.claim_id.asc())
            )
        )
    claim_retrieval_feedback_rows = (
        _claim_retrieval_feedback_rows_for_verification_task(session, verification_task.id)
        if verification_task is not None
        else []
    )
    operator_runs = list(
        session.scalars(
            select(KnowledgeOperatorRun)
            .where(KnowledgeOperatorRun.agent_task_id.in_(related_task_ids))
            .order_by(KnowledgeOperatorRun.created_at.asc())
        )
    )
    harness_task_id = _uuid_or_none_safe(draft_payload.get("harness_task_id"))
    context_pack_eval_task_ids = (
        _context_pack_eval_task_ids_for_harness(session, harness_task_id)
        if harness_task_id is not None
        else []
    )
    context_pack_verifications = _context_pack_verification_rows(
        session,
        harness_task_id=harness_task_id,
        eval_task_ids=context_pack_eval_task_ids,
    )
    context_pack_audit = _technical_report_context_pack_audit_payload(
        harness_task_id=harness_task_id,
        eval_task_ids=context_pack_eval_task_ids,
        artifacts=artifacts,
        verification_rows=context_pack_verifications,
        operator_runs=operator_runs,
    )
    release_readiness_db_gate_row = (
        _technical_report_readiness_db_gate_for_verification_task(
            session,
            verification_task.id,
        )
        if verification_task is not None
        else None
    )
    context_pack_audit = _with_release_readiness_db_gate_record(
        context_pack_audit,
        release_readiness_db_gate_row,
        include_links=include_live_release_readiness_db_gate_links,
    )
    verification_payload = (
        ((verification_task.result_json or {}).get("payload") or {})
        if verification_task is not None
        else None
    )
    change_impact = _change_impact_payload(session, exports)
    claim_support_change_impacts = change_impact.get("claim_support_policy_change_impacts") or {}
    waiver_lifecycle = claim_support_change_impacts.get("waiver_lifecycle") or {}
    replay_alert_fixture_corpus = (
        claim_support_change_impacts.get("replay_alert_fixture_corpus") or {}
    )
    unresolved_waiver_count = int(waiver_lifecycle.get("unresolved_waiver_count") or 0)
    invalid_waiver_closure_count = int(waiver_lifecycle.get("invalid_waiver_closure_count") or 0)
    replay_alert_waiver_closure_integrity_verified = bool(
        waiver_lifecycle.get("waiver_closure_integrity_verified", True)
    )
    replay_alert_waiver_lifecycle_clear = (
        unresolved_waiver_count == 0
        and invalid_waiver_closure_count == 0
        and replay_alert_waiver_closure_integrity_verified
    )
    invalid_replay_alert_fixture_corpus_snapshot_count = int(
        replay_alert_fixture_corpus.get("invalid_snapshot_governance_count") or 0
    )
    incomplete_replay_alert_fixture_corpus_trace_count = int(
        replay_alert_fixture_corpus.get("trace_incomplete_snapshot_count") or 0
    )
    replay_alert_fixture_corpus_snapshot_governed = bool(
        replay_alert_fixture_corpus.get("governance_integrity_verified", True)
    )
    replay_alert_fixture_corpus_trace_complete = bool(
        replay_alert_fixture_corpus.get("trace_complete", True)
    )
    integrity = _technical_report_integrity_payload(draft_payload, report_exports, derivations)
    claim_retrieval_feedback_integrity = (
        _technical_report_claim_feedback_integrity_payload(
            draft_payload,
            claim_retrieval_feedback_rows,
            session=session,
            require_live_links=include_live_claim_retrieval_feedback_links,
        )
    )
    source_evidence_closure = technical_report_search_evidence_closure_payload(
        session,
        draft_payload,
    )
    hash_integrity_verified = (
        integrity["draft_package_hash_matches"]
        and integrity["export_package_hash_matches"]
        and integrity["claim_derivation_count_matches"]
        and integrity["claim_derivation_hash_mismatch_count"] == 0
        and integrity["claim_package_hash_mismatch_count"] == 0
        and integrity["claim_provenance_lock_mismatch_count"] == 0
        and integrity["claim_provenance_lock_contract_mismatch_count"] == 0
        and integrity["missing_claim_provenance_lock_count"] == 0
        and integrity["claim_support_judgment_mismatch_count"] == 0
        and integrity["claim_support_judgment_contract_mismatch_count"] == 0
        and integrity["missing_claim_support_judgment_count"] == 0
        and integrity["failed_claim_support_judgment_count"] == 0
        and integrity["missing_claim_derivation_count"] == 0
    )
    source_evidence_trace_integrity_verified = source_evidence_closure["complete"]
    prov_export_receipts_integrity_verified = bool(prov_export_receipts) and all(
        (row.get("receipt_integrity") or {}).get("complete") for row in prov_export_receipts
    )
    prov_export_receipt_signature_verified = bool(prov_export_receipts) and all(
        (row.get("receipt_integrity") or {}).get("signature_verification_status") == "verified"
        for row in prov_export_receipts
    )
    audit_bundle = {
        "schema_name": "technical_report_audit_bundle",
        "schema_version": "1.0",
        "task": _task_payload(task),
        "draft_task": _task_payload(draft_task),
        "verification_task": _task_payload(verification_task),
        "draft": draft_payload,
        "verification": verification_payload,
        "verification_record": _verification_payload(verification_row),
        "artifacts": [_artifact_payload(row) for row in artifacts],
        "provenance_export_receipts": prov_export_receipts,
        "provenance_export_immutability_events": [
            _immutability_event_payload(row) for row in prov_export_immutability_events
        ],
        "semantic_governance_chain": semantic_governance_chain,
        "evidence_package_exports": [_evidence_export_payload(row) for row in exports],
        "search_evidence_package_traces": source_evidence_closure["trace_summaries"],
        "source_evidence_closure": source_evidence_closure,
        "claim_derivations": [_claim_derivation_payload(row) for row in derivations],
        "claim_retrieval_feedback": [
            _claim_retrieval_feedback_payload(
                row,
                include_live_links=include_live_claim_retrieval_feedback_links,
            )
            for row in claim_retrieval_feedback_rows
        ],
        "claim_retrieval_feedback_integrity": claim_retrieval_feedback_integrity,
        "operator_runs": [_operator_run_summary(row) for row in operator_runs],
        "context_pack_audit": context_pack_audit,
        "change_impact": change_impact,
        "integrity": integrity,
        "audit_checklist": {
            "has_frozen_evidence_package": bool(exports),
            "all_claims_have_derivations": len(derivations)
            == len(draft_payload.get("claims") or []),
            "all_claims_have_provenance_locks": bool(draft_payload.get("claims"))
            and all(
                claim.get("provenance_lock") and claim.get("provenance_lock_sha256")
                for claim in draft_payload.get("claims") or []
            )
            and integrity["missing_claim_provenance_lock_count"] == 0
            and integrity["claim_provenance_lock_mismatch_count"] == 0,
            "all_claim_provenance_locks_match_claim_fields": (
                integrity["claim_provenance_lock_contract_mismatch_count"] == 0
            ),
            "all_claims_have_support_judgments": bool(draft_payload.get("claims"))
            and all(
                claim.get("support_verdict") == "supported"
                and claim.get("support_score") is not None
                and claim.get("support_judge_run_id")
                and claim.get("support_judgment")
                and claim.get("support_judgment_sha256")
                for claim in draft_payload.get("claims") or []
            )
            and integrity["missing_claim_support_judgment_count"] == 0
            and integrity["failed_claim_support_judgment_count"] == 0,
            "all_claim_support_judgments_match_claim_fields": (
                integrity["claim_support_judgment_contract_mismatch_count"] == 0
            ),
            "claim_support_judgment_integrity_verified": (
                integrity["claim_support_judgment_mismatch_count"] == 0
            ),
            "all_claims_have_source_search_results": bool(draft_payload.get("claims"))
            and all(
                claim.get("source_search_request_result_ids")
                for claim in draft_payload.get("claims") or []
            ),
            "has_claim_retrieval_feedback_ledger": bool(claim_retrieval_feedback_rows),
            "claim_retrieval_feedback_coverage_complete": (
                claim_retrieval_feedback_integrity["coverage_complete"]
            ),
            "claim_retrieval_feedback_integrity_verified": (
                claim_retrieval_feedback_integrity["integrity_verified"]
            ),
            "hash_integrity_verified": hash_integrity_verified,
            "has_frozen_source_evidence_packages": bool(search_exports),
            "has_frozen_prov_export": bool(prov_export_artifacts),
            "has_prov_export_receipt": bool(prov_export_receipts)
            and all(
                (row.get("export_receipt") or {}).get("receipt_sha256")
                for row in prov_export_receipts
            ),
            "has_signed_prov_export_receipt": any(
                (row.get("export_receipt") or {}).get("signature_status") == "signed"
                for row in prov_export_receipts
            ),
            "prov_export_receipts_integrity_verified": (prov_export_receipts_integrity_verified),
            "prov_export_receipt_signature_verified": (prov_export_receipt_signature_verified),
            "no_prov_export_immutability_events": not prov_export_immutability_events,
            "has_semantic_governance_chain": semantic_governance_chain["integrity"]["has_events"],
            "semantic_governance_chain_integrity_verified": semantic_governance_chain["integrity"][
                "complete"
            ],
            "semantic_governance_chain_links_prov_receipt": semantic_governance_chain["integrity"][
                "links_requested_prov_receipt"
            ],
            "semantic_governance_chain_change_impact_evaluated": (
                semantic_governance_chain["integrity"]["change_impact_evaluated"]
            ),
            "source_evidence_trace_integrity_verified": (source_evidence_trace_integrity_verified),
            "generation_evidence_closed": (
                hash_integrity_verified and source_evidence_trace_integrity_verified
            ),
            "has_generation_operator_run": any(
                row.operator_kind == "generate" for row in operator_runs
            ),
            "has_support_judge_operator_run": any(
                row.operator_kind == "judge"
                and row.operator_name == "technical_report_claim_support_judge"
                for row in operator_runs
            ),
            "has_verification_operator_run": any(
                row.operator_kind == "verify" for row in operator_runs
            ),
            "has_context_pack_artifact": context_pack_audit["integrity"][
                "has_context_pack_artifact"
            ],
            "has_context_pack_evaluation_artifact": context_pack_audit["integrity"][
                "has_context_pack_evaluation_artifact"
            ],
            "has_context_pack_verifier_record": context_pack_audit["integrity"][
                "has_context_pack_verifier_record"
            ],
            "has_context_pack_evaluation_operator_run": context_pack_audit["integrity"][
                "has_context_pack_evaluation_operator_run"
            ],
            "context_pack_evaluation_passed": context_pack_audit["integrity"][
                "latest_context_pack_evaluation_passed"
            ],
            "context_pack_hash_verified": context_pack_audit["integrity"][
                "context_pack_hash_verified"
            ],
            "has_release_readiness_assessments": context_pack_audit["integrity"][
                "has_release_readiness_assessments"
            ],
            "release_readiness_assessments_cover_source_requests": context_pack_audit["integrity"][
                "release_readiness_assessments_cover_source_requests"
            ],
            "release_readiness_assessments_ready": context_pack_audit["integrity"][
                "release_readiness_assessments_ready"
            ],
            "release_readiness_assessment_integrity_verified": context_pack_audit["integrity"][
                "release_readiness_assessment_integrity_verified"
            ],
            "release_readiness_db_gate_verified": context_pack_audit["integrity"][
                "release_readiness_db_gate_verified"
            ],
            "release_readiness_db_gate_complete": context_pack_audit["integrity"][
                "release_readiness_db_gate_complete"
            ],
            "release_readiness_db_covers_source_requests": context_pack_audit["integrity"][
                "release_readiness_db_covers_source_requests"
            ],
            "has_persisted_release_readiness_db_gate": context_pack_audit["integrity"][
                "has_persisted_release_readiness_db_gate"
            ],
            "persisted_release_readiness_db_gate_integrity_verified": context_pack_audit[
                "integrity"
            ]["persisted_release_readiness_db_gate_integrity_verified"],
            "context_pack_audit_complete": context_pack_audit["integrity"]["complete"],
            "verification_passed": (
                verification_row.outcome == "passed" if verification_row is not None else False
            ),
            "change_impact_clear": not change_impact["impacted"],
            "replay_alert_waiver_closure_integrity_verified": (
                replay_alert_waiver_closure_integrity_verified
            ),
            "unresolved_replay_alert_fixture_coverage_waiver_count": (unresolved_waiver_count),
            "invalid_replay_alert_fixture_coverage_waiver_closure_count": (
                invalid_waiver_closure_count
            ),
            "replay_alert_waiver_lifecycle_clear": (replay_alert_waiver_lifecycle_clear),
            "active_replay_alert_fixture_corpus_snapshot_id": (
                replay_alert_fixture_corpus.get("active_replay_alert_fixture_corpus_snapshot_id")
            ),
            "active_replay_alert_fixture_corpus_sha256": (
                replay_alert_fixture_corpus.get("active_replay_alert_fixture_corpus_sha256")
            ),
            "replay_alert_fixture_corpus_snapshot_governed": (
                replay_alert_fixture_corpus_snapshot_governed
            ),
            "replay_alert_fixture_corpus_trace_complete": (
                replay_alert_fixture_corpus_trace_complete
            ),
            "invalid_replay_alert_fixture_corpus_snapshot_governance_count": (
                invalid_replay_alert_fixture_corpus_snapshot_count
            ),
            "incomplete_replay_alert_fixture_corpus_trace_count": (
                incomplete_replay_alert_fixture_corpus_trace_count
            ),
        },
    }
    audit_bundle["audit_checklist"]["complete"] = (
        audit_bundle["audit_checklist"]["generation_evidence_closed"]
        and audit_bundle["audit_checklist"]["all_claims_have_provenance_locks"]
        and audit_bundle["audit_checklist"]["all_claim_provenance_locks_match_claim_fields"]
        and audit_bundle["audit_checklist"]["all_claims_have_support_judgments"]
        and audit_bundle["audit_checklist"]["all_claim_support_judgments_match_claim_fields"]
        and audit_bundle["audit_checklist"]["claim_support_judgment_integrity_verified"]
        and audit_bundle["audit_checklist"]["all_claims_have_source_search_results"]
        and audit_bundle["audit_checklist"]["has_claim_retrieval_feedback_ledger"]
        and audit_bundle["audit_checklist"]["claim_retrieval_feedback_coverage_complete"]
        and audit_bundle["audit_checklist"]["claim_retrieval_feedback_integrity_verified"]
        and audit_bundle["audit_checklist"]["has_generation_operator_run"]
        and audit_bundle["audit_checklist"]["has_support_judge_operator_run"]
        and audit_bundle["audit_checklist"]["has_verification_operator_run"]
        and audit_bundle["audit_checklist"]["context_pack_audit_complete"]
        and audit_bundle["audit_checklist"]["has_release_readiness_assessments"]
        and audit_bundle["audit_checklist"]["release_readiness_assessments_cover_source_requests"]
        and audit_bundle["audit_checklist"]["release_readiness_assessments_ready"]
        and audit_bundle["audit_checklist"]["release_readiness_assessment_integrity_verified"]
        and audit_bundle["audit_checklist"]["release_readiness_db_gate_verified"]
        and audit_bundle["audit_checklist"]["release_readiness_db_gate_complete"]
        and audit_bundle["audit_checklist"]["release_readiness_db_covers_source_requests"]
        and audit_bundle["audit_checklist"]["has_persisted_release_readiness_db_gate"]
        and audit_bundle["audit_checklist"][
            "persisted_release_readiness_db_gate_integrity_verified"
        ]
        and audit_bundle["audit_checklist"]["has_frozen_prov_export"]
        and audit_bundle["audit_checklist"]["has_prov_export_receipt"]
        and audit_bundle["audit_checklist"]["has_signed_prov_export_receipt"]
        and audit_bundle["audit_checklist"]["prov_export_receipts_integrity_verified"]
        and audit_bundle["audit_checklist"]["prov_export_receipt_signature_verified"]
        and audit_bundle["audit_checklist"]["no_prov_export_immutability_events"]
        and audit_bundle["audit_checklist"]["has_semantic_governance_chain"]
        and audit_bundle["audit_checklist"]["semantic_governance_chain_integrity_verified"]
        and audit_bundle["audit_checklist"]["semantic_governance_chain_links_prov_receipt"]
        and audit_bundle["audit_checklist"]["semantic_governance_chain_change_impact_evaluated"]
        and audit_bundle["audit_checklist"]["verification_passed"]
        and audit_bundle["audit_checklist"]["change_impact_clear"]
        and audit_bundle["audit_checklist"]["replay_alert_waiver_closure_integrity_verified"]
        and audit_bundle["audit_checklist"]["replay_alert_waiver_lifecycle_clear"]
        and audit_bundle["audit_checklist"]["replay_alert_fixture_corpus_snapshot_governed"]
        and audit_bundle["audit_checklist"]["replay_alert_fixture_corpus_trace_complete"]
    )
    audit_bundle["audit_bundle_sha256"] = payload_sha256(audit_bundle)
    return audit_bundle


provenance_export_receipt_payload = _provenance_export_receipt_payload
