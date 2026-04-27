from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskAttempt,
    AgentTaskDependency,
    AgentTaskDependencyKind,
    AgentTaskStatus,
    AgentTaskVerification,
    Document,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    SearchHarnessEvaluation,
    SearchHarnessRelease,
)
from app.schemas.agent_tasks import (
    AgentTaskApprovalRequest,
    AgentTaskCreateRequest,
    AgentTaskRejectionRequest,
)
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task, reject_agent_task
from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedFigure,
    ParsedTable,
    ParsedTableSegment,
)
from tests.integration.pdf_fixtures import valid_test_pdf_bytes

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


class StubParser:
    def __init__(self, parsed_document: ParsedDocument) -> None:
        self.parsed_document = parsed_document

    def parse_pdf(self, source_path, *, source_filename=None) -> ParsedDocument:
        assert source_path.exists()
        assert source_filename
        return self.parsed_document


def _build_parsed_document(*, title: str | None = "Integration Report") -> ParsedDocument:
    chunk_text = "Integration threshold guidance keeps active retrieval grounded."
    table_rows = [
        ["Tier", "Threshold"],
        ["alpha", "integration threshold"],
    ]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title="Integration Threshold Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        metadata={
            "caption": "Integration Threshold Matrix",
            "title_hint": None,
            "segment_label": "table",
            "title_source": "caption",
            "header_rows_retained": 1,
            "header_rows_removed": 0,
            "source_artifact_sha256": "segment-sha",
        },
    )
    table = ParsedTable(
        table_index=0,
        title="Integration Threshold Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        search_text="Integration Threshold Matrix integration threshold alpha",
        preview_text="Tier | Threshold\nalpha | integration threshold",
        metadata={
            "is_merged": False,
            "source_segment_count": 1,
            "segment_count": 1,
            "merge_reason": "single_segment",
            "merge_confidence": 1.0,
            "continuation_candidate": False,
            "ambiguous_continuation_candidate": False,
            "repeated_header_rows_removed": False,
            "header_rows_removed_count": 0,
            "title_resolution_source": "caption",
            "merge_sanity_passed": True,
            "header_removal_passed": True,
            "source_segment_indices": [0],
            "source_titles": ["Integration Threshold Matrix"],
        },
        segments=[segment],
    )
    figure = ParsedFigure(
        figure_index=0,
        source_figure_ref="figure-0",
        caption="Integration system diagram",
        heading="Section 1",
        page_from=1,
        page_to=1,
        confidence=0.99,
        metadata={
            "caption_resolution_source": "explicit_ref",
            "caption_candidates": ["Integration system diagram"],
            "caption_attachment_confidence": 1.0,
            "source_confidence": 0.99,
            "annotations": [],
            "provenance": [
                {
                    "page_no": 1,
                    "bbox": {"l": 0, "t": 0, "r": 1, "b": 1, "coord_origin": "TOPLEFT"},
                    "charspan": [0, 1],
                }
            ],
            "source_artifact_sha256": "figure-sha",
        },
    )
    exported_payload = {
        "name": title,
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [{"self_ref": "figure-0", "captions": ["caption-0"], "prov": []}],
    }
    return ParsedDocument(
        title=title,
        page_count=1,
        yaml_text="document: integration-report\n",
        docling_json=json.dumps(exported_payload, indent=2),
        chunks=[
            ParsedChunk(
                chunk_index=0,
                text=chunk_text,
                heading="Section 1",
                page_from=1,
                page_to=1,
                metadata={"label": "text"},
            )
        ],
        tables=[table],
        raw_table_segments=[segment],
        figures=[figure],
    )


def _create_processed_document(postgres_integration_harness) -> tuple[UUID, UUID]:
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = UUID(create_response.json()["document_id"])
    run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == run_id

    with postgres_integration_harness.session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        assert document.active_run_id == run_id
        assert document.latest_run_id == run_id

        evaluation = (
            session.execute(
                select(DocumentRunEvaluation)
                .where(DocumentRunEvaluation.run_id == run_id)
                .order_by(DocumentRunEvaluation.created_at.desc())
            )
            .scalars()
            .first()
        )
        assert evaluation is not None
        assert evaluation.status == "completed"

        query_rows = (
            session.execute(
                select(DocumentRunEvaluationQuery).where(
                    DocumentRunEvaluationQuery.evaluation_id == evaluation.id
                )
            )
            .scalars()
            .all()
        )
        assert query_rows

    return document_id, run_id


def test_triage_replay_regression_roundtrip(postgres_integration_harness) -> None:
    document_id, run_id = _create_processed_document(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        active_run_before = document.active_run_id
        latest_run_before = document.latest_run_id
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_replay_regression",
                input={
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "replay_limit": 10,
                    "quality_candidate_limit": 10,
                    "min_total_shared_query_count": 1,
                },
                workflow_version="milestone5_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        assert task is not None
        assert task.status == AgentTaskStatus.COMPLETED.value
        assert task.side_effect_level == "read_only"
        assert task.requires_approval is False
        assert task.failure_artifact_path is None

        result_payload = task.result_json["payload"]
        assert result_payload["shadow_mode"] is True
        assert result_payload["triage_kind"] == "replay_regression"
        assert result_payload["candidate_harness_name"] == "wide_v2"
        assert result_payload["baseline_harness_name"] == "default_v1"
        assert result_payload["evaluation"]["total_shared_query_count"] >= 1
        assert result_payload["verification"]["outcome"] in {"passed", "failed"}
        assert result_payload["recommendation"]["next_action"]
        assert result_payload["artifact_kind"] == "triage_summary"
        assert result_payload["repair_case"]["schema_name"] == "search_harness_repair_case"
        assert result_payload["repair_case_artifact_kind"] == "repair_case"
        context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(task_id)
        )
        assert context_path.exists()
        context_payload = json.loads(context_path.read_text())
        assert (
            context_payload["summary"]["next_action"]
            == result_payload["recommendation"]["next_action"]
        )
        assert (
            context_payload["summary"]["metrics"]["confidence"]
            == result_payload["recommendation"]["confidence"]
        )
        assert {row["ref_key"] for row in context_payload["refs"]} >= {
            "triage_summary_artifact",
            "verification_record",
            "repair_case_artifact",
        }

        verification_rows = (
            session.execute(
                select(AgentTaskVerification).where(AgentTaskVerification.target_task_id == task_id)
            )
            .scalars()
            .all()
        )
        assert len(verification_rows) == 1
        verification = verification_rows[0]
        assert verification.verification_task_id == task_id
        assert verification.verifier_type == "shadow_mode_triage_gate"
        assert verification.outcome in {"passed", "failed"}

        artifact_rows = (
            session.execute(select(AgentTaskArtifact).where(AgentTaskArtifact.task_id == task_id))
            .scalars()
            .all()
        )
        assert {row.artifact_kind for row in artifact_rows} == {
            "triage_summary",
            "repair_case",
            "context",
        }
        artifact = next(row for row in artifact_rows if row.artifact_kind == "triage_summary")
        assert artifact.artifact_kind == "triage_summary"
        assert artifact.storage_path is not None
        artifact_path = Path(artifact.storage_path)
        assert artifact_path.exists()
        assert artifact_path.parent == (
            postgres_integration_harness.storage_service.storage_root / "agent_tasks" / str(task_id)
        )

        artifact_payload = json.loads(artifact_path.read_text())
        assert artifact_payload["shadow_mode"] is True
        assert artifact_payload["triage_kind"] == "replay_regression"
        assert artifact_payload["recommendation"] == result_payload["recommendation"]
        assert artifact_payload["evaluation"]["total_shared_query_count"] >= 1

        document = session.get(Document, document_id)
        assert document is not None
        assert document.active_run_id == active_run_before == run_id
        assert document.latest_run_id == latest_run_before == run_id

    client = postgres_integration_harness.client
    artifact_list_response = client.get(f"/agent-tasks/{task_id}/artifacts")
    assert artifact_list_response.status_code == 200
    assert {row["artifact_kind"] for row in artifact_list_response.json()} == {
        "triage_summary",
        "repair_case",
        "context",
    }
    artifact_id = next(
        row["artifact_id"]
        for row in artifact_list_response.json()
        if row["artifact_kind"] == "triage_summary"
    )

    artifact_detail_response = client.get(f"/agent-tasks/{task_id}/artifacts/{artifact_id}")
    assert artifact_detail_response.status_code == 200
    assert artifact_detail_response.json()["triage_kind"] == "replay_regression"

    context_response = client.get(f"/agent-tasks/{task_id}/context")
    assert context_response.status_code == 200
    assert context_response.json()["summary"]["next_action"] in {
        "candidate_ready_for_review",
        "keep_baseline_and_investigate",
        "investigate_unresolved_gaps",
        "collect_more_evidence",
        "no_change",
    }
    assert context_response.json()["freshness_status"] == "fresh"

    detail_response = client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert (
        detail_response.json()["context_summary"]["next_action"]
        == context_response.json()["summary"]["next_action"]
    )
    assert detail_response.json()["context_freshness_status"] == "fresh"

    verification_response = client.get(f"/agent-tasks/{task_id}/verifications")
    assert verification_response.status_code == 200
    assert len(verification_response.json()) == 1
    assert verification_response.json()[0]["verifier_type"] == "shadow_mode_triage_gate"


def test_evaluate_search_harness_context_roundtrip(postgres_integration_harness) -> None:
    _document_id, _run_id = _create_processed_document(postgres_integration_harness)
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_search_harness",
                input={
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "limit": 10,
                },
                workflow_version="milestone9_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        assert task is not None
        assert task.status == AgentTaskStatus.COMPLETED.value
        result_payload = task.result_json["payload"]
        evaluation_id = result_payload["evaluation"]["evaluation_id"]
        assert result_payload["evaluation"]["total_shared_query_count"] >= 1
        evaluation_row = session.get(SearchHarnessEvaluation, UUID(evaluation_id))
        assert evaluation_row is not None
        assert evaluation_row.status == "completed"
        context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(task_id)
        )
        assert context_path.exists()
        context_payload = json.loads(context_path.read_text())
        assert context_payload["summary"]["verification_state"] == "pending"
        assert context_payload["summary"]["metrics"]["total_shared_query_count"] >= 1
        assert {row["ref_key"] for row in context_payload["refs"]} >= {
            "search_harness_evaluation",
            "evaluation_queries_baseline_replay_run",
            "evaluation_queries_candidate_replay_run",
        }
        assert {row["ref_kind"] for row in context_payload["refs"]} == {
            "search_harness_evaluation",
            "replay_run",
        }

    action_catalog_response = client.get("/agent-tasks/actions")
    assert action_catalog_response.status_code == 200
    evaluate_action = next(
        row
        for row in action_catalog_response.json()
        if row["task_type"] == "evaluate_search_harness"
    )
    assert evaluate_action["output_schema_name"] == "evaluate_search_harness_output"

    context_response = client.get(f"/agent-tasks/{task_id}/context")
    assert context_response.status_code == 200
    context_json = context_response.json()
    assert context_json["summary"]["headline"].startswith("Evaluated wide_v2 against default_v1")
    assert context_json["refs"][0]["freshness_status"] == "fresh"

    evaluations_response = client.get("/search/harness-evaluations")
    assert evaluations_response.status_code == 200
    assert evaluations_response.json()[0]["evaluation_id"] == evaluation_id

    evaluation_response = client.get(f"/search/harness-evaluations/{evaluation_id}")
    assert evaluation_response.status_code == 200
    evaluation_json = evaluation_response.json()
    assert evaluation_json["evaluation_id"] == evaluation_id
    assert evaluation_json["sources"][0]["source_type"] == "evaluation_queries"

    detail_response = client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["context_summary"]["verification_state"] == "pending"

    export_response = client.get(
        "/agent-tasks/traces/export",
        params={
            "limit": 10,
            "workflow_version": "milestone9_integration",
            "task_type": "evaluate_search_harness",
        },
    )
    assert export_response.status_code == 200
    assert (
        export_response.json()["traces"][0]["context_summary"]["metrics"][
            "total_shared_query_count"
        ]
        >= 1
    )


def test_verify_search_harness_evaluation_context_roundtrip(postgres_integration_harness) -> None:
    _document_id, _run_id = _create_processed_document(postgres_integration_harness)
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        evaluate_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_search_harness",
                input={
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "limit": 10,
                },
                workflow_version="milestone10_integration",
            ),
        )
        evaluate_task_id = evaluate_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == evaluate_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_search_harness_evaluation",
                input={
                    "target_task_id": str(evaluate_task_id),
                    "max_total_regressed_count": 0,
                    "max_mrr_drop": 0.0,
                    "max_zero_result_count_increase": 0,
                    "max_foreign_top_result_count_increase": 0,
                    "min_total_shared_query_count": 1,
                },
                workflow_version="milestone10_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == verify_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        assert verify_task_row.status == AgentTaskStatus.COMPLETED.value
        verify_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(
                verify_task_id
            )
        )
        assert verify_context_path.exists()
        verify_context_payload = json.loads(verify_context_path.read_text())
        assert verify_context_payload["summary"]["verification_state"] in {"passed", "failed"}
        assert verify_context_payload["summary"]["metrics"]["max_total_regressed_count"] == 0
        assert verify_context_payload["output"]["release"]["release_package_sha256"]
        assert {row["ref_key"] for row in verify_context_payload["refs"]} >= {
            "target_task_output",
            "verification_record",
        }
        release_rows = (
            session.execute(
                select(SearchHarnessRelease)
                .where(SearchHarnessRelease.requested_by == f"agent_task:{verify_task_id}")
                .order_by(SearchHarnessRelease.created_at.desc())
            )
            .scalars()
            .all()
        )
        assert len(release_rows) == 1
        assert release_rows[0].search_harness_evaluation_id == UUID(
            verify_context_payload["output"]["evaluation"]["evaluation_id"]
        )

    context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert context_response.status_code == 200
    context_json = context_response.json()
    assert (
        context_json["output"]["verification"]["details"]["thresholds"]["max_total_regressed_count"]
        == 0
    )
    assert context_json["output"]["release"]["release_id"]
    assert context_json["output"]["verification"]["details"]["search_harness_release_id"] == (
        context_json["output"]["release"]["release_id"]
    )
    assert context_json["refs"][0]["ref_key"] == "target_task_output"

    detail_response = client.get(f"/agent-tasks/{verify_task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["context_summary"]["verification_state"] in {"passed", "failed"}
    assert detail_response.json()["context_refs"][0]["freshness_status"] == "fresh"

    export_response = client.get(
        "/agent-tasks/traces/export",
        params={
            "limit": 10,
            "workflow_version": "milestone10_integration",
            "task_type": "verify_search_harness_evaluation",
        },
    )
    assert export_response.status_code == 200
    export_trace = export_response.json()["traces"][0]
    assert export_trace["context_summary"]["metrics"]["max_total_regressed_count"] == 0
    assert export_trace["context_refs"][0]["ref_key"] == "target_task_output"


def test_triage_replay_regression_failure_writes_failure_artifact(
    postgres_integration_harness,
) -> None:
    with postgres_integration_harness.session_factory() as session:
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_replay_regression",
                input={
                    "candidate_harness_name": "does_not_exist",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "replay_limit": 10,
                    "quality_candidate_limit": 10,
                    "min_total_shared_query_count": 0,
                },
                workflow_version="milestone5_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        assert task is not None
        assert task.status == AgentTaskStatus.FAILED.value
        assert "Unknown search harness 'does_not_exist'" in (task.error_message or "")
        assert task.failure_artifact_path is not None

        failure_path = Path(task.failure_artifact_path)
        assert failure_path.exists()
        assert failure_path.parent == (
            postgres_integration_harness.storage_service.storage_root / "agent_tasks" / str(task_id)
        )

        failure_payload = json.loads(failure_path.read_text())
        assert failure_payload["task_id"] == str(task_id)
        assert failure_payload["task_type"] == "triage_replay_regression"
        assert failure_payload["failure_type"] == "ValueError"
        assert failure_payload["failure_stage"] == "execute"
        assert "Unknown search harness 'does_not_exist'" in failure_payload["error_message"]

    failure_response = postgres_integration_harness.client.get(
        f"/agent-tasks/{task_id}/failure-artifact"
    )
    assert failure_response.status_code == 200
    assert failure_response.json()["failure_type"] == "ValueError"


def test_enqueue_document_reprocess_requires_approval_before_queuing_new_run(
    postgres_integration_harness,
) -> None:
    document_id, original_run_id = _create_processed_document(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "reason": "shadow-mode triage recommended a fresh parse",
                },
                workflow_version="milestone6_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        document = session.get(Document, document_id)
        assert task is not None
        assert document is not None
        assert task.status == AgentTaskStatus.AWAITING_APPROVAL.value
        assert task.side_effect_level == "promotable"
        assert task.requires_approval is True
        assert task.approved_at is None
        assert document.active_run_id == original_run_id
        assert document.latest_run_id == original_run_id
        assert claim_next_agent_task(session, "integration-agent-worker") is None

    with postgres_integration_harness.session_factory() as session:
        approved_task = approve_agent_task(
            session,
            task_id,
            AgentTaskApprovalRequest(
                approved_by="operator@example.com",
                approval_note="approved for milestone-6 integration coverage",
            ),
        )
        assert approved_task.status == AgentTaskStatus.QUEUED.value
        assert approved_task.approved_by == "operator@example.com"

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        document = session.get(Document, document_id)
        assert task is not None
        assert document is not None
        assert task.status == AgentTaskStatus.COMPLETED.value
        assert task.approved_by == "operator@example.com"
        assert task.approved_at is not None
        assert task.result_json["payload"]["document_id"] == str(document_id)
        assert (
            task.result_json["payload"]["reason"] == "shadow-mode triage recommended a fresh parse"
        )
        reprocess_payload = task.result_json["payload"]["reprocess"]
        assert reprocess_payload["document_id"] == str(document_id)
        assert reprocess_payload["status"] == "queued"
        assert reprocess_payload["run_id"] is not None

        new_run_id = UUID(reprocess_payload["run_id"])
        assert new_run_id != original_run_id
        assert document.active_run_id == original_run_id
        assert document.latest_run_id == new_run_id
        reprocess_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(task_id)
        )
        assert reprocess_context_path.exists()
        reprocess_context_payload = json.loads(reprocess_context_path.read_text())
        assert reprocess_context_payload["output"]["document_id"] == str(document_id)

    detail_response = postgres_integration_harness.client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["approved_by"] == "operator@example.com"
    assert detail_response.json()["context_summary"]["headline"] == (
        "enqueue_document_reprocess produced typed output."
    )
    context_response = postgres_integration_harness.client.get(f"/agent-tasks/{task_id}/context")
    assert context_response.status_code == 200
    assert context_response.json()["output"]["document_id"] == str(document_id)


def test_rejected_enqueue_document_reprocess_never_queues_new_run(
    postgres_integration_harness,
) -> None:
    document_id, original_run_id = _create_processed_document(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_detail = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "reason": "operator rejected this promotion request",
                },
                workflow_version="milestone6_integration",
            ),
        )
        task_id = task_detail.task_id

    with postgres_integration_harness.session_factory() as session:
        rejected_task = reject_agent_task(
            session,
            task_id,
            AgentTaskRejectionRequest(
                rejected_by="reviewer@example.com",
                rejection_note="not enough evidence for reprocess",
            ),
        )
        assert rejected_task.status == AgentTaskStatus.REJECTED.value

    with postgres_integration_harness.session_factory() as session:
        task = session.get(AgentTask, task_id)
        document = session.get(Document, document_id)
        assert task is not None
        assert document is not None
        assert task.status == AgentTaskStatus.REJECTED.value
        assert task.rejected_by == "reviewer@example.com"
        assert task.rejected_at is not None
        assert task.completed_at is not None
        assert task.approved_at is None
        assert claim_next_agent_task(session, "integration-agent-worker") is None
        assert document.active_run_id == original_run_id
        assert document.latest_run_id == original_run_id

    detail_response = postgres_integration_harness.client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "rejected"
    assert detail_response.json()["rejected_by"] == "reviewer@example.com"


def test_agent_task_learning_surfaces_roundtrip(postgres_integration_harness) -> None:
    document_id, _run_id = _create_processed_document(postgres_integration_harness)
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        triage_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_replay_regression",
                input={
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "replay_limit": 10,
                    "quality_candidate_limit": 10,
                    "min_total_shared_query_count": 1,
                },
                workflow_version="milestone7_integration",
            ),
        )
        triage_task_id = triage_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == triage_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        reprocess_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "source_task_id": str(triage_task_id),
                    "reason": "learning-surface integration coverage",
                },
                workflow_version="milestone7_integration",
            ),
        )
        reprocess_task_id = reprocess_task.task_id
        reject_agent_task(
            session,
            reprocess_task_id,
            AgentTaskRejectionRequest(
                rejected_by="reviewer@example.com",
                rejection_note="not enough evidence for promotion",
            ),
        )

    useful_outcome_response = client.post(
        f"/agent-tasks/{triage_task_id}/outcomes",
        json={
            "outcome_label": "useful",
            "created_by": "operator@example.com",
            "note": "shadow-mode recommendation was helpful",
        },
    )
    assert useful_outcome_response.status_code == 200
    assert useful_outcome_response.json()["outcome_label"] == "useful"

    correct_outcome_response = client.post(
        f"/agent-tasks/{reprocess_task_id}/outcomes",
        json={
            "outcome_label": "correct",
            "created_by": "reviewer@example.com",
            "note": "rejection was the right call",
        },
    )
    assert correct_outcome_response.status_code == 200
    assert correct_outcome_response.json()["outcome_label"] == "correct"

    duplicate_outcome_response = client.post(
        f"/agent-tasks/{triage_task_id}/outcomes",
        json={
            "outcome_label": "useful",
            "created_by": "operator@example.com",
            "note": "attempted duplicate label",
        },
    )
    assert duplicate_outcome_response.status_code == 409
    assert "already been recorded" in duplicate_outcome_response.json()["detail"]

    outcome_list_response = client.get(f"/agent-tasks/{triage_task_id}/outcomes")
    assert outcome_list_response.status_code == 200
    assert outcome_list_response.json()[0]["outcome_label"] == "useful"

    analytics_response = client.get("/agent-tasks/analytics/summary")
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["task_count"] == 2
    assert analytics["completed_count"] == 1
    assert analytics["rejected_count"] == 1
    assert analytics["labeled_task_count"] == 2
    assert analytics["outcome_label_counts"]["useful"] == 1
    assert analytics["outcome_label_counts"]["correct"] == 1
    assert analytics["verification_outcome_counts"]

    workflow_response = client.get("/agent-tasks/analytics/workflow-versions")
    assert workflow_response.status_code == 200
    workflow_row = next(
        row
        for row in workflow_response.json()
        if row["workflow_version"] == "milestone7_integration"
    )
    assert workflow_row["task_count"] == 2
    assert workflow_row["labeled_task_count"] == 2
    assert workflow_row["outcome_label_counts"]["useful"] == 1

    export_response = client.get(
        "/agent-tasks/traces/export?workflow_version=milestone7_integration&limit=10"
    )
    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload["export_count"] == 2
    assert export_payload["workflow_version"] == "milestone7_integration"
    traced_task_ids = {row["task_id"] for row in export_payload["traces"]}
    assert traced_task_ids == {str(triage_task_id), str(reprocess_task_id)}
    assert all("outcomes" in row for row in export_payload["traces"])


def test_harness_draft_review_flow_roundtrip(postgres_integration_harness) -> None:
    _document_id, _run_id = _create_processed_document(postgres_integration_harness)
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        triage_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_replay_regression",
                input={
                    "candidate_harness_name": "wide_v2",
                    "baseline_harness_name": "default_v1",
                    "source_types": ["evaluation_queries"],
                    "replay_limit": 10,
                    "quality_candidate_limit": 10,
                    "min_total_shared_query_count": 1,
                },
                workflow_version="milestone8_integration",
            ),
        )
        triage_task_id = triage_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == triage_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_harness_config_update",
                input={
                    "draft_harness_name": "wide_v2_review_integration",
                    "base_harness_name": "wide_v2",
                    "source_task_id": str(triage_task_id),
                    "rationale": "publish a review harness with a small reranker tweak",
                    "reranker_overrides": {"result_type_priority_bonus": 0.009},
                },
                workflow_version="milestone8_integration",
            ),
        )
        draft_task_id = draft_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == draft_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        assert draft_task_row.status == AgentTaskStatus.COMPLETED.value
        draft_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(
                draft_task_id
            )
        )
        draft_context_yaml_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_yaml_path(
                draft_task_id
            )
        )
        assert draft_context_path.exists()
        assert draft_context_yaml_path.exists()
        assert draft_task_row.result_json["payload"]["draft"]["draft_harness_name"] == (
            "wide_v2_review_integration"
        )
        draft_context_row = (
            session.execute(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == draft_task_id,
                    AgentTaskArtifact.artifact_kind == "context",
                )
            )
            .scalars()
            .one()
        )
        assert draft_context_row.storage_path == str(draft_context_path)
        draft_dependencies = (
            session.execute(
                select(AgentTaskDependency).where(AgentTaskDependency.task_id == draft_task_id)
            )
            .scalars()
            .all()
        )
        assert len(draft_dependencies) == 1
        assert draft_dependencies[0].depends_on_task_id == triage_task_id
        assert draft_dependencies[0].dependency_kind == AgentTaskDependencyKind.SOURCE_TASK.value
        draft_context_payload = json.loads(draft_context_path.read_text())
        assert draft_context_payload["summary"]["verification_state"] == "pending"
        assert draft_context_payload["refs"][0]["ref_key"] == "source_task"

        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_draft_harness_config",
                input={
                    "target_task_id": str(draft_task_id),
                    "baseline_harness_name": "wide_v2",
                    "source_types": ["evaluation_queries"],
                    "limit": 10,
                    "min_total_shared_query_count": 1,
                },
                workflow_version="milestone8_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == verify_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        assert verify_task_row.status == AgentTaskStatus.COMPLETED.value
        verify_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(
                verify_task_id
            )
        )
        assert verify_context_path.exists()
        verification = verify_task_row.result_json["payload"]["verification"]
        assert verification["outcome"] == "passed"
        verify_context_payload = json.loads(verify_context_path.read_text())
        assert verify_context_payload["summary"]["verification_state"] == "passed"
        assert {row["ref_key"] for row in verify_context_payload["refs"]} >= {
            "draft_task_output",
            "verification_record",
        }

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_harness_config_update",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "publish verified review harness",
                },
                workflow_version="milestone8_integration",
            ),
        )
        apply_task_id = apply_task.task_id

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        assert apply_task_row.status == AgentTaskStatus.AWAITING_APPROVAL.value
        assert claim_next_agent_task(session, "integration-agent-worker") is None

    with postgres_integration_harness.session_factory() as session:
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="operator@example.com",
                approval_note="publish the verified review harness",
            ),
        )

    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        assert task.id == apply_task_id
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        assert apply_task_row.status == AgentTaskStatus.COMPLETED.value
        apply_payload = apply_task_row.result_json["payload"]
        assert apply_payload["draft_harness_name"] == "wide_v2_review_integration"
        assert Path(apply_payload["config_path"]).exists()
        assert apply_payload["follow_up_summary"]["schema_name"] == (
            "search_harness_follow_up_evidence"
        )
        assert apply_payload["follow_up_artifact_kind"] == "follow_up_evaluation_summary"
        apply_context_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_json_path(
                apply_task_id
            )
        )
        apply_context_yaml_path = (
            postgres_integration_harness.storage_service.get_agent_task_context_yaml_path(
                apply_task_id
            )
        )
        assert apply_context_path.exists()
        assert apply_context_yaml_path.exists()
        apply_context_row = (
            session.execute(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == apply_task_id,
                    AgentTaskArtifact.artifact_kind == "context",
                )
            )
            .scalars()
            .one()
        )
        assert apply_context_row.storage_path == str(apply_context_path)
        apply_dependencies = (
            session.execute(
                select(AgentTaskDependency).where(AgentTaskDependency.task_id == apply_task_id)
            )
            .scalars()
            .all()
        )
        assert {row.dependency_kind for row in apply_dependencies} == {
            AgentTaskDependencyKind.DRAFT_TASK.value,
            AgentTaskDependencyKind.VERIFICATION_TASK.value,
        }
        apply_context_payload = json.loads(apply_context_path.read_text())
        assert apply_context_payload["summary"]["approval_state"] == "approved"
        assert apply_context_payload["summary"]["verification_state"] == "passed"
        assert {row["ref_key"] for row in apply_context_payload["refs"]} >= {
            "draft_task_output",
            "verification_task_output",
            "applied_artifact",
            "follow_up_evaluation_artifact",
        }
        apply_attempt = (
            session.execute(
                select(AgentTaskAttempt)
                .where(AgentTaskAttempt.task_id == apply_task_id)
                .order_by(AgentTaskAttempt.attempt_number.desc())
            )
            .scalars()
            .first()
        )
        assert apply_attempt is not None
        assert apply_attempt.cost_json["estimated_usd"] == 0.0
        assert apply_attempt.performance_json["execution_latency_ms"] is not None

    harnesses_response = client.get("/search/harnesses")
    assert harnesses_response.status_code == 200
    draft_context_response = client.get(f"/agent-tasks/{draft_task_id}/context")
    assert draft_context_response.status_code == 200
    assert draft_context_response.json()["task_type"] == "draft_harness_config_update"
    assert draft_context_response.json()["freshness_status"] == "fresh"
    draft_context_yaml_response = client.get(f"/agent-tasks/{draft_task_id}/context?format=yaml")
    assert draft_context_yaml_response.status_code == 200
    assert "agent_task_context" in draft_context_yaml_response.text
    draft_detail_response = client.get(f"/agent-tasks/{draft_task_id}")
    assert draft_detail_response.status_code == 200
    assert draft_detail_response.json()["dependency_edges"][0]["dependency_kind"] == "source_task"
    assert draft_detail_response.json()["context_freshness_status"] == "fresh"
    verify_context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert verify_context_response.status_code == 200
    verify_refs = {row["ref_key"]: row for row in verify_context_response.json()["refs"]}
    assert verify_refs["draft_task_output"]["freshness_status"] == "fresh"
    assert verify_refs["verification_record"]["freshness_status"] == "fresh"
    verify_detail_response = client.get(f"/agent-tasks/{verify_task_id}")
    assert verify_detail_response.status_code == 200
    assert verify_detail_response.json()["context_summary"]["verification_state"] == "passed"
    assert verify_detail_response.json()["context_refs"][0]["freshness_status"] == "fresh"
    apply_context_response = client.get(f"/agent-tasks/{apply_task_id}/context")
    assert apply_context_response.status_code == 200
    apply_context = apply_context_response.json()
    assert apply_context["summary"]["approval_state"] == "approved"
    assert apply_context["summary"]["verification_state"] == "passed"
    assert apply_context["summary"]["follow_up_status"] == "completed"
    apply_detail_response = client.get(f"/agent-tasks/{apply_task_id}")
    assert apply_detail_response.status_code == 200
    assert apply_detail_response.json()["context_summary"]["approval_state"] == "approved"
    assert apply_detail_response.json()["context_refs"][0]["freshness_status"] == "fresh"
    apply_artifact_id = apply_detail_response.json()["result"]["payload"]["artifact_id"]
    apply_artifact_response = client.get(
        f"/agent-tasks/{apply_task_id}/artifacts/{apply_artifact_id}"
    )
    assert apply_artifact_response.status_code == 200
    assert apply_artifact_response.json()["draft_harness_name"] == "wide_v2_review_integration"
    apply_export_response = client.get(
        "/agent-tasks/traces/export",
        params={
            "limit": 10,
            "workflow_version": "milestone8_integration",
            "task_type": "apply_harness_config_update",
        },
    )
    assert apply_export_response.status_code == 200
    assert apply_export_response.json()["traces"][0]["context_summary"]["approval_state"] == (
        "approved"
    )
    harness_row = next(
        row
        for row in harnesses_response.json()
        if row["harness_name"] == "wide_v2_review_integration"
    )
    assert harness_row["harness_config"]["base_harness_name"] == "wide_v2"
    assert harness_row["harness_config"]["metadata"]["override_type"] == (
        "applied_harness_config_update"
    )

    search_response = client.post(
        "/search",
        json={
            "query": "integration threshold",
            "mode": "keyword",
            "limit": 5,
            "harness_name": "wide_v2_review_integration",
        },
    )
    assert search_response.status_code == 200
    assert search_response.json()

    request_id = search_response.headers["X-Search-Request-Id"]
    detail_response = client.get(f"/search/requests/{request_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["harness_name"] == "wide_v2_review_integration"
    assert detail["harness_config"]["base_harness_name"] == "wide_v2"

    explanation_response = client.get(f"/search/requests/{request_id}/explain")
    assert explanation_response.status_code == 200
    explanation = explanation_response.json()
    assert explanation["schema_name"] == "search_request_explanation"
    assert explanation["harness_name"] == "wide_v2_review_integration"
    assert explanation["diagnosis"]["category"] in {
        "healthy",
        "low_recall",
        "bad_ranking",
        "fallback_only",
        "filter_overconstraint",
        "table_recall_gap",
        "metadata_bias",
        "unknown",
    }

    descriptor_response = client.get("/search/harnesses/wide_v2_review_integration/descriptor")
    assert descriptor_response.status_code == 200
    descriptor = descriptor_response.json()
    assert descriptor["schema_name"] == "search_harness_descriptor"
    assert descriptor["harness_name"] == "wide_v2_review_integration"
    assert descriptor["base_harness_name"] == "wide_v2"

    recommendation_summary_response = client.get(
        "/agent-tasks/analytics/recommendations?workflow_version=milestone8_integration"
    )
    assert recommendation_summary_response.status_code == 200
    recommendation_summary = recommendation_summary_response.json()
    assert recommendation_summary["recommendation_task_count"] >= 1
    assert recommendation_summary["draft_count"] >= 1
    assert recommendation_summary["passed_verification_count"] >= 1
    assert recommendation_summary["applied_count"] >= 1

    trends_response = client.get(
        "/agent-tasks/analytics/trends?workflow_version=milestone8_integration"
    )
    assert trends_response.status_code == 200
    assert trends_response.json()["series"]

    cost_summary_response = client.get(
        "/agent-tasks/analytics/costs?workflow_version=milestone8_integration"
    )
    assert cost_summary_response.status_code == 200
    assert cost_summary_response.json()["attempt_count"] >= 4

    performance_summary_response = client.get(
        "/agent-tasks/analytics/performance?workflow_version=milestone8_integration"
    )
    assert performance_summary_response.status_code == 200
    assert performance_summary_response.json()["median_execution_latency_ms"] is not None

    value_density_response = client.get("/agent-tasks/analytics/value-density")
    assert value_density_response.status_code == 200
    assert any(
        row["workflow_version"] == "milestone8_integration" for row in value_density_response.json()
    )

    decision_signals_response = client.get("/agent-tasks/analytics/decision-signals")
    assert decision_signals_response.status_code == 200
    assert any(
        row["workflow_version"] == "milestone8_integration"
        for row in decision_signals_response.json()
    )
