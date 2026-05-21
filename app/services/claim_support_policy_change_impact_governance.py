from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import unique_strings as _unique_strings
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskVerification,
    KnowledgeOperatorRun,
)
from app.db.public.audit_and_evidence import ClaimEvidenceDerivation, EvidencePackageExport
from app.db.public.claim_support import ClaimSupportCalibrationPolicy
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.claim_support_policy_governance import value_sha256
from app.services.evidence import payload_sha256
from app.services.semantic_governance import active_semantic_basis

CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_SCHEMA = "claim_support_policy_change_impact"
CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_PROFILE = "claim_support_policy_change_impact_v1"
CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD = (
    "activation_change_impact_payload_sha256"
)
TECHNICAL_REPORT_CLAIM_SUPPORT_JUDGE = "technical_report_claim_support_judge"
TECHNICAL_REPORT_DRAFT_ARTIFACT_KIND = "technical_report_draft"
TECHNICAL_REPORT_GATE_VERIFIER_TYPE = "technical_report_gate"
def claim_support_policy_change_impact_payload_sha256(payload: dict[str, Any]) -> str:
    payload_basis = _json_payload(payload)
    payload_basis.pop(CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD, None)
    return str(payload_sha256(payload_basis))


def _policy_snapshot(row: ClaimSupportCalibrationPolicy | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "policy_id": str(row.id),
        "policy_name": row.policy_name,
        "policy_version": row.policy_version,
        "status": row.status,
        "policy_sha256": row.policy_sha256,
        "owner": row.owner,
        "source": row.source,
        "thresholds": row.thresholds_json or {},
        "min_hard_case_kind_count": row.min_hard_case_kind_count,
        "required_hard_case_kinds": list(row.required_hard_case_kinds_json or []),
        "required_verdicts": list(row.required_verdicts_json or []),
        "metadata": row.metadata_json or {},
        "created_at": row.created_at.isoformat(),
    }


def _policy_diff(
    previous_active_policy: ClaimSupportCalibrationPolicy | None,
    activated_policy: ClaimSupportCalibrationPolicy,
) -> dict[str, Any]:
    previous = _policy_snapshot(previous_active_policy)
    activated = _policy_snapshot(activated_policy) or {}
    fields = (
        "policy_name",
        "policy_version",
        "policy_sha256",
        "thresholds",
        "min_hard_case_kind_count",
        "required_hard_case_kinds",
        "required_verdicts",
        "owner",
        "source",
    )
    changed_fields = [
        field
        for field in fields
        if (previous or {}).get(field) != activated.get(field)
    ]
    diff = {
        "schema_name": "claim_support_policy_diff",
        "schema_version": "1.0",
        "previous_active_policy": previous,
        "activated_policy": activated,
        "changed_fields": changed_fields,
    }
    return {**diff, "policy_diff_sha256": value_sha256(diff)}


policy_diff = _policy_diff


def _task_snapshot(row: AgentTask | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "task_id": str(row.id),
        "task_type": row.task_type,
        "status": row.status,
        "workflow_version": row.workflow_version,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "result_sha256": value_sha256(row.result_json or {}),
    }


def _artifact_snapshot(row: AgentTaskArtifact | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "artifact_id": str(row.id),
        "task_id": str(row.task_id),
        "artifact_kind": row.artifact_kind,
        "storage_path": row.storage_path,
        "payload_sha256": value_sha256(row.payload_json or {}),
        "created_at": row.created_at.isoformat(),
    }


def _support_derivation_snapshot(
    derivation: ClaimEvidenceDerivation,
    support_run: KnowledgeOperatorRun,
    draft_task: AgentTask | None,
    export: EvidencePackageExport | None,
) -> dict[str, Any]:
    return {
        "claim_derivation_id": str(derivation.id),
        "claim_id": derivation.claim_id,
        "claim_text": derivation.claim_text,
        "draft_task_id": str(derivation.agent_task_id) if derivation.agent_task_id else None,
        "draft_task": _task_snapshot(draft_task),
        "evidence_package_export_id": str(derivation.evidence_package_export_id),
        "evidence_package_sha256": derivation.evidence_package_sha256,
        "evidence_export_package_sha256": export.package_sha256 if export else None,
        "evidence_export_trace_sha256": export.trace_sha256 if export else None,
        "support_judge_run_id": str(support_run.id),
        "support_judge_run_output_sha256": support_run.output_sha256,
        "support_judgment_sha256": derivation.support_judgment_sha256,
        "support_verdict": derivation.support_verdict,
        "support_score": derivation.support_score,
        "derivation_sha256": derivation.derivation_sha256,
        "created_at": derivation.created_at.isoformat(),
        "impact_reason": "support_judgment_predates_active_claim_support_policy",
    }


def _verification_snapshot(
    verification: AgentTaskVerification,
    verification_task: AgentTask | None,
) -> dict[str, Any]:
    return {
        "verification_record_id": str(verification.id),
        "draft_task_id": str(verification.target_task_id),
        "verification_task_id": (
            str(verification.verification_task_id)
            if verification.verification_task_id
            else None
        ),
        "verification_task": _task_snapshot(verification_task),
        "verifier_type": verification.verifier_type,
        "outcome": verification.outcome,
        "metrics": verification.metrics_json or {},
        "reasons": list(verification.reasons_json or []),
        "created_at": verification.created_at.isoformat(),
        "completed_at": (
            verification.completed_at.isoformat() if verification.completed_at else None
        ),
        "impact_reason": "technical_report_verification_predates_active_claim_support_policy",
    }


def build_claim_support_policy_change_impact_payload(
    session: Session,
    *,
    task: AgentTask,
    activated_policy: ClaimSupportCalibrationPolicy,
    previous_active_policy: ClaimSupportCalibrationPolicy | None,
    activation_artifact: AgentTaskArtifact,
    governance_artifact_id: UUID,
    governance_artifact_path: str | None,
    apply_payload: dict[str, Any],
    change_impact_id: UUID | None = None,
    policy_diff: dict[str, Any] | None = None,
    recorded_at: Any | None = None,
    detail_limit: int = 500,
) -> dict[str, Any]:
    if detail_limit < 1:
        raise ValueError("Change-impact detail_limit must be at least 1.")
    recorded_at = recorded_at or utcnow()
    policy_diff = policy_diff or _policy_diff(previous_active_policy, activated_policy)
    support_rows = list(
        session.execute(
            select(
                ClaimEvidenceDerivation,
                KnowledgeOperatorRun,
                AgentTask,
                EvidencePackageExport,
            )
            .join(
                KnowledgeOperatorRun,
                ClaimEvidenceDerivation.support_judge_run_id == KnowledgeOperatorRun.id,
            )
            .outerjoin(AgentTask, ClaimEvidenceDerivation.agent_task_id == AgentTask.id)
            .outerjoin(
                EvidencePackageExport,
                ClaimEvidenceDerivation.evidence_package_export_id == EvidencePackageExport.id,
            )
            .where(
                ClaimEvidenceDerivation.support_judge_run_id.is_not(None),
                KnowledgeOperatorRun.operator_name == TECHNICAL_REPORT_CLAIM_SUPPORT_JUDGE,
                ClaimEvidenceDerivation.created_at < recorded_at,
                KnowledgeOperatorRun.created_at < recorded_at,
            )
            .order_by(ClaimEvidenceDerivation.created_at.desc(), ClaimEvidenceDerivation.id)
        )
    )
    support_snapshots = [
        _support_derivation_snapshot(derivation, support_run, draft_task, export)
        for derivation, support_run, draft_task, export in support_rows[:detail_limit]
    ]
    support_derivation_ids = _unique_strings(
        [str(derivation.id) for derivation, _support_run, _draft_task, _export in support_rows]
    )
    support_judgment_sha256s = _unique_strings(
        [
            derivation.support_judgment_sha256
            for derivation, _support_run, _draft_task, _export in support_rows
            if derivation.support_judgment_sha256
        ]
    )
    draft_task_ids = _unique_strings(
        [
            str(derivation.agent_task_id)
            for derivation, _support_run, _draft_task, _export in support_rows
            if derivation.agent_task_id
        ]
        + [
            str(support_run.agent_task_id)
            for _derivation, support_run, _draft_task, _export in support_rows
            if support_run.agent_task_id
        ]
    )
    draft_task_uuid_by_text = {str(UUID(task_id)): UUID(task_id) for task_id in draft_task_ids}
    generated_document_artifacts: list[dict[str, Any]] = []
    generated_document_artifact_count = 0
    if draft_task_uuid_by_text:
        artifacts = list(
            session.scalars(
                select(AgentTaskArtifact)
                .where(
                    AgentTaskArtifact.task_id.in_(list(draft_task_uuid_by_text.values())),
                    AgentTaskArtifact.artifact_kind == TECHNICAL_REPORT_DRAFT_ARTIFACT_KIND,
                )
                .order_by(AgentTaskArtifact.created_at.desc(), AgentTaskArtifact.id)
            )
        )
        generated_document_artifact_count = len(artifacts)
        generated_document_artifacts = [
            snapshot
            for snapshot in [_artifact_snapshot(row) for row in artifacts[:detail_limit]]
            if snapshot is not None
        ]

    verification_snapshots: list[dict[str, Any]] = []
    verification_rows: list[tuple[AgentTaskVerification, AgentTask | None]] = []
    if draft_task_uuid_by_text:
        verification_rows = list(
            session.execute(
                select(AgentTaskVerification, AgentTask)
                .outerjoin(AgentTask, AgentTask.id == AgentTaskVerification.verification_task_id)
                .where(
                    AgentTaskVerification.target_task_id.in_(
                        list(draft_task_uuid_by_text.values())
                    ),
                    AgentTaskVerification.verifier_type == TECHNICAL_REPORT_GATE_VERIFIER_TYPE,
                    AgentTaskVerification.created_at < recorded_at,
                )
                .order_by(AgentTaskVerification.created_at.desc(), AgentTaskVerification.id)
            )
        )
        verification_snapshots = [
            _verification_snapshot(verification, verification_task)
            for verification, verification_task in verification_rows[:detail_limit]
        ]
    verification_task_ids = _unique_strings(
        [
            str(verification.verification_task_id)
            for verification, _verification_task in verification_rows
            if verification.verification_task_id
        ]
    )
    verification_result_sha256s = _unique_strings(
        [
            value_sha256(verification_task.result_json or {})
            for _verification, verification_task in verification_rows
            if verification_task is not None
        ]
    )

    changed_fields = list(policy_diff.get("changed_fields") or [])
    impact_reasons = [
        "claim_support_calibration_policy_changed",
        "prior_support_judgments_predate_active_policy",
        "technical_report_verifications_depend_on_prior_support_judgments",
    ]
    if changed_fields:
        impact_reasons.append(
            "policy_fields_changed:" + ",".join(sorted(str(field) for field in changed_fields))
        )
    if not support_rows:
        impact_reasons.append("no_prior_technical_report_support_judgments_found")

    replay_recommendations: list[dict[str, Any]] = []
    for draft_task_id in draft_task_ids[:detail_limit]:
        replay_recommendations.append(
            {
                "action": "rerun_draft_technical_report",
                "target_task_id": draft_task_id,
                "reason": (
                    "The draft contains claim-support judgments created before the "
                    "active calibration policy changed."
                ),
                "priority": "high",
            }
        )
        related_verifications = [
            row
            for row in verification_snapshots
            if row.get("draft_task_id") == draft_task_id and row.get("verification_task_id")
        ]
        for verification in related_verifications:
            replay_recommendations.append(
                {
                    "action": "rerun_verify_technical_report",
                    "target_task_id": verification["draft_task_id"],
                    "prior_verification_task_id": verification["verification_task_id"],
                    "reason": (
                        "The technical-report gate accepted support judgments that "
                        "predate the active calibration policy."
                    ),
                    "priority": "high",
                }
            )

    total_replay_recommended_count = len(draft_task_ids) + len(verification_rows)
    impact_summary = {
        "affected_support_judgment_count": len(support_rows),
        "affected_generated_document_count": len(draft_task_ids),
        "affected_technical_report_verification_count": len(verification_rows),
        "affected_generated_document_artifact_count": generated_document_artifact_count,
        "replay_recommended_count": total_replay_recommended_count,
        "replay_recommendation_detail_count": len(replay_recommendations),
        "details_truncated": (
            len(support_rows) > detail_limit
            or len(draft_task_ids) > detail_limit
            or len(verification_rows) > detail_limit
        ),
        "detail_limit": detail_limit,
    }
    payload_basis = {
        "schema_name": CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_SCHEMA,
        "schema_version": "1.0",
        "governance_profile": CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_PROFILE,
        "source": {
            "source_table": "claim_support_policy_change_impacts",
            "source_id": str(change_impact_id) if change_impact_id else None,
        },
        "change_impact_id": str(change_impact_id) if change_impact_id else None,
        "created_at": recorded_at.isoformat(),
        "created_by": task.approved_by,
        "impact_scope": f"claim_support_policy:{activated_policy.policy_name}",
        "policy_name": activated_policy.policy_name,
        "policy_version": activated_policy.policy_version,
        "activated_policy_id": str(activated_policy.id),
        "activated_policy_sha256": activated_policy.policy_sha256,
        "previous_active_policy_id": (
            str(previous_active_policy.id) if previous_active_policy else None
        ),
        "previous_active_policy_sha256": (
            previous_active_policy.policy_sha256 if previous_active_policy else None
        ),
        "policy_diff": policy_diff,
        "activation": {
            "task_id": str(task.id),
            "activation_artifact_id": str(activation_artifact.id),
            "activation_artifact_path": activation_artifact.storage_path,
            "governance_artifact_id": str(governance_artifact_id),
            "governance_artifact_path": governance_artifact_path,
            "reason": apply_payload.get("reason"),
            "approved_by": apply_payload.get("approved_by"),
            "approved_at": apply_payload.get("approved_at"),
            "operator_run_id": apply_payload.get("operator_run_id"),
        },
        "semantic_basis": active_semantic_basis(session),
        "impact_summary": impact_summary,
        "impact_reasons": impact_reasons,
        "affected_ids": {
            "claim_derivation_ids": support_derivation_ids,
            "draft_task_ids": draft_task_ids,
            "verification_task_ids": verification_task_ids,
        },
        "affected_support_judgments": support_snapshots,
        "affected_generated_documents": {
            "draft_task_ids": draft_task_ids[:detail_limit],
            "artifacts": generated_document_artifacts,
        },
        "affected_technical_report_verifications": verification_snapshots,
        "replay_recommendations": replay_recommendations,
        "integrity_inputs": {
            "policy_diff_sha256": policy_diff.get("policy_diff_sha256"),
            "activation_decision_sha256": value_sha256(apply_payload),
            "support_judgment_sha256s": support_judgment_sha256s,
            "verification_result_sha256s": verification_result_sha256s,
        },
    }
    return {
        **payload_basis,
        CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD: (
            claim_support_policy_change_impact_payload_sha256(payload_basis)
        ),
    }


def persist_claim_support_policy_change_impact(
    session: Session,
    *,
    impact_payload: dict[str, Any],
    task: AgentTask,
    activated_policy: ClaimSupportCalibrationPolicy,
    previous_active_policy: ClaimSupportCalibrationPolicy | None,
    governance_event: SemanticGovernanceEvent | None,
    governance_artifact: AgentTaskArtifact | None,
    change_impact_id: UUID | None = None,
    storage_service: Any | None = None,
):
    recorded_sha = str(impact_payload.get(CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD) or "")
    expected_sha = claim_support_policy_change_impact_payload_sha256(impact_payload)
    if recorded_sha != expected_sha:
        raise ValueError("Claim support policy change impact payload hash mismatch.")
    payload_change_impact_id = _uuid_or_none(impact_payload.get("change_impact_id"))
    if change_impact_id is not None and payload_change_impact_id not in {
        None,
        change_impact_id,
    }:
        raise ValueError("Claim support policy change impact ID mismatch.")
    row_id = change_impact_id or payload_change_impact_id
    summary = impact_payload.get("impact_summary") or {}
    affected_support_judgments = impact_payload.get("affected_support_judgments") or []
    affected_generated_documents = impact_payload.get("affected_generated_documents") or {}
    affected_verifications = impact_payload.get("affected_technical_report_verifications") or []
    affected_ids = impact_payload.get("affected_ids") or {}
    replay_recommended_count = int(summary.get("replay_recommended_count") or 0)
    row_kwargs: dict[str, Any] = {}
    if row_id is not None:
        row_kwargs["id"] = row_id
    from app.db.public.claim_support import ClaimSupportPolicyChangeImpact

    row = ClaimSupportPolicyChangeImpact(
        **row_kwargs,
        activation_task_id=task.id,
        activated_policy_id=activated_policy.id,
        previous_policy_id=previous_active_policy.id if previous_active_policy else None,
        semantic_governance_event_id=governance_event.id if governance_event else None,
        governance_artifact_id=governance_artifact.id if governance_artifact else None,
        impact_scope=str(
            impact_payload.get("impact_scope")
            or f"claim_support_policy:{activated_policy.policy_name}"
        ),
        policy_name=activated_policy.policy_name,
        policy_version=activated_policy.policy_version,
        activated_policy_sha256=activated_policy.policy_sha256,
        previous_policy_sha256=(
            previous_active_policy.policy_sha256 if previous_active_policy else None
        ),
        affected_support_judgment_count=int(
            summary.get("affected_support_judgment_count") or 0
        ),
        affected_generated_document_count=int(
            summary.get("affected_generated_document_count") or 0
        ),
        affected_verification_count=int(
            summary.get("affected_technical_report_verification_count") or 0
        ),
        replay_recommended_count=replay_recommended_count,
        impacted_claim_derivation_ids_json=_unique_strings(
            list(affected_ids.get("claim_derivation_ids") or [])
            + [
                row.get("claim_derivation_id")
                for row in affected_support_judgments
                if row.get("claim_derivation_id")
            ]
        ),
        impacted_task_ids_json=_unique_strings(
            [
                *(affected_ids.get("draft_task_ids") or []),
                *(affected_generated_documents.get("draft_task_ids") or []),
                *[
                    row.get("draft_task_id")
                    for row in affected_support_judgments
                    if row.get("draft_task_id")
                ],
            ]
        ),
        impacted_verification_task_ids_json=_unique_strings(
            list(affected_ids.get("verification_task_ids") or [])
            + [
                row.get("verification_task_id")
                for row in affected_verifications
                if row.get("verification_task_id")
            ]
        ),
        impact_payload_json=impact_payload,
        impact_payload_sha256=expected_sha,
        replay_status="pending" if replay_recommended_count > 0 else "no_action_required",
        replay_status_updated_at=utcnow(),
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    if replay_recommended_count <= 0:
        from importlib import import_module

        import_module(
            "app.services.claim_support_policy_impact_replay_closure"
        ).refresh_claim_support_policy_change_impact_replay_status(
            session,
            row.id,
            storage_service=storage_service,
            commit=False,
        )
    return row
