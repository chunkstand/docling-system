from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.audit_bundle_validation_receipts import (
    receipt_core,
    receipt_sha256,
    validation_receipt_matches_bundle,
)


def test_receipt_core_and_hash_ignore_signature_metadata() -> None:
    receipt = {
        "schema_name": "audit_bundle_validation_receipt",
        "audit_bundle": {"bundle_id": str(uuid4())},
        "validation_status": "passed",
        "receipt_sha256": "stored-sha",
        "signature": "signed-a",
        "signature_algorithm": "hmac-sha256",
        "signing_key_id": "local",
    }

    assert receipt_core(receipt) == {
        "schema_name": "audit_bundle_validation_receipt",
        "audit_bundle": receipt["audit_bundle"],
        "validation_status": "passed",
    }
    assert receipt_sha256(receipt) == receipt_sha256(
        {
            **receipt,
            "receipt_sha256": "different-sha",
            "signature": "signed-b",
            "signing_key_id": "rotated-key",
        }
    )


def test_validation_receipt_matches_bundle_requires_passed_status_and_hash_match() -> None:
    bundle_id = uuid4()
    bundle = SimpleNamespace(
        id=bundle_id,
        payload_sha256="payload-sha",
        bundle_sha256="bundle-sha",
    )
    receipt = SimpleNamespace(
        audit_bundle_export_id=bundle_id,
        validation_status="passed",
        receipt_payload_json={
            "audit_bundle": {
                "bundle_id": str(bundle_id),
                "payload_sha256": "payload-sha",
                "bundle_sha256": "bundle-sha",
            },
            "validation_status": "passed",
        },
    )

    assert validation_receipt_matches_bundle(receipt, bundle) is True

    failed_receipt = SimpleNamespace(
        audit_bundle_export_id=bundle_id,
        validation_status="failed",
        receipt_payload_json=receipt.receipt_payload_json,
    )
    mismatched_receipt = SimpleNamespace(
        audit_bundle_export_id=bundle_id,
        validation_status="passed",
        receipt_payload_json={
            **receipt.receipt_payload_json,
            "audit_bundle": {
                **receipt.receipt_payload_json["audit_bundle"],
                "bundle_sha256": "wrong-bundle-sha",
            },
        },
    )

    assert validation_receipt_matches_bundle(failed_receipt, bundle) is False
    assert validation_receipt_matches_bundle(mismatched_receipt, bundle) is False
