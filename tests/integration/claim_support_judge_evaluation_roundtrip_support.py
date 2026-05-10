from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import select, text

from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskStatus,
    AgentTaskVerification,
    ClaimEvidenceDerivation,
    ClaimSupportPolicyChangeImpact,
    EvidencePackageExport,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
    SemanticGovernanceEvent,
)
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.claim_support_policy_governance import (
    CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD,
    claim_support_policy_change_impact_payload_sha256,
)
from app.services.evidence import payload_sha256


def _process_next_task(postgres_integration_harness) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "claim-support-eval-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id

def _load_revision_0059():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0059_claim_support_policy_activation_governance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0059_claim_support_policy_governance",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0059 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _load_revision_0062():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0062_claim_support_impact_replay_governance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0062_claim_support_impact_replay_governance",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0062 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _enable_claim_support_governance_signing(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.claim_support_policy_governance.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="claim-support-secret",
            audit_bundle_signing_key_id="claim-support-key",
        ),
    )

def _seed_impacted_technical_report_records(session) -> dict[str, UUID | str]:
    now = utcnow()
    harness_task_id = uuid4()
    draft_task_id = uuid4()
    verify_task_id = uuid4()
    support_run_id = uuid4()
    export_id = uuid4()
    draft_artifact_id = uuid4()
    derivation_id = uuid4()
    support_judgment = {
        "schema_name": "technical_report_claim_support_judgment",
        "schema_version": "1.0",
        "judge_kind": "deterministic_v1",
        "claim_id": "claim-impact-1",
        "verdict": "supported",
        "support_score": 0.92,
        "min_support_score": 0.34,
        "evidence_card_ids": ["card-impact-1"],
        "resolved_evidence_card_ids": ["card-impact-1"],
        "graph_edge_ids": [],
        "resolved_graph_edge_ids": [],
        "source_search_request_result_ids": [str(uuid4())],
        "matched_claim_tokens": ["traceable", "evidence"],
        "matched_claim_token_count": 2,
        "claim_token_count": 2,
        "lexical_overlap_ratio": 1.0,
        "support_reasons": ["resolved_evidence_cards"],
        "unsupported_reasons": [],
        "provisional_rule": "integration fixture",
    }
    support_judgment_sha = payload_sha256(support_judgment)
    draft_payload = {
        "schema_name": "draft_technical_report_output",
        "schema_version": "1.0",
        "claims": [
            {
                "claim_id": "claim-impact-1",
                "rendered_text": "A traceable evidence claim.",
                "support_judge_run_id": str(support_run_id),
                "support_judgment_sha256": support_judgment_sha,
                "support_judgment": support_judgment,
            }
        ],
        "claim_support_summary": {
            "support_judge_run_id": str(support_run_id),
            "claims_with_support_judgment_count": 1,
            "supported_claim_count": 1,
        },
    }
    verification_payload = {
        "schema_name": "verify_technical_report_output",
        "schema_version": "1.0",
        "verification_outcome": "passed",
        "summary": {
            "claim_count": 1,
            "claims_with_support_judgment_count": 1,
        },
    }
    session.add_all(
        [
            AgentTask(
                id=harness_task_id,
                task_type="prepare_report_agent_harness",
                status=AgentTaskStatus.COMPLETED.value,
                side_effect_level="read_only",
                input_json={"target_task_id": str(uuid4())},
                result_json={"schema_name": "prepare_report_agent_harness_output"},
                workflow_version="claim_support_policy_impact_fixture",
                created_at=now,
                updated_at=now,
                completed_at=now,
            ),
            AgentTask(
                id=draft_task_id,
                task_type="draft_technical_report",
                status=AgentTaskStatus.COMPLETED.value,
                side_effect_level="draft_change",
                input_json={
                    "target_task_id": str(harness_task_id),
                    "generator_mode": "structured_fallback",
                },
                result_json=draft_payload,
                workflow_version="claim_support_policy_impact_fixture",
                created_at=now,
                updated_at=now,
                completed_at=now,
            ),
            AgentTask(
                id=verify_task_id,
                task_type="verify_technical_report",
                status=AgentTaskStatus.COMPLETED.value,
                side_effect_level="read_only",
                input_json={"target_task_id": str(draft_task_id)},
                result_json=verification_payload,
                workflow_version="claim_support_policy_impact_fixture",
                created_at=now,
                updated_at=now,
                completed_at=now,
            ),
        ]
    )
    session.flush()
    support_output = {
        "schema_name": "technical_report_claim_support_judgments",
        "claim_count": 1,
        "supported_claim_count": 1,
        "claim_judgments": [support_judgment],
    }
    session.add(
        KnowledgeOperatorRun(
            id=support_run_id,
            operator_kind="judge",
            operator_name="technical_report_claim_support_judge",
            operator_version="v1",
            status="completed",
            agent_task_id=draft_task_id,
            output_sha256=payload_sha256(support_output),
            metrics_json={"claim_count": 1, "supported_claim_count": 1},
            metadata_json={"fixture": "claim_support_policy_change_impact"},
            created_at=now,
            started_at=now,
            completed_at=now,
        )
    )
    session.add(
        AgentTaskArtifact(
            id=draft_artifact_id,
            task_id=draft_task_id,
            artifact_kind="technical_report_draft",
            storage_path=f"storage/agent_tasks/{draft_task_id}/technical_report_draft.json",
            payload_json=draft_payload,
            created_at=now,
        )
    )
    session.add(
        EvidencePackageExport(
            id=export_id,
            package_kind="technical_report_claims",
            search_request_id=None,
            agent_task_id=draft_task_id,
            agent_task_artifact_id=draft_artifact_id,
            package_sha256="impact-evidence-package-sha",
            trace_sha256="impact-trace-sha",
            package_payload_json={"claim_ids": ["claim-impact-1"]},
            source_snapshot_sha256s_json=["impact-source-snapshot-sha"],
            operator_run_ids_json=[str(support_run_id)],
            document_ids_json=[],
            run_ids_json=[],
            claim_ids_json=["claim-impact-1"],
            export_status="completed",
            created_at=now,
        )
    )
    session.flush()
    session.add(
        ClaimEvidenceDerivation(
            id=derivation_id,
            evidence_package_export_id=export_id,
            agent_task_id=draft_task_id,
            claim_id="claim-impact-1",
            claim_text="A traceable evidence claim.",
            derivation_rule="integration_fixture_supports_claim",
            evidence_card_ids_json=["card-impact-1"],
            graph_edge_ids_json=[],
            fact_ids_json=[],
            assertion_ids_json=[],
            source_document_ids_json=[],
            source_snapshot_sha256s_json=["impact-source-snapshot-sha"],
            source_search_request_ids_json=[],
            source_search_request_result_ids_json=[],
            source_evidence_package_export_ids_json=[str(export_id)],
            source_evidence_package_sha256s_json=["impact-evidence-package-sha"],
            source_evidence_trace_sha256s_json=["impact-trace-sha"],
            semantic_ontology_snapshot_ids_json=[],
            semantic_graph_snapshot_ids_json=[],
            retrieval_reranker_artifact_ids_json=[],
            search_harness_release_ids_json=[],
            release_audit_bundle_ids_json=[],
            release_validation_receipt_ids_json=[],
            provenance_lock_json={"claim_id": "claim-impact-1"},
            provenance_lock_sha256=payload_sha256({"claim_id": "claim-impact-1"}),
            support_verdict="supported",
            support_score=0.92,
            support_judge_run_id=support_run_id,
            support_judgment_json=support_judgment,
            support_judgment_sha256=support_judgment_sha,
            evidence_package_sha256="impact-evidence-package-sha",
            derivation_sha256="impact-derivation-sha",
            created_at=now,
        )
    )
    session.add(
        AgentTaskVerification(
            id=uuid4(),
            target_task_id=draft_task_id,
            verification_task_id=verify_task_id,
            verifier_type="technical_report_gate",
            outcome="passed",
            metrics_json={"claims_with_support_judgment_count": 1},
            reasons_json=[],
            details_json={"fixture": "claim_support_policy_change_impact"},
            created_at=now,
            completed_at=now,
        )
    )
    session.flush()
    return {
        "harness_task_id": harness_task_id,
        "draft_task_id": draft_task_id,
        "verify_task_id": verify_task_id,
        "support_run_id": support_run_id,
        "derivation_id": derivation_id,
        "support_judgment_sha256": support_judgment_sha,
    }

def _install_claim_support_governance_immutability_trigger(
    postgres_integration_harness,
    postgres_schema_engine,
) -> str:
    revision_0062 = _load_revision_0062()
    _engine, schema_name = postgres_schema_engine
    trigger_sql = """
    DROP TRIGGER IF EXISTS trg_agent_task_artifacts_prevent_frozen_prov_mutation
    ON agent_task_artifacts;
    CREATE TRIGGER trg_agent_task_artifacts_prevent_frozen_prov_mutation
    BEFORE UPDATE OR DELETE ON agent_task_artifacts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_frozen_agent_task_artifact_mutation();
    """
    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(text(revision_0062.PROTECTED_ARTIFACT_MUTATION_FUNCTION_SQL))
        session.execute(text(trigger_sql))
        session.commit()
    return schema_name

def _drop_claim_support_governance_immutability_trigger(
    postgres_integration_harness,
    schema_name: str,
) -> None:
    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(
            text(
                """
                DROP TRIGGER IF EXISTS trg_agent_task_artifacts_prevent_frozen_prov_mutation
                ON agent_task_artifacts;
                DROP FUNCTION IF EXISTS prevent_frozen_agent_task_artifact_mutation();
                """
            )
        )
        session.commit()

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

def _claim_support_change_impact_payload_without_replay(
    *,
    change_impact_id: UUID,
) -> dict:
    payload = {
        "schema_name": "claim_support_policy_change_impact",
        "schema_version": "1.0",
        "change_impact_id": str(change_impact_id),
        "impact_scope": "claim_support_policy:claim_support_judge_calibration_policy",
        "activation": {
            "reason": "no impacted prior support judgments",
        },
        "semantic_basis": {},
        "impact_summary": {
            "affected_support_judgment_count": 0,
            "affected_generated_document_count": 0,
            "affected_technical_report_verification_count": 0,
            "replay_recommended_count": 0,
        },
        "impact_reasons": [],
        "affected_ids": {
            "claim_derivation_ids": [],
            "draft_task_ids": [],
            "verification_task_ids": [],
        },
        "affected_support_judgments": [],
        "affected_generated_documents": {
            "draft_task_ids": [],
            "artifacts": [],
        },
        "affected_technical_report_verifications": [],
        "replay_recommendations": [],
        "integrity_inputs": {},
    }
    return {
        **payload,
        CLAIM_SUPPORT_POLICY_CHANGE_IMPACT_HASH_FIELD: (
            claim_support_policy_change_impact_payload_sha256(payload)
        ),
    }
