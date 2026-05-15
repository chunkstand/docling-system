from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import app.services.evidence_semantic_trace as evidence_semantic_trace


def test_semantic_assertion_payload_normalizes_optional_fields() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        semantic_pass_id=uuid4(),
        concept_id=uuid4(),
        assertion_kind="obligation",
        epistemic_status="supported",
        context_scope="document",
        review_status="accepted",
        matched_terms_json=None,
        source_types_json=None,
        evidence_count=2,
        confidence=0.78,
        details_json=None,
        created_at=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
    )

    payload = evidence_semantic_trace._semantic_assertion_payload(row)

    assert payload["assertion_id"] == row.id
    assert payload["matched_terms"] == []
    assert payload["source_types"] == []
    assert payload["details"] == {}
    assert payload["confidence"] == 0.78


def test_report_evidence_card_source_records_uses_snapshot_hash(monkeypatch) -> None:
    document_id = str(uuid4())
    run_id = str(uuid4())
    monkeypatch.setattr(
        evidence_semantic_trace,
        "_evidence_card_snapshot",
        lambda card: {"evidence_card_sha256": f"sha-{card['evidence_card_id']}"},
    )

    records = evidence_semantic_trace._report_evidence_card_source_records(
        [
            {
                "evidence_card_id": "card-1",
                "evidence_kind": "table",
                "source_type": "document_table",
                "document_id": document_id,
                "run_id": run_id,
                "page_from": 2,
                "page_to": 3,
                "source_artifact_api_path": "/documents/doc-1/tables/table-1",
                "source_snapshot_sha256s": ["snap-a", "snap-b"],
            }
        ]
    )

    assert records == [
        {
            "record_kind": "technical_report_evidence_card",
            "evidence_card_id": "card-1",
            "evidence_kind": "table",
            "source_type": "document_table",
            "document_id": document_id,
            "run_id": run_id,
            "page_from": 2,
            "page_to": 3,
            "source_artifact_api_path": "/documents/doc-1/tables/table-1",
            "evidence_card_sha256": "sha-card-1",
            "source_snapshot_sha256s": ["snap-a", "snap-b"],
        }
    ]
