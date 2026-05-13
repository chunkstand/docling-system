from __future__ import annotations

from types import SimpleNamespace

import app.services.evidence as evidence
import app.services.evidence_audit_views as evidence_audit_views
import app.services.evidence_claim_feedback as evidence_claim_feedback
import app.services.evidence_manifests as evidence_manifests
import app.services.evidence_provenance as evidence_provenance
import app.services.evidence_provenance_exports as evidence_provenance_exports


def test_evidence_facade_exports_owner_family_entrypoints() -> None:
    assert (
        evidence.persist_technical_report_claim_retrieval_feedback_ledger
        is evidence_claim_feedback.persist_technical_report_claim_retrieval_feedback_ledger
    )
    assert (
        evidence.persist_technical_report_release_readiness_db_gate
        is evidence_audit_views.persist_technical_report_release_readiness_db_gate
    )
    assert (
        evidence.get_agent_task_audit_bundle
        is evidence_audit_views.get_agent_task_audit_bundle
    )
    assert (
        evidence.build_technical_report_evidence_manifest_payload
        is evidence_manifests.build_technical_report_evidence_manifest_payload
    )
    assert (
        evidence.persist_technical_report_evidence_manifest
        is evidence_manifests.persist_technical_report_evidence_manifest
    )
    assert (
        evidence.refresh_technical_report_evidence_manifest
        is evidence_manifests.refresh_technical_report_evidence_manifest
    )
    assert (
        evidence.get_agent_task_evidence_manifest
        is evidence_manifests.get_agent_task_evidence_manifest
    )
    assert (
        evidence.get_agent_task_evidence_trace
        is evidence_manifests.get_agent_task_evidence_trace
    )
    assert (
        evidence.persist_agent_task_provenance_export
        is evidence_provenance_exports.persist_agent_task_provenance_export
    )
    assert (
        evidence.get_agent_task_provenance_export
        is evidence_provenance_exports.get_agent_task_provenance_export
    )


def test_evidence_facade_keeps_settings_aware_provenance_wrappers(monkeypatch) -> None:
    monkeypatch.setattr(
        evidence,
        "get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="receipt-secret",
            audit_bundle_signing_key_id="receipt-key",
        ),
    )

    assert evidence._prov_export_receipt_signature("receipt-sha") == (
        evidence_provenance.prov_export_receipt_signature(
            "receipt-sha",
            settings_provider=evidence.get_settings,
        )
    )


def test_evidence_facade_stays_narrow() -> None:
    with open(evidence.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 600
