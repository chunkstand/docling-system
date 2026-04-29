from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import AgentTaskVerification
from app.services.evidence import (
    RELEASE_READINESS_DB_GATE_CHECK_KEY,
    _frozen_prov_export_payload,
    _latest_passed_release_bindings_by_request,
    _prov_export_integrity_payload,
    _prov_export_receipt_integrity,
    _release_readiness_db_gate_payload,
)


def _base_prov_export() -> dict:
    return {
        "schema_name": "technical_report_prov_export",
        "entity": {
            "docling:documents/source": {"prov:type": "docling:SourceDocument"},
            "docling:document-runs/run": {"prov:type": "docling:DocumentRun"},
        },
        "activity": {
            "docling:agent-tasks/verify": {"prov:type": "docling:AgentTask"},
        },
        "agent": {
            "docling:agent/docling-system": {"prov:type": "prov:SoftwareAgent"},
        },
        "wasGeneratedBy": {
            "docling:was-generated-by/000001": {
                "prov:entity": "docling:document-runs/run",
                "prov:activity": "docling:agent-tasks/verify",
            }
        },
        "used": {
            "docling:used/000001": {
                "prov:activity": "docling:agent-tasks/verify",
                "prov:entity": "docling:documents/source",
            }
        },
        "wasDerivedFrom": {
            "docling:was-derived-from/000001": {
                "prov:generatedEntity": "docling:document-runs/run",
                "prov:usedEntity": "docling:documents/source",
            }
        },
        "wasAssociatedWith": {
            "docling:was-associated-with/000001": {
                "prov:activity": "docling:agent-tasks/verify",
                "prov:agent": "docling:agent/docling-system",
            }
        },
        "wasAttributedTo": {
            "docling:was-attributed-to/000001": {
                "prov:entity": "docling:documents/source",
                "prov:agent": "docling:agent/docling-system",
            }
        },
        "retrieval_evaluation": {"complete": True},
        "audit": {
            "manifest_integrity": {"complete": True},
            "trace_integrity": {"complete": True},
        },
        "prov_summary": {"relation_count": 5},
        "prov_integrity": {"stale": True},
    }


class _FakeScalarSession:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self, _statement):
        return iter(self._rows)


def _context_pack_verification_row(
    *, details: dict, outcome: str = "passed"
) -> AgentTaskVerification:
    now = datetime(2026, 4, 29, 12, tzinfo=UTC)
    return AgentTaskVerification(
        id=uuid4(),
        target_task_id=uuid4(),
        verification_task_id=uuid4(),
        verifier_type="document_generation_context_pack_gate",
        outcome=outcome,
        metrics_json={},
        reasons_json=[],
        details_json=details,
        created_at=now,
        completed_at=now,
    )


def test_release_readiness_db_gate_payload_uses_latest_verification() -> None:
    request_id = str(uuid4())
    older_row = _context_pack_verification_row(
        details={
            "checks": [
                {
                    "check_key": RELEASE_READINESS_DB_GATE_CHECK_KEY,
                    "passed": True,
                    "required": True,
                    "observed": {
                        "source_search_request_count": 1,
                        "verified_request_count": 1,
                        "failure_count": 0,
                        "verified_request_ids": [request_id],
                        "complete": True,
                    },
                }
            ]
        }
    )
    latest_row = _context_pack_verification_row(
        details={"checks": [{"check_key": "context_pack_hash_integrity", "passed": True}]}
    )

    gate = _release_readiness_db_gate_payload(
        [older_row, latest_row],
        source_search_request_ids=[request_id],
    )

    assert gate["verification_id"] == str(latest_row.id)
    assert gate["missing_check"] is True
    assert gate["passed"] is False
    assert gate["coverage_complete"] is False
    assert gate["complete"] is False
    assert gate["missing_expected_request_ids"] == [request_id]


def test_release_readiness_db_gate_payload_requires_exact_request_coverage() -> None:
    expected_request_id = str(uuid4())
    unexpected_request_id = str(uuid4())
    row = _context_pack_verification_row(
        details={
            "checks": [
                {
                    "check_key": RELEASE_READINESS_DB_GATE_CHECK_KEY,
                    "passed": True,
                    "required": True,
                    "observed": {
                        "source_search_request_count": 1,
                        "verified_request_count": 1,
                        "failure_count": 0,
                        "verified_request_ids": [unexpected_request_id],
                        "complete": True,
                    },
                }
            ]
        }
    )

    gate = _release_readiness_db_gate_payload(
        [row],
        source_search_request_ids=[expected_request_id],
    )

    assert gate["passed"] is True
    assert gate["coverage_complete"] is False
    assert gate["complete"] is False
    assert gate["missing_expected_request_ids"] == [expected_request_id]
    assert gate["unexpected_verified_request_ids"] == [unexpected_request_id]


def test_release_binding_uses_latest_release_before_search_request() -> None:
    request_id = str(uuid4())
    search_created_at = datetime(2026, 4, 27, 12, tzinfo=UTC)
    older_release = SimpleNamespace(
        id=uuid4(),
        candidate_harness_name="default_v1",
        created_at=datetime(2026, 4, 27, 10, tzinfo=UTC),
    )
    future_release = SimpleNamespace(
        id=uuid4(),
        candidate_harness_name="default_v1",
        created_at=datetime(2026, 4, 27, 13, tzinfo=UTC),
    )
    session = _FakeScalarSession([future_release, older_release])

    bindings, releases = _latest_passed_release_bindings_by_request(
        session,
        {
            request_id: SimpleNamespace(
                harness_name="default_v1",
                created_at=search_created_at,
            )
        },
    )

    assert bindings[request_id]["search_harness_release_id"] == str(older_release.id)
    assert bindings[request_id]["selection_status"] == "release_found_before_request"
    assert list(releases) == [str(older_release.id)]


def test_release_binding_does_not_attach_future_only_release() -> None:
    request_id = str(uuid4())
    future_release = SimpleNamespace(
        id=uuid4(),
        candidate_harness_name="default_v1",
        created_at=datetime(2026, 4, 27, 13, tzinfo=UTC),
    )
    session = _FakeScalarSession([future_release])

    bindings, releases = _latest_passed_release_bindings_by_request(
        session,
        {
            request_id: SimpleNamespace(
                harness_name="default_v1",
                created_at=datetime(2026, 4, 27, 12, tzinfo=UTC),
            )
        },
    )

    assert bindings[request_id]["search_harness_release_id"] is None
    assert bindings[request_id]["selection_status"] == "no_passed_release_before_request"
    assert releases == {}


def test_prov_export_integrity_is_complete_for_closed_relation_graph() -> None:
    integrity = _prov_export_integrity_payload(_base_prov_export())

    assert integrity["complete"] is True
    assert integrity["hash_basis_schema"] == ("technical_report_prov_export_without_integrity_v1")
    assert "prov_integrity" not in integrity["hash_basis_fields"]
    assert "frozen_export" not in integrity["hash_basis_fields"]
    assert integrity["hash_excluded_fields"] == ["frozen_export", "prov_integrity"]
    assert integrity["all_relation_references_declared"] is True
    assert integrity["missing_relation_reference_count"] == 0
    assert integrity["prov_sha256"]


def test_prov_export_integrity_fails_for_undeclared_relation_reference() -> None:
    prov_export = _base_prov_export()
    prov_export["used"]["docling:used/000001"]["prov:entity"] = "docling:documents/missing"

    integrity = _prov_export_integrity_payload(prov_export)

    assert integrity["complete"] is False
    assert integrity["all_used_entities_declared"] is False
    assert integrity["all_relation_references_declared"] is False
    assert integrity["missing_relation_reference_count"] == 1
    assert integrity["missing_relation_references"] == [
        {
            "relation_type": "used",
            "relation_id": "docling:used/000001",
            "reference_field": "prov:entity",
            "reference_id": "docling:documents/missing",
        }
    ]


def test_frozen_prov_export_includes_signed_hash_chain_receipt(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.evidence.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="receipt-secret",
            audit_bundle_signing_key_id="receipt-key",
        ),
    )
    prov_export = _base_prov_export()
    prov_export["audit"]["manifest_sha256"] = "manifest-sha"
    prov_export["audit"]["trace_sha256"] = "trace-sha"
    prov_export["prov_integrity"] = _prov_export_integrity_payload(prov_export)

    frozen_payload = _frozen_prov_export_payload(
        prov_export,
        artifact_id=uuid4(),
        task_id=uuid4(),
        created_at=datetime(2026, 4, 27, tzinfo=UTC),
        storage_path="storage/agent_tasks/task/technical_report_prov_export.json",
    )

    receipt = frozen_payload["frozen_export"]["export_receipt"]
    assert receipt["schema_name"] == "technical_report_prov_export_receipt"
    assert receipt["hash_chain_complete"] is True
    assert [item["name"] for item in receipt["hash_chain"]] == [
        "evidence_manifest",
        "evidence_trace",
        "prov_hash_basis",
        "technical_report_prov_export",
    ]
    assert receipt["signature_status"] == "signed"
    assert receipt["signature_algorithm"] == "hmac-sha256"
    assert receipt["signing_key_id"] == "receipt-key"
    assert receipt["receipt_sha256"]
    assert receipt["signature"]

    integrity = _prov_export_receipt_integrity(frozen_payload)
    assert integrity["complete"] is True
    assert integrity["receipt_hash_matches"] is True
    assert integrity["hash_chain_complete"] is True
    assert integrity["signature_verification_status"] == "verified"


def test_prov_export_receipt_integrity_fails_without_signature_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.evidence.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key=None,
            audit_bundle_signing_key_id="missing-key",
        ),
    )
    prov_export = _base_prov_export()
    prov_export["audit"]["manifest_sha256"] = "manifest-sha"
    prov_export["audit"]["trace_sha256"] = "trace-sha"
    prov_export["prov_integrity"] = _prov_export_integrity_payload(prov_export)

    frozen_payload = _frozen_prov_export_payload(
        prov_export,
        artifact_id=uuid4(),
        task_id=uuid4(),
        created_at=datetime(2026, 4, 27, tzinfo=UTC),
        storage_path="storage/agent_tasks/task/technical_report_prov_export.json",
    )

    integrity = _prov_export_receipt_integrity(frozen_payload)
    assert integrity["complete"] is False
    assert integrity["receipt_hash_matches"] is True
    assert integrity["signature_status"] == "unsigned"
    assert integrity["signature_present"] is False
    assert integrity["signature_valid"] is False


def test_prov_export_receipt_integrity_fails_for_hash_chain_tamper(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.evidence.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="receipt-secret",
            audit_bundle_signing_key_id="receipt-key",
        ),
    )
    prov_export = _base_prov_export()
    prov_export["audit"]["manifest_sha256"] = "manifest-sha"
    prov_export["audit"]["trace_sha256"] = "trace-sha"
    prov_export["prov_integrity"] = _prov_export_integrity_payload(prov_export)
    frozen_payload = _frozen_prov_export_payload(
        prov_export,
        artifact_id=uuid4(),
        task_id=uuid4(),
        created_at=datetime(2026, 4, 27, tzinfo=UTC),
        storage_path="storage/agent_tasks/task/technical_report_prov_export.json",
    )
    frozen_payload["frozen_export"]["export_receipt"]["hash_chain"][-1]["sha256"] = "tampered"

    integrity = _prov_export_receipt_integrity(frozen_payload)
    assert integrity["complete"] is False
    assert integrity["receipt_hash_matches"] is False
    assert integrity["export_payload_hash_matches"] is False
