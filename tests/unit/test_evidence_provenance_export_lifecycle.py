from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import app.services.evidence_provenance_exports as provenance_exports
from app.services.evidence_provenance import (
    TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
    frozen_prov_export_payload,
)
from app.services.evidence_provenance_export_graph_core import (
    build_agent_task_provenance_export,
)
from app.services.evidence_provenance_export_lifecycle import (
    get_agent_task_provenance_export,
    persist_agent_task_provenance_export,
    record_prov_export_supersession_attempt,
    technical_report_change_impact_for_governance,
)


def _base_prov_export() -> dict:
    return {
        "schema_name": "technical_report_prov_export",
        "entity": {"docling:documents/source": {"prov:type": "docling:SourceDocument"}},
        "activity": {"docling:agent-tasks/verify": {"prov:type": "docling:AgentTask"}},
        "agent": {"docling:agent/docling-system": {"prov:type": "prov:SoftwareAgent"}},
        "wasGeneratedBy": {
            "docling:was-generated-by/000001": {
                "prov:entity": "docling:documents/source",
                "prov:activity": "docling:agent-tasks/verify",
            }
        },
        "used": {
            "docling:used/000001": {
                "prov:activity": "docling:agent-tasks/verify",
                "prov:entity": "docling:documents/source",
            }
        },
        "wasDerivedFrom": {
            "docling:was-derived-from/000001": {
                "prov:generatedEntity": "docling:documents/source",
                "prov:usedEntity": "docling:documents/source",
            }
        },
        "wasAssociatedWith": {
            "docling:was-associated-with/000001": {
                "prov:activity": "docling:agent-tasks/verify",
                "prov:agent": "docling:agent/docling-system",
            }
        },
        "wasAttributedTo": {},
        "retrieval_evaluation": {"complete": True},
        "audit": {
            "manifest_integrity": {"complete": True},
            "trace_integrity": {"complete": True},
        },
        "prov_summary": {"relation_count": 4},
        "prov_integrity": {"prov_sha256": "base"},
    }


def test_provenance_exports_facade_forwards_owner_entrypoints() -> None:
    assert (
        provenance_exports._build_agent_task_provenance_export
        is build_agent_task_provenance_export
    )
    assert (
        provenance_exports.persist_agent_task_provenance_export
        is persist_agent_task_provenance_export
    )
    assert provenance_exports.get_agent_task_provenance_export is get_agent_task_provenance_export
    assert (
        provenance_exports._technical_report_change_impact_for_governance
        is technical_report_change_impact_for_governance
    )

    with open(provenance_exports.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 300


def test_record_supersession_attempt_returns_none_for_matching_frozen_export() -> None:
    artifact_id = uuid4()
    task_id = uuid4()
    prov_export = _base_prov_export()
    frozen_payload = frozen_prov_export_payload(
        prov_export,
        artifact_id=artifact_id,
        task_id=task_id,
        created_at=datetime(2026, 5, 13, tzinfo=UTC),
        storage_path="storage/agent_tasks/task/technical_report_prov_export.json",
        settings_provider=lambda: SimpleNamespace(
            audit_bundle_signing_key=None,
            audit_bundle_signing_key_id=None,
        ),
    )
    existing = SimpleNamespace(
        id=artifact_id,
        task_id=task_id,
        artifact_kind=TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        storage_path="storage/agent_tasks/task/technical_report_prov_export.json",
        payload_json=frozen_payload,
    )

    assert record_prov_export_supersession_attempt(
        SimpleNamespace(),
        existing=existing,
        attempted_prov_export=prov_export,
    ) is None


def test_change_impact_for_governance_marks_missing_verification_task() -> None:
    session = SimpleNamespace(get=lambda model, key: None)

    payload = technical_report_change_impact_for_governance(session, uuid4())

    assert payload["impacted"] is True
    assert payload["impact_count"] == 1
    assert payload["impacts"][0]["impact_type"] == "verification_task_missing"
