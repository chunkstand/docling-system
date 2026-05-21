from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def _audit_bundle_payload(bundle_id, release_id) -> dict:
    return {
        "schema_name": "audit_bundle_export",
        "schema_version": "1.0",
        "bundle_id": str(bundle_id),
        "bundle_kind": "search_harness_release_provenance",
        "source_table": "search_harness_releases",
        "source_id": str(release_id),
        "payload_sha256": "payload-sha",
        "bundle_sha256": "bundle-sha",
        "signature": "sig",
        "signature_algorithm": "hmac-sha256",
        "signing_key_id": "test-key",
        "created_by": "operator",
        "export_status": "completed",
        "created_at": "2026-04-21T00:00:03Z",
        "bundle": {
            "schema_name": "audit_bundle_export",
            "payload": {
                "schema_name": "search_harness_release_audit_payload",
                "prov": {"wasDerivedFrom": []},
            },
        },
        "integrity": {"complete": True},
    }


def _training_audit_bundle_payload(bundle_id, training_run_id) -> dict:
    return {
        "schema_name": "audit_bundle_export",
        "schema_version": "1.0",
        "bundle_id": str(bundle_id),
        "bundle_kind": "retrieval_training_run_provenance",
        "source_table": "retrieval_training_runs",
        "source_id": str(training_run_id),
        "payload_sha256": "training-payload-sha",
        "bundle_sha256": "training-bundle-sha",
        "signature": "sig",
        "signature_algorithm": "hmac-sha256",
        "signing_key_id": "test-key",
        "created_by": "operator",
        "export_status": "completed",
        "created_at": "2026-04-21T00:00:03Z",
        "bundle": {
            "schema_name": "audit_bundle_export",
            "payload": {
                "schema_name": "retrieval_training_run_audit_payload",
                "retrieval_judgments": [],
                "retrieval_hard_negatives": [],
                "prov": {"wasDerivedFrom": []},
            },
        },
        "integrity": {"complete": True},
    }


def _validation_receipt_payload(receipt_id, bundle_id, release_id) -> dict:
    return {
        "schema_name": "audit_bundle_validation_receipt",
        "schema_version": "1.0",
        "receipt_id": str(receipt_id),
        "audit_bundle_export_id": str(bundle_id),
        "bundle_kind": "search_harness_release_provenance",
        "source_table": "search_harness_releases",
        "source_id": str(release_id),
        "validation_profile": "audit_bundle_validation_v1",
        "validation_status": "passed",
        "payload_schema_valid": True,
        "prov_graph_valid": True,
        "bundle_integrity_valid": True,
        "source_integrity_valid": True,
        "semantic_governance_valid": True,
        "receipt_sha256": "receipt-sha",
        "prov_jsonld_sha256": "prov-jsonld-sha",
        "signature": "receipt-sig",
        "signature_algorithm": "hmac-sha256",
        "signing_key_id": "test-key",
        "created_by": "operator",
        "created_at": "2026-04-21T00:00:05Z",
        "receipt": {
            "schema_name": "audit_bundle_validation_receipt",
            "validation_status": "passed",
        },
        "prov_jsonld": {
            "@context": {"prov": "http://www.w3.org/ns/prov#"},
            "@graph": [{"@id": "docling:audit_bundle_export:test"}],
        },
        "validation_errors": [],
        "integrity": {"complete": True},
    }


def test_search_harness_release_audit_bundle_routes_return_payloads(monkeypatch) -> None:
    release_id = uuid4()
    bundle_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.create_search_harness_release_audit_bundle",
        lambda session, lookup_release_id, payload, *, storage_service: _audit_bundle_payload(
            bundle_id,
            lookup_release_id,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_search_harness_release_audit_bundle",
        lambda session, lookup_release_id, *, storage_service: _audit_bundle_payload(
            bundle_id,
            lookup_release_id,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_audit_bundle_export",
        lambda session, lookup_bundle_id, *, storage_service: {
            **_audit_bundle_payload(lookup_bundle_id, release_id),
            "bundle_id": str(lookup_bundle_id),
        },
    )

    client = TestClient(app)
    create_response = client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "operator"},
    )

    assert create_response.status_code == 200
    assert create_response.headers["Location"] == f"/search/audit-bundles/{bundle_id}"
    assert create_response.json()["bundle_kind"] == "search_harness_release_provenance"

    latest_response = client.get(f"/search/harness-releases/{release_id}/audit-bundles/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["integrity"]["complete"] is True

    detail_response = client.get(f"/search/audit-bundles/{bundle_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["bundle_id"] == str(bundle_id)


def test_retrieval_training_audit_bundle_routes_return_payloads(monkeypatch) -> None:
    training_run_id = uuid4()
    bundle_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.create_retrieval_training_run_audit_bundle",
        lambda session, lookup_training_run_id, payload, *, storage_service: (
            _training_audit_bundle_payload(bundle_id, lookup_training_run_id)
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_retrieval_training_run_audit_bundle",
        lambda session, lookup_training_run_id, *, storage_service: (
            _training_audit_bundle_payload(bundle_id, lookup_training_run_id)
        ),
    )

    client = TestClient(app)
    create_response = client.post(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles",
        json={"created_by": "operator"},
    )

    assert create_response.status_code == 200
    assert create_response.headers["Location"] == f"/search/audit-bundles/{bundle_id}"
    assert create_response.json()["bundle_kind"] == "retrieval_training_run_provenance"

    latest_response = client.get(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles/latest"
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["bundle_sha256"] == "training-bundle-sha"


def test_audit_bundle_validation_receipt_routes_return_payloads(monkeypatch) -> None:
    release_id = uuid4()
    bundle_id = uuid4()
    receipt_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.create_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, payload, *, storage_service: {
            **_validation_receipt_payload(receipt_id, lookup_bundle_id, release_id),
            "created_by": payload.created_by,
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.list_audit_bundle_validation_receipts",
        lambda session, lookup_bundle_id: [
            {
                key: value
                for key, value in _validation_receipt_payload(
                    receipt_id,
                    lookup_bundle_id,
                    release_id,
                ).items()
                if key not in {"receipt", "prov_jsonld", "validation_errors", "integrity"}
            }
        ],
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, lookup_receipt_id, *, storage_service: {
            **_validation_receipt_payload(lookup_receipt_id, lookup_bundle_id, release_id),
            "receipt_id": str(lookup_receipt_id),
        },
    )
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, *, storage_service: _validation_receipt_payload(
            receipt_id,
            lookup_bundle_id,
            release_id,
        ),
    )

    client = TestClient(app)
    create_response = client.post(
        f"/search/audit-bundles/{bundle_id}/validation-receipts",
        json={"created_by": "operator"},
    )

    assert create_response.status_code == 200
    assert create_response.headers["Location"] == (
        f"/search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}"
    )
    assert create_response.json()["validation_status"] == "passed"
    assert create_response.json()["created_by"] == "operator"

    list_response = client.get(f"/search/audit-bundles/{bundle_id}/validation-receipts")
    assert list_response.status_code == 200
    assert list_response.json()[0]["receipt_id"] == str(receipt_id)

    detail_response = client.get(create_response.headers["Location"])
    assert detail_response.status_code == 200
    assert detail_response.json()["receipt_id"] == str(receipt_id)

    latest_response = client.get(
        f"/search/audit-bundles/{bundle_id}/validation-receipts/latest"
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["receipt_id"] == str(receipt_id)
