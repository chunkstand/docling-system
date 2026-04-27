from app.services.evidence import _prov_export_integrity_payload


def _base_prov_export() -> dict:
    return {
        "schema_name": "technical_report_prov_export",
        "entity": {
            "docling:documents/source": {"prov:type": "docling:SourceDocument"},
            "docling:document-runs/run": {"prov:type": "docling:DocumentRun"},
        },
        "activity": {
            "docling:agent-tasks/verify": {"prov:type": "docling:AgentTask"},
        },
        "agent": {
            "docling:agent/docling-system": {"prov:type": "prov:SoftwareAgent"},
        },
        "wasGeneratedBy": {
            "docling:was-generated-by/000001": {
                "prov:entity": "docling:document-runs/run",
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
                "prov:generatedEntity": "docling:document-runs/run",
                "prov:usedEntity": "docling:documents/source",
            }
        },
        "wasAssociatedWith": {
            "docling:was-associated-with/000001": {
                "prov:activity": "docling:agent-tasks/verify",
                "prov:agent": "docling:agent/docling-system",
            }
        },
        "wasAttributedTo": {
            "docling:was-attributed-to/000001": {
                "prov:entity": "docling:documents/source",
                "prov:agent": "docling:agent/docling-system",
            }
        },
        "retrieval_evaluation": {"complete": True},
        "audit": {
            "manifest_integrity": {"complete": True},
            "trace_integrity": {"complete": True},
        },
        "prov_summary": {"relation_count": 5},
        "prov_integrity": {"stale": True},
    }


def test_prov_export_integrity_is_complete_for_closed_relation_graph() -> None:
    integrity = _prov_export_integrity_payload(_base_prov_export())

    assert integrity["complete"] is True
    assert integrity["hash_basis_schema"] == (
        "technical_report_prov_export_without_integrity_v1"
    )
    assert "prov_integrity" not in integrity["hash_basis_fields"]
    assert integrity["all_relation_references_declared"] is True
    assert integrity["missing_relation_reference_count"] == 0
    assert integrity["prov_sha256"]


def test_prov_export_integrity_fails_for_undeclared_relation_reference() -> None:
    prov_export = _base_prov_export()
    prov_export["used"]["docling:used/000001"]["prov:entity"] = "docling:documents/missing"

    integrity = _prov_export_integrity_payload(prov_export)

    assert integrity["complete"] is False
    assert integrity["all_used_entities_declared"] is False
    assert integrity["all_relation_references_declared"] is False
    assert integrity["missing_relation_reference_count"] == 1
    assert integrity["missing_relation_references"] == [
        {
            "relation_type": "used",
            "relation_id": "docling:used/000001",
            "reference_field": "prov:entity",
            "reference_id": "docling:documents/missing",
        }
    ]
