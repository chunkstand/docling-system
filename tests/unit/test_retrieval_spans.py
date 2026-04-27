from __future__ import annotations

import uuid

from app.core.time import utcnow
from app.db.models import DocumentChunk, DocumentTable, RetrievalEvidenceSpan
from app.services.retrieval_spans import (
    MULTIVECTOR_WORD_WINDOW,
    SPAN_WORD_WINDOW,
    build_chunk_span_specs,
    build_span_multivector_specs,
    build_table_span_specs,
)


def test_build_chunk_span_specs_are_windowed_and_hashed() -> None:
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        chunk_index=7,
        text=" ".join(f"token{i}" for i in range(SPAN_WORD_WINDOW + 25)),
        heading="Evidence",
        page_from=3,
        page_to=4,
        metadata_json={"label": "body"},
        embedding=None,
        created_at=utcnow(),
    )

    spans = build_chunk_span_specs(chunk)

    assert len(spans) == 2
    assert spans[0].source_type == "chunk"
    assert spans[0].source_id == chunk.id
    assert spans[0].chunk_id == chunk.id
    assert spans[0].table_id is None
    assert spans[0].span_index == 0
    assert spans[0].content_sha256 != spans[1].content_sha256
    assert spans[0].source_snapshot_sha256 == spans[1].source_snapshot_sha256
    assert spans[0].metadata["source_chunk_index"] == 7


def test_build_table_span_specs_carry_lineage_metadata() -> None:
    table = DocumentTable(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        table_index=2,
        title="Threshold Matrix",
        logical_table_key="logical-key",
        table_version=3,
        supersedes_table_id=None,
        lineage_group="lineage",
        heading="Section 2",
        page_from=5,
        page_to=6,
        row_count=2,
        col_count=2,
        status="validated",
        search_text="Threshold Matrix alpha beta gamma",
        preview_text="alpha | beta",
        metadata_json={"audit": {"search_text_sha256": "sha"}},
        embedding=None,
        json_path=None,
        yaml_path=None,
        created_at=utcnow(),
    )

    spans = build_table_span_specs(table)

    assert len(spans) == 1
    assert spans[0].source_type == "table"
    assert spans[0].table_id == table.id
    assert spans[0].chunk_id is None
    assert spans[0].heading == "Threshold Matrix Section 2"
    assert spans[0].metadata["source_table_index"] == 2
    assert spans[0].metadata["logical_table_key"] == "logical-key"


def test_build_span_multivector_specs_are_windowed_and_traceable() -> None:
    span = RetrievalEvidenceSpan(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        source_type="chunk",
        source_id=uuid.uuid4(),
        chunk_id=uuid.uuid4(),
        table_id=None,
        span_index=0,
        span_text=" ".join(f"signal{i}" for i in range(MULTIVECTOR_WORD_WINDOW + 8)),
        heading="Evidence",
        page_from=1,
        page_to=1,
        content_sha256="span-sha",
        source_snapshot_sha256="snapshot-sha",
        metadata_json={},
        embedding=None,
        created_at=utcnow(),
    )

    vectors = build_span_multivector_specs(span)

    assert len(vectors) == 2
    assert vectors[0].retrieval_evidence_span_id == span.id
    assert vectors[0].source_type == "chunk"
    assert vectors[0].token_start == 0
    assert vectors[0].token_end == MULTIVECTOR_WORD_WINDOW
    assert vectors[0].content_sha256 != vectors[1].content_sha256
    assert vectors[0].metadata["source_span_content_sha256"] == "span-sha"
    assert vectors[0].metadata["source_snapshot_sha256"] == "snapshot-sha"
