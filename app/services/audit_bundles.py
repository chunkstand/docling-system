from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_bundle_release_payload_prov as _release_payload_prov
import app.services.audit_bundle_release_payload_serialization as _release_ser
import app.services.audit_bundle_release_payload_validation as _release_val
import app.services.audit_bundle_release_payloads as _release_payloads
import app.services.audit_bundle_training_runs as _training_runs
import app.services.audit_bundle_validation_receipts as _validation_receipts
from app.api.errors import api_error
from app.core.config import get_settings
from app.core.hashes import file_sha256 as _file_sha256
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.time import utcnow
from app.db.models import AuditBundleExport, RetrievalTrainingRun, SearchHarnessRelease
from app.schemas.search import (
    AuditBundleExportResponse,
    AuditBundleExportSummaryResponse,
    AuditBundleValidationReceiptRequest,
    AuditBundleValidationReceiptResponse,
    AuditBundleValidationReceiptSummaryResponse,
    RetrievalTrainingRunAuditBundleRequest,
    SearchHarnessReleaseAuditBundleRequest,
)
from app.services import search_release_shared as _release_shared
from app.services.storage import StorageService

SEARCH_RELEASE_AUDIT_BUNDLE_KIND = _release_ser.SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND
SEARCH_RELEASE_SOURCE_TABLE = _release_ser.SEARCH_HARNESS_RELEASE_SOURCE_TABLE
TRAINING_RUN_AUDIT_BUNDLE_KIND = _training_runs.RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND
TRAINING_RUN_SOURCE_TABLE = _training_runs.RETRIEVAL_TRAINING_RUN_SOURCE_TABLE
SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND = SEARCH_RELEASE_AUDIT_BUNDLE_KIND
SEARCH_HARNESS_RELEASE_SOURCE_TABLE = SEARCH_RELEASE_SOURCE_TABLE
SIGNATURE_ALGORITHM = "hmac-sha256"
AUDIT_BUNDLE_VALIDATION_PROFILE = "audit_bundle_validation_v1"
TRAINING_RUN_AUDIT_SCHEMA_VERSION = _training_runs.RETRIEVAL_TRAINING_RUN_AUDIT_SCHEMA_VERSION

_release_payload = _release_ser.release_payload
_evaluation_payload = _release_ser.evaluation_payload
_source_payload = _release_ser.source_payload
_replay_payload = _release_ser.replay_payload
_retrieval_learning_candidate_payload = _release_ser.retrieval_learning_candidate_payload
_retrieval_reranker_artifact_payload = _release_ser.retrieval_reranker_artifact_payload
_audit_bundle_reference_payload = _release_ser.audit_bundle_reference_payload
_validation_receipt_reference_payload = _release_ser.validation_receipt_reference_payload
_semantic_governance_event_payload = _release_ser.semantic_governance_event_payload
_validation_error = _release_val.validation_error
_append_missing_key_errors = _release_val.append_missing_key_errors
_append_required_list_error = _release_val.append_required_list_error
_validate_bundle_payload_schema = _release_val.validate_bundle_payload_schema
_validate_bundle_source_integrity = _release_val.validate_bundle_source_integrity
_semantic_governance_chain_checks = _release_val.semantic_governance_chain_checks
_validate_release_policy = _release_val.validate_release_semantic_governance_policy
_validate_release_semantic_governance_policy = _validate_release_policy
_prov_jsonld_node = _release_payload_prov.prov_jsonld_node
_prov_edge_id = _release_payload_prov.prov_edge_id
_prov_jsonld_from_graph = _release_payload_prov.prov_jsonld_from_graph
_prov_graph = _release_payload_prov.prov_graph
_build_search_harness_release_payload = _release_payloads.build_search_harness_release_payload


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _audit_bundle_not_found(bundle_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "audit_bundle_export_not_found",
        "Audit bundle export not found.",
        bundle_id=str(bundle_id),
    )


def _receipt_not_found(bundle_id: UUID, receipt_id: UUID | None = None) -> HTTPException:
    context = {"bundle_id": str(bundle_id)}
    if receipt_id is not None:
        context["receipt_id"] = str(receipt_id)
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "audit_bundle_validation_receipt_not_found",
        "Audit bundle validation receipt not found.",
        **context,
    )


def _training_run_not_found(training_run_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "retrieval_training_run_not_found",
        "Retrieval training run not found.",
        retrieval_training_run_id=str(training_run_id),
    )


def _training_run_not_completed(training_run: RetrievalTrainingRun) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        "retrieval_training_run_not_completed",
        "Retrieval training run must be completed before exporting an audit bundle.",
        retrieval_training_run_id=str(training_run.id),
        status=training_run.status,
    )


def _signing_key() -> tuple[str, str]:
    settings = get_settings()
    signing_key = getattr(settings, "audit_bundle_signing_key", None)
    if not signing_key:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "audit_bundle_signing_key_missing",
            "DOCLING_SYSTEM_AUDIT_BUNDLE_SIGNING_KEY is required to export signed audit bundles.",
        )
    key_id = getattr(settings, "audit_bundle_signing_key_id", None) or "local"
    return str(signing_key), str(key_id)


def _signature(payload_sha256: str, signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        payload_sha256.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _validate_prov_graph(bundle: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    return _release_payload_prov.validate_prov_graph(bundle, validation_error=_validation_error)


def _bundle_without_bundle_sha256(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(bundle, default=str, sort_keys=True))
    export = normalized.get("bundle_export") or {}
    export.pop("bundle_sha256", None)
    normalized["bundle_export"] = export
    return normalized


def _bundle_sha256(bundle: dict[str, Any]) -> str:
    return _payload_sha256(_bundle_without_bundle_sha256(bundle))


def _signed_bundle(
    *,
    bundle_id: UUID,
    bundle_kind: str,
    source_table: str,
    source_id: UUID,
    payload: dict[str, Any],
    signing_key: str,
    signing_key_id: str,
) -> dict[str, Any]:
    payload_sha256 = _payload_sha256(payload)
    signature = _signature(payload_sha256, signing_key)
    bundle = {
        "schema_name": "audit_bundle_export",
        "schema_version": "1.0",
        "bundle_export": {
            "bundle_id": str(bundle_id),
            "bundle_kind": bundle_kind,
            "source_table": source_table,
            "source_id": str(source_id),
            "payload_sha256": payload_sha256,
            "signature": signature,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signing_key_id": signing_key_id,
        },
        "payload": payload,
    }
    bundle["bundle_export"]["bundle_sha256"] = _bundle_sha256(bundle)
    return bundle


def _to_summary(row: AuditBundleExport) -> AuditBundleExportSummaryResponse:
    return AuditBundleExportSummaryResponse(
        bundle_id=row.id,
        bundle_kind=row.bundle_kind,
        source_table=row.source_table,
        source_id=row.source_id,
        payload_sha256=row.payload_sha256,
        bundle_sha256=row.bundle_sha256,
        signature=row.signature,
        signature_algorithm=row.signature_algorithm,
        signing_key_id=row.signing_key_id,
        created_by=row.created_by,
        export_status=row.export_status,
        created_at=row.created_at,
    )


def _verify_bundle(
    row: AuditBundleExport,
    bundle: dict[str, Any],
    storage_service: StorageService,
) -> dict[str, Any]:
    payload = bundle.get("payload") or {}
    export = bundle.get("bundle_export") or {}
    payload_sha256 = _payload_sha256(payload)
    bundle_sha256 = _bundle_sha256(bundle)
    path = storage_service.resolve_existing_path(row.storage_path)
    file_sha256 = _file_sha256(path)
    try:
        signing_key, _key_id = _signing_key()
        signature_valid = hmac.compare_digest(
            row.signature,
            _signature(row.payload_sha256, signing_key),
        )
        signature_verification_status = "verified" if signature_valid else "mismatch"
    except HTTPException:
        signature_valid = False
        signature_verification_status = "signing_key_missing"
    checks = {
        "payload_hash_matches_row": payload_sha256 == row.payload_sha256,
        "payload_hash_matches_bundle": payload_sha256 == export.get("payload_sha256"),
        "bundle_hash_matches_row": bundle_sha256 == row.bundle_sha256,
        "bundle_hash_matches_bundle": bundle_sha256 == export.get("bundle_sha256"),
        "signature_matches_row": row.signature == export.get("signature"),
        "signature_valid": signature_valid,
        "file_exists": path is not None,
        "file_sha256": file_sha256,
        "stored_payload_matches_file": bool(row.bundle_payload_json == bundle),
    }
    checks["complete"] = all(
        bool(checks[key])
        for key in (
            "payload_hash_matches_row",
            "payload_hash_matches_bundle",
            "bundle_hash_matches_row",
            "bundle_hash_matches_bundle",
            "signature_matches_row",
            "signature_valid",
            "file_exists",
            "stored_payload_matches_file",
        )
    )
    checks["signature_verification_status"] = signature_verification_status
    return checks


def _response(row: AuditBundleExport, *, storage_service: StorageService):
    path = storage_service.resolve_existing_path(row.storage_path)
    bundle = json.loads(path.read_text()) if path is not None else row.bundle_payload_json or {}
    integrity = _verify_bundle(row, bundle, storage_service)
    return AuditBundleExportResponse(
        **_to_summary(row).model_dump(),
        bundle=bundle,
        integrity=integrity,
    )


def _training_run_runtime() -> _training_runs.TrainingRunAuditBundleRuntime:
    return _training_runs.TrainingRunAuditBundleRuntime(
        canonical_json_bytes=_canonical_json_bytes,
        payload_sha256=_payload_sha256,
        sign_bundle=_signed_bundle,
        training_run_not_completed=_training_run_not_completed,
    )


def _validation_receipt_runtime() -> _validation_receipts.ValidationReceiptRuntime:
    return _validation_receipts.ValidationReceiptRuntime(
        verify_bundle=_verify_bundle,
        validate_bundle_payload_schema=lambda row, bundle: _validate_bundle_payload_schema(
            row=row,
            bundle=bundle,
        ),
        validate_bundle_source_integrity=lambda row, bundle: _validate_bundle_source_integrity(
            row=row,
            bundle=bundle,
        ),
        validate_prov_graph=_validate_prov_graph,
        validate_release_semantic_governance_policy=_validate_release_policy,
        validation_error=_validation_error,
        signature=_signature,
        load_signing_key=_signing_key,
        canonical_json_bytes=_canonical_json_bytes,
        validation_profile=AUDIT_BUNDLE_VALIDATION_PROFILE,
        signature_algorithm=SIGNATURE_ALGORITHM,
        search_harness_release_bundle_kind=SEARCH_RELEASE_AUDIT_BUNDLE_KIND,
    )


def _ensure_audit_bundle_validation_receipts(
    session: Session,
    *,
    audit_bundles: list[AuditBundleExport],
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
) -> None:
    _validation_receipts.ensure_audit_bundle_validation_receipts(
        session,
        runtime=_validation_receipt_runtime(),
        audit_bundles=audit_bundles,
        created_by=created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )


def _create_retrieval_training_run_audit_bundle_row(
    session: Session,
    *,
    training_run: RetrievalTrainingRun,
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
) -> AuditBundleExport:
    return _training_runs.create_retrieval_training_run_audit_bundle_row(
        session,
        training_run=training_run,
        created_by=created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
        runtime=_training_run_runtime(),
    )


def _ensure_retrieval_training_run_audit_bundles_for_release(
    session: Session,
    *,
    release: SearchHarnessRelease,
    created_by: str | None,
    storage_service: StorageService,
    signing_key: str,
    signing_key_id: str,
) -> list[AuditBundleExport]:
    return _training_runs.ensure_retrieval_training_run_audit_bundles_for_release(
        session,
        release=release,
        created_by=created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
        runtime=_training_run_runtime(),
    )


def create_search_harness_release_audit_bundle(
    session: Session,
    release_id: UUID,
    payload: SearchHarnessReleaseAuditBundleRequest,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    release = session.get(SearchHarnessRelease, release_id)
    if release is None:
        raise _release_shared.search_harness_release_not_found_error(release_id)
    signing_key, signing_key_id = _signing_key()
    linked_training_bundles = _ensure_retrieval_training_run_audit_bundles_for_release(
        session,
        release=release,
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    _ensure_audit_bundle_validation_receipts(
        session,
        audit_bundles=linked_training_bundles,
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    bundle_id = uuid.uuid4()
    created_at = utcnow()
    audit_payload = _build_search_harness_release_payload(
        session,
        release=release,
        bundle_id=bundle_id,
        created_by=payload.created_by,
        created_at=created_at,
    )
    bundle = _signed_bundle(
        bundle_id=bundle_id,
        bundle_kind=SEARCH_RELEASE_AUDIT_BUNDLE_KIND,
        source_table=SEARCH_RELEASE_SOURCE_TABLE,
        source_id=release.id,
        payload=audit_payload,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    bundle_path = storage_service.get_audit_bundle_json_path(
        SEARCH_RELEASE_AUDIT_BUNDLE_KIND,
        bundle_id,
    )
    bundle_path.write_bytes(_canonical_json_bytes(bundle))
    integrity = {
        "payload_hash_matches_bundle": True,
        "bundle_hash_matches_bundle": True,
        "signature_valid": True,
        "file_exists": True,
        "stored_payload_matches_file": True,
        "complete": True,
    }
    row = AuditBundleExport(
        id=bundle_id,
        bundle_kind=SEARCH_RELEASE_AUDIT_BUNDLE_KIND,
        source_table=SEARCH_RELEASE_SOURCE_TABLE,
        source_id=release.id,
        search_harness_release_id=release.id,
        storage_path=str(bundle_path),
        payload_sha256=bundle["bundle_export"]["payload_sha256"],
        bundle_sha256=bundle["bundle_export"]["bundle_sha256"],
        signature=bundle["bundle_export"]["signature"],
        signature_algorithm=bundle["bundle_export"]["signature_algorithm"],
        signing_key_id=bundle["bundle_export"]["signing_key_id"],
        bundle_payload_json=bundle,
        integrity_json=integrity,
        created_by=payload.created_by,
        export_status="completed",
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    _ensure_audit_bundle_validation_receipts(
        session,
        audit_bundles=[row],
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    return _response(row, storage_service=storage_service)


def create_retrieval_training_run_audit_bundle(
    session: Session,
    training_run_id: UUID,
    payload: RetrievalTrainingRunAuditBundleRequest,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    training_run = session.get(RetrievalTrainingRun, training_run_id)
    if training_run is None:
        raise _training_run_not_found(training_run_id)
    signing_key, signing_key_id = _signing_key()
    row = _create_retrieval_training_run_audit_bundle_row(
        session,
        training_run=training_run,
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    return _response(row, storage_service=storage_service)


def get_audit_bundle_export(
    session: Session,
    bundle_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    row = session.get(AuditBundleExport, bundle_id)
    if row is None:
        raise _audit_bundle_not_found(bundle_id)
    return _response(row, storage_service=storage_service)


def _get_audit_bundle_row(session: Session, bundle_id: UUID) -> AuditBundleExport:
    row = session.get(AuditBundleExport, bundle_id)
    if row is None:
        raise _audit_bundle_not_found(bundle_id)
    return row


def create_audit_bundle_validation_receipt(
    session: Session,
    bundle_id: UUID,
    payload: AuditBundleValidationReceiptRequest,
    *,
    storage_service: StorageService,
) -> AuditBundleValidationReceiptResponse:
    audit_bundle = _get_audit_bundle_row(session, bundle_id)
    signing_key, signing_key_id = _signing_key()
    row = _validation_receipts.create_audit_bundle_validation_receipt_row(
        session,
        runtime=_validation_receipt_runtime(),
        audit_bundle=audit_bundle,
        created_by=payload.created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    return _validation_receipts.to_validation_receipt_response(
        row,
        runtime=_validation_receipt_runtime(),
        storage_service=storage_service,
    )


def list_audit_bundle_validation_receipts(
    session: Session,
    bundle_id: UUID,
) -> list[AuditBundleValidationReceiptSummaryResponse]:
    _get_audit_bundle_row(session, bundle_id)
    return _validation_receipts.list_audit_bundle_validation_receipts(session, bundle_id)


def get_audit_bundle_validation_receipt(
    session: Session,
    bundle_id: UUID,
    receipt_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleValidationReceiptResponse:
    _get_audit_bundle_row(session, bundle_id)
    return _validation_receipts.get_audit_bundle_validation_receipt(
        session,
        bundle_id,
        receipt_id,
        runtime=_validation_receipt_runtime(),
        storage_service=storage_service,
        not_found_error=_receipt_not_found,
    )


def get_latest_audit_bundle_validation_receipt(
    session: Session,
    bundle_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleValidationReceiptResponse:
    _get_audit_bundle_row(session, bundle_id)
    return _validation_receipts.get_latest_audit_bundle_validation_receipt(
        session,
        bundle_id,
        runtime=_validation_receipt_runtime(),
        storage_service=storage_service,
        not_found_error=_receipt_not_found,
    )


def get_latest_retrieval_training_run_audit_bundle(
    session: Session,
    training_run_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    row = session.scalar(
        select(AuditBundleExport)
        .where(
            AuditBundleExport.retrieval_training_run_id == training_run_id,
            AuditBundleExport.bundle_kind == TRAINING_RUN_AUDIT_BUNDLE_KIND,
        )
        .order_by(AuditBundleExport.created_at.desc())
    )
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "retrieval_training_run_audit_bundle_not_found",
            "Retrieval training run audit bundle not found.",
            retrieval_training_run_id=str(training_run_id),
        )
    return _response(row, storage_service=storage_service)


def get_latest_search_harness_release_audit_bundle(
    session: Session,
    release_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    row = session.scalar(
        select(AuditBundleExport)
        .where(
            AuditBundleExport.search_harness_release_id == release_id,
            AuditBundleExport.bundle_kind == SEARCH_RELEASE_AUDIT_BUNDLE_KIND,
        )
        .order_by(AuditBundleExport.created_at.desc())
    )
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_release_audit_bundle_not_found",
            "Search harness release audit bundle not found.",
            release_id=str(release_id),
        )
    return _response(row, storage_service=storage_service)
