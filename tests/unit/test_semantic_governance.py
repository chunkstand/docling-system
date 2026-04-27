from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.models import SemanticGovernanceEvent
from app.services.semantic_governance import (
    _event_hash_basis,
    _payload_sha256,
    semantic_governance_event_integrity,
    semantic_governance_event_payload,
)


def _governance_event() -> SemanticGovernanceEvent:
    event_id = uuid4()
    task_id = uuid4()
    artifact_id = uuid4()
    manifest_id = uuid4()
    created_at = datetime.now(UTC)
    event_payload = {
        "schema_name": "semantic_governance_event",
        "schema_version": "1.0",
        "technical_report_prov_export": {
            "artifact_id": str(artifact_id),
            "receipt_sha256": "receipt-sha",
        },
    }
    payload_sha = _payload_sha256(event_payload)
    event_hash = _payload_sha256(
        _event_hash_basis(
            event_id=event_id,
            event_kind="technical_report_prov_export_frozen",
            governance_scope=f"agent_task:{task_id}",
            subject_table="agent_task_artifacts",
            subject_id=artifact_id,
            task_id=task_id,
            ontology_snapshot_id=None,
            semantic_graph_snapshot_id=None,
            search_harness_evaluation_id=None,
            search_harness_release_id=None,
            evidence_manifest_id=manifest_id,
            evidence_package_export_id=None,
            agent_task_artifact_id=artifact_id,
            previous_event_id=None,
            previous_event_hash=None,
            receipt_sha256="receipt-sha",
            payload_sha256=payload_sha,
            deduplication_key=f"technical_report_prov_export_frozen:{artifact_id}:receipt-sha",
            created_by="technical_report_verification",
            created_at=created_at,
        )
    )
    return SemanticGovernanceEvent(
        id=event_id,
        event_sequence=7,
        event_kind="technical_report_prov_export_frozen",
        governance_scope=f"agent_task:{task_id}",
        subject_table="agent_task_artifacts",
        subject_id=artifact_id,
        task_id=task_id,
        evidence_manifest_id=manifest_id,
        agent_task_artifact_id=artifact_id,
        receipt_sha256="receipt-sha",
        payload_sha256=payload_sha,
        event_hash=event_hash,
        deduplication_key=f"technical_report_prov_export_frozen:{artifact_id}:receipt-sha",
        event_payload_json=event_payload,
        created_by="technical_report_verification",
        created_at=created_at,
    )


def test_semantic_governance_event_payload_verifies_hashes() -> None:
    row = _governance_event()

    payload = semantic_governance_event_payload(row)

    assert payload["event_kind"] == "technical_report_prov_export_frozen"
    assert payload["receipt_sha256"] == "receipt-sha"
    assert payload["integrity"]["complete"] is True
    assert payload["integrity"]["payload_hash_matches"] is True
    assert payload["integrity"]["event_hash_matches"] is True


def test_semantic_governance_event_integrity_detects_payload_tamper() -> None:
    row = _governance_event()
    row.event_payload_json = {
        **row.event_payload_json,
        "technical_report_prov_export": {"artifact_id": "tampered"},
    }

    integrity = semantic_governance_event_integrity(row)

    assert integrity["complete"] is False
    assert integrity["payload_hash_matches"] is False
    assert integrity["event_hash_matches"] is True
