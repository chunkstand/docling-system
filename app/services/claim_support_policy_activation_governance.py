from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact, KnowledgeOperatorRun
from app.db.public.claim_support import (
    ClaimSupportCalibrationPolicy,
    ClaimSupportEvaluation,
    ClaimSupportFixtureSet,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent, SemanticGovernanceEventKind
from app.services.claim_support_policy_governance import (
    activation_governance_event_payload,
    evaluation_snapshot,
    fixture_set_diff,
    fixture_set_snapshot,
    signature_payload,
    value_sha256,
)
from app.services.evidence import payload_sha256
from app.services.semantic_governance import (
    active_semantic_basis,
    record_semantic_governance_event,
)

CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND = (
    "claim_support_policy_activation_governance"
)
CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_FILENAME = (
    "claim_support_policy_activation_governance.json"
)
CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_SCHEMA = (
    "claim_support_policy_activation_governance"
)
CLAIM_SUPPORT_POLICY_ACTIVATION_RECEIPT_SCHEMA = (
    "claim_support_policy_activation_governance_receipt"
)
CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_PROFILE = (
    "claim_support_policy_activation_governance_v1"
)


def _prov_jsonld(
    *,
    task: AgentTask,
    activated_policy: ClaimSupportCalibrationPolicy,
    previous_active_policy: ClaimSupportCalibrationPolicy | None,
    retired_policies: list[ClaimSupportCalibrationPolicy],
    verification: dict[str, Any],
    fixture_set: ClaimSupportFixtureSet | None,
    verification_evaluation: ClaimSupportEvaluation | None,
    activation_artifact: AgentTaskArtifact,
    governance_artifact_id: UUID,
    governance_artifact_path: str | None,
    operator_run: KnowledgeOperatorRun | None,
    apply_payload: dict[str, Any],
    policy_diff_sha256: str | None,
    change_impact_payload: dict[str, Any] | None,
    created_by: str | None,
    recorded_at: Any,
) -> dict[str, Any]:
    activation_activity = f"docling:activity:claim_support_policy_activation:{task.id}"
    verification_activity = (
        "docling:activity:claim_support_policy_verification:"
        f"{apply_payload.get('verification_task_id')}"
    )
    agent_id = f"docling:agent:{created_by or 'docling-system'}"
    activated_policy_entity = f"docling:claim_support_calibration_policy:{activated_policy.id}"
    activation_artifact_entity = f"docling:agent_task_artifact:{activation_artifact.id}"
    governance_artifact_entity = f"docling:agent_task_artifact:{governance_artifact_id}"
    change_impact_sha = (
        (change_impact_payload or {}).get("activation_change_impact_payload_sha256")
    )
    change_impact_id = (change_impact_payload or {}).get("change_impact_id")
    change_impact_entity = (
        f"docling:claim_support_policy_change_impact:{change_impact_id}"
        if change_impact_id
        else f"docling:claim_support_policy_change_impact:{change_impact_sha}"
        if change_impact_sha
        else f"docling:claim_support_policy_change_impact:{task.id}"
    )

    graph: list[dict[str, Any]] = [
        {
            "@id": activated_policy_entity,
            "@type": "docling:ClaimSupportCalibrationPolicy",
            "docling:policyName": activated_policy.policy_name,
            "docling:policyVersion": activated_policy.policy_version,
            "docling:policySha256": activated_policy.policy_sha256,
            "docling:status": activated_policy.status,
        },
        {
            "@id": activation_artifact_entity,
            "@type": "docling:AgentTaskArtifact",
            "docling:artifactKind": activation_artifact.artifact_kind,
            "docling:storagePath": activation_artifact.storage_path,
        },
        {
            "@id": governance_artifact_entity,
            "@type": "docling:AgentTaskArtifact",
            "docling:artifactKind": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND,
            "docling:storagePath": governance_artifact_path,
        },
        {
            "@id": activation_activity,
            "@type": "docling:ClaimSupportPolicyActivation",
            "prov:endedAtTime": recorded_at.isoformat()
            if hasattr(recorded_at, "isoformat")
            else str(recorded_at),
            "docling:reason": apply_payload.get("reason"),
        },
        {
            "@id": change_impact_entity,
            "@type": "docling:ClaimSupportPolicyChangeImpact",
            "docling:changeImpactId": change_impact_id,
            "docling:impactPayloadSha256": change_impact_sha,
            "docling:affectedSupportJudgmentCount": (
                ((change_impact_payload or {}).get("impact_summary") or {}).get(
                    "affected_support_judgment_count"
                )
            ),
            "docling:replayRecommendedCount": (
                ((change_impact_payload or {}).get("impact_summary") or {}).get(
                    "replay_recommended_count"
                )
            ),
        },
        {
            "@id": verification_activity,
            "@type": "docling:ClaimSupportPolicyVerification",
            "docling:verificationOutcome": apply_payload.get("verification_outcome"),
        },
        {
            "@id": agent_id,
            "@type": "prov:Person" if created_by else "prov:SoftwareAgent",
            "docling:identifier": created_by or "docling-system",
        },
    ]
    if previous_active_policy is not None:
        graph.append(
            {
                "@id": f"docling:claim_support_calibration_policy:{previous_active_policy.id}",
                "@type": "docling:ClaimSupportCalibrationPolicy",
                "docling:policySha256": previous_active_policy.policy_sha256,
                "docling:status": "retired",
            }
        )
    if fixture_set is not None:
        graph.append(
            {
                "@id": f"docling:claim_support_fixture_set:{fixture_set.id}",
                "@type": "docling:ClaimSupportFixtureSet",
                "docling:fixtureSetSha256": fixture_set.fixture_set_sha256,
                "docling:fixtureCount": fixture_set.fixture_count,
            }
        )
    if verification_evaluation is not None:
        graph.append(
            {
                "@id": f"docling:claim_support_evaluation:{verification_evaluation.id}",
                "@type": "docling:ClaimSupportEvaluation",
                "docling:evaluationPayloadSha256": (
                    verification_evaluation.evaluation_payload_sha256
                ),
                "docling:gateOutcome": verification_evaluation.gate_outcome,
            }
        )
    if operator_run is not None:
        graph.append(
            {
                "@id": f"docling:knowledge_operator_run:{operator_run.id}",
                "@type": "docling:KnowledgeOperatorRun",
                "docling:operatorKind": operator_run.operator_kind,
                "docling:operatorName": operator_run.operator_name,
                "docling:outputSha256": operator_run.output_sha256,
            }
        )
    graph.append(
        {
            "@id": f"docling:claim_support_policy_diff:{activated_policy.id}",
            "@type": "docling:ClaimSupportPolicyDiff",
            "docling:policyDiffSha256": policy_diff_sha256,
        }
    )
    for row in retired_policies:
        graph.append(
            {
                "@id": f"docling:retired_claim_support_policy:{row.id}",
                "@type": "prov:Entity",
                "prov:wasInvalidatedBy": {"@id": activation_activity},
            }
        )
    verification_entity = {
        "@id": f"docling:agent_task_verification:{verification.get('verification_id')}"
    }
    edge_specs = (
        (
            "generated-policy",
            "prov:Generation",
            {
                "prov:entity": {"@id": activated_policy_entity},
                "prov:activity": {"@id": activation_activity},
            },
        ),
        (
            "generated-artifact",
            "prov:Generation",
            {
                "prov:entity": {"@id": activation_artifact_entity},
                "prov:activity": {"@id": activation_activity},
            },
        ),
        (
            "generated-governance-artifact",
            "prov:Generation",
            {
                "prov:entity": {"@id": governance_artifact_entity},
                "prov:activity": {"@id": activation_activity},
            },
        ),
        (
            "generated-change-impact",
            "prov:Generation",
            {
                "prov:entity": {"@id": change_impact_entity},
                "prov:activity": {"@id": activation_activity},
            },
        ),
        (
            "associated",
            "prov:Association",
            {
                "prov:activity": {"@id": activation_activity},
                "prov:agent": {"@id": agent_id},
            },
        ),
        (
            "used-verification",
            "prov:Usage",
            {
                "prov:activity": {"@id": activation_activity},
                "prov:entity": verification_entity,
            },
        ),
        (
            "derived-policy",
            "prov:Derivation",
            {
                "prov:generatedEntity": {"@id": activated_policy_entity},
                "prov:usedEntity": verification_entity,
            },
        ),
    )
    graph.extend(
        {
            "@id": f"docling:edge:{edge_name}:{task.id}",
            "@type": edge_type,
            **edge_payload,
        }
        for edge_name, edge_type, edge_payload in edge_specs
    )
    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://local.docling-system/prov#",
        },
        "@graph": graph,
    }


def _receipt(
    *,
    payload_basis: dict[str, Any],
    payload_sha: str,
    prov_jsonld_sha: str | None,
    created_by: str | None,
) -> dict[str, Any]:
    policy_diff = dict(payload_basis.get("policy_diff") or {})
    fixture_replay = dict(payload_basis.get("fixture_replay") or {})
    hash_entries = (
        (
            1,
            "previous_active_policy",
            dict(policy_diff.get("previous_active_policy") or {}).get("policy_sha256"),
            False,
        ),
        (
            2,
            "activated_policy",
            dict(policy_diff.get("activated_policy") or {}).get("policy_sha256"),
            True,
        ),
        (3, "verification_record", value_sha256(payload_basis.get("verification")), True),
        (
            4,
            "verification_fixture_set",
            dict(fixture_replay.get("fixture_set") or {}).get("fixture_set_sha256"),
            True,
        ),
        (
            5,
            "verification_fixture_set_diff",
            dict(fixture_replay.get("fixture_set_diff") or {}).get(
                "fixture_set_diff_sha256"
            ),
            True,
        ),
        (
            6,
            "mined_failure_summary",
            dict(fixture_replay.get("mined_failure_summary") or {}).get("summary_sha256"),
            False,
        ),
        (7, "activation_decision", value_sha256(payload_basis.get("activation")), True),
        (
            8,
            "policy_change_impact",
            dict(payload_basis.get("activation_change_impact") or {}).get(
                "activation_change_impact_payload_sha256"
            ),
            True,
        ),
        (9, "prov_jsonld", prov_jsonld_sha, True),
        (10, "claim_support_policy_activation_governance", payload_sha, True),
    )
    hash_chain = [
        {
            "position": position,
            "name": name,
            "sha256": sha256,
            "required": required,
        }
        for position, name, sha256, required in hash_entries
    ]
    receipt_core = {
        "schema_name": CLAIM_SUPPORT_POLICY_ACTIVATION_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "governance_profile": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_PROFILE,
        "signed_payload_sha256": payload_sha,
        "prov_jsonld_sha256": prov_jsonld_sha,
        "hash_chain": hash_chain,
        "hash_chain_complete": all(
            bool(item.get("sha256")) for item in hash_chain if item.get("required")
        ),
        "created_at": utcnow().isoformat(),
        "created_by": created_by,
    }
    receipt_sha = str(payload_sha256(receipt_core))
    return {
        **receipt_core,
        "receipt_sha256": receipt_sha,
        **signature_payload(receipt_sha),
    }


def build_claim_support_policy_activation_governance_payload(
    session: Session,
    *,
    task: AgentTask,
    activated_policy: ClaimSupportCalibrationPolicy,
    previous_active_policy: ClaimSupportCalibrationPolicy | None,
    retired_policies: list[ClaimSupportCalibrationPolicy],
    verification: dict[str, Any],
    verification_output: dict[str, Any],
    apply_payload: dict[str, Any],
    activation_artifact: AgentTaskArtifact,
    governance_artifact_id: UUID,
    governance_artifact_path: str | None,
    operator_run: KnowledgeOperatorRun | None,
    change_impact_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recorded_at = utcnow()
    verification_fixture_set_id = _uuid_or_none(apply_payload.get("verification_fixture_set_id"))
    verification_evaluation_id = _uuid_or_none(apply_payload.get("verification_evaluation_id"))
    fixture_set = (
        session.get(ClaimSupportFixtureSet, verification_fixture_set_id)
        if verification_fixture_set_id
        else None
    )
    verification_evaluation = (
        session.get(ClaimSupportEvaluation, verification_evaluation_id)
        if verification_evaluation_id
        else None
    )
    from app.services.claim_support_policy_change_impact_governance import (
        policy_diff as build_policy_diff,
    )

    policy_diff = build_policy_diff(previous_active_policy, activated_policy)
    created_by = task.approved_by
    activation_summary = {
        "task_id": str(task.id),
        "draft_task_id": apply_payload.get("draft_task_id"),
        "verification_task_id": apply_payload.get("verification_task_id"),
        "reason": apply_payload.get("reason"),
        "approved_by": task.approved_by,
        "approved_at": task.approved_at.isoformat() if task.approved_at else None,
        "approval_note": task.approval_note,
        "activated_policy_id": str(activated_policy.id),
        "activated_policy_sha256": activated_policy.policy_sha256,
        "previous_active_policy_id": (
            str(previous_active_policy.id) if previous_active_policy else None
        ),
        "previous_active_policy_sha256": (
            previous_active_policy.policy_sha256 if previous_active_policy else None
        ),
        "retired_policy_ids": [str(row.id) for row in retired_policies],
        "waiver_activation_approval": (apply_payload.get("waiver_activation_approval") or {}),
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }
    verification_summary = {
        "verification": _json_payload(verification),
        "verification_evaluation": evaluation_snapshot(verification_evaluation),
        "verification_output_sha256": value_sha256(verification_output),
    }
    mined_failure_summary = apply_payload.get("verification_mined_failure_summary") or {}
    replay_alert_fixture_summary = (
        apply_payload.get("verification_replay_alert_fixture_summary") or {}
    )
    replay_alert_fixture_coverage_waiver = (
        apply_payload.get("verification_replay_alert_fixture_coverage_waiver") or {}
    )
    fixture_replay = {
        "fixture_set": fixture_set_snapshot(fixture_set),
        "fixture_set_diff": fixture_set_diff(fixture_set, mined_failure_summary),
        "replay_alert_fixture_summary": replay_alert_fixture_summary,
        "replay_alert_fixture_coverage_waiver": replay_alert_fixture_coverage_waiver,
        "mined_failure_summary": mined_failure_summary,
    }
    prov_jsonld = _prov_jsonld(
        task=task,
        activated_policy=activated_policy,
        previous_active_policy=previous_active_policy,
        retired_policies=retired_policies,
        verification=_json_payload(verification),
        fixture_set=fixture_set,
        verification_evaluation=verification_evaluation,
        activation_artifact=activation_artifact,
        governance_artifact_id=governance_artifact_id,
        governance_artifact_path=governance_artifact_path,
        operator_run=operator_run,
        apply_payload=apply_payload,
        policy_diff_sha256=policy_diff.get("policy_diff_sha256"),
        change_impact_payload=change_impact_payload,
        created_by=created_by,
        recorded_at=recorded_at,
    )
    prov_jsonld_sha = value_sha256(prov_jsonld)
    payload_basis = {
        "schema_name": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_SCHEMA,
        "schema_version": "1.0",
        "governance_profile": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_PROFILE,
        "source": {
            "source_table": "claim_support_calibration_policies",
            "source_id": str(activated_policy.id),
            "artifact_kind": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND,
        },
        "created_at": recorded_at.isoformat(),
        "created_by": created_by,
        "semantic_basis": active_semantic_basis(session),
        "policy_diff": policy_diff,
        "verification": verification_summary,
        "fixture_replay": fixture_replay,
        "activation": activation_summary,
        "activation_change_impact": change_impact_payload or {},
        "source_artifacts": {
            "activation_artifact_id": str(activation_artifact.id),
            "activation_artifact_kind": activation_artifact.artifact_kind,
            "activation_artifact_path": activation_artifact.storage_path,
            "activation_artifact_payload_sha256": value_sha256(
                activation_artifact.payload_json or {}
            ),
            "governance_artifact_id": str(governance_artifact_id),
            "governance_artifact_kind": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND,
            "governance_artifact_path": governance_artifact_path,
        },
        "prov_jsonld": prov_jsonld,
        "integrity_inputs": {
            "policy_diff_sha256": policy_diff.get("policy_diff_sha256"),
            "prov_jsonld_sha256": prov_jsonld_sha,
            "verification_output_sha256": verification_summary["verification_output_sha256"],
            "activation_decision_sha256": value_sha256(activation_summary),
            "activation_change_impact_payload_sha256": (
                (change_impact_payload or {}).get("activation_change_impact_payload_sha256")
            ),
        },
    }
    governance_payload_sha = str(payload_sha256(payload_basis))
    receipt = _receipt(
        payload_basis=payload_basis,
        payload_sha=governance_payload_sha,
        prov_jsonld_sha=prov_jsonld_sha,
        created_by=created_by,
    )
    return {
        **payload_basis,
        "activation_governance_payload_sha256": governance_payload_sha,
        "activation_governance_receipt": receipt,
        "integrity": {
            "payload_hash_recorded": True,
            "receipt_hash_recorded": bool(receipt.get("receipt_sha256")),
            "hash_chain_complete": receipt.get("hash_chain_complete") is True,
            "prov_jsonld_sha256": prov_jsonld_sha,
            "signature_status": receipt.get("signature_status"),
            "signature_present": bool(receipt.get("signature")),
            "complete": (
                bool(governance_payload_sha)
                and bool(receipt.get("receipt_sha256"))
                and receipt.get("hash_chain_complete") is True
                and bool(prov_jsonld_sha)
            ),
        },
    }


def record_claim_support_policy_activation_governance_event(
    session: Session,
    *,
    task: AgentTask,
    activated_policy: ClaimSupportCalibrationPolicy,
    governance_artifact: AgentTaskArtifact,
    governance_payload: dict[str, Any],
) -> SemanticGovernanceEvent:
    receipt_sha = (
        (governance_payload.get("activation_governance_receipt") or {}).get(
            "receipt_sha256"
        )
    )
    event_payload = activation_governance_event_payload(
        task=task,
        governance_artifact=governance_artifact,
        activated_policy=activated_policy,
        governance_payload=governance_payload,
    )
    return record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.CLAIM_SUPPORT_POLICY_ACTIVATED.value,
        governance_scope=f"claim_support_policy:{activated_policy.policy_name}",
        subject_table="claim_support_calibration_policies",
        subject_id=activated_policy.id,
        task_id=task.id,
        agent_task_artifact_id=governance_artifact.id,
        receipt_sha256=receipt_sha,
        event_payload=event_payload,
        deduplication_key=(
            f"claim_support_policy_activated:{activated_policy.id}:"
            f"{receipt_sha or governance_payload.get('activation_governance_payload_sha256')}"
        ),
        created_by=task.approved_by or "claim_support_policy_activation",
    )
