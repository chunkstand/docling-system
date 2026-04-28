from __future__ import annotations

import importlib.util
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select, text, update

from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    AgentTaskStatus,
    AgentTaskVerification,
    ClaimEvidenceDerivation,
    ClaimSupportCalibrationPolicy,
    ClaimSupportEvaluation,
    ClaimSupportEvaluationCase,
    ClaimSupportFixtureSet,
    ClaimSupportPolicyChangeImpact,
    EvidencePackageExport,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
    SemanticGovernanceEvent,
)
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.claim_support_evaluations import (
    build_claim_support_calibration_policy_payload,
    default_claim_support_evaluation_fixtures,
    draft_claim_support_calibration_policy,
    ensure_claim_support_calibration_policy,
    resolve_claim_support_calibration_policy,
)
from app.services.evidence import payload_sha256

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


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
                id=draft_task_id,
                task_type="draft_technical_report",
                status=AgentTaskStatus.COMPLETED.value,
                side_effect_level="draft_change",
                input_json={"target_task_id": str(uuid4())},
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
    revision_0059 = _load_revision_0059()
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
        session.execute(text(revision_0059.PROTECTED_ARTIFACT_MUTATION_FUNCTION_SQL))
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


def test_claim_support_judge_evaluation_task_persists_replay_rows(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_calibration",
                    "fixture_set_name": "default_claim_support_v1",
                    "min_support_score": 0.34,
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                },
                workflow_version="claim_support_judge_eval_integration",
            ),
        )
        task_id = task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_row = session.get(AgentTask, task_id)
        assert task_row is not None
        payload = task_row.result_json["payload"]
        evaluation_id = UUID(payload["evaluation_id"])
        assert payload["summary"]["gate_outcome"] == "passed"
        assert payload["summary"]["overall_accuracy"] == 1.0
        assert payload["fixture_set_sha256"]
        assert payload["fixture_set_id"]
        assert payload["fixture_set_version"] == "v1"
        assert payload["policy_id"]
        assert payload["policy_name"] == "claim_support_judge_calibration_policy"
        assert payload["policy_version"] == "v1"
        assert payload["policy_sha256"]
        assert payload["operator_run_id"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.agent_task_id == task_id
        assert str(evaluation_row.operator_run_id) == payload["operator_run_id"]
        assert str(evaluation_row.fixture_set_id) == payload["fixture_set_id"]
        assert str(evaluation_row.policy_id) == payload["policy_id"]
        assert evaluation_row.gate_outcome == "passed"
        assert evaluation_row.fixture_set_version == "v1"
        assert evaluation_row.fixture_set_sha256 == payload["fixture_set_sha256"]
        assert evaluation_row.policy_sha256 == payload["policy_sha256"]
        assert evaluation_row.evaluation_payload_sha256 == payload_sha256(
            evaluation_row.evaluation_payload_json
        )
        fixture_set_row = session.get(ClaimSupportFixtureSet, UUID(payload["fixture_set_id"]))
        policy_row = session.get(ClaimSupportCalibrationPolicy, UUID(payload["policy_id"]))
        assert fixture_set_row is not None
        assert fixture_set_row.fixture_set_sha256 == payload["fixture_set_sha256"]
        assert policy_row is not None
        assert policy_row.policy_sha256 == payload["policy_sha256"]

        case_rows = list(
            session.scalars(
                select(ClaimSupportEvaluationCase)
                .where(ClaimSupportEvaluationCase.evaluation_id == evaluation_id)
                .order_by(ClaimSupportEvaluationCase.case_index.asc())
            )
        )
        assert len(case_rows) == payload["summary"]["case_count"]
        assert all(row.passed for row in case_rows)
        assert {row.expected_verdict for row in case_rows} == {
            "supported",
            "unsupported",
            "insufficient_evidence",
        }
        assert any(row.hard_case_kind == "lexical_overlap_wrong_evidence" for row in case_rows)
        assert all(row.support_judgment_json for row in case_rows)

        operator_run = session.get(KnowledgeOperatorRun, UUID(payload["operator_run_id"]))
        assert operator_run is not None
        assert operator_run.operator_kind == "judge"
        assert operator_run.operator_name == "technical_report_claim_support_judge_evaluation"
        assert operator_run.metrics_json["policy_sha256"] == payload["policy_sha256"]
        assert operator_run.output_sha256

        artifacts = list(
            session.scalars(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == task_id,
                    AgentTaskArtifact.artifact_kind == "claim_support_judge_evaluation",
                )
            )
        )
        assert len(artifacts) == 1
        assert artifacts[0].payload_json["evaluation_id"] == str(evaluation_id)


def test_claim_support_judge_evaluation_task_fails_single_fixture_coverage_gate(
    postgres_integration_harness,
):
    fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    fixture["case_id"] = "single_fixture_coverage_gap"

    with postgres_integration_harness.session_factory() as session:
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_coverage_gap",
                    "fixture_set_name": "single_fixture_coverage_gap",
                    "fixtures": [fixture],
                    "min_support_score": 0.34,
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                },
                workflow_version="claim_support_judge_eval_coverage_gap_integration",
            ),
        )
        task_id = task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_row = session.get(AgentTask, task_id)
        assert task_row is not None
        assert task_row.status == "completed"
        payload = task_row.result_json["payload"]
        evaluation_id = UUID(payload["evaluation_id"])
        assert payload["summary"]["gate_outcome"] == "failed"
        assert payload["summary"]["overall_accuracy"] == 1.0
        assert payload["summary"]["failed_case_count"] == 0
        assert payload["summary"]["hard_case_kind_count"] == 1
        assert "Support-judge quality satisfies the governed hard-case policy." in payload[
            "reasons"
        ]
        assert payload["fixture_set_id"]
        assert payload["policy_id"]
        assert payload["policy_sha256"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.gate_outcome == "failed"
        assert str(evaluation_row.fixture_set_id) == payload["fixture_set_id"]
        assert str(evaluation_row.policy_id) == payload["policy_id"]
        assert evaluation_row.metrics_json["gate_outcome"] == "failed"
        assert evaluation_row.metrics_json["policy_sha256"] == payload["policy_sha256"]
        assert evaluation_row.reasons_json == payload["reasons"]

        operator_run = session.get(KnowledgeOperatorRun, UUID(payload["operator_run_id"]))
        assert operator_run is not None
        assert operator_run.metrics_json["gate_outcome"] == "failed"

        operator_output = session.scalar(
            select(KnowledgeOperatorOutput).where(
                KnowledgeOperatorOutput.operator_run_id == operator_run.id,
                KnowledgeOperatorOutput.output_kind == "claim_support_judge_evaluation",
            )
        )
        assert operator_output is not None
        assert operator_output.payload_json["gate_outcome"] == "failed"
        assert operator_output.payload_json["policy_sha256"] == payload["policy_sha256"]


def test_claim_support_judge_evaluation_task_uses_persisted_custom_policy(
    postgres_integration_harness,
):
    fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    fixture["case_id"] = "custom_policy_missing_kind"
    policy_payload = build_claim_support_calibration_policy_payload(
        policy_name="strict_claim_support_policy",
        policy_version="v1",
        min_hard_case_kind_count=1,
        required_hard_case_kinds=["required_kind_not_in_fixture"],
        required_verdicts=["supported"],
        source="integration_test",
    )

    with postgres_integration_harness.session_factory() as session:
        policy_row = ensure_claim_support_calibration_policy(
            session,
            policy_payload=policy_payload,
        )
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_custom_policy",
                    "fixture_set_name": "custom_policy_fixture_set",
                    "fixture_set_version": "v1",
                    "policy_name": "strict_claim_support_policy",
                    "policy_version": "v1",
                    "fixtures": [fixture],
                    "min_support_score": 0.34,
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                },
                workflow_version="claim_support_judge_eval_custom_policy_integration",
            ),
        )
        policy_id = policy_row.id
        task_id = task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_row = session.get(AgentTask, task_id)
        assert task_row is not None
        payload = task_row.result_json["payload"]
        evaluation_id = UUID(payload["evaluation_id"])
        assert payload["summary"]["gate_outcome"] == "failed"
        assert payload["summary"]["overall_accuracy"] == 1.0
        assert payload["summary"]["missing_hard_case_kinds"] == [
            "required_kind_not_in_fixture"
        ]
        assert payload["policy_id"] == str(policy_id)
        assert payload["policy_sha256"] == policy_payload["policy_sha256"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.gate_outcome == "failed"
        assert evaluation_row.policy_id == policy_id
        assert evaluation_row.policy_name == "strict_claim_support_policy"
        assert evaluation_row.policy_sha256 == policy_payload["policy_sha256"]


def test_claim_support_policy_promotion_workflow_activates_verified_policy(
    postgres_integration_harness,
    postgres_schema_engine,
    monkeypatch,
):
    _enable_claim_support_governance_signing(monkeypatch)

    with postgres_integration_harness.session_factory() as session:
        initial_policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v2",
                    "rationale": "promote a focused one-kind calibration policy for integration",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_promotion_integration",
            ),
        )
        initial_policy_id = initial_policy.id
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_payload = draft_row.result_json["payload"]
        draft_policy_id = UUID(draft_payload["policy_id"])
        draft_policy = session.get(ClaimSupportCalibrationPolicy, draft_policy_id)
        assert draft_policy is not None
        assert draft_policy.status == "draft"
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "active"

        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_promotion_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        assert verify_payload["verification"]["outcome"] == "passed"
        assert verify_payload["evaluation"]["policy_id"] == str(draft_policy_id)
        assert verify_payload["mined_failure_summary"]["mined_failure_case_count"] == 0
        verification_id = verify_payload["verification"]["verification_id"]
        verification_fixture_set_id = verify_payload["evaluation"]["fixture_set_id"]
        verification_fixture_set_sha256 = verify_payload["evaluation"]["fixture_set_sha256"]
        verification_policy_sha256 = verify_payload["evaluation"]["policy_sha256"]

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "activate the verified focused calibration policy",
                },
                workflow_version="claim_support_policy_promotion_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.AWAITING_APPROVAL.value
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="verified policy may become active",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        apply_payload = apply_row.result_json["payload"]
        assert apply_payload["activated_policy_id"] == str(draft_policy_id)
        assert apply_payload["previous_active_policy_id"] == str(initial_policy_id)
        assert apply_payload["approved_by"] == "claim-support-operator@example.com"
        assert apply_payload["approved_at"]
        assert apply_payload["approval_note"] == "verified policy may become active"
        assert apply_payload["verification_id"] == verification_id
        assert apply_payload["verification_outcome"] == "passed"
        assert apply_payload["verification_reasons"] == []
        assert apply_payload["verification_fixture_set_id"] == verification_fixture_set_id
        assert apply_payload["verification_fixture_set_sha256"] == verification_fixture_set_sha256
        assert apply_payload["verification_policy_sha256"] == verification_policy_sha256
        assert apply_payload["draft_policy_sha256"] == verification_policy_sha256
        assert apply_payload["verification_mined_failure_summary"][
            "mined_failure_case_count"
        ] == 0
        assert apply_payload["operator_run_id"]
        _assert_claim_support_activation_governance(
            session,
            apply_payload=apply_payload,
            activated_policy_id=draft_policy_id,
            previous_policy_id=initial_policy_id,
            verification_fixture_set_sha256=verification_fixture_set_sha256,
            expected_mined_failure_count=0,
        )
        governance_artifact_id = UUID(apply_payload["activation_governance_artifact_id"])

        initial_policy = session.get(ClaimSupportCalibrationPolicy, initial_policy_id)
        activated_policy = session.get(ClaimSupportCalibrationPolicy, draft_policy_id)
        assert initial_policy is not None
        assert initial_policy.status == "retired"
        assert activated_policy is not None
        assert activated_policy.status == "active"

        active_policies = list(
            session.scalars(
                select(ClaimSupportCalibrationPolicy).where(
                    ClaimSupportCalibrationPolicy.policy_name
                    == "claim_support_judge_calibration_policy",
                    ClaimSupportCalibrationPolicy.status == "active",
                )
            )
        )
        assert [row.id for row in active_policies] == [draft_policy_id]

    schema_name = _install_claim_support_governance_immutability_trigger(
        postgres_integration_harness,
        postgres_schema_engine,
    )
    try:
        with postgres_integration_harness.session_factory() as session:
            session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
            session.execute(
                update(AgentTaskArtifact)
                .where(AgentTaskArtifact.id == governance_artifact_id)
                .values(payload_json={"tampered": True})
            )
            session.commit()

        with postgres_integration_harness.session_factory() as session:
            governance_artifact = session.get(AgentTaskArtifact, governance_artifact_id)
            assert governance_artifact is not None
            assert (
                governance_artifact.payload_json["schema_name"]
                == "claim_support_policy_activation_governance"
            )
            mutation_events = list(
                session.scalars(
                    select(AgentTaskArtifactImmutabilityEvent).where(
                        AgentTaskArtifactImmutabilityEvent.artifact_id
                        == governance_artifact_id
                    )
                )
            )
            assert len(mutation_events) == 1
            assert mutation_events[0].event_kind == "mutation_blocked"
            assert mutation_events[0].mutation_operation == "UPDATE"
            assert mutation_events[0].attempted_payload_sha256 is None

        with postgres_integration_harness.session_factory() as session:
            session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
            session.execute(
                delete(AgentTaskArtifact).where(AgentTaskArtifact.id == governance_artifact_id)
            )
            session.commit()

        with postgres_integration_harness.session_factory() as session:
            assert session.get(AgentTaskArtifact, governance_artifact_id) is not None
            mutation_events = list(
                session.scalars(
                    select(AgentTaskArtifactImmutabilityEvent)
                    .where(
                        AgentTaskArtifactImmutabilityEvent.artifact_id
                        == governance_artifact_id
                    )
                    .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
                )
            )
            assert [row.mutation_operation for row in mutation_events] == ["UPDATE", "DELETE"]
    finally:
        _drop_claim_support_governance_immutability_trigger(
            postgres_integration_harness,
            schema_name,
        )

    with postgres_integration_harness.session_factory() as session:
        eval_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_active_policy_check",
                    "fixture_set_name": "active_policy_fixture_set",
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_promotion_integration",
            ),
        )
        eval_task_id = eval_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        eval_row = session.get(AgentTask, eval_task_id)
        assert eval_row is not None
        eval_payload = eval_row.result_json["payload"]
        assert eval_payload["summary"]["gate_outcome"] == "passed"
        assert eval_payload["policy_id"] == str(draft_policy_id)
        assert eval_payload["policy_version"] == "v2"


def test_claim_support_policy_activation_records_change_impact_for_prior_reports(
    postgres_integration_harness,
    monkeypatch,
):
    _enable_claim_support_governance_signing(monkeypatch)

    with postgres_integration_harness.session_factory() as session:
        initial_policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        impacted = _seed_impacted_technical_report_records(session)
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_change_impact",
                    "rationale": "prove policy activation identifies stale report support gates",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_change_impact_integration",
            ),
        )
        initial_policy_id = initial_policy.id
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_policy_id = UUID(draft_row.result_json["payload"]["policy_id"])
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_change_impact_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        assert verify_payload["verification"]["outcome"] == "passed"
        verification_fixture_set_sha256 = verify_payload["evaluation"][
            "fixture_set_sha256"
        ]
        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "activate policy and enumerate downstream report impact",
                },
                workflow_version="claim_support_policy_change_impact_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="impact analysis required before relying on prior reports",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.COMPLETED.value
        apply_payload = apply_row.result_json["payload"]
        governance_payload = _assert_claim_support_activation_governance(
            session,
            apply_payload=apply_payload,
            activated_policy_id=draft_policy_id,
            previous_policy_id=initial_policy_id,
            verification_fixture_set_sha256=verification_fixture_set_sha256,
            expected_mined_failure_count=0,
            expected_affected_support_judgment_count=1,
            expected_affected_generated_document_count=1,
            expected_affected_verification_count=1,
            expected_impacted_draft_task_id=impacted["draft_task_id"],
            expected_impacted_verification_task_id=impacted["verify_task_id"],
            expected_impacted_derivation_id=impacted["derivation_id"],
        )
        change_impact = governance_payload["activation_change_impact"]
        assert change_impact["affected_support_judgments"][0][
            "support_judgment_sha256"
        ] == impacted["support_judgment_sha256"]
        assert {
            row["action"] for row in change_impact["replay_recommendations"]
        } == {"rerun_draft_technical_report", "rerun_verify_technical_report"}
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "retired"
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "active"


def test_claim_support_policy_verification_replays_mined_failed_cases(
    postgres_integration_harness,
):
    failure_fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    failure_fixture["case_id"] = "mined_claim_support_failure"
    failure_fixture["description"] = "Persisted failure should become future policy evidence."
    failure_fixture["hard_case_kind"] = "mined_failed_claim_support_case"
    failure_fixture["expected_verdict"] = "unsupported"

    with postgres_integration_harness.session_factory() as session:
        source_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_mined_failure_source",
                    "fixture_set_name": "mined_failure_source_fixture_set",
                    "fixtures": [failure_fixture],
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["mined_failed_claim_support_case"],
                    "required_verdicts": ["unsupported"],
                },
                workflow_version="claim_support_policy_mined_failure_integration",
            ),
        )
        source_task_id = source_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        source_row = session.get(AgentTask, source_task_id)
        assert source_row is not None
        source_payload = source_row.result_json["payload"]
        source_evaluation_id = source_payload["evaluation_id"]
        source_fixture_set_id = source_payload["fixture_set_id"]
        source_fixture_set_sha256 = source_payload["fixture_set_sha256"]
        assert source_payload["summary"]["gate_outcome"] == "failed"
        assert source_payload["summary"]["failed_case_count"] == 1

        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_mined_failures",
                    "rationale": "prove mined support-judge failures join verification evidence",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_mined_failure_integration",
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixture_set_name": "mined_failure_policy_verification",
                    "fixture_set_version": "v1",
                    "include_mined_failures": True,
                    "mined_failure_limit": 5,
                },
                workflow_version="claim_support_policy_mined_failure_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        mined_summary = verify_payload["mined_failure_summary"]
        mined_source = mined_summary["sources"][0]

        assert verify_payload["verification"]["outcome"] == "failed"
        assert verify_payload["evaluation"]["summary"]["failed_case_count"] == 1
        assert verify_payload["evaluation"]["summary"]["case_count"] == (
            len(default_claim_support_evaluation_fixtures()) + 1
        )
        assert mined_summary["enabled"] is True
        assert mined_summary["default_fixture_count"] == len(
            default_claim_support_evaluation_fixtures()
        )
        assert mined_summary["explicit_fixture_count"] == 0
        assert mined_summary["mined_failure_case_count"] == 1
        assert mined_summary["combined_fixture_count"] == (
            len(default_claim_support_evaluation_fixtures()) + 1
        )
        assert mined_summary["manifest_sha256"]
        assert mined_summary["summary_sha256"]
        assert mined_source["source_evaluation_id"] == source_evaluation_id
        assert (
            mined_source["source_evaluation_name"]
            == "claim_support_judge_mined_failure_source"
        )
        assert mined_source["source_gate_outcome"] == "failed"
        assert mined_source["source_agent_task_id"] == str(source_task_id)
        assert mined_source["source_operator_run_id"] == source_payload["operator_run_id"]
        assert mined_source["source_case_id"] == "mined_claim_support_failure"
        assert mined_source["case_index"] == 0
        assert mined_source["source_fixture_set_id"] == source_fixture_set_id
        assert mined_source["source_fixture_set_name"] == "mined_failure_source_fixture_set"
        assert mined_source["source_fixture_set_version"] == "v1"
        assert mined_source["source_fixture_set_sha256"] == source_fixture_set_sha256
        assert mined_source["source_policy_name"] == "claim_support_judge_calibration_policy"
        assert mined_source["source_policy_version"]
        assert mined_source["source_fixture_sha256"]


def test_claim_support_policy_activation_carries_remediated_mined_failures(
    postgres_integration_harness,
    monkeypatch,
):
    _enable_claim_support_governance_signing(monkeypatch)

    failure_fixture = deepcopy(default_claim_support_evaluation_fixtures()[1])
    failure_fixture["case_id"] = "mined_remediated_claim_support_failure"
    failure_fixture["description"] = (
        "A prior high-threshold support failure should replay and pass after remediation."
    )
    failure_fixture["hard_case_kind"] = "mined_remediated_claim_support_case"

    with postgres_integration_harness.session_factory() as session:
        source_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_mined_remediation_source",
                    "fixture_set_name": "mined_remediation_source_fixture_set",
                    "fixtures": [failure_fixture],
                    "min_support_score": 0.99,
                },
                workflow_version="claim_support_policy_mined_remediation_integration",
            ),
        )
        source_task_id = source_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        source_row = session.get(AgentTask, source_task_id)
        assert source_row is not None
        source_payload = source_row.result_json["payload"]
        assert source_payload["summary"]["gate_outcome"] == "failed"
        assert source_payload["summary"]["failed_case_count"] == 1
        assert source_payload["case_results"][0]["expected_verdict"] == "supported"
        assert source_payload["case_results"][0]["predicted_verdict"] == "unsupported"
        initial_policy_id = UUID(source_payload["policy_id"])

        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_mined_remediated",
                    "rationale": "prove remediated mined failures gate activation auditably",
                    "min_support_score": 0.34,
                },
                workflow_version="claim_support_policy_mined_remediation_integration",
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_policy_id = UUID(draft_row.result_json["payload"]["policy_id"])
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixture_set_name": "mined_remediated_policy_verification",
                    "fixture_set_version": "v1",
                    "include_mined_failures": True,
                    "mined_failure_limit": 5,
                },
                workflow_version="claim_support_policy_mined_remediation_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        mined_summary = verify_payload["mined_failure_summary"]
        mined_source = mined_summary["sources"][0]
        assert verify_payload["verification"]["outcome"] == "passed"
        assert verify_payload["evaluation"]["summary"]["gate_outcome"] == "passed"
        assert verify_payload["evaluation"]["summary"]["case_count"] == (
            len(default_claim_support_evaluation_fixtures()) + 1
        )
        verification_fixture_set_sha256 = verify_payload["evaluation"]["fixture_set_sha256"]
        assert mined_summary["mined_failure_case_count"] == 1
        assert mined_summary["summary_sha256"]
        assert mined_source["source_case_id"] == "mined_remediated_claim_support_failure"
        assert (
            mined_source["source_evaluation_name"]
            == "claim_support_judge_mined_remediation_source"
        )
        assert mined_source["source_agent_task_id"] == str(source_task_id)

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "activate remediated mined-failure calibration policy",
                },
                workflow_version="claim_support_policy_mined_remediation_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="verification replayed and remediated mined failures",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.COMPLETED.value
        apply_payload = apply_row.result_json["payload"]
        assert apply_payload["activated_policy_id"] == str(draft_policy_id)
        assert apply_payload["previous_active_policy_id"] == str(initial_policy_id)
        verification_mined_summary = apply_payload["verification_mined_failure_summary"]
        assert verification_mined_summary["mined_failure_case_count"] == 1
        assert verification_mined_summary["summary_sha256"] == mined_summary["summary_sha256"]
        assert verification_mined_summary["manifest_sha256"] == mined_summary["manifest_sha256"]
        assert apply_payload["success_metrics"][0]["details"][
            "mined_failure_summary_sha256"
        ] == mined_summary["summary_sha256"]
        _assert_claim_support_activation_governance(
            session,
            apply_payload=apply_payload,
            activated_policy_id=draft_policy_id,
            previous_policy_id=initial_policy_id,
            verification_fixture_set_sha256=verification_fixture_set_sha256,
            expected_mined_failure_count=1,
            expected_mined_failure_summary_sha256=mined_summary["summary_sha256"],
        )
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "retired"
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "active"


def test_claim_support_policy_apply_blocks_stale_draft_after_verification(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        initial_policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_stale",
                    "rationale": "prove stale draft policy rows cannot be activated",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_stale_apply_integration",
            ),
        )
        initial_policy_id = initial_policy.id
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_policy_id = UUID(draft_row.result_json["payload"]["policy_id"])
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_stale_apply_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_policy = session.get(ClaimSupportCalibrationPolicy, draft_policy_id)
        assert draft_policy is not None
        draft_policy.policy_payload_json = {
            **dict(draft_policy.policy_payload_json or {}),
            "metadata": {"tampered_after_verification": True},
        }
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "stale draft rows must not activate",
                },
                workflow_version="claim_support_policy_stale_apply_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="exercise stale draft guard",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.FAILED.value
        assert "Draft policy payload no longer matches" in str(apply_row.error_message)
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "active"
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "draft"


def test_claim_support_policy_promotion_blocks_failed_verification(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_bad",
                    "rationale": "prove failed verification blocks activation",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["nonexistent_hard_case_kind"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_failed_promotion_integration",
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_failed_promotion_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        assert verify_row.result_json["payload"]["verification"]["outcome"] == "failed"

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "this failed verification must not activate",
                },
                workflow_version="claim_support_policy_failed_promotion_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="exercise failed promotion guard",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.FAILED.value
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_policy = session.get(
            ClaimSupportCalibrationPolicy,
            UUID(draft_row.result_json["payload"]["policy_id"]),
        )
        assert draft_policy is not None
        assert draft_policy.status == "draft"


def test_claim_support_active_policy_resolution_rejects_retired_identity(
    postgres_integration_harness,
):
    policy_payload = build_claim_support_calibration_policy_payload()

    with postgres_integration_harness.session_factory() as session:
        policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=policy_payload,
        )
        policy.status = "retired"
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        with pytest.raises(ValueError, match="status retired"):
            ensure_claim_support_calibration_policy(
                session,
                policy_payload=policy_payload,
            )
        with pytest.raises(ValueError, match="status retired"):
            resolve_claim_support_calibration_policy(session)


def test_claim_support_policy_draft_rejects_retired_identity(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        draft_policy = draft_claim_support_calibration_policy(
            session,
            policy_name="claim_support_judge_calibration_policy",
            policy_version="v_retired_redraft",
            thresholds={
                "min_overall_accuracy": 1.0,
                "min_verdict_precision": 1.0,
                "min_verdict_recall": 1.0,
                "min_support_score": 0.34,
            },
            min_hard_case_kind_count=1,
            required_hard_case_kinds=["exact_source_support"],
            required_verdicts=["supported"],
            owner="integration-test",
            source="integration_test",
            rationale="prove retired policy identities cannot be redrafted",
        )
        draft_policy.status = "retired"
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        with pytest.raises(ValueError, match="cannot be redrafted"):
            draft_claim_support_calibration_policy(
                session,
                policy_name="claim_support_judge_calibration_policy",
                policy_version="v_retired_redraft",
                thresholds={
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                    "min_support_score": 0.34,
                },
                min_hard_case_kind_count=1,
                required_hard_case_kinds=["exact_source_support"],
                required_verdicts=["supported"],
                owner="integration-test",
                source="integration_test",
                rationale="prove retired policy identities cannot be redrafted",
            )


def test_claim_support_judge_evaluation_task_persists_failed_gate(
    postgres_integration_harness,
):
    fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    fixture["case_id"] = "forced_claim_support_regression"
    fixture["description"] = "Intentional mismatch proves failed gates persist audit evidence."
    fixture["hard_case_kind"] = "forced_gate_failure"
    fixture["expected_verdict"] = "unsupported"

    with postgres_integration_harness.session_factory() as session:
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_forced_failure",
                    "fixture_set_name": "forced_failure_fixture_set",
                    "fixtures": [fixture],
                    "min_support_score": 0.34,
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                },
                workflow_version="claim_support_judge_eval_failure_integration",
            ),
        )
        task_id = task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_row = session.get(AgentTask, task_id)
        assert task_row is not None
        assert task_row.status == "completed"
        payload = task_row.result_json["payload"]
        evaluation_id = UUID(payload["evaluation_id"])
        assert payload["summary"]["gate_outcome"] == "failed"
        assert payload["summary"]["failed_case_count"] == 1
        assert payload["reasons"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.agent_task_id == task_id
        assert evaluation_row.status == "completed"
        assert evaluation_row.gate_outcome == "failed"
        assert evaluation_row.reasons_json == payload["reasons"]
        assert evaluation_row.evaluation_payload_sha256 == payload_sha256(
            evaluation_row.evaluation_payload_json
        )

        case_rows = list(
            session.scalars(
                select(ClaimSupportEvaluationCase)
                .where(ClaimSupportEvaluationCase.evaluation_id == evaluation_id)
                .order_by(ClaimSupportEvaluationCase.case_index.asc())
            )
        )
        assert len(case_rows) == 1
        assert case_rows[0].case_id == "forced_claim_support_regression"
        assert case_rows[0].hard_case_kind == "forced_gate_failure"
        assert case_rows[0].passed is False
        assert case_rows[0].expected_verdict == "unsupported"
        assert case_rows[0].predicted_verdict == "supported"
        assert case_rows[0].failure_reasons_json == ["expected_unsupported_got_supported"]

        operator_run = session.get(KnowledgeOperatorRun, UUID(payload["operator_run_id"]))
        assert operator_run is not None
        assert operator_run.metrics_json["gate_outcome"] == "failed"

        artifacts = list(
            session.scalars(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == task_id,
                    AgentTaskArtifact.artifact_kind == "claim_support_judge_evaluation",
                )
            )
        )
        assert len(artifacts) == 1
        assert artifacts[0].payload_json["summary"]["gate_outcome"] == "failed"
