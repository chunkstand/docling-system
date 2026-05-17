from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import app.services.semantics as semantics
from app.services import semantic_pass_reads as read_owners
from app.services import semantic_pass_source_records as source_record_owner


def test_semantics_facade_forwards_read_owner_symbols() -> None:
    assert semantics.SemanticSourceItem is read_owners.SemanticSourceItem
    assert semantics.build_semantic_sources is read_owners.build_semantic_sources
    assert semantics.get_active_semantic_pass_detail is read_owners.get_active_semantic_pass_detail

    with open(semantics.__file__, encoding="utf-8") as handle:
        facade_line_count = sum(1 for _ in handle)

    assert facade_line_count <= 600


def test_read_root_reexports_source_record_owner_symbols() -> None:
    assert read_owners.SemanticSourceItem is source_record_owner.SemanticSourceItem
    assert read_owners.SemanticReviewOverlay is source_record_owner.SemanticReviewOverlay
    assert read_owners.assertion_records is source_record_owner.assertion_records
    assert (
        read_owners.concept_category_binding_records
        is source_record_owner.concept_category_binding_records
    )
    assert (
        read_owners.details_with_review_overlay
        is source_record_owner.details_with_review_overlay
    )
    assert read_owners.build_semantic_sources is source_record_owner.build_semantic_sources
    assert (
        read_owners.materialize_semantic_assertions
        is source_record_owner.materialize_semantic_assertions
    )
    assert read_owners.source_artifact_api_path is source_record_owner.source_artifact_api_path

    with open(read_owners.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 400


def test_details_with_review_overlay_adds_and_clears_overlay() -> None:
    overlay = read_owners.SemanticReviewOverlay(
        review_id=uuid4(),
        review_status="approved",
        review_note="confirmed",
        reviewed_by="operator@example.com",
        created_at=datetime(2026, 5, 13, tzinfo=UTC),
    )

    payload = read_owners.details_with_review_overlay({"stable": True}, overlay)
    cleared = read_owners.details_with_review_overlay(
        {"review_overlay": {"old": "value"}, "stable": True},
        None,
    )

    assert payload["review_overlay"]["review_status"] == "approved"
    assert payload["review_overlay"]["review_note"] == "confirmed"
    assert payload["stable"] is True
    assert "review_overlay" not in cleared
    assert cleared["stable"] is True


def test_source_artifact_api_path_routes_table_and_figure_sources() -> None:
    document_id = uuid4()
    table_id = uuid4()
    figure_id = uuid4()

    assert (
        read_owners.source_artifact_api_path(
            document_id,
            source_type="table",
            table_id=table_id,
            figure_id=None,
        )
        == f"/documents/{document_id}/tables/{table_id}/artifacts/json"
    )
    assert (
        read_owners.source_artifact_api_path(
            document_id,
            source_type="figure",
            table_id=None,
            figure_id=figure_id,
        )
        == f"/documents/{document_id}/figures/{figure_id}/artifacts/json"
    )
    assert (
        read_owners.source_artifact_api_path(
            document_id,
            source_type="chunk",
            table_id=None,
            figure_id=None,
        )
        is None
    )


def test_build_semantic_sources_uses_document_figure_contract_fields(monkeypatch) -> None:
    figure = SimpleNamespace(
        id=uuid4(),
        figure_index=2,
        source_figure_ref="figure-2",
        caption="Integration system diagram",
        heading="Section 2",
        page_from=3,
        page_to=3,
        metadata_json={"caption_resolution_source": "explicit_ref"},
        json_path="storage/figure.json",
        yaml_path="storage/figure.yaml",
    )

    class _ScalarResult:
        def __init__(self, items) -> None:
            self._items = items

        def scalars(self):
            return self

        def all(self):
            return list(self._items)

    class _Session:
        def __init__(self) -> None:
            self._calls = 0

        def execute(self, _statement):
            self._calls += 1
            if self._calls < 3:
                return _ScalarResult([])
            return _ScalarResult([figure])

    sources = read_owners.build_semantic_sources(_Session(), uuid4())

    assert len(sources) == 1
    source = sources[0]
    assert source.source_type == "figure"
    assert source.source_label == "Integration system diagram"
    assert source.excerpt == "Integration system diagram"
    assert source.details["source_figure_ref"] == "figure-2"
    assert "figure_type" not in source.details
