from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    ClaimSupportCalibrationPolicy,
    ClaimSupportEvaluation,
    ClaimSupportFixtureSet,
    KnowledgeOperatorRun,
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
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
CLAIM_SUPPORT_POLICY_ACTIVATION_SIGNATURE_ALGORITHM = "hmac-sha256"


def _json_payload(payload: Any | None) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        value = payload
    else:
        value = {"value": payload}
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _value_sha256(value: Any | None) -> str | None:
    return str(payload_sha256(value)) if value is not None else None


def _signature_value(receipt_sha256: str, signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        receipt_sha256.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _signature_payload(receipt_sha256: str) -> dict[str, Any]:
    settings = get_settings()
    signing_key = getattr(settings, "audit_bundle_signing_key", None)
    if not signing_key:
        return {
            "signature_status": "unsigned",
            "signature": None,
            "signature_algorithm": CLAIM_SUPPORT_POLICY_ACTIVATION_SIGNATURE_ALGORITHM,
            "signing_key_id": None,
        }
    signing_key_id = getattr(settings, "audit_bundle_signing_key_id", None) or "local"
    return {
        "signature_status": "signed",
        "signature": _signature_value(receipt_sha256, str(signing_key)),
        "signature_algorithm": CLAIM_SUPPORT_POLICY_ACTIVATION_SIGNATURE_ALGORITHM,
        "signing_key_id": str(signing_key_id),
    }


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
    return {**diff, "policy_diff_sha256": _value_sha256(diff)}


def _fixture_set_snapshot(row: ClaimSupportFixtureSet | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "fixture_set_id": str(row.id),
        "fixture_set_name": row.fixture_set_name,
        "fixture_set_version": row.fixture_set_version,
        "status": row.status,
        "fixture_set_sha256": row.fixture_set_sha256,
        "fixture_count": row.fixture_count,
        "hard_case_kinds": list(row.hard_case_kinds_json or []),
        "verdicts": list(row.verdicts_json or []),
        "metadata": row.metadata_json or {},
        "created_at": row.created_at.isoformat(),
    }


def _fixture_set_diff(
    row: ClaimSupportFixtureSet | None,
    mined_failure_summary: dict[str, Any],
) -> dict[str, Any] | None:
    if row is None:
        return None
    default_fixture_count = mined_failure_summary.get("default_fixture_count")
    combined_fixture_count = mined_failure_summary.get("combined_fixture_count")
    diff = {
        "schema_name": "claim_support_fixture_set_diff",
        "schema_version": "1.0",
        "fixture_set_id": str(row.id),
        "fixture_set_sha256": row.fixture_set_sha256,
        "fixture_count": row.fixture_count,
        "hard_case_kinds": list(row.hard_case_kinds_json or []),
        "verdicts": list(row.verdicts_json or []),
        "replay_composition": {
            "default_fixture_count": default_fixture_count,
            "explicit_fixture_count": mined_failure_summary.get("explicit_fixture_count"),
            "mined_failure_case_count": mined_failure_summary.get(
                "mined_failure_case_count"
            ),
            "combined_fixture_count": combined_fixture_count,
            "manifest_sha256": mined_failure_summary.get("manifest_sha256"),
            "summary_sha256": mined_failure_summary.get("summary_sha256"),
        },
        "fixture_count_delta_from_default": (
            combined_fixture_count - default_fixture_count
            if isinstance(default_fixture_count, int)
            and isinstance(combined_fixture_count, int)
            else None
        ),
    }
    return {**diff, "fixture_set_diff_sha256": _value_sha256(diff)}


def _evaluation_snapshot(row: ClaimSupportEvaluation | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "evaluation_id": str(row.id),
        "evaluation_name": row.evaluation_name,
        "agent_task_id": str(row.agent_task_id) if row.agent_task_id else None,
        "operator_run_id": str(row.operator_run_id) if row.operator_run_id else None,
        "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
        "fixture_set_sha256": row.fixture_set_sha256,
        "policy_id": str(row.policy_id) if row.policy_id else None,
        "policy_sha256": row.policy_sha256,
        "judge_name": row.judge_name,
        "judge_version": row.judge_version,
        "gate_outcome": row.gate_outcome,
        "metrics": row.metrics_json or {},
        "reasons": list(row.reasons_json or []),
        "evaluation_payload_sha256": row.evaluation_payload_sha256,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _uuid_or_none(value: Any | None) -> UUID | None:
    if not value:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


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
    operator_run: KnowledgeOperatorRun | None,
    apply_payload: dict[str, Any],
    policy_diff_sha256: str | None,
    created_by: str | None,
) -> dict[str, Any]:
    activation_activity = f"docling:activity:claim_support_policy_activation:{task.id}"
    verification_activity = (
        "docling:activity:claim_support_policy_verification:"
        f"{apply_payload.get('verification_task_id')}"
    )
    agent_id = f"docling:agent:{created_by or 'docling-system'}"
    activated_policy_entity = f"docling:claim_support_calibration_policy:{activated_policy.id}"
    artifact_entity = f"docling:agent_task_artifact:{activation_artifact.id}"

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
            "@id": artifact_entity,
            "@type": "docling:AgentTaskArtifact",
            "docling:artifactKind": activation_artifact.artifact_kind,
            "docling:storagePath": activation_artifact.storage_path,
        },
        {
            "@id": activation_activity,
            "@type": "docling:ClaimSupportPolicyActivation",
            "prov:endedAtTime": task.completed_at.isoformat() if task.completed_at else None,
            "docling:reason": apply_payload.get("reason"),
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
    graph.extend(
        [
            {
                "@id": f"docling:edge:generated-policy:{task.id}",
                "@type": "prov:Generation",
                "prov:entity": {"@id": activated_policy_entity},
                "prov:activity": {"@id": activation_activity},
            },
            {
                "@id": f"docling:edge:generated-artifact:{task.id}",
                "@type": "prov:Generation",
                "prov:entity": {"@id": artifact_entity},
                "prov:activity": {"@id": activation_activity},
            },
            {
                "@id": f"docling:edge:associated:{task.id}",
                "@type": "prov:Association",
                "prov:activity": {"@id": activation_activity},
                "prov:agent": {"@id": agent_id},
            },
            {
                "@id": f"docling:edge:used-verification:{task.id}",
                "@type": "prov:Usage",
                "prov:activity": {"@id": activation_activity},
                "prov:entity": {
                    "@id": f"docling:agent_task_verification:{verification.get('verification_id')}"
                },
            },
            {
                "@id": f"docling:edge:derived-policy:{task.id}",
                "@type": "prov:Derivation",
                "prov:generatedEntity": {"@id": activated_policy_entity},
                "prov:usedEntity": {
                    "@id": (
                        "docling:agent_task_verification:"
                        f"{verification.get('verification_id')}"
                    )
                },
            },
        ]
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
    hash_chain = [
        {
            "position": 1,
            "name": "previous_active_policy",
            "sha256": (
                ((payload_basis.get("policy_diff") or {}).get("previous_active_policy") or {})
                .get("policy_sha256")
            ),
            "required": False,
        },
        {
            "position": 2,
            "name": "activated_policy",
            "sha256": (
                (payload_basis.get("policy_diff") or {})
                .get("activated_policy", {})
                .get("policy_sha256")
            ),
            "required": True,
        },
        {
            "position": 3,
            "name": "verification_record",
            "sha256": _value_sha256(payload_basis.get("verification")),
            "required": True,
        },
        {
            "position": 4,
            "name": "verification_fixture_set",
            "sha256": (
                ((payload_basis.get("fixture_replay") or {}).get("fixture_set") or {})
                .get("fixture_set_sha256")
            ),
            "required": True,
        },
        {
            "position": 5,
            "name": "verification_fixture_set_diff",
            "sha256": (
                ((payload_basis.get("fixture_replay") or {}).get("fixture_set_diff") or {})
                .get("fixture_set_diff_sha256")
            ),
            "required": True,
        },
        {
            "position": 6,
            "name": "mined_failure_summary",
            "sha256": (
                (payload_basis.get("fixture_replay") or {})
                .get("mined_failure_summary", {})
                .get("summary_sha256")
            ),
            "required": False,
        },
        {
            "position": 7,
            "name": "activation_decision",
            "sha256": _value_sha256(payload_basis.get("activation")),
            "required": True,
        },
        {
            "position": 8,
            "name": "prov_jsonld",
            "sha256": prov_jsonld_sha,
            "required": True,
        },
        {
            "position": 9,
            "name": "claim_support_policy_activation_governance",
            "sha256": payload_sha,
            "required": True,
        },
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
        **_signature_payload(receipt_sha),
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
    operator_run: KnowledgeOperatorRun | None,
) -> dict[str, Any]:
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
    policy_diff = _policy_diff(previous_active_policy, activated_policy)
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
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
    }
    verification_summary = {
        "verification": _json_payload(verification),
        "verification_evaluation": _evaluation_snapshot(verification_evaluation),
        "verification_output_sha256": _value_sha256(verification_output),
    }
    mined_failure_summary = apply_payload.get("verification_mined_failure_summary") or {}
    fixture_replay = {
        "fixture_set": _fixture_set_snapshot(fixture_set),
        "fixture_set_diff": _fixture_set_diff(fixture_set, mined_failure_summary),
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
        operator_run=operator_run,
        apply_payload=apply_payload,
        policy_diff_sha256=policy_diff.get("policy_diff_sha256"),
        created_by=created_by,
    )
    prov_jsonld_sha = _value_sha256(prov_jsonld)
    payload_basis = {
        "schema_name": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_SCHEMA,
        "schema_version": "1.0",
        "governance_profile": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_PROFILE,
        "source": {
            "source_table": "claim_support_calibration_policies",
            "source_id": str(activated_policy.id),
            "artifact_kind": CLAIM_SUPPORT_POLICY_ACTIVATION_GOVERNANCE_ARTIFACT_KIND,
        },
        "created_at": utcnow().isoformat(),
        "created_by": created_by,
        "semantic_basis": active_semantic_basis(session),
        "policy_diff": policy_diff,
        "verification": verification_summary,
        "fixture_replay": fixture_replay,
        "activation": activation_summary,
        "source_artifacts": {
            "activation_artifact_id": str(activation_artifact.id),
            "activation_artifact_kind": activation_artifact.artifact_kind,
            "activation_artifact_path": activation_artifact.storage_path,
            "activation_artifact_payload_sha256": _value_sha256(
                activation_artifact.payload_json or {}
            ),
        },
        "prov_jsonld": prov_jsonld,
        "integrity_inputs": {
            "policy_diff_sha256": policy_diff.get("policy_diff_sha256"),
            "prov_jsonld_sha256": prov_jsonld_sha,
            "verification_output_sha256": verification_summary["verification_output_sha256"],
            "activation_decision_sha256": _value_sha256(activation_summary),
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
    receipt = governance_payload.get("activation_governance_receipt") or {}
    activation = governance_payload.get("activation") or {}
    fixture_replay = governance_payload.get("fixture_replay") or {}
    fixture_set_diff = fixture_replay.get("fixture_set_diff") or {}
    mined_failure_summary = fixture_replay.get("mined_failure_summary") or {}
    receipt_sha = receipt.get("receipt_sha256")
    event_payload = {
        "claim_support_policy_activation": {
            "task_id": str(task.id),
            "artifact_id": str(governance_artifact.id),
            "artifact_kind": governance_artifact.artifact_kind,
            "artifact_path": governance_artifact.storage_path,
            "activated_policy_id": str(activated_policy.id),
            "activated_policy_sha256": activated_policy.policy_sha256,
            "policy_name": activated_policy.policy_name,
            "policy_version": activated_policy.policy_version,
            "previous_active_policy_id": activation.get("previous_active_policy_id"),
            "retired_policy_ids": list(activation.get("retired_policy_ids") or []),
            "verification_task_id": activation.get("verification_task_id"),
            "verification_id": (
                (governance_payload.get("verification") or {})
                .get("verification", {})
                .get("verification_id")
            ),
            "verification_fixture_set_sha256": (
                (fixture_replay.get("fixture_set") or {}).get("fixture_set_sha256")
            ),
            "verification_fixture_set_diff_sha256": fixture_set_diff.get(
                "fixture_set_diff_sha256"
            ),
            "mined_failure_summary_sha256": mined_failure_summary.get("summary_sha256"),
            "activation_governance_payload_sha256": (
                governance_payload.get("activation_governance_payload_sha256")
            ),
            "receipt_sha256": receipt_sha,
            "signature_status": receipt.get("signature_status"),
            "prov_jsonld_sha256": (
                (governance_payload.get("integrity") or {}).get("prov_jsonld_sha256")
            ),
        },
        "semantic_basis": governance_payload.get("semantic_basis") or {},
        "integrity": governance_payload.get("integrity") or {},
    }
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
