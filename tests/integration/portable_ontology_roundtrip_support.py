from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest
import yaml

from app.core.config import get_settings
from app.db.public.semantic_memory import SemanticOntologySourceKind
from app.schemas.agent_task_core import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedTable,
    ParsedTableSegment,
)
from app.services.semantic_registry import (
    clear_semantic_registry_cache,
    ensure_workspace_semantic_registry,
    get_active_semantic_ontology_snapshot,
    persist_semantic_ontology_snapshot,
)
from tests.integration.pdf_fixtures import valid_test_pdf_bytes

INTEGRATION_SKIP_MARK = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)
DEFAULT_APPROVER = "ontology-operator@example.com"


class StubParser:
    def __init__(self, parsed_document: ParsedDocument) -> None:
        self.parsed_document = parsed_document

    def parse_pdf(self, source_path, *, source_filename=None) -> ParsedDocument:
        assert source_path.exists()
        assert source_filename
        return self.parsed_document


def _write_upper_ontology(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "registry_name": "portable_upper_ontology",
                "registry_version": "portable-upper-ontology-v1",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "categories": [],
                "concepts": [],
                "relations": [
                    {
                        "relation_key": "document_mentions_concept",
                        "preferred_label": "Document Mentions Concept",
                        "domain_entity_types": ["document"],
                        "range_entity_types": ["concept"],
                        "symmetric": False,
                        "allow_literal_object": False,
                    },
                    {
                        "relation_key": "concept_related_to_concept",
                        "preferred_label": "Concept Related To Concept",
                        "domain_entity_types": ["concept"],
                        "range_entity_types": ["concept"],
                        "symmetric": True,
                        "allow_literal_object": False,
                        "inverse_relation_key": "concept_related_to_concept",
                    },
                    {
                        "relation_key": "claim_supported_by_evidence",
                        "preferred_label": "Claim Supported By Evidence",
                        "domain_entity_types": ["claim"],
                        "range_entity_types": ["evidence"],
                        "symmetric": False,
                        "allow_literal_object": False,
                    },
                    {
                        "relation_key": "evidence_cites_source",
                        "preferred_label": "Evidence Cites Source",
                        "domain_entity_types": ["evidence"],
                        "range_entity_types": ["source"],
                        "symmetric": False,
                        "allow_literal_object": False,
                    },
                    {
                        "relation_key": "document_cites_source",
                        "preferred_label": "Document Cites Source",
                        "domain_entity_types": ["document"],
                        "range_entity_types": ["source"],
                        "symmetric": False,
                        "allow_literal_object": False,
                    },
                    {
                        "relation_key": "table_reports_measurement",
                        "preferred_label": "Table Reports Measurement",
                        "domain_entity_types": ["table"],
                        "range_entity_types": ["measurement"],
                        "symmetric": False,
                        "allow_literal_object": False,
                    },
                    {
                        "relation_key": "measurement_has_unit",
                        "preferred_label": "Measurement Has Unit",
                        "domain_entity_types": ["measurement"],
                        "range_entity_types": ["unit"],
                        "symmetric": False,
                        "allow_literal_object": False,
                    },
                    {
                        "relation_key": "obligation_applies_to_actor",
                        "preferred_label": "Obligation Applies To Actor",
                        "domain_entity_types": ["obligation"],
                        "range_entity_types": ["actor"],
                        "symmetric": False,
                        "allow_literal_object": False,
                    },
                    {
                        "relation_key": "event_occurs_before_event",
                        "preferred_label": "Event Occurs Before Event",
                        "domain_entity_types": ["event"],
                        "range_entity_types": ["event"],
                        "symmetric": False,
                        "allow_literal_object": False,
                    },
                ],
                "entity_types": [
                    {"entity_type": "document", "preferred_label": "Document"},
                    {"entity_type": "concept", "preferred_label": "Concept"},
                    {"entity_type": "literal", "preferred_label": "Literal"},
                    {"entity_type": "claim", "preferred_label": "Claim"},
                    {"entity_type": "evidence", "preferred_label": "Evidence"},
                    {"entity_type": "source", "preferred_label": "Source"},
                    {"entity_type": "table", "preferred_label": "Table"},
                    {"entity_type": "measurement", "preferred_label": "Measurement"},
                    {"entity_type": "unit", "preferred_label": "Unit"},
                    {"entity_type": "actor", "preferred_label": "Actor"},
                    {"entity_type": "obligation", "preferred_label": "Obligation"},
                    {"entity_type": "event", "preferred_label": "Event"},
                ],
            },
            sort_keys=False,
        )
    )


def _write_empty_semantic_eval_corpus(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """corpus_name: portable_semantic_eval
eval_version: 2
documents: []
"""
    )


def bootstrap_portable_ontology_env(
    monkeypatch,
    tmp_path: Path,
    *,
    set_registry_path: bool,
) -> Path:
    upper_ontology_path = tmp_path / "config" / "upper_ontology.yaml"
    eval_corpus_path = tmp_path / "docs" / "semantic_evaluation_corpus.yaml"
    _write_upper_ontology(upper_ontology_path)
    _write_empty_semantic_eval_corpus(eval_corpus_path)
    monkeypatch.delenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", raising=False)
    if set_registry_path:
        monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(upper_ontology_path))
    monkeypatch.setenv("DOCLING_SYSTEM_UPPER_ONTOLOGY_PATH", str(upper_ontology_path))
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH", str(eval_corpus_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()
    return upper_ontology_path


def build_parsed_document(*, title: str, phrase: str) -> ParsedDocument:
    title_slug = phrase.title()
    chunk_text = (
        f"{title_slug} target remains under active review. "
        f"The {phrase} dashboard is reviewed weekly."
    )
    table_rows = [
        ["Metric", "Target"],
        [title_slug, phrase],
    ]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title=f"{title_slug} Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        metadata={
            "caption": f"{title_slug} Matrix",
            "title_hint": None,
            "segment_label": "table",
            "title_source": "caption",
            "header_rows_retained": 1,
            "header_rows_removed": 0,
            "source_artifact_sha256": "segment-sha",
        },
    )
    table = ParsedTable(
        table_index=0,
        title=f"{title_slug} Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        search_text=f"{title_slug} Matrix {phrase}",
        preview_text=f"Metric | Target\n{title_slug} | {phrase}",
        metadata={
            "is_merged": False,
            "source_segment_count": 1,
            "segment_count": 1,
            "merge_reason": "single_segment",
            "merge_confidence": 1.0,
            "continuation_candidate": False,
            "ambiguous_continuation_candidate": False,
            "repeated_header_rows_removed": False,
            "header_rows_removed_count": 0,
            "title_resolution_source": "caption",
            "merge_sanity_passed": True,
            "header_removal_passed": True,
            "source_segment_indices": [0],
            "source_titles": [f"{title_slug} Matrix"],
        },
        segments=[segment],
    )
    exported_payload = {
        "name": title,
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [],
    }
    return ParsedDocument(
        title=title,
        page_count=1,
        yaml_text=f"document: {title.lower().replace(' ', '-')}\n",
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
        tables=[table],
        raw_table_segments=[segment],
        figures=[],
    )


def process_next_task(postgres_integration_harness) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "portable-ontology-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id


def create_workflow_task(session, *, task_type: str, input: dict, workflow_version: str) -> UUID:
    task = create_agent_task(
        session,
        AgentTaskCreateRequest(
            task_type=task_type,
            input=input,
            workflow_version=workflow_version,
        ),
    )
    return task.task_id


def approve_workflow_task(
    session,
    task_id: UUID,
    *,
    approval_note: str,
    approved_by: str = DEFAULT_APPROVER,
) -> None:
    approve_agent_task(
        session,
        task_id,
        AgentTaskApprovalRequest(
            approved_by=approved_by,
            approval_note=approval_note,
        ),
    )


def seed_workspace_ontology_snapshot(
    postgres_integration_harness,
    *,
    concepts: list[dict[str, object]],
    registry_version: str = "portable-upper-ontology-v1.seeded",
) -> None:
    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        base_snapshot = get_active_semantic_ontology_snapshot(session)
        seeded_payload = dict(base_snapshot.payload_json or {})
        seeded_payload["registry_version"] = registry_version
        seeded_payload["concepts"] = concepts
        persist_semantic_ontology_snapshot(
            session,
            seeded_payload,
            source_kind=SemanticOntologySourceKind.ONTOLOGY_EXTENSION_APPLY.value,
            parent_snapshot_id=base_snapshot.id,
            activate=True,
        )
        session.commit()


def create_document_upload(client, *, source_filename: str) -> tuple[UUID, UUID]:
    response = client.post(
        "/documents",
        files={
            "file": (
                source_filename,
                valid_test_pdf_bytes(),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 202
    payload = response.json()
    return UUID(payload["document_id"]), UUID(payload["run_id"])


def process_document_run(postgres_integration_harness, *, title: str, phrase: str) -> UUID:
    return postgres_integration_harness.process_next_run(
        StubParser(build_parsed_document(title=title, phrase=phrase))
    )
