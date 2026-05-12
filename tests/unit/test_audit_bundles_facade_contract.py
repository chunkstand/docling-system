from __future__ import annotations

import app.services.audit_bundle_release_payload_prov as release_payload_prov
import app.services.audit_bundle_release_payload_serialization as release_payload_serialization
import app.services.audit_bundle_release_payload_validation as release_payload_validation
import app.services.audit_bundle_release_payloads as release_payloads
from app.services import audit_bundles

AUDIT_BUNDLE_FACADE_ALIASES = {
    "_release_payload": release_payload_serialization.release_payload,
    "_evaluation_payload": release_payload_serialization.evaluation_payload,
    "_source_payload": release_payload_serialization.source_payload,
    "_replay_payload": release_payload_serialization.replay_payload,
    "_retrieval_learning_candidate_payload": (
        release_payload_serialization.retrieval_learning_candidate_payload
    ),
    "_retrieval_reranker_artifact_payload": (
        release_payload_serialization.retrieval_reranker_artifact_payload
    ),
    "_audit_bundle_reference_payload": (
        release_payload_serialization.audit_bundle_reference_payload
    ),
    "_validation_receipt_reference_payload": (
        release_payload_serialization.validation_receipt_reference_payload
    ),
    "_semantic_governance_event_payload": (
        release_payload_serialization.semantic_governance_event_payload
    ),
    "_validation_error": release_payload_validation.validation_error,
    "_append_missing_key_errors": release_payload_validation.append_missing_key_errors,
    "_append_required_list_error": release_payload_validation.append_required_list_error,
    "_validate_bundle_payload_schema": release_payload_validation.validate_bundle_payload_schema,
    "_validate_bundle_source_integrity": (
        release_payload_validation.validate_bundle_source_integrity
    ),
    "_semantic_governance_chain_checks": (
        release_payload_validation.semantic_governance_chain_checks
    ),
    "_validate_release_semantic_governance_policy": (
        release_payload_validation.validate_release_semantic_governance_policy
    ),
    "_prov_jsonld_node": release_payload_prov.prov_jsonld_node,
    "_prov_edge_id": release_payload_prov.prov_edge_id,
    "_prov_jsonld_from_graph": release_payload_prov.prov_jsonld_from_graph,
    "_prov_graph": release_payload_prov.prov_graph,
    "_build_search_harness_release_payload": release_payloads.build_search_harness_release_payload,
}


def test_audit_bundles_facade_reexports_release_payload_owner_helpers() -> None:
    assert (
        audit_bundles.SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND
        == release_payload_serialization.SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND
    )
    assert (
        audit_bundles.SEARCH_HARNESS_RELEASE_SOURCE_TABLE
        == release_payload_serialization.SEARCH_HARNESS_RELEASE_SOURCE_TABLE
    )
    for facade_name, owner_symbol in AUDIT_BUNDLE_FACADE_ALIASES.items():
        assert getattr(audit_bundles, facade_name) is owner_symbol


def test_audit_bundles_facade_wraps_prov_validation_runtime() -> None:
    _, errors = audit_bundles._validate_prov_graph({"payload": {"prov": "invalid"}})

    assert errors == [
        {
            "code": "prov_graph_missing",
            "message": "PROV graph must be present.",
            "path": "bundle.payload.prov",
        }
    ]
