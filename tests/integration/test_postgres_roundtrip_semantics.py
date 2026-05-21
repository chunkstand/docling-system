from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest

from app.core.config import get_settings
from app.db.public.semantic_memory import SemanticGraphSourceKind, SemanticOntologySourceKind
from app.services.semantic_graph import persist_semantic_graph_snapshot
from app.services.semantic_registry import (
    clear_semantic_registry_cache,
    ensure_workspace_semantic_registry,
    get_active_semantic_ontology_snapshot,
    persist_semantic_ontology_snapshot,
)
from tests.integration.pdf_fixtures import valid_test_pdf_bytes
from tests.integration.postgres_roundtrip_support import (
    StubParser,
    _build_parsed_document,
    _configure_sample_semantics,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_semantic_reviews_persist_across_reruns_and_emit_continuity(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    _configure_sample_semantics(monkeypatch)
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
    document_id = create_response.json()["document_id"]
    original_run_id = UUID(create_response.json()["run_id"])

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))

    first_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert first_semantics.status_code == 200
    first_payload = first_semantics.json()
    threshold_assertion = next(
        assertion
        for assertion in first_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    threshold_binding = threshold_assertion["category_bindings"][0]

    assertion_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{threshold_assertion['assertion_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Confirmed governance concept for this document.",
            "reviewed_by": "semantic-operator",
        },
    )
    assert assertion_review_response.status_code == 200
    assert assertion_review_response.json()["scope"] == "assertion"
    assert assertion_review_response.json()["review_status"] == "approved"

    binding_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertion-category-bindings/{threshold_binding['binding_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Confirmed category binding for governance.",
            "reviewed_by": "semantic-operator",
        },
    )
    assert binding_review_response.status_code == 200
    assert binding_review_response.json()["scope"] == "assertion_category_binding"
    assert binding_review_response.json()["review_status"] == "approved"

    reviewed_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert reviewed_semantics.status_code == 200
    reviewed_payload = reviewed_semantics.json()
    reviewed_threshold_assertion = next(
        assertion
        for assertion in reviewed_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert reviewed_threshold_assertion["review_status"] == "approved"
    assert reviewed_threshold_assertion["details"]["review_overlay"]["review_note"] == (
        "Confirmed governance concept for this document."
    )
    assert reviewed_threshold_assertion["category_bindings"][0]["review_status"] == "approved"
    assert (
        reviewed_threshold_assertion["category_bindings"][0]["details"]["review_overlay"][
            "review_note"
        ]
        == "Confirmed category binding for governance."
    )

    reviewed_artifact = client.get(f"/documents/{document_id}/semantics/latest/artifacts/json")
    assert reviewed_artifact.status_code == 200
    reviewed_artifact_payload = reviewed_artifact.json()
    reviewed_artifact_threshold_assertion = next(
        assertion
        for assertion in reviewed_artifact_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert reviewed_artifact_threshold_assertion["review_status"] == "approved"
    assert reviewed_artifact_threshold_assertion["category_bindings"][0]["review_status"] == (
        "approved"
    )

    reprocess_response = client.post(f"/documents/{document_id}/reprocess")
    assert reprocess_response.status_code == 202
    rerun_id = UUID(reprocess_response.json()["run_id"])
    assert rerun_id != original_run_id

    postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document(figure_caption="Overview illustration"))
    )

    latest_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert latest_semantics.status_code == 200
    latest_payload = latest_semantics.json()
    assert latest_payload["run_id"] == str(rerun_id)
    assert latest_payload["baseline_run_id"] == str(original_run_id)
    assert latest_payload["baseline_semantic_pass_id"] is not None
    assert latest_payload["continuity_summary"]["has_baseline"] is True
    assert latest_payload["continuity_summary"]["removed_concept_keys"] == ["system_diagram"]
    assert latest_payload["continuity_summary"]["added_concept_keys"] == []
    assert latest_payload["continuity_summary"]["changed_assertion_review_statuses"] == []
    latest_threshold_assertion = next(
        assertion
        for assertion in latest_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert latest_threshold_assertion["review_status"] == "approved"
    assert latest_threshold_assertion["category_bindings"][0]["review_status"] == "approved"
    assert latest_payload["evaluation_summary"]["all_expectations_passed"] is False

    continuity_response = client.get(f"/documents/{document_id}/semantics/latest/continuity")
    assert continuity_response.status_code == 200
    continuity = continuity_response.json()
    assert continuity["baseline_run_id"] == str(original_run_id)
    assert continuity["summary"]["removed_concept_keys"] == ["system_diagram"]
    assert continuity["summary"]["change_count"] == 1


def test_workspace_seed_snapshot_same_version_resync_does_not_self_parent(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts: []
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
"""
    )
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        original_snapshot = get_active_semantic_ontology_snapshot(session)
        original_snapshot_id = original_snapshot.id
        assert original_snapshot.parent_snapshot_id is None
        original_sha256 = original_snapshot.sha256

    registry_path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts:
  - concept_key: incident_response_latency
    preferred_label: Incident Response Latency
    scope_note: Time to respond to incidents.
    aliases:
      - response latency
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
"""
    )
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        active_snapshot = get_active_semantic_ontology_snapshot(session)
        assert active_snapshot.id == original_snapshot_id
        assert active_snapshot.parent_snapshot_id is None
        assert active_snapshot.sha256 != original_sha256
        assert active_snapshot.payload_json["concepts"][0]["concept_key"] == (
            "incident_response_latency"
        )


def test_ontology_extension_snapshot_version_is_immutable(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts: []
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
"""
    )
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        base_snapshot = get_active_semantic_ontology_snapshot(session)

        persist_semantic_ontology_snapshot(
            session,
            {
                "registry_name": "portable_upper_ontology",
                "registry_version": "portable-upper-ontology-v2",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "categories": [],
                "concepts": [
                    {
                        "concept_key": "incident_response_latency",
                        "preferred_label": "Incident Response Latency",
                        "aliases": ["response latency"],
                    }
                ],
                "relations": [
                    {
                        "relation_key": "document_mentions_concept",
                        "preferred_label": "Document Mentions Concept",
                    }
                ],
            },
            source_kind=SemanticOntologySourceKind.ONTOLOGY_EXTENSION_APPLY.value,
            parent_snapshot_id=base_snapshot.id,
            activate=False,
        )

        with pytest.raises(ValueError, match="immutable"):
            persist_semantic_ontology_snapshot(
                session,
                {
                    "registry_name": "portable_upper_ontology",
                    "registry_version": "portable-upper-ontology-v2",
                    "upper_ontology_version": "portable-upper-ontology-v1",
                    "categories": [],
                    "concepts": [
                        {
                            "concept_key": "vendor_escalation_owner",
                            "preferred_label": "Vendor Escalation Owner",
                            "aliases": ["escalation owner"],
                        }
                    ],
                    "relations": [
                        {
                            "relation_key": "document_mentions_concept",
                            "preferred_label": "Document Mentions Concept",
                        }
                    ],
                },
                source_kind=SemanticOntologySourceKind.ONTOLOGY_EXTENSION_APPLY.value,
                parent_snapshot_id=base_snapshot.id,
                activate=False,
            )


def test_semantic_graph_snapshot_version_is_immutable(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts: []
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
  - relation_key: concept_related_to_concept
    preferred_label: Concept Related To Concept
"""
    )
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        ontology_snapshot = get_active_semantic_ontology_snapshot(session)
        persist_semantic_graph_snapshot(
            session,
            {
                "graph_name": "workspace_semantic_graph",
                "graph_version": "portable-upper-ontology-v1.graph.1",
                "ontology_snapshot_id": str(ontology_snapshot.id),
                "nodes": [],
                "edges": [],
            },
            source_kind=SemanticGraphSourceKind.GRAPH_PROMOTION_APPLY.value,
            activate=False,
        )

        with pytest.raises(ValueError, match="immutable"):
            persist_semantic_graph_snapshot(
                session,
                {
                    "graph_name": "workspace_semantic_graph",
                    "graph_version": "portable-upper-ontology-v1.graph.1",
                    "ontology_snapshot_id": str(ontology_snapshot.id),
                    "nodes": [],
                    "edges": [
                        {
                            "edge_id": (
                                "graph_edge:concept_related_to_concept:"
                                "concept:incident_response_latency:"
                                "concept:vendor_escalation_owner"
                            ),
                            "relation_key": "concept_related_to_concept",
                        }
                    ],
                },
                source_kind=SemanticGraphSourceKind.GRAPH_PROMOTION_APPLY.value,
                activate=False,
            )


def test_semantic_reviews_survive_additive_registry_version_bump(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """registry_name: semantics_layer_foundation
registry_version: semantics-layer-foundation-alpha.2
categories:
  - category_key: integration_governance
    preferred_label: Integration Governance
    scope_note: Controls, thresholds, and governance mechanisms for integration decisions.
  - category_key: system_representation
    preferred_label: System Representation
    scope_note: Representations that communicate system structure, flow, or architecture.
concepts:
  - concept_key: integration_threshold
    preferred_label: Integration Threshold
    scope_note: Threshold guidance or threshold matrices used to govern integration decisions.
    category_keys:
      - integration_governance
    aliases:
      - integration threshold
      - threshold guidance
  - concept_key: system_diagram
    preferred_label: System Diagram
    scope_note: Figures or diagrams that communicate a system structure, flow, or arrangement.
    category_keys:
      - system_representation
    aliases:
      - system diagram
      - architecture diagram
"""
    )
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

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
    document_id = create_response.json()["document_id"]
    original_run_id = UUID(create_response.json()["run_id"])

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))

    first_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert first_semantics.status_code == 200
    first_payload = first_semantics.json()
    threshold_assertion = next(
        assertion
        for assertion in first_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    threshold_binding = threshold_assertion["category_bindings"][0]

    assertion_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{threshold_assertion['assertion_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Carry this approval across additive registry versions.",
            "reviewed_by": "semantic-operator",
        },
    )
    assert assertion_review_response.status_code == 200

    binding_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertion-category-bindings/{threshold_binding['binding_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Carry this binding approval across additive registry versions.",
            "reviewed_by": "semantic-operator",
        },
    )
    assert binding_review_response.status_code == 200

    registry_path.write_text(
        """registry_name: semantics_layer_foundation
registry_version: semantics-layer-foundation-alpha.3
categories:
  - category_key: integration_governance
    preferred_label: Integration Governance
    scope_note: Controls, thresholds, and governance mechanisms for integration decisions.
  - category_key: system_representation
    preferred_label: System Representation
    scope_note: Representations that communicate system structure, flow, or architecture.
concepts:
  - concept_key: integration_threshold
    preferred_label: Integration Threshold
    scope_note: Threshold guidance or threshold matrices used to govern integration decisions.
    category_keys:
      - integration_governance
    aliases:
      - integration threshold
      - threshold guidance
      - integration control threshold
  - concept_key: system_diagram
    preferred_label: System Diagram
    scope_note: Figures or diagrams that communicate a system structure, flow, or arrangement.
    category_keys:
      - system_representation
    aliases:
      - system diagram
      - architecture diagram
"""
    )
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    reprocess_response = client.post(f"/documents/{document_id}/reprocess")
    assert reprocess_response.status_code == 202
    rerun_id = UUID(reprocess_response.json()["run_id"])
    assert rerun_id != original_run_id

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))

    latest_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert latest_semantics.status_code == 200
    latest_payload = latest_semantics.json()
    assert latest_payload["registry_version"] == "semantics-layer-foundation-alpha.3"
    latest_threshold_assertion = next(
        assertion
        for assertion in latest_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert latest_threshold_assertion["review_status"] == "approved"
    assert latest_threshold_assertion["details"]["review_overlay"]["review_note"] == (
        "Carry this approval across additive registry versions."
    )
    assert latest_threshold_assertion["category_bindings"][0]["review_status"] == "approved"
    assert (
        latest_threshold_assertion["category_bindings"][0]["details"]["review_overlay"][
            "review_note"
        ]
        == "Carry this binding approval across additive registry versions."
    )
