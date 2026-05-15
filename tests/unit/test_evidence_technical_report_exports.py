from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import app.services.evidence_technical_report_export_contracts as technical_report_export_contracts
import app.services.evidence_technical_report_exports as technical_report_exports
from app.db.models import ClaimEvidenceDerivation, EvidencePackageExport
from app.services import evidence
from app.services import (
    evidence_technical_report_export_provenance_locks as technical_report_export_provenance_locks,
)
from app.services.evidence_common import payload_sha256

TECHNICAL_REPORT_EXPORT_FACADE_ALIASES = {
    "_claim_derivation_provenance_lock_contract_mismatches": (
        "_claim_derivation_provenance_lock_contract_mismatches"
    ),
    "_claim_derivation_support_judgment_contract_mismatches": (
        "_claim_derivation_support_judgment_contract_mismatches"
    ),
    "_evidence_card_snapshot": "_evidence_card_snapshot",
    "_latest_passed_release_bindings_by_request": "_latest_passed_release_bindings_by_request",
    "attach_operator_run_to_evidence_export": "attach_operator_run_to_evidence_export",
    "apply_technical_report_derivation_links": "apply_technical_report_derivation_links",
    "build_technical_report_derivation_package": "build_technical_report_derivation_package",
    "persist_technical_report_evidence_export": "persist_technical_report_evidence_export",
}


class _FakeSession:
    def __init__(self, export: EvidencePackageExport | None) -> None:
        self.export = export
        self.flush_count = 0

    def get(self, _model, row_id):
        if self.export is None or self.export.id != row_id:
            return None
        return self.export

    def flush(self) -> None:
        self.flush_count += 1


class _ScalarRoutingSession:
    def __init__(self, rows_by_entity: dict[object, list[object]]) -> None:
        self.rows_by_entity = rows_by_entity

    def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return iter(self.rows_by_entity.get(entity, []))


def test_evidence_facade_reexports_technical_report_export_owner_functions() -> None:
    for facade_name, owner_name in TECHNICAL_REPORT_EXPORT_FACADE_ALIASES.items():
        assert getattr(evidence, facade_name) is getattr(technical_report_exports, owner_name)


def test_evidence_facade_wraps_blocked_owner_names() -> None:
    derivation = ClaimEvidenceDerivation(
        id=uuid4(),
        evidence_package_export_id=uuid4(),
        claim_id="claim:1",
        derivation_rule="technical_report_claim_contract_v1",
        evidence_package_sha256="package-sha",
        derivation_sha256="derivation-sha",
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    assert evidence._claim_derivation_payload(
        derivation
    ) == technical_report_exports._claim_derivation_payload(derivation)


def test_attach_helpers_update_evidence_export_rows() -> None:
    export_id = uuid4()
    artifact_id = uuid4()
    operator_run_id = uuid4()
    export = EvidencePackageExport(
        id=export_id,
        package_kind="technical_report_claims",
        package_sha256="package-sha",
        export_status="completed",
        operator_run_ids_json=["existing"],
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )
    session = _FakeSession(export)

    evidence.attach_artifact_to_evidence_export(
        session,
        evidence_package_export_id=export_id,
        agent_task_artifact_id=artifact_id,
    )
    technical_report_exports.attach_operator_run_to_evidence_export(
        session,
        evidence_package_export_id=export_id,
        operator_run_id=operator_run_id,
    )

    assert export.agent_task_artifact_id == artifact_id
    assert export.operator_run_ids_json == ["existing", str(operator_run_id)]
    assert session.flush_count == 2


def test_claim_derivation_payload_preserves_hash_and_lock_fields() -> None:
    derivation = ClaimEvidenceDerivation(
        id=uuid4(),
        evidence_package_export_id=uuid4(),
        agent_task_id=uuid4(),
        claim_id="claim:1",
        derivation_rule="technical_report_claim_contract_v1",
        evidence_card_ids_json=["card-1"],
        source_search_request_ids_json=["request-1"],
        source_search_request_result_ids_json=["result-1"],
        source_evidence_package_export_ids_json=["export-1"],
        provenance_lock_json={"schema_name": "technical_report_claim_provenance_lock"},
        provenance_lock_sha256="prov-lock-sha",
        support_verdict="supported",
        support_score=0.91,
        support_judgment_json={"schema_name": "technical_report_claim_support_judgment"},
        support_judgment_sha256="judge-sha",
        evidence_package_sha256="package-sha",
        derivation_sha256="derivation-sha",
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    payload = technical_report_exports._claim_derivation_payload(derivation)

    assert payload["claim_id"] == "claim:1"
    assert payload["source_search_request_ids"] == ["request-1"]
    assert payload["source_search_request_result_ids"] == ["result-1"]
    assert payload["source_evidence_package_export_ids"] == ["export-1"]
    assert payload["provenance_lock_sha256"] == "prov-lock-sha"
    assert payload["support_judgment_sha256"] == "judge-sha"
    assert payload["evidence_package_sha256"] == "package-sha"
    assert payload["derivation_sha256"] == "derivation-sha"


def test_contract_helpers_accept_matching_provenance_lock_and_support_judgment() -> None:
    derivation = ClaimEvidenceDerivation(
        id=uuid4(),
        evidence_package_export_id=uuid4(),
        agent_task_id=uuid4(),
        claim_id="claim:1",
        derivation_rule="technical_report_claim_contract_v1",
        evidence_card_ids_json=["card-1"],
        graph_edge_ids_json=["edge-1"],
        source_search_request_ids_json=["request-1"],
        source_search_request_result_ids_json=["result-1"],
        source_evidence_package_export_ids_json=["export-1"],
        source_evidence_package_sha256s_json=["package-upstream"],
        source_evidence_trace_sha256s_json=["trace-upstream"],
        semantic_ontology_snapshot_ids_json=["ontology-1"],
        semantic_graph_snapshot_ids_json=["graph-snapshot-1"],
        retrieval_reranker_artifact_ids_json=["reranker-1"],
        search_harness_release_ids_json=["release-1"],
        release_audit_bundle_ids_json=["bundle-1"],
        release_validation_receipt_ids_json=["receipt-1"],
        provenance_lock_json={
            "schema_name": "technical_report_claim_provenance_lock",
            "schema_version": "1.0",
            "claim_id": "claim:1",
            "source_search_request_ids": ["request-1"],
            "source_search_request_result_ids": ["result-1"],
            "source_evidence_package_export_ids": ["export-1"],
            "source_evidence_package_sha256s": ["package-upstream"],
            "source_evidence_trace_sha256s": ["trace-upstream"],
            "semantic_ontology_snapshot_ids": ["ontology-1"],
            "semantic_graph_snapshot_ids": ["graph-snapshot-1"],
            "retrieval_reranker_artifact_ids": ["reranker-1"],
            "search_harness_release_ids": ["release-1"],
            "release_audit_bundle_ids": ["bundle-1"],
            "release_validation_receipt_ids": ["receipt-1"],
            "coverage": {
                "source_search_request_count": 1,
                "source_search_request_result_count": 1,
                "source_evidence_package_export_count": 1,
                "semantic_ontology_snapshot_count": 1,
                "semantic_graph_snapshot_count": 1,
                "retrieval_reranker_artifact_count": 1,
                "search_harness_release_count": 1,
                "release_audit_bundle_count": 1,
                "release_validation_receipt_count": 1,
            },
        },
        provenance_lock_sha256="prov-lock-sha",
        support_verdict="supported",
        support_score=0.91,
        support_judge_run_id=uuid4(),
        support_judgment_json={
            "schema_name": "technical_report_claim_support_judgment",
            "schema_version": "1.0",
            "judge_kind": "deterministic_claim_support_v1",
            "claim_id": "claim:1",
            "verdict": "supported",
            "support_score": 0.91,
            "source_search_request_result_ids": ["result-1"],
            "evidence_card_ids": ["card-1"],
            "graph_edge_ids": ["edge-1"],
        },
        support_judgment_sha256="judge-sha",
        evidence_package_sha256="package-sha",
        derivation_sha256="derivation-sha",
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    assert (
        technical_report_export_contracts.claim_derivation_provenance_lock_contract_mismatches(
            derivation
        )
        == []
    )
    assert (
        technical_report_export_contracts.claim_derivation_support_judgment_contract_mismatches(
            derivation
        )
        == []
    )


def test_contract_helpers_report_provenance_lock_and_support_judgment_mismatches() -> None:
    derivation = ClaimEvidenceDerivation(
        id=uuid4(),
        evidence_package_export_id=uuid4(),
        claim_id="claim:1",
        evidence_card_ids_json=["card-1"],
        graph_edge_ids_json=["edge-1"],
        source_search_request_result_ids_json=["result-1"],
        support_verdict="supported",
        support_score=0.91,
        provenance_lock_json={
            "schema_name": "wrong_schema",
            "schema_version": "1.0",
            "claim_id": "claim:1",
            "source_search_request_ids": [],
            "source_search_request_result_ids": ["result-2"],
            "source_evidence_package_export_ids": [],
            "source_evidence_package_sha256s": [],
            "source_evidence_trace_sha256s": [],
            "semantic_ontology_snapshot_ids": [],
            "semantic_graph_snapshot_ids": [],
            "retrieval_reranker_artifact_ids": [],
            "search_harness_release_ids": [],
            "release_audit_bundle_ids": [],
            "release_validation_receipt_ids": [],
            "coverage": {
                "source_search_request_count": 0,
                "source_search_request_result_count": 2,
                "source_evidence_package_export_count": 0,
                "semantic_ontology_snapshot_count": 0,
                "semantic_graph_snapshot_count": 0,
                "retrieval_reranker_artifact_count": 0,
                "search_harness_release_count": 0,
                "release_audit_bundle_count": 0,
                "release_validation_receipt_count": 0,
            },
        },
        support_judgment_json={
            "schema_name": "technical_report_claim_support_judgment",
            "schema_version": "1.0",
            "judge_kind": "deterministic_claim_support_v1",
            "claim_id": "claim:2",
            "verdict": "contradicted",
            "support_score": "not-a-number",
            "source_search_request_result_ids": ["other-result"],
            "evidence_card_ids": ["card-2"],
            "graph_edge_ids": ["edge-2"],
        },
        created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
    )

    provenance_mismatches = (
        technical_report_export_contracts.claim_derivation_provenance_lock_contract_mismatches(
            derivation
        )
    )
    support_mismatches = (
        technical_report_export_contracts.claim_derivation_support_judgment_contract_mismatches(
            derivation
        )
    )

    assert "schema_name" in provenance_mismatches
    assert "source_search_request_result_ids" in provenance_mismatches
    assert "coverage.source_search_request_result_count" in provenance_mismatches
    assert "claim_id" in support_mismatches
    assert "verdict" in support_mismatches
    assert "support_score" in support_mismatches
    assert "evidence_card_ids" in support_mismatches
    assert "graph_edge_ids" in support_mismatches


def test_apply_provenance_locks_builds_release_bundle_and_receipt_refs(monkeypatch) -> None:
    fact_id = uuid4()
    ontology_snapshot_id = uuid4()
    graph_snapshot_id = uuid4()
    search_request_id = uuid4()
    search_request_result_id = uuid4()
    evidence_export_id = uuid4()
    release_id = uuid4()
    bundle_id = uuid4()
    receipt_id = uuid4()
    reranker_artifact_id = uuid4()
    evidence_card_id = uuid4()
    edge_id = uuid4()

    session = _ScalarRoutingSession(
        rows_by_entity={
            technical_report_export_provenance_locks.SemanticFact: [
                SimpleNamespace(id=fact_id, ontology_snapshot_id=ontology_snapshot_id)
            ],
            technical_report_export_provenance_locks.SemanticGraphSnapshot: [
                SimpleNamespace(id=graph_snapshot_id, ontology_snapshot_id=ontology_snapshot_id)
            ],
            technical_report_export_provenance_locks.SearchRequestRecord: [
                SimpleNamespace(
                    id=search_request_id,
                    harness_name="default_v1",
                    created_at=datetime(2026, 5, 10, 12, 0, tzinfo=UTC),
                )
            ],
            technical_report_export_provenance_locks.RetrievalRerankerArtifact: [
                SimpleNamespace(
                    id=reranker_artifact_id,
                    search_harness_release_id=release_id,
                    created_at=datetime(2026, 5, 10, 12, 5, tzinfo=UTC),
                )
            ],
        }
    )
    monkeypatch.setattr(
        technical_report_export_provenance_locks,
        "_latest_passed_release_bindings_by_request",
        lambda _session, _request_rows: (
            {
                str(search_request_id): {
                    "search_request_id": str(search_request_id),
                    "harness_name": "default_v1",
                    "search_harness_release_id": str(release_id),
                    "selection_rule": "latest_passed_release_at_or_before_search_request",
                    "selection_status": "release_found_before_request",
                }
            },
            {str(release_id): SimpleNamespace(id=release_id)},
        ),
    )
    monkeypatch.setattr(
        technical_report_export_provenance_locks,
        "_latest_release_audit_bundles_by_release",
        lambda _session, _release_ids: {
            release_id: SimpleNamespace(id=bundle_id),
        },
    )
    monkeypatch.setattr(
        technical_report_export_provenance_locks,
        "_latest_passed_receipts_by_bundle",
        lambda _session, _bundle_ids: {
            bundle_id: SimpleNamespace(id=receipt_id),
        },
    )

    draft_payload = {
        "evidence_cards": [
            {
                "evidence_card_id": str(evidence_card_id),
                "source_search_request_ids": [str(search_request_id)],
                "source_search_request_result_ids": [str(search_request_result_id)],
                "source_evidence_package_export_ids": [str(evidence_export_id)],
                "source_evidence_package_sha256s": ["package-upstream"],
                "source_evidence_trace_sha256s": ["trace-upstream"],
            }
        ],
        "graph_context": [
            {
                "edge_id": str(edge_id),
                "graph_snapshot_id": str(graph_snapshot_id),
            }
        ],
        "claims": [
            {
                "claim_id": "claim:1",
                "evidence_card_ids": [str(evidence_card_id)],
                "graph_edge_ids": [str(edge_id)],
                "fact_ids": [str(fact_id)],
            }
        ],
    }

    technical_report_export_provenance_locks.apply_technical_report_claim_provenance_locks(
        session,
        draft_payload,
    )

    claim = draft_payload["claims"][0]
    assert claim["source_search_request_ids"] == [str(search_request_id)]
    assert claim["source_search_request_result_ids"] == [str(search_request_result_id)]
    assert claim["semantic_ontology_snapshot_ids"] == [str(ontology_snapshot_id)]
    assert claim["semantic_graph_snapshot_ids"] == [str(graph_snapshot_id)]
    assert claim["retrieval_reranker_artifact_ids"] == [str(reranker_artifact_id)]
    assert claim["search_harness_release_ids"] == [str(release_id)]
    assert claim["release_audit_bundle_ids"] == [str(bundle_id)]
    assert claim["release_validation_receipt_ids"] == [str(receipt_id)]
    assert claim["provenance_lock"]["coverage"]["release_validation_receipt_count"] == 1
    assert claim["provenance_lock_sha256"] == payload_sha256(claim["provenance_lock"])
    assert draft_payload["provenance_lock_summary"]["claims_with_provenance_lock_count"] == 1
    assert draft_payload["release_validation_receipt_ids"] == [str(receipt_id)]
