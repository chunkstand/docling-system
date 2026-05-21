from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from app.db.public.audit_and_evidence import AuditBundleExport
from app.db.public.retrieval import SearchHarnessRelease
from tests.integration.search_harness_release_audit_support import (
    materialize_search_harness_release_learning_records,
)
from tests.integration.search_harness_release_support import (
    create_search_harness_release,
    seed_search_harness_release_evaluation,
)


def test_search_harness_release_gate_roundtrip_records_release_details(
    postgres_integration_harness,
) -> None:
    _, evaluation_id = seed_search_harness_release_evaluation(
        postgres_integration_harness.session_factory
    )

    response = create_search_harness_release(
        postgres_integration_harness.client,
        evaluation_id=evaluation_id,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "passed"
    assert body["evaluation_id"] == str(evaluation_id)
    assert body["evaluation_snapshot"]["evaluation_id"] == str(evaluation_id)
    assert body["release_package_sha256"]
    release_id = body["release_id"]

    with postgres_integration_harness.session_factory() as session:
        release = session.get(SearchHarnessRelease, UUID(release_id))
        assert release is not None

    list_response = postgres_integration_harness.client.get("/search/harness-releases")
    assert list_response.status_code == 200
    assert list_response.json()[0]["release_id"] == release_id

    detail_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}"
    )
    assert detail_response.status_code == 200
    assert (
        detail_response.json()["details"]["per_source"]["evaluation_queries"]["shared_query_count"]
        == 4
    )


def test_search_harness_release_gate_roundtrip_materializes_audit_bundle_and_detects_tampering(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.audit_bundles.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="integration-secret",
            audit_bundle_signing_key_id="integration-key",
        ),
    )
    now, evaluation_id = seed_search_harness_release_evaluation(
        postgres_integration_harness.session_factory
    )

    response = create_search_harness_release(
        postgres_integration_harness.client,
        evaluation_id=evaluation_id,
    )
    assert response.status_code == 200
    release_body = response.json()
    release_id = release_body["release_id"]
    artifacts = materialize_search_harness_release_learning_records(
        postgres_integration_harness.session_factory,
        now=now,
        evaluation_id=evaluation_id,
        release_body=release_body,
    )

    audit_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "integration"},
    )
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    assert audit_response.headers["Location"] == (
        f"/search/audit-bundles/{audit_bundle['bundle_id']}"
    )
    assert audit_bundle["bundle_kind"] == "search_harness_release_provenance"
    assert audit_bundle["integrity"]["complete"] is True
    assert audit_bundle["integrity"]["signature_valid"] is True
    assert audit_bundle["bundle"]["payload"]["schema_version"] == "1.1"
    assert audit_bundle["bundle"]["payload"]["audit_checklist"]["complete"] is True
    assert audit_bundle["bundle"]["payload"]["audit_checklist"]["learning_candidate_count"] == 1
    assert audit_bundle["bundle"]["payload"]["integrity"]["release_package_hash_matches"] is True
    assert audit_bundle["bundle"]["payload"]["integrity"]["training_run_count"] == 1
    assert audit_bundle["bundle"]["payload"]["integrity"]["training_audit_bundle_count"] == 1
    assert (
        audit_bundle["bundle"]["payload"]["integrity"][
            "training_audit_bundle_hashes_match_training_runs"
        ]
        is True
    )
    assert (
        audit_bundle["bundle"]["payload"]["integrity"][
            "training_audit_bundle_validation_receipt_count"
        ]
        == 1
    )
    assert (
        audit_bundle["bundle"]["payload"]["integrity"][
            "training_audit_bundle_validation_receipts_complete"
        ]
        is True
    )
    assert audit_bundle["bundle"]["payload"]["audit_checklist"]["reranker_artifact_count"] == 1
    assert audit_bundle["bundle"]["payload"]["integrity"]["reranker_artifact_count"] == 1
    assert (
        audit_bundle["bundle"]["payload"]["integrity"]["reranker_artifact_trace_complete"] is True
    )
    assert audit_bundle["bundle"]["payload"]["integrity"]["reranker_artifact_hashes_match"] is True
    assert (
        audit_bundle["bundle"]["payload"]["integrity"]["reranker_artifact_change_impacts_complete"]
        is True
    )
    assert (
        audit_bundle["bundle"]["payload"]["retrieval_learning_candidates"][0][
            "training_dataset_sha256"
        ]
        == artifacts["training_dataset_sha256"]
    )
    reranker_artifact_ref = audit_bundle["bundle"]["payload"]["retrieval_reranker_artifacts"][0]
    assert reranker_artifact_ref["artifact_id"] == str(artifacts["reranker_artifact_id"])
    assert reranker_artifact_ref["artifact_sha256"] == (
        artifacts["reranker_payloads"]["artifact_sha256"]
    )
    assert (
        reranker_artifact_ref["payload_artifact_sha256"]
        == artifacts["reranker_payloads"]["artifact_sha256"]
    )
    assert (
        reranker_artifact_ref["change_impact_sha256"]
        == artifacts["reranker_payloads"]["change_impact_sha256"]
    )
    assert (
        reranker_artifact_ref["payload_change_impact_sha256"]
        == artifacts["reranker_payloads"]["change_impact_sha256"]
    )
    assert reranker_artifact_ref["payload_training_dataset_sha256"] == (
        artifacts["training_dataset_sha256"]
    )
    assert reranker_artifact_ref["payload_release_id"] == release_id
    assert reranker_artifact_ref["change_impact_report"]["schema_name"] == (
        "retrieval_reranker_change_impact_report"
    )
    assert (
        audit_bundle["bundle"]["payload"]["retrieval_training_runs"][0]["training_dataset_sha256"]
        == artifacts["training_dataset_sha256"]
    )
    assert any(
        row["event_kind"] == "search_harness_release_recorded"
        for row in audit_bundle["bundle"]["payload"]["semantic_governance_events"]
    )
    assert any(
        row["event_kind"] == "retrieval_learning_candidate_evaluated"
        for row in audit_bundle["bundle"]["payload"]["semantic_governance_events"]
    )
    assert any(
        row["event_kind"] == "retrieval_reranker_artifact_materialized"
        for row in audit_bundle["bundle"]["payload"]["semantic_governance_events"]
    )
    semantic_governance_policy = audit_bundle["bundle"]["payload"]["semantic_governance_policy"]
    assert semantic_governance_policy["policy_profile"] == "release_semantic_governance_v1"
    assert semantic_governance_policy["checks"]["has_release_governance_event"] is True
    assert semantic_governance_policy["checks"]["hash_links_verified"] is True
    assert semantic_governance_policy["complete"] is True
    training_audit_bundle_ref = audit_bundle["bundle"]["payload"][
        "retrieval_training_audit_bundles"
    ][0]
    assert training_audit_bundle_ref["bundle_kind"] == "retrieval_training_run_provenance"
    assert training_audit_bundle_ref["source_id"] == str(artifacts["training_run_id"])
    assert training_audit_bundle_ref["payload_source_id"] == str(artifacts["training_run_id"])
    assert training_audit_bundle_ref["payload_training_dataset_sha256"] == (
        artifacts["training_dataset_sha256"]
    )
    assert training_audit_bundle_ref["payload_training_dataset_hash_matches"] is True
    training_validation_receipt_ref = audit_bundle["bundle"]["payload"][
        "retrieval_training_audit_bundle_validation_receipts"
    ][0]
    assert (
        training_validation_receipt_ref["audit_bundle_export_id"]
        == training_audit_bundle_ref["bundle_id"]
    )
    assert training_validation_receipt_ref["validation_profile"] == "audit_bundle_validation_v1"
    assert training_validation_receipt_ref["validation_status"] == "passed"
    assert training_validation_receipt_ref["payload_schema_valid"] is True
    assert training_validation_receipt_ref["prov_graph_valid"] is True
    assert training_validation_receipt_ref["bundle_integrity_valid"] is True
    assert training_validation_receipt_ref["source_integrity_valid"] is True
    assert training_validation_receipt_ref["receipt_sha256"]
    assert training_validation_receipt_ref["prov_jsonld_sha256"]
    assert audit_bundle["bundle"]["payload"]["prov"]["wasDerivedFrom"]
    assert any(
        edge["usedEntity"].startswith("docling:retrieval_training_run:")
        for edge in audit_bundle["bundle"]["payload"]["prov"]["wasDerivedFrom"]
    )
    assert any(
        edge["usedEntity"]
        == f"docling:retrieval_reranker_artifact:{artifacts['reranker_artifact_id']}"
        for edge in audit_bundle["bundle"]["payload"]["prov"]["wasDerivedFrom"]
    )
    assert any(
        edge["usedEntity"]
        == f"docling:audit_bundle_export:{training_audit_bundle_ref['bundle_id']}"
        for edge in audit_bundle["bundle"]["payload"]["prov"]["wasDerivedFrom"]
    )
    assert audit_bundle["signing_key_id"] == "integration-key"

    latest_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/audit-bundles/latest"
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["bundle_id"] == audit_bundle["bundle_id"]

    audit_detail_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}"
    )
    assert audit_detail_response.status_code == 200
    assert audit_detail_response.json()["integrity"]["bundle_hash_matches_row"] is True

    auto_latest_validation_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts/latest"
    )
    assert auto_latest_validation_response.status_code == 200
    auto_validation_receipt = auto_latest_validation_response.json()
    assert auto_validation_receipt["validation_status"] == "passed"
    assert auto_validation_receipt["semantic_governance_valid"] is True

    with postgres_integration_harness.session_factory() as session:
        row = session.get(AuditBundleExport, audit_bundle["bundle_id"])
        assert row is not None
        assert row.bundle_sha256 == audit_bundle["bundle_sha256"]
        assert row.search_harness_release_id == UUID(audit_bundle["source_id"])
        training_bundle_row = session.get(
            AuditBundleExport,
            UUID(training_audit_bundle_ref["bundle_id"]),
        )
        assert training_bundle_row is not None
        assert training_bundle_row.retrieval_training_run_id == artifacts["training_run_id"]
        storage_path = Path(row.storage_path)

    stored_bundle = json.loads(storage_path.read_text())
    stored_bundle["payload"]["release"]["outcome"] = "tampered"
    storage_path.write_text(json.dumps(stored_bundle))

    tampered_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}"
    )
    assert tampered_response.status_code == 200
    tampered_integrity = tampered_response.json()["integrity"]
    assert tampered_integrity["complete"] is False
    assert tampered_integrity["payload_hash_matches_row"] is False
    assert tampered_integrity["bundle_hash_matches_row"] is False
    assert tampered_integrity["stored_payload_matches_file"] is False
