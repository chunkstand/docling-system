from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.evidence_audit_views as evidence_audit_views


def test_provenance_export_receipt_payload_preserves_frozen_export_hashes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        evidence_audit_views,
        "_frozen_export_receipt",
        lambda payload: {"receipt_id": "receipt-1", "payload_keys": sorted(payload)},
    )
    monkeypatch.setattr(
        evidence_audit_views,
        "_prov_export_receipt_integrity",
        lambda payload: {"ok": True, "frozen_export": "frozen_export" in payload},
    )
    row = SimpleNamespace(
        id=uuid4(),
        task_id=uuid4(),
        artifact_kind="technical_report_prov_export",
        storage_path="storage/evidence/prov-export.json",
        payload_json={
            "frozen_export": {
                "export_payload_sha256": "export-sha",
                "prov_hash_basis_sha256": "basis-sha",
            }
        },
    )

    payload = evidence_audit_views._provenance_export_receipt_payload(row)

    assert payload["artifact_id"] == row.id
    assert payload["task_id"] == row.task_id
    assert payload["export_payload_sha256"] == "export-sha"
    assert payload["prov_hash_basis_sha256"] == "basis-sha"
    assert payload["export_receipt"]["receipt_id"] == "receipt-1"
    assert payload["receipt_integrity"] == {"ok": True, "frozen_export": True}


def test_context_pack_audit_raises_for_missing_verification_task() -> None:
    class _MissingSession:
        def get(self, *_args, **_kwargs):
            return None

    with pytest.raises(ValueError, match="was not found"):
        evidence_audit_views._technical_report_context_pack_audit_for_verification_task(
            _MissingSession(),
            uuid4(),
        )
