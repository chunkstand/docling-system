from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from app.db.models import SearchHarnessReleaseReadinessAssessment, SemanticGovernanceEvent
from tests.integration.search_harness_release_audit_support import (
    materialize_search_harness_release_learning_records,
)
from tests.integration.search_harness_release_support import (
    create_search_harness_release,
    seed_search_harness_release_evaluation,
)


def test_search_harness_release_readiness_assessment_roundtrip(
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
    materialize_search_harness_release_learning_records(
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

    auto_latest_validation_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts/latest"
    )
    assert auto_latest_validation_response.status_code == 200
    auto_validation_receipt = auto_latest_validation_response.json()
    assert auto_validation_receipt["validation_status"] == "passed"
    assert auto_validation_receipt["semantic_governance_valid"] is True

    readiness_after_export_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_after_export_response.status_code == 200
    readiness_after_export = readiness_after_export_response.json()
    assert readiness_after_export["schema_version"] == "1.3"
    assert readiness_after_export["ready"] is True
    assert readiness_after_export["blocker_details"] == []
    assert readiness_after_export["checks"] == {
        "retrieval_ready": True,
        "provenance_ready": True,
        "semantic_governance_ready": True,
        "validation_receipts_ready": True,
        "ready": True,
    }
    assert (
        readiness_after_export["validation_receipts"]["latest_release_validation_receipt_id"]
        == auto_validation_receipt["receipt_id"]
    )
    assert readiness_after_export["diagnostics"]["validation_error_codes"] == []
    assert readiness_after_export["lineage_remediation"]["status"] == "clear"

    validation_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts",
        json={"created_by": "integration"},
    )
    assert validation_response.status_code == 200
    validation_receipt = validation_response.json()
    assert validation_response.headers["Location"] == (
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts/"
        f"{validation_receipt['receipt_id']}"
    )
    assert validation_receipt["validation_status"] == "passed"
    assert validation_receipt["receipt"]["audit_bundle"]["bundle_id"] == audit_bundle["bundle_id"]
    assert validation_receipt["receipt"]["receipt_sha256"] == validation_receipt["receipt_sha256"]
    assert validation_receipt["prov_jsonld"]["@context"]["prov"] == "http://www.w3.org/ns/prov#"
    assert validation_receipt["prov_jsonld"]["@graph"]
    assert validation_receipt["integrity"]["complete"] is True
    assert validation_receipt["semantic_governance_valid"] is True
    assert validation_receipt["receipt"]["validation_checks"]["semantic_governance_valid"] is True

    validation_list_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts"
    )
    assert validation_list_response.status_code == 200
    assert validation_list_response.json()[0]["receipt_id"] == validation_receipt["receipt_id"]

    validation_detail_response = postgres_integration_harness.client.get(
        validation_response.headers["Location"]
    )
    assert validation_detail_response.status_code == 200
    assert validation_detail_response.json()["receipt_id"] == validation_receipt["receipt_id"]

    latest_validation_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts/latest"
    )
    assert latest_validation_response.status_code == 200
    assert latest_validation_response.json()["receipt_id"] == validation_receipt["receipt_id"]

    readiness_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert readiness["ready"] is True
    assert readiness["blocker_details"] == []
    assert readiness["checks"] == {
        "retrieval_ready": True,
        "provenance_ready": True,
        "semantic_governance_ready": True,
        "validation_receipts_ready": True,
        "ready": True,
    }
    assert readiness["semantic_governance"]["checks"]["has_release_governance_event"] is True
    assert readiness["validation_receipts"]["semantic_governance_valid"] is True
    assert readiness["latest_readiness_assessment"] is None

    missing_assessment_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness-assessments/latest"
    )
    assert missing_assessment_response.status_code == 404
    assert missing_assessment_response.json()["error_code"] == (
        "search_harness_release_readiness_assessment_not_found"
    )

    assessment_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/readiness-assessments",
        json={"created_by": "integration", "review_note": "freeze passed readiness"},
    )
    assert assessment_response.status_code == 200
    assessment = assessment_response.json()
    assert assessment_response.headers["Location"] == (
        f"/search/harness-releases/{release_id}/readiness-assessments/"
        f"{assessment['assessment_id']}"
    )
    assert assessment["schema_name"] == "search_harness_release_readiness_assessment"
    assert assessment["schema_version"] == "1.1"
    assert assessment["readiness_status"] == "ready"
    assert assessment["ready"] is True
    assert assessment["blockers"] == []
    assert assessment["latest_release_audit_bundle_id"] == audit_bundle["bundle_id"]
    assert (
        assessment["latest_release_validation_receipt_id"]
        == validation_receipt["receipt_id"]
    )
    assert assessment["semantic_governance_event_id"]
    assert assessment["readiness_payload_sha256"]
    assert assessment["assessment_payload_sha256"]
    assert assessment["readiness"]["ready"] is True
    assert assessment["readiness"]["latest_readiness_assessment"] is None
    assert assessment["assessment"]["readiness_status"] == "ready"
    assert assessment["integrity"]["complete"] is True
    assert assessment["integrity"]["readiness_payload_hash_matches"] is True
    assert assessment["integrity"]["assessment_payload_hash_matches"] is True
    assert assessment["integrity"]["assessment_payload_embeds_readiness_hash"] is True
    assert assessment["integrity"]["release_audit_bundle_id_matches"] is True
    assert assessment["integrity"]["release_validation_receipt_id_matches"] is True

    latest_assessment_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness-assessments/latest"
    )
    assert latest_assessment_response.status_code == 200
    assert latest_assessment_response.json()["assessment_id"] == assessment["assessment_id"]
    assert latest_assessment_response.json()["integrity"]["complete"] is True

    assessment_detail_response = postgres_integration_harness.client.get(
        assessment_response.headers["Location"]
    )
    assert assessment_detail_response.status_code == 200
    assert assessment_detail_response.json()["assessment_id"] == assessment["assessment_id"]
    assert assessment_detail_response.json()["integrity"]["complete"] is True

    readiness_with_assessment_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_with_assessment_response.status_code == 200
    readiness_with_assessment = readiness_with_assessment_response.json()
    assert readiness_with_assessment["latest_readiness_assessment"]["assessment_id"] == (
        assessment["assessment_id"]
    )
    assert readiness_with_assessment["latest_readiness_assessment"]["ready"] is True

    with postgres_integration_harness.session_factory() as session:
        assessment_row = session.get(
            SearchHarnessReleaseReadinessAssessment,
            UUID(assessment["assessment_id"]),
        )
        assert assessment_row is not None
        assert assessment_row.ready is True
        assert assessment_row.release_audit_bundle_id == UUID(audit_bundle["bundle_id"])
        assert assessment_row.release_validation_receipt_id == UUID(
            validation_receipt["receipt_id"]
        )
        assert assessment_row.semantic_governance_event_id == UUID(
            assessment["semantic_governance_event_id"]
        )
        event_row = session.get(
            SemanticGovernanceEvent,
            assessment_row.semantic_governance_event_id,
        )
        assert event_row is not None
        assert event_row.event_kind == "search_harness_release_readiness_assessed"
        assert event_row.subject_table == "search_harness_release_readiness_assessments"
        assert event_row.subject_id == assessment_row.id
        assert event_row.search_harness_release_id == UUID(release_id)
