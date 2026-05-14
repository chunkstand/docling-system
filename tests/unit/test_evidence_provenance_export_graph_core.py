from __future__ import annotations

from uuid import uuid4

from app.services.evidence_provenance import prov_identifier
from app.services.evidence_provenance_export_graph_core import (
    build_agent_task_provenance_export,
)


def _task(task_id: str, task_type: str) -> dict[str, str]:
    return {
        "task_id": task_id,
        "task_type": task_type,
        "status": "completed",
        "workflow_version": "v1",
        "created_at": "2026-05-13T00:00:00Z",
        "updated_at": "2026-05-13T00:05:00Z",
        "completed_at": "2026-05-13T00:05:00Z",
    }


def test_build_agent_task_provenance_export_preserves_base_graph(monkeypatch) -> None:
    verification_task_id = str(uuid4())
    draft_task_id = str(uuid4())
    search_request_id = str(uuid4())
    document_id = str(uuid4())
    run_id = str(uuid4())
    manifest = {
        "evidence_manifest_id": str(uuid4()),
        "manifest_sha256": "manifest-sha",
        "trace_sha256": "trace-sha",
        "manifest_kind": "technical_report",
        "task": _task(str(uuid4()), "generate_technical_report"),
        "draft_task": _task(draft_task_id, "draft_technical_report"),
        "verification_task": _task(verification_task_id, "verify_technical_report"),
        "retrieval_trace": {
            "source_evidence_closure": {"complete": True, "source_record_recall": 1.0}
        },
        "report_trace": {
            "context_pack_audit": {
                "release_readiness_db_gate": {
                    "verification_id": verification_task_id,
                    "verification_task_id": verification_task_id,
                    "check_key": "release_readiness_db_gate",
                    "passed": True,
                    "required": True,
                    "complete": True,
                    "failure_count": 0,
                    "source_search_request_count": 1,
                    "verified_request_count": 1,
                }
            },
            "evidence_package_exports": [
                {
                    "evidence_package_export_id": str(uuid4()),
                    "package_kind": "technical_report_support",
                    "package_sha256": "package-sha",
                    "trace_sha256": "trace-sha",
                    "search_request_id": search_request_id,
                }
            ],
        },
        "source_documents": [
            {
                "id": document_id,
                "sha256": "document-sha",
                "source_filename": "report.pdf",
                "title": "Report",
            }
        ],
        "document_runs": [
            {
                "id": run_id,
                "document_id": document_id,
                "validation_status": "validated",
                "artifact_hashes": {
                    "docling_json_sha256": "docling-sha",
                    "document_yaml_sha256": "yaml-sha",
                },
            }
        ],
        "source_records": [
            {
                "source_table": "document_chunks",
                "id": "chunk-1",
                "document_id": document_id,
                "run_id": run_id,
                "source_type": "chunk",
                "source_snapshot_sha256": "chunk-sha",
            }
        ],
        "provenance_edges": [
            {
                "from": {"table": "documents", "id": document_id},
                "to": {"table": "document_runs", "id": run_id},
                "edge_type": "document_to_run",
            }
        ],
        "manifest_integrity": {"complete": True},
        "audit_checklist": ["integrity"],
    }
    trace = {"trace_sha256": "trace-sha", "trace_integrity": {"complete": True}}

    monkeypatch.setattr(
        "app.services.evidence_provenance_export_graph_core.get_agent_task_evidence_manifest",
        lambda session, task_id: manifest,
    )
    monkeypatch.setattr(
        "app.services.evidence_provenance_export_graph_core.get_agent_task_evidence_trace",
        lambda session, task_id: trace,
    )

    payload = build_agent_task_provenance_export(None, uuid4())

    assert payload["schema_name"] == "technical_report_prov_export"
    assert payload["prov_integrity"]["complete"] is True
    assert payload["audit"]["trace_integrity"]["complete"] is True
    assert payload["audit"]["release_readiness_db_gate"]["complete"] is True
    assert payload["activity"][prov_identifier("search_requests", search_request_id)][
        "prov:type"
    ] == "docling:SearchRequest"
    assert payload["entity"][prov_identifier("documents", document_id)]["docling:sha256"] == (
        "document-sha"
    )
    assert payload["entity"][
        prov_identifier("evidence_manifests", manifest["evidence_manifest_id"])
    ]["docling:manifest_sha256"] == "manifest-sha"
