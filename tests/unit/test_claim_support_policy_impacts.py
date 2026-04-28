from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import ClaimEvidenceDerivation
from app.services.claim_support_policy_impacts import _candidate_from_derivation


def _derivation() -> ClaimEvidenceDerivation:
    export_id = uuid4()
    return ClaimEvidenceDerivation(
        id=uuid4(),
        evidence_package_export_id=export_id,
        agent_task_id=uuid4(),
        claim_id="claim-impact-1",
        claim_text="A traceable evidence claim.",
        derivation_rule="unit_fixture_supports_claim",
        evidence_card_ids_json=["card-impact-1"],
        graph_edge_ids_json=[],
        fact_ids_json=[],
        assertion_ids_json=[],
        source_document_ids_json=[],
        source_snapshot_sha256s_json=["source-snapshot-sha"],
        source_search_request_ids_json=[],
        source_search_request_result_ids_json=[],
        source_evidence_package_export_ids_json=[str(export_id)],
        source_evidence_package_sha256s_json=["evidence-package-sha"],
        source_evidence_trace_sha256s_json=["evidence-trace-sha"],
        semantic_ontology_snapshot_ids_json=[],
        semantic_graph_snapshot_ids_json=[],
        retrieval_reranker_artifact_ids_json=[],
        search_harness_release_ids_json=[],
        release_audit_bundle_ids_json=[],
        release_validation_receipt_ids_json=[],
        provenance_lock_json={"claim_id": "claim-impact-1"},
        provenance_lock_sha256="provenance-lock-sha",
        support_verdict="supported",
        support_score=0.92,
        support_judge_run_id=uuid4(),
        support_judgment_json={
            "verdict": "supported",
            "source_search_request_result_ids": [str(uuid4())],
        },
        support_judgment_sha256="support-judgment-sha",
        evidence_package_sha256="evidence-package-sha",
        derivation_sha256="derivation-sha",
        created_at=datetime(2026, 4, 28, tzinfo=UTC),
    )


def _alert_item(*, escalation_event_ids: list) -> SimpleNamespace:
    change_impact_id = uuid4()
    activation_task_id = uuid4()
    verification_task_id = uuid4()
    return SimpleNamespace(
        change_impact=SimpleNamespace(
            change_impact_id=change_impact_id,
            impact_payload_sha256="impact-payload-sha",
            activation_task_id=activation_task_id,
        ),
        alert_kind="blocked",
        severity="critical",
        replay_status="blocked",
        is_stale=False,
        affected_verification_task_ids=[verification_task_id],
        escalation_events=[
            SimpleNamespace(event_id=event_id) for event_id in escalation_event_ids
        ],
        latest_escalation_event_id=escalation_event_ids[-1]
        if escalation_event_ids
        else None,
    )


def test_replay_fixture_candidate_identity_survives_escalation_receipt_changes() -> None:
    derivation = _derivation()
    escalation_one = uuid4()
    escalation_two = uuid4()
    item_one = _alert_item(escalation_event_ids=[escalation_one])
    item_two = _alert_item(escalation_event_ids=[escalation_two, escalation_one])
    item_two.change_impact = item_one.change_impact
    item_two.affected_verification_task_ids = item_one.affected_verification_task_ids
    item_reordered = _alert_item(escalation_event_ids=[escalation_one, escalation_two])
    item_reordered.change_impact = item_one.change_impact
    item_reordered.affected_verification_task_ids = item_one.affected_verification_task_ids
    item_reordered.latest_escalation_event_id = item_two.latest_escalation_event_id

    candidate_one = _candidate_from_derivation(
        item_one,
        derivation=derivation,
        draft_task=None,
    )
    candidate_two = _candidate_from_derivation(
        item_two,
        derivation=derivation,
        draft_task=None,
    )
    candidate_reordered = _candidate_from_derivation(
        item_reordered,
        derivation=derivation,
        draft_task=None,
    )

    assert candidate_one.candidate_id == candidate_two.candidate_id
    assert candidate_two.candidate_id == (
        candidate_two.fixture["replay_alert_source"]["candidate_identity_sha256"]
    )
    assert candidate_one.source_payload_sha256 != candidate_two.source_payload_sha256
    assert candidate_two.source_payload_sha256 == candidate_reordered.source_payload_sha256
    assert candidate_two.fixture["replay_alert_source"]["draft_source"] == (
        "reconstructed_claim_derivation"
    )
    assert candidate_two.expected_verdict == "insufficient_evidence"
    assert candidate_two.fixture["draft_payload"]["warnings"]
