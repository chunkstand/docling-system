from __future__ import annotations

from uuid import UUID

from app.db.public.agent_tasks import AgentTask
from app.services.semantic_registry_operation_contracts import (
    SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION,
)
from tests.integration.portable_ontology_roundtrip_support import (
    approve_workflow_task,
    bootstrap_portable_ontology_env,
    create_document_upload,
    create_workflow_task,
    process_document_run,
    process_next_task,
    seed_workspace_ontology_snapshot,
)


def run_manual_lifecycle_draft_roundtrip(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    bootstrap_portable_ontology_env(monkeypatch, tmp_path, set_registry_path=True)
    seed_workspace_ontology_snapshot(
        postgres_integration_harness,
        concepts=[
            {
                "concept_key": "legacy_control",
                "preferred_label": "Legacy Control",
                "aliases": ["legacy governance control"],
            },
            {
                "concept_key": "governance_control",
                "preferred_label": "Governance Control",
            },
        ],
    )

    workflow_version = "portable_ontology_lifecycle_contract"
    with postgres_integration_harness.session_factory() as session:
        draft_task_id = create_workflow_task(
            session,
            task_type="draft_ontology_extension",
            input={
                "rationale": "replace the legacy concept with the governed successor",
                "operations": [
                    {
                        "operation_id": "replace:legacy_control:governance_control",
                        "operation_type": "replace_concept",
                        "concept_key": "legacy_control",
                        "successor_concepts": [{"concept_key": "governance_control"}],
                    }
                ],
            },
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        assert draft_payload.get("source_task_id") is None
        assert draft_payload.get("source_task_type") is None
        assert (
            draft_payload["operation_contract_version"]
            == SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION
        )
        assert draft_payload["operations"][0]["operation_type"] == "replace_concept"
        assert draft_payload["operations"][0]["successor_concepts"][0]["concept_key"] == (
            "governance_control"
        )
        concepts_by_key = {
            concept["concept_key"]: concept
            for concept in draft_payload["effective_ontology"]["concepts"]
        }
        assert concepts_by_key["legacy_control"]["lifecycle_status"] == "replaced"
        assert concepts_by_key["legacy_control"]["successor_concept_keys"] == [
            "governance_control"
        ]
        assert concepts_by_key["governance_control"]["predecessor_concept_keys"] == [
            "legacy_control"
        ]
        assert "Legacy Control" in concepts_by_key["governance_control"]["aliases"]


def run_manual_lifecycle_verification_and_apply_roundtrip(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    bootstrap_portable_ontology_env(monkeypatch, tmp_path, set_registry_path=True)
    seed_workspace_ontology_snapshot(
        postgres_integration_harness,
        concepts=[
            {
                "concept_key": "legacy_control",
                "preferred_label": "Legacy Control",
                "aliases": ["legacy control"],
            },
            {
                "concept_key": "governance_control",
                "preferred_label": "Governance Control",
            },
        ],
    )

    workflow_version = "portable_ontology_lifecycle_preview_contract"
    client = postgres_integration_harness.client
    document_id, run_id = create_document_upload(client, source_filename="legacy-control.pdf")

    processed_run_id = process_document_run(
        postgres_integration_harness,
        title="Legacy Control Memo",
        phrase="legacy control",
    )
    assert processed_run_id == run_id
    expected_lifecycle_version = "portable-upper-ontology-v1.seeded.1"

    initial_semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert initial_semantics_response.status_code == 200
    initial_semantics = initial_semantics_response.json()
    assert initial_semantics["assertion_count"] == 1
    assert initial_semantics["assertions"][0]["concept_key"] == "legacy_control"

    with postgres_integration_harness.session_factory() as session:
        draft_task_id = create_workflow_task(
            session,
            task_type="draft_ontology_extension",
            input={
                "rationale": "replace the legacy concept with the governed successor",
                "operations": [
                    {
                        "operation_id": "replace:legacy_control:governance_control",
                        "operation_type": "replace_concept",
                        "concept_key": "legacy_control",
                        "successor_concepts": [{"concept_key": "governance_control"}],
                    }
                ],
            },
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task_id = create_workflow_task(
            session,
            task_type="verify_draft_ontology_extension",
            input={
                "target_task_id": str(draft_task_id),
                "document_ids": [str(document_id)],
                "max_regressed_document_count": 0,
                "max_failed_expectation_increase": 0,
                "min_improved_document_count": 1,
            },
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        verify_payload = verify_task_row.result_json["payload"]
        assert verify_payload["verification"]["outcome"] == "passed"
        assert verify_payload["summary"]["lifecycle_preview_required"] is True
        assert verify_payload["summary"]["lifecycle_preview_evidence_complete"] is True
        lifecycle_preview = verify_payload["lifecycle_preview"]
        assert lifecycle_preview["required"] is True
        assert lifecycle_preview["evidence_complete"] is True
        assert lifecycle_preview["operations_with_preview_count"] == 1
        assert lifecycle_preview["operations_without_preview_count"] == 0
        preview_signal = lifecycle_preview["operations"][0]["preview_signals"][0]
        assert preview_signal["document_id"] == str(document_id)
        assert preview_signal["added_successor_concept_keys"] == ["governance_control"]
        assert (
            verify_payload["verification"]["details"]["lifecycle_preview"]["evidence_complete"]
            is True
        )

        apply_task_id = create_workflow_task(
            session,
            task_type="apply_ontology_extension",
            input={
                "draft_task_id": str(draft_task_id),
                "verification_task_id": str(verify_task_id),
                "reason": "publish the verified lifecycle ontology extension",
            },
            workflow_version=workflow_version,
        )
        approve_workflow_task(
            session,
            apply_task_id,
            approval_note="publish the verified lifecycle ontology extension",
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        apply_payload = apply_task_row.result_json["payload"]
        assert apply_payload["applied_ontology_version"] == expected_lifecycle_version
        assert apply_payload["verification_summary"]["lifecycle_preview_required"] is True
        assert apply_payload["lifecycle_preview"]["evidence_complete"] is True
        assert any(
            metric["metric_key"] == "lifecycle_preview_preserved" and metric["passed"]
            for metric in apply_payload["success_metrics"]
        )

        reprocess_task_id = create_workflow_task(
            session,
            task_type="enqueue_document_reprocess",
            input={
                "document_id": str(document_id),
                "source_task_id": str(apply_task_id),
                "reason": "refresh the document under the lifecycle-updated ontology",
            },
            workflow_version=workflow_version,
        )
        approve_workflow_task(
            session,
            reprocess_task_id,
            approval_note="refresh semantics under the lifecycle-updated ontology",
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        reprocess_task_row = session.get(AgentTask, reprocess_task_id)
        assert reprocess_task_row is not None
        latest_run_id = UUID(reprocess_task_row.result_json["payload"]["reprocess"]["run_id"])

    rerun_id = process_document_run(
        postgres_integration_harness,
        title="Legacy Control Memo",
        phrase="legacy control",
    )
    assert rerun_id == latest_run_id

    final_semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert final_semantics_response.status_code == 200
    final_semantics = final_semantics_response.json()
    assert final_semantics["run_id"] == str(latest_run_id)
    assert final_semantics["registry_version"] == expected_lifecycle_version
    assert any(
        assertion["concept_key"] == "governance_control"
        for assertion in final_semantics["assertions"]
    )
