from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import app.services.semantics as semantics
from app.services import semantic_pass_artifacts as artifact_owner
from app.services import semantic_pass_lifecycle as lifecycle
from app.services import semantic_pass_reviews as review_owner


def test_semantics_facade_forwards_lifecycle_entrypoints() -> None:
    assert semantics.execute_semantic_pass is lifecycle.execute_semantic_pass
    assert semantics.review_active_semantic_assertion is lifecycle.review_active_semantic_assertion
    assert (
        semantics.review_active_semantic_assertion_category_binding
        is lifecycle.review_active_semantic_assertion_category_binding
    )
    assert semantics.latest_concept_review_overlays is lifecycle.latest_concept_review_overlays


def test_lifecycle_root_reexports_review_owner_entrypoints() -> None:
    assert (
        lifecycle.review_active_semantic_assertion
        is review_owner.review_active_semantic_assertion
    )
    assert (
        lifecycle.review_active_semantic_assertion_category_binding
        is review_owner.review_active_semantic_assertion_category_binding
    )
    assert lifecycle.latest_concept_review_overlays is review_owner.latest_concept_review_overlays
    assert lifecycle.latest_category_review_overlays is review_owner.latest_category_review_overlays
    assert lifecycle._semantic_artifact_payload is artifact_owner.semantic_artifact_payload

    with open(lifecycle.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 600


def test_semantic_artifact_payload_includes_registry_evaluation_and_continuity() -> None:
    now = datetime(2026, 5, 13, tzinfo=UTC)
    payload = lifecycle._semantic_artifact_payload(
        document=SimpleNamespace(id=uuid4()),
        run=SimpleNamespace(id=uuid4()),
        semantic_pass=SimpleNamespace(
            id=uuid4(),
            ontology_snapshot_id=uuid4(),
            baseline_run_id=uuid4(),
            baseline_semantic_pass_id=uuid4(),
            status="completed",
            created_at=now,
            completed_at=now,
        ),
        registry=SimpleNamespace(
            registry_name="semantic_registry",
            registry_version="semantics-layer-foundation-alpha.4",
            sha256="registry-sha",
            upper_ontology_version="upper-v1",
        ),
        assertions=[{"concept_key": "integration_threshold"}],
        concept_category_bindings=[{"category_key": "integration_governance"}],
        summary={"assertion_count": 1},
        evaluation_status="completed",
        evaluation_fixture_name="integration-fixture",
        evaluation_summary={"all_expectations_passed": True},
        continuity_summary={"has_baseline": True},
        artifact_sha256="artifact-sha",
    )

    assert payload["schema_name"] == lifecycle.SEMANTIC_ARTIFACT_SCHEMA_NAME
    assert payload["schema_version"] == lifecycle.SEMANTIC_ARTIFACT_SCHEMA_VERSION
    assert payload["registry"]["version"] == "semantics-layer-foundation-alpha.4"
    assert payload["evaluation"]["status"] == "completed"
    assert payload["continuity"]["has_baseline"] is True
