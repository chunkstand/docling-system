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
    AgentTaskStatus,
    AgentTaskVerification,
    Document,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
)
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedFigure,
    ParsedTable,
    ParsedTableSegment,
)

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
            b"%PDF-1.7\nintegration-test",
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
            session.execute(
                select(AgentTaskArtifact).where(AgentTaskArtifact.task_id == task_id)
            )
            .scalars()
            .all()
        )
        assert len(artifact_rows) == 1
        artifact = artifact_rows[0]
        assert artifact.artifact_kind == "triage_summary"
        assert artifact.storage_path is not None
        artifact_path = Path(artifact.storage_path)
        assert artifact_path.exists()
        assert artifact_path.parent == (
            postgres_integration_harness.storage_service.storage_root
            / "agent_tasks"
            / str(task_id)
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
    assert len(artifact_list_response.json()) == 1
    artifact_id = artifact_list_response.json()[0]["artifact_id"]

    artifact_detail_response = client.get(f"/agent-tasks/{task_id}/artifacts/{artifact_id}")
    assert artifact_detail_response.status_code == 200
    assert artifact_detail_response.json()["triage_kind"] == "replay_regression"

    verification_response = client.get(f"/agent-tasks/{task_id}/verifications")
    assert verification_response.status_code == 200
    assert len(verification_response.json()) == 1
    assert verification_response.json()[0]["verifier_type"] == "shadow_mode_triage_gate"


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
            postgres_integration_harness.storage_service.storage_root
            / "agent_tasks"
            / str(task_id)
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
            task.result_json["payload"]["reason"]
            == "shadow-mode triage recommended a fresh parse"
        )
        reprocess_payload = task.result_json["payload"]["reprocess"]
        assert reprocess_payload["document_id"] == str(document_id)
        assert reprocess_payload["status"] == "queued"
        assert reprocess_payload["run_id"] is not None

        new_run_id = UUID(reprocess_payload["run_id"])
        assert new_run_id != original_run_id
        assert document.active_run_id == original_run_id
        assert document.latest_run_id == new_run_id

    detail_response = postgres_integration_harness.client.get(f"/agent-tasks/{task_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["approved_by"] == "operator@example.com"
