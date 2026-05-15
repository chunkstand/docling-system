from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.evidence_claim_feedback as evidence_claim_feedback
import app.services.evidence_claim_feedback_payloads as evidence_claim_feedback_payloads
from app.db.models import SearchRequestRecord, SearchRequestResult
from app.services import evidence

CLAIM_FEEDBACK_ROOT_ALIASES = {
    "_claim_feedback_retrieval_context": (
        evidence_claim_feedback_payloads,
        "_claim_feedback_retrieval_context",
    ),
    "_technical_report_claim_feedback_payloads": (
        evidence_claim_feedback_payloads,
        "_technical_report_claim_feedback_payloads",
    ),
    "_technical_report_claim_feedback_status": (
        evidence_claim_feedback_payloads,
        "_technical_report_claim_feedback_status",
    ),
}

CLAIM_FEEDBACK_EVIDENCE_ALIASES = {
    "_technical_report_claim_feedback_payloads": (
        evidence_claim_feedback_payloads,
        "_technical_report_claim_feedback_payloads",
    ),
    "_technical_report_claim_feedback_status": (
        evidence_claim_feedback_payloads,
        "_technical_report_claim_feedback_status",
    ),
    "technical_report_claim_feedback_payloads": (
        evidence_claim_feedback_payloads,
        "technical_report_claim_feedback_payloads",
    ),
    "technical_report_claim_feedback_status": (
        evidence_claim_feedback_payloads,
        "technical_report_claim_feedback_status",
    ),
}


def test_claim_feedback_facades_reexport_payload_owner_functions() -> None:
    for facade_name, (owner_module, owner_name) in CLAIM_FEEDBACK_ROOT_ALIASES.items():
        assert getattr(evidence_claim_feedback, facade_name) is getattr(
            owner_module,
            owner_name,
        )

    for facade_name, (owner_module, owner_name) in CLAIM_FEEDBACK_EVIDENCE_ALIASES.items():
        assert getattr(evidence, facade_name) is getattr(owner_module, owner_name)


def test_technical_report_claim_feedback_status_classifies_core_verdicts() -> None:
    assert evidence_claim_feedback_payloads._technical_report_claim_feedback_status(
        {"support_verdict": "supported", "support_score": 0.91}
    ) == ("supported", "positive", None)
    assert evidence_claim_feedback_payloads._technical_report_claim_feedback_status(
        {"support_verdict": "supported", "support_score": 0.2}
    ) == ("weak", "positive", None)
    assert evidence_claim_feedback_payloads._technical_report_claim_feedback_status(
        {"support_verdict": "insufficient_evidence"}
    ) == ("missing", "missing", "missing_expected")
    assert evidence_claim_feedback_payloads._technical_report_claim_feedback_status(
        {
            "support_verdict": "unsupported",
            "support_judgment": {
                "unsupported_reasons": ["evidence_contains_contradiction_cue"]
            },
        }
    ) == ("contradicted", "negative", "explicit_irrelevant")


def test_claim_feedback_retrieval_context_uses_primary_request_defaults() -> None:
    request_id = uuid4()
    table_id = uuid4()
    request_row = SimpleNamespace(
        id=request_id,
        origin="operator",
        query_text="forest plan standards",
        mode=None,
        filters_json=None,
        harness_name="table_harness",
        reranker_name="reranker-v1",
        reranker_version="1.0",
        retrieval_profile_name="default",
        harness_config_json=None,
        embedding_status="ready",
        candidate_count=3,
        result_count=1,
        table_hit_count=1,
        created_at=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
    )
    result_row = SimpleNamespace(
        id=uuid4(),
        search_request_id=request_id,
        rank=1,
        base_rank=1,
        result_type="table",
        document_id=uuid4(),
        run_id=uuid4(),
        chunk_id=None,
        table_id=table_id,
        score=0.92,
        keyword_score=0.17,
        semantic_score=0.88,
        hybrid_score=0.92,
        rerank_features_json=None,
        page_from=4,
        page_to=5,
        source_filename="forest-plan.pdf",
        label="Table 2",
        preview_text="Standard and guideline summary",
    )

    payload = evidence_claim_feedback_payloads._claim_feedback_retrieval_context(
        [request_row],
        [result_row],
    )

    assert payload["schema_name"] == "technical_report_claim_retrieval_context"
    assert payload["request_count"] == 1
    assert payload["result_count"] == 1
    assert payload["primary_mode"] == "hybrid"
    assert payload["primary_harness_name"] == "table_harness"
    assert payload["requests"][0]["filters"] == {}
    assert payload["results"][0]["table_id"] == str(table_id)


def test_claim_feedback_payloads_capture_status_edges_and_context(monkeypatch) -> None:
    verification_task_id = uuid4()
    supported_request_id = uuid4()
    supported_result_id = uuid4()
    contradicted_result_id = uuid4()
    gate_id = uuid4()
    derivation_id = uuid4()
    now = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
    request_row = SimpleNamespace(
        id=supported_request_id,
        origin="operator",
        query_text="forest plan standards",
        mode=None,
        filters_json=None,
        harness_name="table_harness",
        reranker_name="reranker-v1",
        reranker_version="1.0",
        retrieval_profile_name="default",
        harness_config_json={"top_k": 3},
        embedding_status="ready",
        candidate_count=3,
        result_count=2,
        table_hit_count=1,
        created_at=now,
    )
    supported_result = SimpleNamespace(
        id=supported_result_id,
        search_request_id=supported_request_id,
        rank=1,
        base_rank=1,
        result_type="table",
        document_id=uuid4(),
        run_id=uuid4(),
        chunk_id=None,
        table_id=uuid4(),
        score=0.92,
        keyword_score=0.17,
        semantic_score=0.88,
        hybrid_score=0.92,
        rerank_features_json={"coverage": 0.91},
        page_from=4,
        page_to=5,
        source_filename="forest-plan.pdf",
        label="Table 2",
        preview_text="Standard and guideline summary",
    )
    contradicted_result = SimpleNamespace(
        id=contradicted_result_id,
        search_request_id=supported_request_id,
        rank=2,
        base_rank=2,
        result_type="chunk",
        document_id=uuid4(),
        run_id=uuid4(),
        chunk_id=uuid4(),
        table_id=None,
        score=0.54,
        keyword_score=0.12,
        semantic_score=0.51,
        hybrid_score=0.54,
        rerank_features_json={"coverage": 0.42},
        page_from=7,
        page_to=7,
        source_filename="forest-plan.pdf",
        label="Section 4",
        preview_text="Contradictory paragraph",
    )
    spans_by_result_id = {
        supported_result_id: [
            SimpleNamespace(
                id=uuid4(),
                search_request_id=supported_request_id,
                search_request_result_id=supported_result_id,
                retrieval_evidence_span_id=uuid4(),
                span_rank=1,
                score_kind="hybrid",
                score=0.92,
                source_type="table",
                source_id=supported_result.table_id,
                span_index=0,
                page_from=4,
                page_to=5,
                text_excerpt="Standard A",
                content_sha256="excerpt-sha-1",
                source_snapshot_sha256="snapshot-sha-1",
                metadata_json={"section": "A"},
            )
        ],
        contradicted_result_id: [
            SimpleNamespace(
                id=uuid4(),
                search_request_id=supported_request_id,
                search_request_result_id=contradicted_result_id,
                retrieval_evidence_span_id=uuid4(),
                span_rank=1,
                score_kind="semantic",
                score=0.54,
                source_type="chunk",
                source_id=contradicted_result.chunk_id,
                span_index=0,
                page_from=7,
                page_to=7,
                text_excerpt="Contradiction cue",
                content_sha256="excerpt-sha-2",
                source_snapshot_sha256="snapshot-sha-2",
                metadata_json={"section": "B"},
            )
        ],
    }

    def _fake_select_by_ids(_session, model, ids):
        if model is SearchRequestResult:
            rows = {
                supported_result_id: supported_result,
                contradicted_result_id: contradicted_result,
            }
        elif model is SearchRequestRecord:
            rows = {supported_request_id: request_row}
        else:
            raise AssertionError(f"Unexpected model lookup: {model}")
        return {row_id: rows[row_id] for row_id in ids if row_id in rows}

    monkeypatch.setattr(
        evidence_claim_feedback_payloads,
        "_select_by_ids",
        _fake_select_by_ids,
    )
    monkeypatch.setattr(
        evidence_claim_feedback_payloads,
        "_search_request_result_spans_by_result_id",
        lambda _session, _ids: spans_by_result_id,
    )

    rows = evidence_claim_feedback_payloads._technical_report_claim_feedback_payloads(
        object(),
        verification_task_id=verification_task_id,
        draft_payload={
            "claims": [
                {
                    "claim_id": "claim:supported",
                    "rendered_text": "Supported claim",
                    "support_verdict": "supported",
                    "support_score": 0.91,
                    "support_judgment": {},
                    "source_search_request_ids": [str(supported_request_id)],
                    "source_search_request_result_ids": [str(supported_result_id)],
                    "semantic_ontology_snapshot_ids": ["ontology-1"],
                    "semantic_graph_snapshot_ids": ["graph-1"],
                    "retrieval_reranker_artifact_ids": ["reranker-1"],
                    "search_harness_release_ids": ["release-1"],
                    "release_audit_bundle_ids": ["bundle-1"],
                    "release_validation_receipt_ids": ["receipt-1"],
                },
                {
                    "claim_id": "claim:missing",
                    "rendered_text": "Missing claim",
                    "support_verdict": "insufficient_evidence",
                    "support_judgment": {},
                },
                {
                    "claim_id": "claim:contradicted",
                    "rendered_text": "Contradicted claim",
                    "support_verdict": "unsupported",
                    "support_judgment": {
                        "unsupported_reasons": [
                            "evidence_contains_contradiction_cue"
                        ]
                    },
                    "source_search_request_ids": [str(supported_request_id)],
                    "source_search_request_result_ids": [str(contradicted_result_id)],
                },
            ]
        },
        derivations=[
            SimpleNamespace(
                id=derivation_id,
                claim_id="claim:supported",
                derivation_sha256="derivation-sha",
            )
        ],
        release_readiness_db_gate=SimpleNamespace(
            id=gate_id,
            gate_payload_sha256="gate-payload-sha",
        ),
    )

    rows_by_claim_id = {row["claim_id"]: row for row in rows}

    assert rows_by_claim_id["claim:supported"]["feedback_status"] == "supported"
    assert rows_by_claim_id["claim:supported"]["learning_label"] == "positive"
    assert rows_by_claim_id["claim:supported"]["claim_evidence_derivation_id"] == derivation_id
    assert (
        rows_by_claim_id["claim:supported"]["retrieval_context_json"]["primary_mode"]
        == "hybrid"
    )
    assert (
        rows_by_claim_id["claim:supported"]["retrieval_context_json"]["requests"][0]["filters"]
        == {}
    )
    assert len(rows_by_claim_id["claim:supported"]["evidence_refs_json"]) == 1
    assert (
        rows_by_claim_id["claim:supported"]["source_payload_json"][
            "release_readiness_db_gate_id"
        ]
        == str(gate_id)
    )

    assert rows_by_claim_id["claim:missing"]["feedback_status"] == "missing"
    assert rows_by_claim_id["claim:missing"]["learning_label"] == "missing"
    assert (
        rows_by_claim_id["claim:missing"]["hard_negative_kind"] == "missing_expected"
    )
    assert rows_by_claim_id["claim:missing"]["retrieval_context_json"]["result_count"] == 0

    assert rows_by_claim_id["claim:contradicted"]["feedback_status"] == "contradicted"
    assert rows_by_claim_id["claim:contradicted"]["learning_label"] == "negative"
    assert (
        rows_by_claim_id["claim:contradicted"]["hard_negative_kind"]
        == "explicit_irrelevant"
    )
    assert len(rows_by_claim_id["claim:contradicted"]["evidence_refs_json"]) == 1


def test_set_claim_feedback_append_only_link_is_idempotent_and_rejects_drift() -> None:
    row = SimpleNamespace(id=uuid4(), evidence_manifest_id=None)
    first_value = uuid4()

    assert evidence_claim_feedback.set_claim_feedback_append_only_link(
        row,
        field_name="evidence_manifest_id",
        value=first_value,
    )
    assert row.evidence_manifest_id == first_value
    assert not evidence_claim_feedback.set_claim_feedback_append_only_link(
        row,
        field_name="evidence_manifest_id",
        value=first_value,
    )
    with pytest.raises(ValueError, match="append-only"):
        evidence_claim_feedback.set_claim_feedback_append_only_link(
            row,
            field_name="evidence_manifest_id",
            value=uuid4(),
        )
