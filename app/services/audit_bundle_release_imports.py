from __future__ import annotations

import json
from functools import cache
from importlib import import_module
from typing import Any


@cache
def release_payload_prov_module():
    return import_module("app.services.audit_bundle_release_payload_prov")


@cache
def release_serialization_module():
    return import_module("app.services.audit_bundle_release_payload_serialization")


@cache
def release_validation_module():
    return import_module("app.services.audit_bundle_release_payload_validation")


@cache
def release_payloads_module():
    return import_module("app.services.audit_bundle_release_payloads")


@cache
def training_runs_module():
    return import_module("app.services.audit_bundle_training_runs")


@cache
def validation_receipts_module():
    return import_module("app.services.audit_bundle_validation_receipts")


@cache
def release_shared_module():
    return import_module("app.services.search_release_shared")


SEARCH_RELEASE_AUDIT_BUNDLE_KIND = (
    release_serialization_module().SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND
)
SEARCH_RELEASE_SOURCE_TABLE = release_serialization_module().SEARCH_HARNESS_RELEASE_SOURCE_TABLE
TRAINING_RUN_AUDIT_BUNDLE_KIND = (
    training_runs_module().RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND
)
TRAINING_RUN_SOURCE_TABLE = training_runs_module().RETRIEVAL_TRAINING_RUN_SOURCE_TABLE
SIGNATURE_ALGORITHM = "hmac-sha256"
AUDIT_BUNDLE_VALIDATION_PROFILE = "audit_bundle_validation_v1"


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def training_run_runtime(
    *,
    canonical_json_bytes,
    payload_sha256,
    sign_bundle,
    training_run_not_completed,
):
    return training_runs_module().TrainingRunAuditBundleRuntime(
        canonical_json_bytes=canonical_json_bytes,
        payload_sha256=payload_sha256,
        sign_bundle=sign_bundle,
        training_run_not_completed=training_run_not_completed,
    )


def validation_receipt_runtime(
    *,
    verify_bundle,
    signature,
    load_signing_key,
    canonical_json_bytes,
):
    return validation_receipts_module().ValidationReceiptRuntime(
        verify_bundle=verify_bundle,
        validate_bundle_payload_schema=(
            lambda row, bundle: release_validation_module().validate_bundle_payload_schema(
                row=row,
                bundle=bundle,
            )
        ),
        validate_bundle_source_integrity=(
            lambda row, bundle: release_validation_module().validate_bundle_source_integrity(
                row=row,
                bundle=bundle,
            )
        ),
        validate_prov_graph=(
            lambda bundle: release_payload_prov_module().validate_prov_graph(
                bundle,
                validation_error=release_validation_module().validation_error,
            )
        ),
        validate_release_semantic_governance_policy=(
            release_validation_module().validate_release_semantic_governance_policy
        ),
        validation_error=release_validation_module().validation_error,
        signature=signature,
        load_signing_key=load_signing_key,
        canonical_json_bytes=canonical_json_bytes,
        validation_profile=AUDIT_BUNDLE_VALIDATION_PROFILE,
        signature_algorithm=SIGNATURE_ALGORITHM,
        search_harness_release_bundle_kind=SEARCH_RELEASE_AUDIT_BUNDLE_KIND,
    )


def ensure_audit_bundle_validation_receipts(
    session,
    *,
    audit_bundles,
    created_by,
    storage_service,
    signing_key,
    signing_key_id,
    verify_bundle,
    signature,
    load_signing_key,
    canonical_json_bytes,
):
    return validation_receipts_module().ensure_audit_bundle_validation_receipts(
        session,
        runtime=validation_receipt_runtime(
            verify_bundle=verify_bundle,
            signature=signature,
            load_signing_key=load_signing_key,
            canonical_json_bytes=canonical_json_bytes,
        ),
        audit_bundles=audit_bundles,
        created_by=created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )


def create_retrieval_training_run_audit_bundle_row(
    session,
    *,
    training_run,
    created_by,
    storage_service,
    signing_key,
    signing_key_id,
    canonical_json_bytes,
    payload_sha256,
    sign_bundle,
    training_run_not_completed,
):
    return training_runs_module().create_retrieval_training_run_audit_bundle_row(
        session,
        training_run=training_run,
        created_by=created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
        runtime=training_run_runtime(
            canonical_json_bytes=canonical_json_bytes,
            payload_sha256=payload_sha256,
            sign_bundle=sign_bundle,
            training_run_not_completed=training_run_not_completed,
        ),
    )


def ensure_retrieval_training_run_audit_bundles_for_release(
    session,
    *,
    release,
    created_by,
    storage_service,
    signing_key,
    signing_key_id,
    canonical_json_bytes,
    payload_sha256,
    sign_bundle,
    training_run_not_completed,
):
    return training_runs_module().ensure_retrieval_training_run_audit_bundles_for_release(
        session,
        release=release,
        created_by=created_by,
        storage_service=storage_service,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
        runtime=training_run_runtime(
            canonical_json_bytes=canonical_json_bytes,
            payload_sha256=payload_sha256,
            sign_bundle=sign_bundle,
            training_run_not_completed=training_run_not_completed,
        ),
    )
