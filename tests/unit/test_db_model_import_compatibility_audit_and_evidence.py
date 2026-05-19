from __future__ import annotations

import pytest

import app.db.models as model_module
from app.db.base import Base
from tests.db_model_contract import AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS

EXPECTED_MODEL_MODULES = {
    "AuditBundleExport": "app.db.model_domains.audit_and_evidence_audit_bundles",
    "AuditBundleValidationReceipt": "app.db.model_domains.audit_and_evidence_audit_bundles",
    "EvidencePackageExport": "app.db.model_domains.audit_and_evidence_manifests",
    "EvidenceManifest": "app.db.model_domains.audit_and_evidence_manifests",
    "TechnicalReportReleaseReadinessDbGate": (
        "app.db.model_domains.audit_and_evidence_technical_reports"
    ),
    "TechnicalReportClaimRetrievalFeedback": (
        "app.db.model_domains.audit_and_evidence_technical_reports"
    ),
    "EvidenceTraceNode": "app.db.model_domains.audit_and_evidence_trace",
    "EvidenceTraceEdge": "app.db.model_domains.audit_and_evidence_trace",
    "ClaimEvidenceDerivation": "app.db.model_domains.audit_and_evidence_trace",
}


@pytest.mark.parametrize(("model_name", "expected_module"), EXPECTED_MODEL_MODULES.items())
def test_audit_and_evidence_models_are_owned_by_family_local_modules(
    model_name: str, expected_module: str
) -> None:
    model = getattr(model_module, model_name)

    assert model.__module__ == expected_module
    assert model.__table__ is Base.metadata.tables[model.__table__.name]


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_audit_and_evidence_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns
