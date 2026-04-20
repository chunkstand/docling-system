from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.models import Document
from app.services.semantic_bootstrap import discover_semantic_bootstrap_candidates
from app.services.semantic_registry import normalize_semantic_text, semantic_registry_from_payload
from app.services.semantics import SemanticSourceItem


class FakeSession:
    def __init__(self, *, documents=None) -> None:
        self.documents = documents or {}

    def get(self, model, key):
        if model.__name__ == "Document":
            return self.documents.get(key)
        return None


def _document(*, document_id: UUID, source_filename: str, title: str) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=document_id,
        source_filename=source_filename,
        source_path=f"/tmp/{source_filename}",
        sha256=f"sha-{source_filename}",
        mime_type="application/pdf",
        title=title,
        page_count=1,
        active_run_id=uuid4(),
        latest_run_id=uuid4(),
        created_at=now,
        updated_at=now,
    )


def _registry():
    return semantic_registry_from_payload(
        {
            "registry_name": "semantic_registry",
            "registry_version": "semantics-layer-foundation-alpha.4",
            "categories": [],
            "concepts": [
                {
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "aliases": ["integration threshold"],
                }
            ],
        }
    )


def test_discover_semantic_bootstrap_candidates_finds_domain_agnostic_phrase(monkeypatch) -> None:
    document_id = uuid4()
    document = _document(
        document_id=document_id,
        source_filename="incident-review.pdf",
        title="Incident Review",
    )
    session = FakeSession(documents={document_id: document})

    monkeypatch.setattr(
        "app.services.semantic_bootstrap.get_semantic_registry",
        lambda session: _registry(),
    )
    monkeypatch.setattr(
        "app.services.semantic_bootstrap._build_semantic_sources",
        lambda _session, _run_id: [
            SemanticSourceItem(
                source_type="chunk",
                source_locator="chunk-1",
                chunk_id=uuid4(),
                table_id=None,
                figure_id=None,
                page_from=1,
                page_to=1,
                normalized_text=normalize_semantic_text(
                    "Incident response latency target remains under fifteen minutes. "
                    "The incident response latency dashboard is reviewed weekly."
                ),
                excerpt="Incident response latency target remains under fifteen minutes.",
                source_label="Operations Summary",
                source_artifact_path=None,
                source_artifact_sha256="chunk-sha",
                details={},
            ),
            SemanticSourceItem(
                source_type="table",
                source_locator="table-1",
                chunk_id=None,
                table_id=uuid4(),
                figure_id=None,
                page_from=1,
                page_to=1,
                normalized_text=normalize_semantic_text("Metric incident response latency target"),
                excerpt="Metric | Incident response latency target",
                source_label="Latency Metrics",
                source_artifact_path="/tmp/table.json",
                source_artifact_sha256="table-sha",
                details={},
            ),
        ],
    )

    report = discover_semantic_bootstrap_candidates(
        session,
        document_ids=[document_id],
        max_candidates=5,
        min_document_count=1,
        min_source_count=2,
        min_phrase_tokens=2,
        max_phrase_tokens=4,
        exclude_existing_registry_terms=True,
    )

    candidate = next(
        row for row in report["candidates"] if row["concept_key"] == "incident_response_latency"
    )
    assert candidate["preferred_label"] == "Incident Response Latency"
    assert candidate["epistemic_status"] == "candidate_bootstrap"
    assert candidate["source_types"] == ["chunk", "table"]
    assert any(metric["stakeholder"] == "Figay" for metric in report["success_metrics"])
    assert any(metric["stakeholder"] == "Sutton" for metric in report["success_metrics"])


def test_discover_semantic_bootstrap_candidates_sorts_document_ids(monkeypatch) -> None:
    first_document_id = UUID("00000000-0000-0000-0000-0000000000b2")
    second_document_id = UUID("00000000-0000-0000-0000-0000000000a1")
    first_document = _document(
        document_id=first_document_id,
        source_filename="incident-review-two.pdf",
        title="Incident Review Two",
    )
    second_document = _document(
        document_id=second_document_id,
        source_filename="incident-review-one.pdf",
        title="Incident Review One",
    )
    session = FakeSession(
        documents={
            first_document_id: first_document,
            second_document_id: second_document,
        }
    )

    monkeypatch.setattr(
        "app.services.semantic_bootstrap.get_semantic_registry",
        lambda session: _registry(),
    )
    monkeypatch.setattr(
        "app.services.semantic_bootstrap._build_semantic_sources",
        lambda _session, _run_id: [
            SemanticSourceItem(
                source_type="chunk",
                source_locator="chunk-1",
                chunk_id=uuid4(),
                table_id=None,
                figure_id=None,
                page_from=1,
                page_to=1,
                normalized_text=normalize_semantic_text(
                    "Incident response latency target remains under fifteen minutes."
                ),
                excerpt="Incident response latency target remains under fifteen minutes.",
                source_label="Operations Summary",
                source_artifact_path=None,
                source_artifact_sha256="chunk-sha",
                details={},
            ),
            SemanticSourceItem(
                source_type="table",
                source_locator="table-1",
                chunk_id=None,
                table_id=uuid4(),
                figure_id=None,
                page_from=1,
                page_to=1,
                normalized_text=normalize_semantic_text("Metric incident response latency target"),
                excerpt="Metric | Incident response latency target",
                source_label="Latency Metrics",
                source_artifact_path="/tmp/table.json",
                source_artifact_sha256="table-sha",
                details={},
            ),
        ],
    )

    report = discover_semantic_bootstrap_candidates(
        session,
        document_ids=[first_document_id, second_document_id],
        max_candidates=5,
        min_document_count=1,
        min_source_count=2,
        min_phrase_tokens=2,
        max_phrase_tokens=4,
        exclude_existing_registry_terms=True,
    )

    candidate = next(
        row for row in report["candidates"] if row["concept_key"] == "incident_response_latency"
    )
    assert candidate["document_ids"] == sorted(
        [first_document_id, second_document_id],
        key=str,
    )
