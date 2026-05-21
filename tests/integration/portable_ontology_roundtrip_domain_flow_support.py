from __future__ import annotations

from uuid import UUID

from app.db.public.agent_tasks import AgentTask, AgentTaskStatus
from tests.integration.portable_ontology_roundtrip_support import (
    StubParser,
    approve_workflow_task,
    bootstrap_portable_ontology_env,
    build_parsed_document,
    create_document_upload,
    create_workflow_task,
    process_document_run,
    process_next_task,
)


def run_domain_agnostic_roundtrip(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
    *,
    title: str,
    source_filename: str,
    phrase: str,
    expected_concept_key: str,
) -> None:
    bootstrap_portable_ontology_env(monkeypatch, tmp_path, set_registry_path=False)
    workflow_version = "portable_ontology_integration"
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        initialize_task_id = create_workflow_task(
            session,
            task_type="initialize_workspace_ontology",
            input={},
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        initialize_task_row = session.get(AgentTask, initialize_task_id)
        assert initialize_task_row is not None
        initialize_payload = initialize_task_row.result_json["payload"]
        assert initialize_payload["snapshot"]["ontology_version"] == "portable-upper-ontology-v1"
        assert initialize_payload["snapshot"]["concept_count"] == 0
        assert any(
            metric["metric_key"] == "portable_bootstrap" and metric["passed"]
            for metric in initialize_payload["success_metrics"]
        )

        snapshot_task_id = create_workflow_task(
            session,
            task_type="get_active_ontology_snapshot",
            input={},
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        snapshot_task_row = session.get(AgentTask, snapshot_task_id)
        assert snapshot_task_row is not None
        snapshot_payload = snapshot_task_row.result_json["payload"]
        assert snapshot_payload["snapshot"]["relation_keys"] == [
            "claim_supported_by_evidence",
            "concept_related_to_concept",
            "document_cites_source",
            "document_mentions_concept",
            "event_occurs_before_event",
            "evidence_cites_source",
            "measurement_has_unit",
            "obligation_applies_to_actor",
            "table_reports_measurement",
        ]

    document_id, run_id = create_document_upload(client, source_filename=source_filename)

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(build_parsed_document(title=title, phrase=phrase))
    )
    assert processed_run_id == run_id

    initial_semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert initial_semantics_response.status_code == 200
    initial_semantics = initial_semantics_response.json()
    assert initial_semantics["assertion_count"] == 0
    assert initial_semantics["ontology_snapshot_id"] is not None
    assert initial_semantics["upper_ontology_version"] == "portable-upper-ontology-v1"
    status_response = client.get("/semantics/backfill/status")
    assert status_response.status_code == 200
    status = status_response.json()
    assert status["current_registry"]["ontology_contract"]["report_semantics_ready"] is True
    assert (
        status["current_registry"]["ontology_contract"]["missing_report_semantics_relation_keys"]
        == []
    )
    assert "claim_supported_by_evidence" in status["current_registry"]["ontology_contract"][
        "report_semantics_relation_keys"
    ]

    with postgres_integration_harness.session_factory() as session:
        discover_task_id = create_workflow_task(
            session,
            task_type="discover_semantic_bootstrap_candidates",
            input={
                "document_ids": [str(document_id)],
                "max_candidates": 8,
                "min_document_count": 1,
                "min_source_count": 2,
                "min_phrase_tokens": 2,
                "max_phrase_tokens": 4,
                "exclude_existing_registry_terms": True,
            },
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        discover_task_row = session.get(AgentTask, discover_task_id)
        assert discover_task_row is not None
        discover_payload = discover_task_row.result_json["payload"]
        report = discover_payload["report"]
        candidate = next(
            row for row in report["candidates"] if row["concept_key"] == expected_concept_key
        )
        candidate_id = candidate["candidate_id"]
        assert any(
            metric["metric_key"] == "bitter_lesson_alignment" and metric["passed"]
            for metric in report["success_metrics"]
        )

        draft_task_id = create_workflow_task(
            session,
            task_type="draft_ontology_extension",
            input={
                "source_task_id": str(discover_task_id),
                "candidate_ids": [candidate_id],
                "rationale": "extend the workspace ontology from corpus evidence",
            },
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        assert draft_payload["proposed_ontology_version"] == "portable-upper-ontology-v1.1"
        assert draft_payload["operations"][0]["concept_key"] == expected_concept_key

        verify_task_id = create_workflow_task(
            session,
            task_type="verify_draft_ontology_extension",
            input={
                "target_task_id": str(draft_task_id),
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
        assert any(
            metric["metric_key"] == "semantic_value_gain" and metric["passed"]
            for metric in verify_payload["success_metrics"]
        )

        apply_task_id = create_workflow_task(
            session,
            task_type="apply_ontology_extension",
            input={
                "draft_task_id": str(draft_task_id),
                "verification_task_id": str(verify_task_id),
                "reason": "publish the verified ontology extension",
            },
            workflow_version=workflow_version,
        )

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        assert apply_task_row.status == AgentTaskStatus.AWAITING_APPROVAL.value
        approve_workflow_task(
            session,
            apply_task_id,
            approval_note="publish the verified ontology extension",
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        apply_payload = apply_task_row.result_json["payload"]
        assert apply_payload["applied_ontology_version"] == "portable-upper-ontology-v1.1"
        assert any(
            metric["metric_key"] == "semantic_contract_published" and metric["passed"]
            for metric in apply_payload["success_metrics"]
        )

        reprocess_task_id = create_workflow_task(
            session,
            task_type="enqueue_document_reprocess",
            input={
                "document_id": str(document_id),
                "source_task_id": str(apply_task_id),
                "reason": "refresh the document under the new ontology snapshot",
            },
            workflow_version=workflow_version,
        )
        approve_workflow_task(
            session,
            reprocess_task_id,
            approval_note="refresh semantics under the new ontology snapshot",
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        reprocess_task_row = session.get(AgentTask, reprocess_task_id)
        assert reprocess_task_row is not None
        latest_run_id = UUID(reprocess_task_row.result_json["payload"]["reprocess"]["run_id"])

    rerun_id = process_document_run(postgres_integration_harness, title=title, phrase=phrase)
    assert rerun_id == latest_run_id

    final_semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert final_semantics_response.status_code == 200
    final_semantics = final_semantics_response.json()
    assert final_semantics["run_id"] == str(latest_run_id)
    assert final_semantics["registry_version"] == "portable-upper-ontology-v1.1"
    assert final_semantics["assertion_count"] >= 1
    assertion = next(
        row for row in final_semantics["assertions"] if row["concept_key"] == expected_concept_key
    )

    assertion_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{assertion['assertion_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Approve the corpus-derived concept before fact generation.",
            "reviewed_by": "ontology-operator@example.com",
        },
    )
    assert assertion_review_response.status_code == 200

    with postgres_integration_harness.session_factory() as session:
        fact_task_id = create_workflow_task(
            session,
            task_type="build_document_fact_graph",
            input={
                "document_id": str(document_id),
                "minimum_review_status": "approved",
            },
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        fact_task_row = session.get(AgentTask, fact_task_id)
        assert fact_task_row is not None
        fact_payload = fact_task_row.result_json["payload"]
        assert fact_payload["fact_count"] >= 1
        assert any(
            metric["metric_key"] == "semantic_integrity" and metric["passed"]
            for metric in fact_payload["success_metrics"]
        )

        brief_task_id = create_workflow_task(
            session,
            task_type="prepare_semantic_generation_brief",
            input={
                "title": f"{title} Brief",
                "goal": f"Summarize the knowledge base guidance on {phrase}.",
                "audience": "Operators",
                "document_ids": [str(document_id)],
                "concept_keys": [expected_concept_key],
                "target_length": "medium",
                "review_policy": "approved_only",
            },
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        brief_task_row = session.get(AgentTask, brief_task_id)
        assert brief_task_row is not None
        brief_payload = brief_task_row.result_json["payload"]["brief"]
        assert brief_payload["claim_candidates"][0]["fact_ids"]
        assert brief_payload["semantic_dossier"][0]["facts"]
        assert any(
            metric["metric_key"] == "approved_fact_support_ratio" and metric["passed"]
            for metric in brief_payload["success_metrics"]
        )

        grounded_draft_task_id = create_workflow_task(
            session,
            task_type="draft_semantic_grounded_document",
            input={"target_task_id": str(brief_task_id)},
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        grounded_draft_task_row = session.get(AgentTask, grounded_draft_task_id)
        assert grounded_draft_task_row is not None
        grounded_draft_payload = grounded_draft_task_row.result_json["payload"]["draft"]
        assert grounded_draft_payload["fact_index"]
        assert grounded_draft_payload["claims"][0]["fact_ids"]

        grounded_verify_task_id = create_workflow_task(
            session,
            task_type="verify_semantic_grounded_document",
            input={
                "target_task_id": str(grounded_draft_task_id),
                "max_unsupported_claim_count": 0,
                "require_full_claim_traceability": True,
                "require_full_concept_coverage": True,
            },
            workflow_version=workflow_version,
        )

    process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        grounded_verify_task_row = session.get(AgentTask, grounded_verify_task_id)
        assert grounded_verify_task_row is not None
        grounded_verify_payload = grounded_verify_task_row.result_json["payload"]
        assert grounded_verify_payload["verification"]["outcome"] == "passed"
        assert grounded_verify_payload["summary"]["fact_ref_coverage_ratio"] == 1.0
        assert grounded_verify_payload["summary"]["required_concept_coverage_ratio"] == 1.0
        assert any(
            metric["metric_key"] == "semantic_integrity" and metric["passed"]
            for metric in grounded_verify_payload["success_metrics"]
        )
