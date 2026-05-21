from __future__ import annotations

import hmac
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.time import utcnow
from app.db.public.audit_and_evidence import AuditBundleExport, AuditBundleValidationReceipt
from app.schemas.search import (
    AuditBundleValidationReceiptResponse,
    AuditBundleValidationReceiptSummaryResponse,
)
from app.services.storage import StorageService


@dataclass(frozen=True)
class ValidationReceiptRuntime:
    verify_bundle: Callable[[AuditBundleExport, dict[str, Any], StorageService], dict[str, Any]]
    validate_bundle_payload_schema: Callable[
        [AuditBundleExport, dict[str, Any]],
        list[dict[str, str]],
    ]
    validate_bundle_source_integrity: Callable[
        [AuditBundleExport, dict[str, Any]],
        list[dict[str, str]],
    ]
    validate_prov_graph: Callable[[dict[str, Any]], tuple[dict[str, Any], list[dict[str, str]]]]
    validate_release_semantic_governance_policy: Callable[[dict[str, Any]], list[dict[str, str]]]
    validation_error: Callable[[str, str, str], dict[str, str]]
    signature: Callable[[str, str], str]
    load_signing_key: Callable[[], tuple[str, str]]
    canonical_json_bytes: Callable[[Any], bytes]
    validation_profile: str
    signature_algorithm: str
    search_harness_release_bundle_kind: str


def receipt_core(receipt: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(receipt, default=str, sort_keys=True))
    normalized.pop("receipt_sha256", None)
    normalized.pop("signature", None)
    normalized.pop("signature_algorithm", None)
    normalized.pop("signing_key_id", None)
    return normalized


def receipt_sha256(receipt: dict[str, Any]) -> str:
    return _payload_sha256(receipt_core(receipt))


def validation_receipt_matches_bundle(
    receipt: AuditBundleValidationReceipt | None,
    bundle: AuditBundleExport,
) -> bool:
    if receipt is None or receipt.validation_status != "passed":
        return False
    payload = receipt.receipt_payload_json or {}
    audit_bundle = payload.get("audit_bundle") or {}
    return all(
        (
            receipt.audit_bundle_export_id == bundle.id,
            audit_bundle.get("bundle_id") == str(bundle.id),
            audit_bundle.get("payload_sha256") == bundle.payload_sha256,
            audit_bundle.get("bundle_sha256") == bundle.bundle_sha256,
            payload.get("validation_status") == "passed",
        )
    )


def _validate_audit_bundle(
    *,
    runtime: ValidationReceiptRuntime,
    row: AuditBundleExport,
    bundle: dict[str, Any],
    storage_service: StorageService,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    bundle_integrity = runtime.verify_bundle(row, bundle, storage_service)
    schema_errors = runtime.validate_bundle_payload_schema(row, bundle)
    source_errors = runtime.validate_bundle_source_integrity(row, bundle)
    prov_jsonld, prov_errors = runtime.validate_prov_graph(bundle)
    payload = bundle.get("payload") or {}
    semantic_governance_errors = (
        runtime.validate_release_semantic_governance_policy(payload)
        if row.bundle_kind == runtime.search_harness_release_bundle_kind
        else []
    )
    errors = [*schema_errors, *source_errors, *prov_errors, *semantic_governance_errors]
    if not bundle_integrity.get("complete"):
        errors.append(
            runtime.validation_error(
                "bundle_integrity_failed",
                "Stored bundle hash, file, or signature integrity failed.",
                "audit_bundle.integrity",
            )
        )
    checks = {
        "payload_schema_valid": not schema_errors,
        "prov_graph_valid": not prov_errors,
        "bundle_integrity_valid": bool(bundle_integrity.get("complete")),
        "source_integrity_valid": not source_errors,
        "semantic_governance_valid": not semantic_governance_errors,
    }
    checks["complete"] = all(checks.values())
    return checks, prov_jsonld, errors


def to_validation_receipt_summary(
    row: AuditBundleValidationReceipt,
) -> AuditBundleValidationReceiptSummaryResponse:
    return AuditBundleValidationReceiptSummaryResponse(
        receipt_id=row.id,
        audit_bundle_export_id=row.audit_bundle_export_id,
        bundle_kind=row.bundle_kind,
        source_table=row.source_table,
        source_id=row.source_id,
        validation_profile=row.validation_profile,
        validation_status=row.validation_status,
        payload_schema_valid=row.payload_schema_valid,
        prov_graph_valid=row.prov_graph_valid,
        bundle_integrity_valid=row.bundle_integrity_valid,
        source_integrity_valid=row.source_integrity_valid,
        semantic_governance_valid=row.semantic_governance_valid,
        receipt_sha256=row.receipt_sha256,
        prov_jsonld_sha256=row.prov_jsonld_sha256,
        signature=row.signature,
        signature_algorithm=row.signature_algorithm,
        signing_key_id=row.signing_key_id,
        created_by=row.created_by,
        created_at=row.created_at,
    )


def _verify_validation_receipt(
    row: AuditBundleValidationReceipt,
    *,
    runtime: ValidationReceiptRuntime,
    storage_service: StorageService,
) -> dict[str, Any]:
    receipt_path = storage_service.resolve_existing_path(row.receipt_storage_path)
    prov_path = storage_service.resolve_existing_path(row.prov_jsonld_storage_path)
    receipt_payload = (
        json.loads(receipt_path.read_text())
        if receipt_path is not None
        else row.receipt_payload_json
    )
    prov_jsonld = (
        json.loads(prov_path.read_text()) if prov_path is not None else row.prov_jsonld_json
    )
    try:
        signing_key, _key_id = runtime.load_signing_key()
        signature_valid = hmac.compare_digest(
            row.signature,
            runtime.signature(row.receipt_sha256, signing_key),
        )
        signature_verification_status = "verified" if signature_valid else "mismatch"
    except HTTPException:
        signature_valid = False
        signature_verification_status = "signing_key_missing"
    checks = {
        "receipt_file_exists": receipt_path is not None,
        "prov_jsonld_file_exists": prov_path is not None,
        "receipt_hash_matches_row": receipt_sha256(receipt_payload) == row.receipt_sha256,
        "receipt_hash_matches_payload": (
            receipt_sha256(receipt_payload) == receipt_payload.get("receipt_sha256")
        ),
        "prov_jsonld_hash_matches_row": _payload_sha256(prov_jsonld) == row.prov_jsonld_sha256,
        "stored_receipt_matches_file": bool(row.receipt_payload_json == receipt_payload),
        "stored_prov_jsonld_matches_file": bool(row.prov_jsonld_json == prov_jsonld),
        "signature_valid": signature_valid,
    }
    checks["complete"] = all(bool(value) for value in checks.values())
    checks["signature_verification_status"] = signature_verification_status
    return checks


def to_validation_receipt_response(
    row: AuditBundleValidationReceipt,
    *,
    runtime: ValidationReceiptRuntime,
    storage_service: StorageService,
) -> AuditBundleValidationReceiptResponse:
    receipt_path = storage_service.resolve_existing_path(row.receipt_storage_path)
    prov_path = storage_service.resolve_existing_path(row.prov_jsonld_storage_path)
    receipt = (
        json.loads(receipt_path.read_text())
        if receipt_path is not None
        else row.receipt_payload_json
    )
    prov_jsonld = (
        json.loads(prov_path.read_text()) if prov_path is not None else row.prov_jsonld_json
    )
    return AuditBundleValidationReceiptResponse(
        **to_validation_receipt_summary(row).model_dump(),
        receipt=receipt,
        prov_jsonld=prov_jsonld,
        validation_errors=row.validation_errors_json or [],
        integrity=_verify_validation_receipt(
            row,
            runtime=runtime,
            storage_service=storage_service,
        ),
    )


def create_audit_bundle_validation_receipt_row(
    session: Session,
    *,
    runtime: ValidationReceiptRuntime,
    audit_bundle: AuditBundleExport,
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
) -> AuditBundleValidationReceipt:
    bundle_path = storage_service.resolve_existing_path(audit_bundle.storage_path)
    bundle = (
        json.loads(bundle_path.read_text())
        if bundle_path is not None
        else audit_bundle.bundle_payload_json or {}
    )
    validation_checks, prov_jsonld, validation_errors = _validate_audit_bundle(
        runtime=runtime,
        row=audit_bundle,
        bundle=bundle,
        storage_service=storage_service,
    )
    receipt_id = uuid.uuid4()
    created_at = utcnow()
    validation_status = "passed" if validation_checks["complete"] else "failed"
    prov_jsonld_sha256 = _payload_sha256(prov_jsonld)
    receipt_basis = {
        "schema_name": "audit_bundle_validation_receipt",
        "schema_version": "1.0",
        "receipt_id": str(receipt_id),
        "audit_bundle": {
            "bundle_id": str(audit_bundle.id),
            "bundle_kind": audit_bundle.bundle_kind,
            "source_table": audit_bundle.source_table,
            "source_id": str(audit_bundle.source_id),
            "payload_sha256": audit_bundle.payload_sha256,
            "bundle_sha256": audit_bundle.bundle_sha256,
        },
        "validation_profile": runtime.validation_profile,
        "validation_status": validation_status,
        "validation_checks": validation_checks,
        "validation_errors": validation_errors,
        "prov_jsonld_sha256": prov_jsonld_sha256,
        "created_at": created_at.isoformat(),
        "created_by": created_by,
        "receipt_policy": (
            "Validation receipt for immutable audit bundles. The receipt links the "
            "signed bundle payload, signed bundle envelope, and standards-facing "
            "PROV JSON-LD export."
        ),
        "hash_chain": [
            {
                "position": 1,
                "name": "audit_bundle_payload",
                "sha256": audit_bundle.payload_sha256,
            },
            {
                "position": 2,
                "name": "audit_bundle_export",
                "sha256": audit_bundle.bundle_sha256,
                "derived_from": ["audit_bundle_payload"],
            },
            {
                "position": 3,
                "name": "prov_jsonld_export",
                "sha256": prov_jsonld_sha256,
                "derived_from": ["audit_bundle_export"],
            },
        ],
    }
    receipt_basis["hash_chain_complete"] = all(
        bool(item.get("sha256")) for item in receipt_basis["hash_chain"]
    )
    computed_receipt_sha256 = _payload_sha256(receipt_basis)
    receipt = {
        **receipt_basis,
        "receipt_sha256": computed_receipt_sha256,
        "signature": runtime.signature(computed_receipt_sha256, signing_key),
        "signature_algorithm": runtime.signature_algorithm,
        "signing_key_id": signing_key_id,
    }
    receipt_path = storage_service.get_audit_bundle_validation_receipt_json_path(
        audit_bundle.bundle_kind,
        audit_bundle.id,
        receipt_id,
    )
    prov_jsonld_path = storage_service.get_audit_bundle_validation_prov_jsonld_path(
        audit_bundle.bundle_kind,
        audit_bundle.id,
        receipt_id,
    )
    receipt_path.write_bytes(runtime.canonical_json_bytes(receipt))
    prov_jsonld_path.write_bytes(runtime.canonical_json_bytes(prov_jsonld))
    row = AuditBundleValidationReceipt(
        id=receipt_id,
        audit_bundle_export_id=audit_bundle.id,
        bundle_kind=audit_bundle.bundle_kind,
        source_table=audit_bundle.source_table,
        source_id=audit_bundle.source_id,
        validation_profile=runtime.validation_profile,
        validation_status=validation_status,
        payload_schema_valid=validation_checks["payload_schema_valid"],
        prov_graph_valid=validation_checks["prov_graph_valid"],
        bundle_integrity_valid=validation_checks["bundle_integrity_valid"],
        source_integrity_valid=validation_checks["source_integrity_valid"],
        semantic_governance_valid=validation_checks["semantic_governance_valid"],
        receipt_storage_path=str(receipt_path),
        prov_jsonld_storage_path=str(prov_jsonld_path),
        receipt_sha256=computed_receipt_sha256,
        prov_jsonld_sha256=prov_jsonld_sha256,
        signature=receipt["signature"],
        signature_algorithm=runtime.signature_algorithm,
        signing_key_id=signing_key_id,
        validation_errors_json=validation_errors,
        receipt_payload_json=receipt,
        prov_jsonld_json=prov_jsonld,
        created_by=created_by,
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    return row


def ensure_audit_bundle_validation_receipts(
    session: Session,
    *,
    runtime: ValidationReceiptRuntime,
    audit_bundles: list[AuditBundleExport],
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
) -> None:
    bundle_ids = [row.id for row in audit_bundles]
    if not bundle_ids:
        return
    existing_receipts = (
        session.execute(
            select(AuditBundleValidationReceipt)
            .where(AuditBundleValidationReceipt.audit_bundle_export_id.in_(bundle_ids))
            .order_by(
                AuditBundleValidationReceipt.audit_bundle_export_id.asc(),
                AuditBundleValidationReceipt.created_at.desc(),
                AuditBundleValidationReceipt.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    receipts_by_bundle_id: dict[UUID, AuditBundleValidationReceipt] = {}
    for receipt in existing_receipts:
        receipts_by_bundle_id.setdefault(receipt.audit_bundle_export_id, receipt)
    for bundle in audit_bundles:
        receipt = receipts_by_bundle_id.get(bundle.id)
        if validation_receipt_matches_bundle(receipt, bundle):
            continue
        create_audit_bundle_validation_receipt_row(
            session,
            runtime=runtime,
            audit_bundle=bundle,
            created_by=created_by,
            storage_service=storage_service,
            signing_key=signing_key,
            signing_key_id=signing_key_id,
        )


def list_audit_bundle_validation_receipts(
    session: Session,
    bundle_id: UUID,
) -> list[AuditBundleValidationReceiptSummaryResponse]:
    rows = (
        session.execute(
            select(AuditBundleValidationReceipt)
            .where(AuditBundleValidationReceipt.audit_bundle_export_id == bundle_id)
            .order_by(
                AuditBundleValidationReceipt.created_at.desc(),
                AuditBundleValidationReceipt.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    return [to_validation_receipt_summary(row) for row in rows]


def get_audit_bundle_validation_receipt(
    session: Session,
    bundle_id: UUID,
    receipt_id: UUID,
    *,
    runtime: ValidationReceiptRuntime,
    storage_service: StorageService,
    not_found_error: Callable[[UUID, UUID | None], HTTPException],
) -> AuditBundleValidationReceiptResponse:
    row = session.scalar(
        select(AuditBundleValidationReceipt).where(
            AuditBundleValidationReceipt.audit_bundle_export_id == bundle_id,
            AuditBundleValidationReceipt.id == receipt_id,
        )
    )
    if row is None:
        raise not_found_error(bundle_id, receipt_id)
    return to_validation_receipt_response(
        row,
        runtime=runtime,
        storage_service=storage_service,
    )


def get_latest_audit_bundle_validation_receipt(
    session: Session,
    bundle_id: UUID,
    *,
    runtime: ValidationReceiptRuntime,
    storage_service: StorageService,
    not_found_error: Callable[[UUID, UUID | None], HTTPException],
) -> AuditBundleValidationReceiptResponse:
    row = session.scalar(
        select(AuditBundleValidationReceipt)
        .where(AuditBundleValidationReceipt.audit_bundle_export_id == bundle_id)
        .order_by(
            AuditBundleValidationReceipt.created_at.desc(),
            AuditBundleValidationReceipt.id.asc(),
        )
    )
    if row is None:
        raise not_found_error(bundle_id, None)
    return to_validation_receipt_response(
        row,
        runtime=runtime,
        storage_service=storage_service,
    )
