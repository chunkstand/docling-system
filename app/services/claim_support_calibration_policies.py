from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.public.claim_support import ClaimSupportCalibrationPolicy
from app.services.claim_support_evaluation_fixtures import (
    CLAIM_SUPPORT_JUDGE_NAME,
    CLAIM_SUPPORT_JUDGE_VERSION,
    CLAIM_SUPPORT_VERDICTS,
    normalize_string_list,
)
from app.services.evidence import payload_sha256

CLAIM_SUPPORT_CALIBRATION_POLICY_SCHEMA_NAME = "claim_support_calibration_policy"
CLAIM_SUPPORT_CALIBRATION_POLICY_SCHEMA_VERSION = "1.0"
DEFAULT_CLAIM_SUPPORT_POLICY_NAME = "claim_support_judge_calibration_policy"
DEFAULT_CLAIM_SUPPORT_POLICY_VERSION = "v1"
DEFAULT_REQUIRED_HARD_CASE_KINDS = (
    "exact_source_support",
    "weak_wording_support",
    "wrong_evidence",
    "lexical_overlap_wrong_evidence",
    "missing_traceable_evidence",
    "graph_only_support",
)
DEFAULT_MIN_HARD_CASE_KIND_COUNT = 4


def _thresholds_payload(
    *,
    min_overall_accuracy: float,
    min_verdict_precision: float,
    min_verdict_recall: float,
    min_support_score: float,
) -> dict[str, Any]:
    return {
        "min_overall_accuracy": min_overall_accuracy,
        "min_verdict_precision": min_verdict_precision,
        "min_verdict_recall": min_verdict_recall,
        "min_support_score": min_support_score,
    }


def _policy_payload_sha256(payload: dict[str, Any]) -> str:
    return str(
        payload_sha256({key: value for key, value in payload.items() if key != "policy_sha256"})
    )


def build_claim_support_calibration_policy_payload(
    *,
    policy_name: str = DEFAULT_CLAIM_SUPPORT_POLICY_NAME,
    policy_version: str = DEFAULT_CLAIM_SUPPORT_POLICY_VERSION,
    status: str = "active",
    thresholds: dict[str, Any] | None = None,
    min_hard_case_kind_count: int = DEFAULT_MIN_HARD_CASE_KIND_COUNT,
    required_hard_case_kinds: list[str] | tuple[str, ...] | None = None,
    required_verdicts: list[str] | tuple[str, ...] | None = None,
    owner: str = "docling-system",
    source: str = "built_in_default",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy_thresholds = dict(
        thresholds
        or _thresholds_payload(
            min_overall_accuracy=1.0,
            min_verdict_precision=1.0,
            min_verdict_recall=1.0,
            min_support_score=0.34,
        )
    )
    payload = {
        "schema_name": CLAIM_SUPPORT_CALIBRATION_POLICY_SCHEMA_NAME,
        "schema_version": CLAIM_SUPPORT_CALIBRATION_POLICY_SCHEMA_VERSION,
        "policy_name": policy_name,
        "policy_version": policy_version,
        "status": status,
        "owner": owner,
        "source": source,
        "judge_name": CLAIM_SUPPORT_JUDGE_NAME,
        "judge_version": CLAIM_SUPPORT_JUDGE_VERSION,
        "thresholds": policy_thresholds,
        "min_hard_case_kind_count": int(min_hard_case_kind_count),
        "required_hard_case_kinds": normalize_string_list(
            required_hard_case_kinds or DEFAULT_REQUIRED_HARD_CASE_KINDS
        ),
        "required_verdicts": normalize_string_list(required_verdicts or CLAIM_SUPPORT_VERDICTS),
        "metadata": metadata or {},
    }
    return {**payload, "policy_sha256": _policy_payload_sha256(payload)}


def _policy_row_from_payload(
    payload: dict[str, Any],
    *,
    status: str,
) -> ClaimSupportCalibrationPolicy:
    return ClaimSupportCalibrationPolicy(
        id=uuid.uuid4(),
        policy_name=str(payload["policy_name"]),
        policy_version=str(payload["policy_version"]),
        status=status,
        policy_sha256=str(payload["policy_sha256"]),
        owner=payload.get("owner"),
        source=payload.get("source"),
        min_hard_case_kind_count=int(payload.get("min_hard_case_kind_count") or 0),
        required_hard_case_kinds_json=list(payload.get("required_hard_case_kinds") or []),
        required_verdicts_json=list(payload.get("required_verdicts") or []),
        thresholds_json=dict(payload.get("thresholds") or {}),
        policy_payload_json=dict(payload),
        metadata_json=dict(payload.get("metadata") or {}),
        created_at=utcnow(),
    )


def _validated_policy_payload(
    policy_payload: dict[str, Any] | None = None,
    *,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(
        policy_payload
        or build_claim_support_calibration_policy_payload(thresholds=thresholds)
    )
    policy_sha256 = _policy_payload_sha256(payload)
    provided_policy_sha256 = payload.get("policy_sha256")
    if provided_policy_sha256 and str(provided_policy_sha256) != policy_sha256:
        raise ValueError("Claim support calibration policy payload SHA does not match payload.")
    return {**payload, "policy_sha256": policy_sha256}


thresholds_payload = _thresholds_payload
validated_policy_payload = _validated_policy_payload


def get_active_claim_support_calibration_policy(
    session: Session,
    *,
    policy_name: str = DEFAULT_CLAIM_SUPPORT_POLICY_NAME,
) -> ClaimSupportCalibrationPolicy | None:
    return session.scalar(
        select(ClaimSupportCalibrationPolicy)
        .where(
            ClaimSupportCalibrationPolicy.policy_name == policy_name,
            ClaimSupportCalibrationPolicy.status == "active",
        )
        .order_by(ClaimSupportCalibrationPolicy.created_at.desc())
    )


def ensure_claim_support_calibration_policy(
    session: Session,
    *,
    policy_payload: dict[str, Any] | None = None,
    thresholds: dict[str, Any] | None = None,
) -> ClaimSupportCalibrationPolicy:
    payload = _validated_policy_payload(policy_payload, thresholds=thresholds)
    policy_sha256 = str(payload["policy_sha256"])
    existing = session.scalar(
        select(ClaimSupportCalibrationPolicy).where(
            ClaimSupportCalibrationPolicy.policy_name == str(payload["policy_name"]),
            ClaimSupportCalibrationPolicy.policy_version == str(payload["policy_version"]),
            ClaimSupportCalibrationPolicy.policy_sha256 == policy_sha256,
        )
    )
    status = str(payload.get("status") or "active")
    if existing is not None:
        if existing.status != status:
            raise ValueError(
                "A matching claim support calibration policy already exists with "
                f"status {existing.status}; active policy resolution cannot reuse it."
            )
        return existing
    if status == "active":
        active = get_active_claim_support_calibration_policy(
            session,
            policy_name=str(payload["policy_name"]),
        )
        if active is not None and active.policy_sha256 != policy_sha256:
            raise ValueError(
                "An active claim support calibration policy already exists; "
                "draft, verify, and apply a policy change instead."
            )
    row = _policy_row_from_payload(payload, status=status)
    session.add(row)
    session.flush()
    return row


def draft_claim_support_calibration_policy(
    session: Session,
    *,
    policy_name: str,
    policy_version: str,
    thresholds: dict[str, Any],
    min_hard_case_kind_count: int,
    required_hard_case_kinds: list[str],
    required_verdicts: list[str],
    owner: str,
    source: str,
    rationale: str,
) -> ClaimSupportCalibrationPolicy:
    payload = _validated_policy_payload(
        build_claim_support_calibration_policy_payload(
            policy_name=policy_name,
            policy_version=policy_version,
            status="active",
            thresholds=thresholds,
            min_hard_case_kind_count=min_hard_case_kind_count,
            required_hard_case_kinds=required_hard_case_kinds,
            required_verdicts=required_verdicts,
            owner=owner,
            source=source,
            metadata={"rationale": rationale},
        )
    )
    existing = session.scalar(
        select(ClaimSupportCalibrationPolicy).where(
            ClaimSupportCalibrationPolicy.policy_name == policy_name,
            ClaimSupportCalibrationPolicy.policy_version == policy_version,
            ClaimSupportCalibrationPolicy.policy_sha256 == payload["policy_sha256"],
        )
    )
    if existing is not None:
        if existing.status == "active":
            raise ValueError("The proposed claim support calibration policy is already active.")
        if existing.status != "draft":
            raise ValueError(
                "Retired claim support calibration policies cannot be redrafted; "
                "choose a new policy version."
            )
        return existing
    row = _policy_row_from_payload(payload, status="draft")
    session.add(row)
    session.flush()
    return row


def resolve_claim_support_calibration_policy(
    session: Session,
    *,
    policy_name: str = DEFAULT_CLAIM_SUPPORT_POLICY_NAME,
    policy_version: str | None = None,
    thresholds: dict[str, Any] | None = None,
) -> ClaimSupportCalibrationPolicy:
    if policy_version is None:
        active = get_active_claim_support_calibration_policy(session, policy_name=policy_name)
        if active is not None:
            return active
        if policy_name == DEFAULT_CLAIM_SUPPORT_POLICY_NAME:
            return ensure_claim_support_calibration_policy(session, thresholds=thresholds)
        raise ValueError(f"No active claim support calibration policy found for {policy_name}.")
    row = session.scalar(
        select(ClaimSupportCalibrationPolicy)
        .where(
            ClaimSupportCalibrationPolicy.policy_name == policy_name,
            ClaimSupportCalibrationPolicy.policy_version == policy_version,
            ClaimSupportCalibrationPolicy.status == "active",
        )
        .order_by(ClaimSupportCalibrationPolicy.created_at.desc())
    )
    if row is None:
        if (
            policy_name == DEFAULT_CLAIM_SUPPORT_POLICY_NAME
            and policy_version == DEFAULT_CLAIM_SUPPORT_POLICY_VERSION
        ):
            return ensure_claim_support_calibration_policy(session, thresholds=thresholds)
        raise ValueError(
            f"No active claim support calibration policy found for {policy_name} "
            f"version {policy_version}."
        )
    return row


def activate_claim_support_calibration_policy(
    session: Session,
    *,
    policy_id: UUID,
    activation_metadata: dict[str, Any] | None = None,
) -> tuple[ClaimSupportCalibrationPolicy, list[ClaimSupportCalibrationPolicy]]:
    row = session.get(ClaimSupportCalibrationPolicy, policy_id)
    if row is None:
        raise ValueError(f"Claim support calibration policy not found: {policy_id}")
    if row.status != "draft":
        raise ValueError("Only draft claim support calibration policies can be activated.")

    active_rows = list(
        session.scalars(
            select(ClaimSupportCalibrationPolicy)
            .where(
                ClaimSupportCalibrationPolicy.policy_name == row.policy_name,
                ClaimSupportCalibrationPolicy.status == "active",
            )
            .with_for_update()
        )
    )
    for active_row in active_rows:
        active_row.status = "retired"
        active_row.metadata_json = {
            **dict(active_row.metadata_json or {}),
            "retired_by_policy_id": str(row.id),
            "retired_at": utcnow().isoformat(),
        }
    if active_rows:
        session.flush()
    row.status = "active"
    row.metadata_json = {
        **dict(row.metadata_json or {}),
        **dict(activation_metadata or {}),
        "activated_at": utcnow().isoformat(),
    }
    session.flush()
    return row, active_rows
