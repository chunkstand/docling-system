from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import DocumentRunSemanticPass, SemanticFact
from app.services.docling_parser import ParsedChunk, ParsedDocument
from app.services.semantic_registry import clear_semantic_registry_cache
from tests.integration.pdf_fixtures import valid_test_pdf_bytes

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


class StubParser:
    def __init__(self, parsed_document: ParsedDocument) -> None:
        self.parsed_document = parsed_document

    def parse_pdf(self, source_path, *, source_filename=None) -> ParsedDocument:
        assert source_path.exists()
        assert source_filename
        return self.parsed_document


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """registry_name: semantic_backfill_registry
registry_version: semantic-backfill-registry-v1
categories:
  - category_key: integration_governance
    preferred_label: Integration Governance
concepts:
  - concept_key: integration_threshold
    preferred_label: Integration Threshold
    category_keys:
      - integration_governance
    aliases:
      - integration threshold
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
    domain_entity_types:
      - document
    range_entity_types:
      - concept
    symmetric: false
    allow_literal_object: false
"""
    )


def _write_empty_semantic_eval_corpus(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """corpus_name: semantic_backfill
eval_version: 2
documents: []
"""
    )


def _build_parsed_document() -> ParsedDocument:
    chunk_text = "The integration threshold keeps the report workflow governed."
    exported_payload = {
        "name": "Backfill Report",
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [],
        "pictures": [],
    }
    return ParsedDocument(
        title="Backfill Report",
        page_count=1,
        yaml_text="document: backfill-report\n",
        docling_json=json.dumps(exported_payload, indent=2),
        chunks=[
            ParsedChunk(
                chunk_index=0,
                text=chunk_text,
                heading="Section 1",
                page_from=1,
                page_to=1,
                metadata={"label": "text"},
            )
        ],
        tables=[],
        raw_table_segments=[],
        figures=[],
    )


def test_semantic_backfill_runs_over_existing_active_run(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    eval_corpus_path = tmp_path / "docs" / "semantic_evaluation_corpus.yaml"
    _write_registry(registry_path)
    _write_empty_semantic_eval_corpus(eval_corpus_path)
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH", str(eval_corpus_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    client = postgres_integration_harness.client
    create_response = client.post(
        "/documents",
        files={
            "file": (
                "backfill-report.pdf",
                valid_test_pdf_bytes(),
                "application/pdf",
            )
        },
    )
    assert create_response.status_code == 202
    document_id = UUID(create_response.json()["document_id"])
    original_run_id = UUID(create_response.json()["run_id"])
    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == original_run_id

    with postgres_integration_harness.session_factory() as session:
        semantic_pass_ids = list(
            session.execute(select(DocumentRunSemanticPass.id)).scalars().all()
        )
        assert semantic_pass_ids
        session.query(DocumentRunSemanticPass).delete()
        session.commit()

    status_response = client.get("/semantics/backfill/status")
    assert status_response.status_code == 200
    status = status_response.json()
    assert status["active_document_count"] == 1
    assert status["missing_current_pass_count"] == 1
    assert status["current_registry"]["concept_count"] == 1

    backfill_response = client.post(
        "/semantics/backfill",
        json={
            "document_ids": [str(document_id)],
            "limit": 1,
            "build_fact_graphs": True,
            "minimum_review_status": "candidate",
        },
    )
    assert backfill_response.status_code == 200
    payload = backfill_response.json()
    assert payload["processed_document_count"] == 1
    assert payload["semantic_pass_count"] == 1
    assert payload["fact_graph_count"] == 1
    assert payload["documents"][0]["assertion_count"] == 1
    assert payload["documents"][0]["fact_count"] == 1
    assert payload["status_after"]["active_current_pass_count"] == 1
    assert payload["status_after"]["fact_count"] == 1

    with postgres_integration_harness.session_factory() as session:
        assert session.execute(select(SemanticFact)).scalars().first() is not None
