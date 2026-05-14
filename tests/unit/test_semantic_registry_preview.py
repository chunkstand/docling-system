from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import app.services.semantics as semantics
from app.services import semantic_registry_preview as preview
from app.services.semantic_pass_reads import (
    SemanticAssertionMaterialization,
    SemanticEvidenceMaterialization,
    SemanticReviewOverlay,
    SemanticSourceItem,
)
from app.services.semantic_registry import semantic_registry_from_payload


def _registry():
    return semantic_registry_from_payload(
        {
            "registry_name": "semantic_registry",
            "registry_version": "semantics-layer-foundation-alpha.4",
            "categories": [
                {
                    "category_key": "integration_governance",
                    "preferred_label": "Integration Governance",
                }
            ],
            "concepts": [
                {
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "category_keys": ["integration_governance"],
                    "aliases": ["integration threshold"],
                }
            ],
        }
    )


def test_semantics_facade_forwards_preview_owner_symbols() -> None:
    assert semantics.preview_assertions is preview.preview_assertions
    assert semantics.preview_concept_category_bindings is preview.preview_concept_category_bindings
    assert semantics.semantic_evaluation_result is preview.semantic_evaluation_result


def test_preview_assertions_applies_review_overlay_details() -> None:
    registry = _registry()
    source = SemanticSourceItem(
        source_type="chunk",
        source_locator=str(uuid4()),
        chunk_id=uuid4(),
        table_id=None,
        figure_id=None,
        page_from=1,
        page_to=1,
        normalized_text="integration threshold",
        excerpt="Integration threshold remains in force.",
        source_label="Section 1",
        source_artifact_path=None,
        source_artifact_sha256="chunk-sha",
        details={"chunk_index": 0},
    )
    materialization = SemanticAssertionMaterialization(
        concept_definition=registry.concepts[0],
        matched_terms={"integration threshold"},
        source_types={"chunk"},
        evidence=[
            SemanticEvidenceMaterialization(
                source_item=source,
                matched_terms=["integration threshold"],
            )
        ],
    )
    concept_overlay = SemanticReviewOverlay(
        review_id=uuid4(),
        review_status="approved",
        review_note="confirmed",
        reviewed_by="operator@example.com",
        created_at=SimpleNamespace(isoformat=lambda: "2026-05-13T00:00:00+00:00"),
    )
    category_overlay = SemanticReviewOverlay(
        review_id=uuid4(),
        review_status="approved",
        review_note="category confirmed",
        reviewed_by="operator@example.com",
        created_at=SimpleNamespace(isoformat=lambda: "2026-05-13T00:00:00+00:00"),
    )

    assertions = preview.preview_assertions(
        [materialization],
        concept_review_overlays={"integration_threshold": concept_overlay},
        category_review_overlays={
            ("integration_threshold", "integration_governance"): category_overlay
        },
        registry=registry,
    )

    assert assertions[0]["review_status"] == "approved"
    assert assertions[0]["details"]["review_overlay"]["review_note"] == "confirmed"
    assert (
        assertions[0]["category_bindings"][0]["details"]["review_overlay"]["review_status"]
        == "approved"
    )


def test_semantic_evaluation_result_skips_without_fixture(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.services.semantic_registry_preview.get_settings",
        lambda: SimpleNamespace(semantic_evaluation_corpus_path=tmp_path / "missing.yaml"),
    )

    status, fixture_name, summary = preview.semantic_evaluation_result(
        SimpleNamespace(source_filename="integration-shadow.pdf"),
        [],
        [],
    )

    assert status == "skipped"
    assert fixture_name is None
    assert summary["reason"] == "no_semantic_fixture"
