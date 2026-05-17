from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import app.services.evidence_semantic_trace as evidence_semantic_trace
import app.services.evidence_semantic_trace_integrity as integrity_owner
import app.services.evidence_semantic_trace_provenance as provenance_owner
import app.services.evidence_semantic_trace_source_records as source_record_owner


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
        source_record_owner,
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


def test_technical_report_integrity_payload_reports_mismatches(monkeypatch) -> None:
    monkeypatch.setattr(
        integrity_owner,
        "build_technical_report_derivation_package",
        lambda _draft: {
            "package_sha256": "pkg-expected",
            "claim_derivations": [
                {
                    "claim_id": "claim-1",
                    "derivation_sha256": "drv-expected",
                    "provenance_lock_sha256": "lock-expected",
                    "support_judgment_sha256": "support-expected",
                },
                {
                    "claim_id": "claim-2",
                    "derivation_sha256": "drv-2",
                    "provenance_lock_sha256": "lock-2",
                    "support_judgment_sha256": "support-2",
                },
            ],
        },
    )
    monkeypatch.setattr(
        integrity_owner,
        "_claim_derivation_provenance_lock_contract_mismatches",
        lambda row: row.claim_id == "claim-1",
    )
    monkeypatch.setattr(
        integrity_owner,
        "_claim_derivation_support_judgment_contract_mismatches",
        lambda row: row.claim_id == "claim-1",
    )

    payload = evidence_semantic_trace._technical_report_integrity_payload(
        {},
        exports=[SimpleNamespace(package_sha256="pkg-other")],
        derivations=[
            SimpleNamespace(
                claim_id="claim-1",
                derivation_sha256="drv-other",
                evidence_package_sha256="pkg-other",
                provenance_lock_json=None,
                provenance_lock_sha256=None,
                support_verdict="unsupported",
                support_score=0.4,
                support_judge_run_id="judge-1",
                support_judgment_json={"status": "reported"},
                support_judgment_sha256="support-other",
            )
        ],
    )

    assert payload["expected_evidence_package_sha256"] == "pkg-expected"
    assert payload["export_package_hash_mismatch_count"] == 1
    assert payload["expected_claim_derivation_count"] == 2
    assert payload["stored_claim_derivation_count"] == 1
    assert payload["claim_derivation_count_matches"] is False
    assert payload["claim_derivation_hash_mismatch_count"] == 1
    assert payload["claim_package_hash_mismatch_count"] == 1
    assert payload["missing_claim_provenance_lock_count"] == 1
    assert payload["claim_provenance_lock_contract_mismatch_count"] == 1
    assert payload["claim_support_judgment_mismatch_count"] == 1
    assert payload["claim_support_judgment_contract_mismatch_count"] == 1
    assert payload["failed_claim_support_judgment_count"] == 1
    assert payload["missing_claim_derivation_count"] == 1
    assert payload["missing_claim_derivation_ids"] == ["claim-2"]


def test_technical_report_provenance_edges_cover_context_and_claim_links(monkeypatch) -> None:
    monkeypatch.setattr(
        provenance_owner,
        "_release_readiness_db_gate_trace_ref",
        lambda _audit: {"table": "technical_report_release_readiness_db_gates", "id": "gate-1"},
    )

    edges = evidence_semantic_trace._technical_report_provenance_edges(
        source_documents=[{"id": "doc-1", "sha256": "doc-sha"}],
        document_runs=[{"id": "run-1", "document_id": "doc-1"}],
        evidence_exports=[
            {
                "package_kind": "search_request",
                "search_request_id": "search-1",
                "evidence_package_export_id": "export-1",
            }
        ],
        evidence_cards=[
            {
                "evidence_card_id": "card-1",
                "source_evidence_package_export_ids": ["export-1"],
                "evidence_ids": ["assertion-evidence-1"],
            }
        ],
        claims=[
            {
                "claim_id": "claim-1",
                "provenance_lock_sha256": "lock-1",
                "derivation_sha256": "drv-1",
                "support_judgment_sha256": "support-1",
                "support_verdict": "supported",
                "support_score": 0.9,
                "support_judge_run_id": "judge-1",
                "source_search_request_result_ids": ["result-1"],
                "source_evidence_package_export_ids": ["export-1"],
                "semantic_ontology_snapshot_ids": ["ontology-1"],
                "semantic_graph_snapshot_ids": ["graph-1"],
                "retrieval_reranker_artifact_ids": ["reranker-1"],
                "search_harness_release_ids": ["release-1"],
                "release_audit_bundle_ids": ["bundle-1"],
                "release_validation_receipt_ids": ["receipt-1"],
                "evidence_card_ids": ["card-1"],
            }
        ],
        claim_derivations=[
            {
                "claim_id": "claim-1",
                "claim_evidence_derivation_id": "derivation-1",
                "derivation_sha256": "drv-1",
            }
        ],
        claim_retrieval_feedback=[
            {
                "feedback_id": "feedback-1",
                "claim_id": "claim-1",
                "feedback_payload_sha256": "feedback-sha",
                "source_payload_sha256": "source-sha",
                "release_readiness_db_gate_id": "gate-1",
                "source_search_request_ids": ["search-1"],
                "source_search_request_result_ids": ["result-1"],
                "search_request_result_span_ids": ["span-1"],
                "semantic_governance_event_id": "governance-1",
            }
        ],
        semantic_trace={
            "assertion_evidence": [
                {
                    "source_type": "chunk",
                    "chunk_id": "chunk-1",
                    "run_id": "run-1",
                    "evidence_id": "assertion-evidence-1",
                }
            ]
        },
        context_pack_audit={
            "harness_task_id": "task-1",
            "context_pack_artifacts": [{"artifact_id": "artifact-1"}],
            "evaluation_artifacts": [{"artifact_id": "eval-artifact-1", "task_id": "eval-task-1"}],
            "verifications": [
                {
                    "verification_id": "verification-1",
                    "verification_task_id": "verification-task-1",
                    "details": {"context_pack_sha256": "context-pack-sha"},
                }
            ],
            "operator_runs": [{"operator_run_id": "operator-run-1"}],
            "release_readiness_assessments": [
                {
                    "assessment_id": "assessment-1",
                    "search_harness_release_id": "release-1",
                    "assessment_payload_sha256": "assessment-sha",
                }
            ],
            "release_readiness_db_gate": {
                "verification_id": "verification-1",
                "complete": True,
            },
        },
    )

    edge_types = {edge["edge_type"] for edge in edges}

    assert {
        "harness_task_to_context_pack_artifact",
        "context_pack_verifier_record_to_release_readiness_db_gate",
        "search_request_to_evidence_package_export",
        "source_document_to_document_run",
        "document_run_to_source_record",
        "search_evidence_export_to_report_card",
        "semantic_evidence_to_report_card",
        "claim_to_provenance_lock",
        "claim_to_support_judgment",
        "support_judge_run_to_claim",
        "claim_to_derivation_hash",
        "claim_to_retrieval_feedback",
        "release_readiness_db_gate_to_claim_retrieval_feedback",
    }.issubset(edge_types)
    assert any(
        edge["edge_type"] == "context_pack_verifier_record_to_release_readiness_db_gate"
        and edge["complete"] is True
        for edge in edges
    )


def test_semantic_trace_facade_stays_narrow() -> None:
    with open(evidence_semantic_trace.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 600
