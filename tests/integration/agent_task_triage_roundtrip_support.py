from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select

from app.db.models import Document, DocumentRunEvaluation, DocumentRunEvaluationQuery
from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedFigure,
    ParsedTable,
    ParsedTableSegment,
)
from tests.integration.pdf_fixtures import valid_test_pdf_bytes


class StubParser:
    def __init__(self, parsed_document: ParsedDocument) -> None:
        self.parsed_document = parsed_document

    def parse_pdf(self, source_path, *, source_filename=None) -> ParsedDocument:
        assert source_path.exists()
        assert source_filename
        return self.parsed_document


def _build_parsed_document(*, title: str | None = "Integration Report") -> ParsedDocument:
    chunk_text = "Integration threshold guidance keeps active retrieval grounded."
    table_rows = [
        ["Tier", "Threshold"],
        ["alpha", "integration threshold"],
    ]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title="Integration Threshold Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        metadata={
            "caption": "Integration Threshold Matrix",
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
        title="Integration Threshold Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        search_text="Integration Threshold Matrix integration threshold alpha",
        preview_text="Tier | Threshold\nalpha | integration threshold",
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
            "source_titles": ["Integration Threshold Matrix"],
        },
        segments=[segment],
    )
    figure = ParsedFigure(
        figure_index=0,
        source_figure_ref="figure-0",
        caption="Integration system diagram",
        heading="Section 1",
        page_from=1,
        page_to=1,
        confidence=0.99,
        metadata={
            "caption_resolution_source": "explicit_ref",
            "caption_candidates": ["Integration system diagram"],
            "caption_attachment_confidence": 1.0,
            "source_confidence": 0.99,
            "annotations": [],
            "provenance": [
                {
                    "page_no": 1,
                    "bbox": {"l": 0, "t": 0, "r": 1, "b": 1, "coord_origin": "TOPLEFT"},
                    "charspan": [0, 1],
                }
            ],
            "source_artifact_sha256": "figure-sha",
        },
    )
    exported_payload = {
        "name": title,
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [{"self_ref": "figure-0", "captions": ["caption-0"], "prov": []}],
    }
    return ParsedDocument(
        title=title,
        page_count=1,
        yaml_text="document: integration-report\n",
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
        figures=[figure],
    )


def _create_processed_document(postgres_integration_harness) -> tuple[UUID, UUID]:
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
    document_id = UUID(create_response.json()["document_id"])
    run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == run_id

    with postgres_integration_harness.session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        assert document.active_run_id == run_id
        assert document.latest_run_id == run_id

        evaluation = (
            session.execute(
                select(DocumentRunEvaluation)
                .where(DocumentRunEvaluation.run_id == run_id)
                .order_by(DocumentRunEvaluation.created_at.desc())
            )
            .scalars()
            .first()
        )
        assert evaluation is not None
        assert evaluation.status == "completed"

        query_rows = (
            session.execute(
                select(DocumentRunEvaluationQuery).where(
                    DocumentRunEvaluationQuery.evaluation_id == evaluation.id
                )
            )
            .scalars()
            .all()
        )
        assert query_rows

    return document_id, run_id
