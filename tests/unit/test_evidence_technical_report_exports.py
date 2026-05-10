from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import app.services.evidence_technical_report_exports as technical_report_exports
from app.db.models import ClaimEvidenceDerivation, EvidencePackageExport
from app.services import evidence

TECHNICAL_REPORT_EXPORT_FACADE_ALIASES = {
    "_claim_derivation_provenance_lock_contract_mismatches": (
        "_claim_derivation_provenance_lock_contract_mismatches"
    ),
    "_claim_derivation_support_judgment_contract_mismatches": (
        "_claim_derivation_support_judgment_contract_mismatches"
    ),
    "_evidence_card_snapshot": "_evidence_card_snapshot",
    "_latest_passed_release_bindings_by_request": "_latest_passed_release_bindings_by_request",
    "attach_operator_run_to_evidence_export": "attach_operator_run_to_evidence_export",
    "apply_technical_report_derivation_links": "apply_technical_report_derivation_links",
    "build_technical_report_derivation_package": "build_technical_report_derivation_package",
    "persist_technical_report_evidence_export": "persist_technical_report_evidence_export",
}


class _FakeSession:
    def __init__(self, export: EvidencePackageExport | None) -> None:
        self.export = export
        self.flush_count = 0

    def get(self, _model, row_id):
        if self.export is None or self.export.id != row_id:
            return None
        return self.export

    def flush(self) -> None:
        self.flush_count += 1


def test_evidence_facade_reexports_technical_report_export_owner_functions() -> None:
    for facade_name, owner_name in TECHNICAL_REPORT_EXPORT_FACADE_ALIASES.items():
        assert getattr(evidence, facade_name) is getattr(technical_report_exports, owner_name)


def test_evidence_facade_wraps_blocked_owner_names() -> None:
    derivation = ClaimEvidenceDerivation(
        id=uuid4(),
        evidence_package_export_id=uuid4(),
        claim_id="claim:1",
        derivation_rule="technical_report_claim_contract_v1",
        evidence_package_sha256="package-sha",
        derivation_sha256="derivation-sha",
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    assert evidence._claim_derivation_payload(
        derivation
    ) == technical_report_exports._claim_derivation_payload(derivation)


def test_attach_helpers_update_evidence_export_rows() -> None:
    export_id = uuid4()
    artifact_id = uuid4()
    operator_run_id = uuid4()
    export = EvidencePackageExport(
        id=export_id,
        package_kind="technical_report_claims",
        package_sha256="package-sha",
        export_status="completed",
        operator_run_ids_json=["existing"],
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )
    session = _FakeSession(export)

    evidence.attach_artifact_to_evidence_export(
        session,
        evidence_package_export_id=export_id,
        agent_task_artifact_id=artifact_id,
    )
    technical_report_exports.attach_operator_run_to_evidence_export(
        session,
        evidence_package_export_id=export_id,
        operator_run_id=operator_run_id,
    )

    assert export.agent_task_artifact_id == artifact_id
    assert export.operator_run_ids_json == ["existing", str(operator_run_id)]
    assert session.flush_count == 2


def test_claim_derivation_payload_preserves_hash_and_lock_fields() -> None:
    derivation = ClaimEvidenceDerivation(
        id=uuid4(),
        evidence_package_export_id=uuid4(),
        agent_task_id=uuid4(),
        claim_id="claim:1",
        derivation_rule="technical_report_claim_contract_v1",
        evidence_card_ids_json=["card-1"],
        source_search_request_ids_json=["request-1"],
        source_search_request_result_ids_json=["result-1"],
        source_evidence_package_export_ids_json=["export-1"],
        provenance_lock_json={"schema_name": "technical_report_claim_provenance_lock"},
        provenance_lock_sha256="prov-lock-sha",
        support_verdict="supported",
        support_score=0.91,
        support_judgment_json={"schema_name": "technical_report_claim_support_judgment"},
        support_judgment_sha256="judge-sha",
        evidence_package_sha256="package-sha",
        derivation_sha256="derivation-sha",
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    payload = technical_report_exports._claim_derivation_payload(derivation)

    assert payload["claim_id"] == "claim:1"
    assert payload["source_search_request_ids"] == ["request-1"]
    assert payload["source_search_request_result_ids"] == ["result-1"]
    assert payload["source_evidence_package_export_ids"] == ["export-1"]
    assert payload["provenance_lock_sha256"] == "prov-lock-sha"
    assert payload["support_judgment_sha256"] == "judge-sha"
    assert payload["evidence_package_sha256"] == "package-sha"
    assert payload["derivation_sha256"] == "derivation-sha"
