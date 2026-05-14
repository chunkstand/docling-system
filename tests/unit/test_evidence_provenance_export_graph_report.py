from __future__ import annotations

from uuid import uuid4

from app.services.evidence_provenance import prov_identifier
from app.services.evidence_provenance_export_graph_core import (
    ProvenanceGraphContext,
    ProvenanceGraphState,
)
from app.services.evidence_provenance_export_graph_report import populate_report_graph


def test_populate_report_graph_adds_claim_lineage_and_operator_runs() -> None:
    claim_id = str(uuid4())
    feedback_id = str(uuid4())
    result_id = str(uuid4())
    operator_run_id = str(uuid4())
    verification_activity_id = prov_identifier("agent_tasks", str(uuid4()))
    context = ProvenanceGraphContext(
        manifest={"provenance_edges": []},
        trace={},
        report_trace={
            "evidence_cards": [
                {
                    "evidence_card_id": str(uuid4()),
                    "evidence_kind": "claim_support",
                    "source_type": "chunk",
                    "source_evidence_match_status": "matched",
                }
            ],
            "claims": [
                {
                    "claim_id": claim_id,
                    "rendered_text": "The cited evidence supports the claim.",
                    "source_evidence_match_status": "matched",
                }
            ],
            "claim_retrieval_feedback": [
                {
                    "feedback_id": feedback_id,
                    "claim_id": claim_id,
                    "support_verdict": "supported",
                    "support_score": 0.9,
                    "feedback_status": "supported",
                    "learning_label": "positive",
                    "hard_negative_kind": None,
                    "feedback_payload_sha256": "feedback-sha",
                    "source_payload_sha256": "source-sha",
                    "source_search_request_result_ids": [result_id],
                }
            ],
            "claim_derivations": [
                {
                    "claim_evidence_derivation_id": str(uuid4()),
                    "claim_id": claim_id,
                    "derivation_sha256": "derivation-sha",
                }
            ],
            "operator_runs": [
                {
                    "operator_run_id": operator_run_id,
                    "operator_kind": "retrieval",
                    "operator_name": "retriever",
                    "operator_version": "v1",
                    "status": "completed",
                    "config_sha256": "config-sha",
                    "input_sha256": "input-sha",
                    "output_sha256": "output-sha",
                    "created_at": "2026-05-13T00:00:00Z",
                }
            ],
        },
        retrieval_evaluation={},
        context_pack_audit={},
        release_readiness_db_gate={},
        release_readiness_db_gate_record={},
        release_readiness_db_gate_entity_id=None,
        manifest_entity_id=None,
        trace_entity_id=None,
        harness_activity_id=None,
        verification_activity_id=verification_activity_id,
    )
    state = ProvenanceGraphState.new()

    populate_report_graph(state, context)

    feedback_entity_id = prov_identifier(
        "technical_report_claim_retrieval_feedback",
        feedback_id,
    )
    assert feedback_entity_id in state.entities
    assert prov_identifier("knowledge_operator_runs", operator_run_id) in state.activities
    assert any(
        relation.get("docling:edge_type") == "claim_to_retrieval_feedback"
        for relation in state.was_derived_from.values()
    )
    assert any(
        relation.get("docling:edge_type") == "search_result_to_claim_retrieval_feedback"
        for relation in state.was_derived_from.values()
    )
