from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.db.public.agent_tasks import (
    AgentTaskArtifact,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
)
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.evidence_common import payload_sha256


def _assert_claim_support_activation_governance(
    session,
    *,
    apply_payload: dict,
    activated_policy_id: UUID,
    previous_policy_id: UUID | None,
    verification_fixture_set_sha256: str,
    expected_mined_failure_count: int,
    expected_mined_failure_summary_sha256: str | None = None,
    expected_affected_support_judgment_count: int = 0,
    expected_affected_generated_document_count: int = 0,
    expected_affected_verification_count: int = 0,
    expected_impacted_draft_task_id: UUID | None = None,
    expected_impacted_verification_task_id: UUID | None = None,
    expected_impacted_derivation_id: UUID | None = None,
    expected_replay_alert_fixture_coverage_waiver_sha256: str | None = None,
) -> dict:
    assert (
        apply_payload["activation_governance_artifact_kind"]
        == "claim_support_policy_activation_governance"
    )
    assert apply_payload["activation_governance_artifact_id"]
    assert apply_payload["activation_governance_artifact_path"]
    assert apply_payload["activation_governance_payload_sha256"]
    assert apply_payload["activation_governance_receipt_sha256"]
    assert apply_payload["activation_governance_signature_status"] == "signed"
    assert apply_payload["activation_governance_prov_jsonld_sha256"]
    assert apply_payload["activation_governance_event_id"]
    assert apply_payload["activation_governance_event_hash"]
    assert apply_payload["activation_change_impact_id"]
    assert apply_payload["activation_change_impact_payload_sha256"]
    assert apply_payload["activation_change_impact_summary"]
    assert apply_payload["activation_change_impact_replay_recommended_count"] is not None

    governance_artifact = session.get(
        AgentTaskArtifact,
        UUID(apply_payload["activation_governance_artifact_id"]),
    )
    assert governance_artifact is not None
    assert governance_artifact.artifact_kind == "claim_support_policy_activation_governance"
    assert governance_artifact.storage_path == apply_payload["activation_governance_artifact_path"]

    governance_payload = governance_artifact.payload_json
    assert governance_payload["schema_name"] == "claim_support_policy_activation_governance"
    assert governance_payload["governance_profile"] == (
        "claim_support_policy_activation_governance_v1"
    )
    assert (
        governance_payload["activation_governance_payload_sha256"]
        == apply_payload["activation_governance_payload_sha256"]
    )
    assert governance_payload["policy_diff"]["activated_policy"]["policy_id"] == str(
        activated_policy_id
    )
    assert (
        governance_payload["policy_diff"]["activated_policy"]["policy_sha256"]
        == apply_payload["activated_policy_sha256"]
    )
    previous_snapshot = governance_payload["policy_diff"]["previous_active_policy"]
    if previous_policy_id is None:
        assert previous_snapshot is None
    else:
        assert previous_snapshot["policy_id"] == str(previous_policy_id)
        assert (
            previous_snapshot["policy_sha256"]
            == apply_payload["previous_active_policy_sha256"]
        )
    assert (
        governance_payload["verification"]["verification"]["verification_id"]
        == apply_payload["verification_id"]
    )
    assert (
        governance_payload["fixture_replay"]["fixture_set"]["fixture_set_sha256"]
        == verification_fixture_set_sha256
    )
    fixture_set_diff = governance_payload["fixture_replay"]["fixture_set_diff"]
    assert fixture_set_diff["fixture_set_sha256"] == verification_fixture_set_sha256
    assert fixture_set_diff["fixture_set_diff_sha256"]
    assert (
        fixture_set_diff["replay_composition"]["mined_failure_case_count"]
        == expected_mined_failure_count
    )
    mined_summary = governance_payload["fixture_replay"]["mined_failure_summary"]
    assert mined_summary["mined_failure_case_count"] == expected_mined_failure_count
    if expected_mined_failure_summary_sha256 is not None:
        assert mined_summary["summary_sha256"] == expected_mined_failure_summary_sha256
    replay_alert_coverage_waiver = governance_payload["fixture_replay"][
        "replay_alert_fixture_coverage_waiver"
    ]
    if expected_replay_alert_fixture_coverage_waiver_sha256 is None:
        assert replay_alert_coverage_waiver == {}
    else:
        assert (
            replay_alert_coverage_waiver["waiver_sha256"]
            == expected_replay_alert_fixture_coverage_waiver_sha256
        )
        assert (
            apply_payload["verification_replay_alert_fixture_coverage_waiver"][
                "waiver_sha256"
            ]
            == expected_replay_alert_fixture_coverage_waiver_sha256
        )

    change_impact = governance_payload["activation_change_impact"]
    impact_summary = change_impact["impact_summary"]
    assert change_impact["change_impact_id"] == apply_payload["activation_change_impact_id"]
    assert change_impact["source"] == {
        "source_table": "claim_support_policy_change_impacts",
        "source_id": apply_payload["activation_change_impact_id"],
    }
    assert (
        change_impact["activation_change_impact_payload_sha256"]
        == apply_payload["activation_change_impact_payload_sha256"]
    )
    impact_hash_basis = dict(change_impact)
    impact_hash_basis.pop("activation_change_impact_payload_sha256")
    assert payload_sha256(impact_hash_basis) == apply_payload[
        "activation_change_impact_payload_sha256"
    ]
    assert (
        apply_payload["activation_change_impact_summary"]["affected_support_judgment_count"]
        == expected_affected_support_judgment_count
    )
    assert (
        impact_summary["affected_support_judgment_count"]
        == expected_affected_support_judgment_count
    )
    assert (
        impact_summary["affected_generated_document_count"]
        == expected_affected_generated_document_count
    )
    assert (
        impact_summary["affected_technical_report_verification_count"]
        == expected_affected_verification_count
    )
    assert (
        apply_payload["activation_change_impact_replay_recommended_count"]
        == impact_summary["replay_recommended_count"]
    )
    assert "claim_support_calibration_policy_changed" in change_impact["impact_reasons"]
    if expected_impacted_derivation_id is not None:
        assert str(expected_impacted_derivation_id) in change_impact["affected_ids"][
            "claim_derivation_ids"
        ]
        assert any(
            row["claim_derivation_id"] == str(expected_impacted_derivation_id)
            for row in change_impact["affected_support_judgments"]
        )
    if expected_impacted_draft_task_id is not None:
        assert str(expected_impacted_draft_task_id) in change_impact["affected_ids"][
            "draft_task_ids"
        ]
        assert str(expected_impacted_draft_task_id) in change_impact[
            "affected_generated_documents"
        ]["draft_task_ids"]
    if expected_impacted_verification_task_id is not None:
        assert str(expected_impacted_verification_task_id) in change_impact["affected_ids"][
            "verification_task_ids"
        ]
        assert any(
            row["verification_task_id"] == str(expected_impacted_verification_task_id)
            for row in change_impact["affected_technical_report_verifications"]
        )

    receipt = governance_payload["activation_governance_receipt"]
    assert receipt["signature_status"] == "signed"
    assert receipt["signing_key_id"] == "claim-support-key"
    assert receipt["hash_chain_complete"] is True
    assert receipt["signed_payload_sha256"] == apply_payload[
        "activation_governance_payload_sha256"
    ]
    assert receipt["receipt_sha256"] == apply_payload["activation_governance_receipt_sha256"]
    assert any(
        item["name"] == "claim_support_policy_activation_governance"
        and item["sha256"] == apply_payload["activation_governance_payload_sha256"]
        for item in receipt["hash_chain"]
    )
    assert any(
        item["name"] == "verification_fixture_set_diff"
        and item["sha256"] == fixture_set_diff["fixture_set_diff_sha256"]
        for item in receipt["hash_chain"]
    )
    assert any(
        item["name"] == "policy_change_impact"
        and item["sha256"] == apply_payload["activation_change_impact_payload_sha256"]
        for item in receipt["hash_chain"]
    )

    assert governance_payload["integrity"]["complete"] is True
    assert governance_payload["integrity"]["signature_present"] is True
    assert (
        governance_payload["integrity"]["prov_jsonld_sha256"]
        == apply_payload["activation_governance_prov_jsonld_sha256"]
    )
    prov_jsonld = governance_payload["prov_jsonld"]
    assert prov_jsonld["@context"]["prov"] == "http://www.w3.org/ns/prov#"
    graph_ids = {node["@id"] for node in prov_jsonld["@graph"]}
    assert f"docling:claim_support_calibration_policy:{activated_policy_id}" in graph_ids
    assert f"docling:agent_task_artifact:{apply_payload['artifact_id']}" in graph_ids
    assert (
        f"docling:agent_task_artifact:{apply_payload['activation_governance_artifact_id']}"
        in graph_ids
    )
    assert (
        "docling:claim_support_policy_change_impact:"
        f"{apply_payload['activation_change_impact_id']}"
        in graph_ids
    )
    activation_activity = next(
        node
        for node in prov_jsonld["@graph"]
        if node["@id"]
        == f"docling:activity:claim_support_policy_activation:{governance_artifact.task_id}"
    )
    assert activation_activity["prov:endedAtTime"]

    governance_event = session.get(
        SemanticGovernanceEvent,
        UUID(apply_payload["activation_governance_event_id"]),
    )
    assert governance_event is not None
    assert governance_event.event_kind == "claim_support_policy_activated"
    assert governance_event.governance_scope == (
        "claim_support_policy:claim_support_judge_calibration_policy"
    )
    assert governance_event.subject_table == "claim_support_calibration_policies"
    assert governance_event.subject_id == activated_policy_id
    assert governance_event.task_id == governance_artifact.task_id
    assert governance_event.agent_task_artifact_id == governance_artifact.id
    assert governance_event.receipt_sha256 == apply_payload[
        "activation_governance_receipt_sha256"
    ]
    assert governance_event.event_hash == apply_payload["activation_governance_event_hash"]
    event_activation = governance_event.event_payload_json["claim_support_policy_activation"]
    assert event_activation["artifact_id"] == str(governance_artifact.id)
    assert event_activation["activated_policy_id"] == str(activated_policy_id)
    assert event_activation["activated_policy_sha256"] == apply_payload[
        "activated_policy_sha256"
    ]
    assert event_activation["receipt_sha256"] == apply_payload[
        "activation_governance_receipt_sha256"
    ]
    assert event_activation["signature_status"] == "signed"
    assert (
        event_activation["verification_fixture_set_diff_sha256"]
        == fixture_set_diff["fixture_set_diff_sha256"]
    )
    assert (
        event_activation["activation_governance_payload_sha256"]
        == apply_payload["activation_governance_payload_sha256"]
    )
    assert (
        event_activation["activation_change_impact_payload_sha256"]
        == apply_payload["activation_change_impact_payload_sha256"]
    )
    assert (
        event_activation["activation_change_impact_id"]
        == apply_payload["activation_change_impact_id"]
    )
    assert (
        event_activation["affected_support_judgment_count"]
        == expected_affected_support_judgment_count
    )
    impact_row = session.get(
        ClaimSupportPolicyChangeImpact,
        UUID(apply_payload["activation_change_impact_id"]),
    )
    assert impact_row is not None
    assert str(impact_row.id) == change_impact["change_impact_id"]
    assert impact_row.activation_task_id == governance_artifact.task_id
    assert impact_row.activated_policy_id == activated_policy_id
    assert impact_row.previous_policy_id == previous_policy_id
    assert impact_row.semantic_governance_event_id == governance_event.id
    assert impact_row.governance_artifact_id == governance_artifact.id
    assert impact_row.impact_payload_sha256 == apply_payload[
        "activation_change_impact_payload_sha256"
    ]
    assert (
        impact_row.affected_support_judgment_count
        == expected_affected_support_judgment_count
    )
    assert (
        impact_row.affected_generated_document_count
        == expected_affected_generated_document_count
    )
    assert impact_row.affected_verification_count == expected_affected_verification_count
    assert impact_row.impact_payload_json["impact_summary"] == impact_summary
    assert (
        impact_row.impact_payload_json["change_impact_id"]
        == apply_payload["activation_change_impact_id"]
    )
    if expected_impacted_derivation_id is not None:
        assert str(expected_impacted_derivation_id) in (
            impact_row.impacted_claim_derivation_ids_json
        )
    if expected_impacted_draft_task_id is not None:
        assert str(expected_impacted_draft_task_id) in impact_row.impacted_task_ids_json
    if expected_impacted_verification_task_id is not None:
        assert str(expected_impacted_verification_task_id) in (
            impact_row.impacted_verification_task_ids_json
        )
    operator_run = session.get(KnowledgeOperatorRun, UUID(apply_payload["operator_run_id"]))
    assert operator_run is not None
    assert operator_run.output_sha256 == payload_sha256(apply_payload)
    assert operator_run.metrics_json["activation_governance_artifact_id"] == str(
        governance_artifact.id
    )
    assert operator_run.metrics_json["activation_change_impact_id"] == str(impact_row.id)
    operator_output = session.scalar(
        select(KnowledgeOperatorOutput).where(
            KnowledgeOperatorOutput.operator_run_id == operator_run.id,
            KnowledgeOperatorOutput.output_kind
            == "claim_support_calibration_policy_activation",
        )
    )
    assert operator_output is not None
    assert operator_output.artifact_path == governance_artifact.storage_path
    assert (
        operator_output.artifact_sha256
        == apply_payload["activation_governance_payload_sha256"]
    )
    assert operator_output.payload_json["activation_governance_artifact_id"] == str(
        governance_artifact.id
    )
    assert operator_output.payload_json["activation_change_impact_id"] == str(
        impact_row.id
    )
    return governance_payload
