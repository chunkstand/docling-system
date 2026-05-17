# ruff: noqa: E501
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.db.models import (
    DocumentChunk,
    DocumentFigure,
    DocumentTable,
    DocumentTableSegment,
)
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_records import (
    chunk_payload as _chunk_payload,
)
from app.services.evidence_records import (
    figure_payload as _figure_payload,
)
from app.services.evidence_records import (
    select_by_ids as _select_by_ids,
)
from app.services.evidence_records import (
    table_payload as _table_payload,
)
from app.services.evidence_technical_report_exports import (
    evidence_card_snapshot as _evidence_card_snapshot,
)


def _source_record_payloads_from_semantic_trace(
    session: Session,
    assertion_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chunk_ids = _uuid_values(row.get("chunk_id") for row in assertion_evidence)
    table_ids = _uuid_values(row.get("table_id") for row in assertion_evidence)
    figure_ids = _uuid_values(row.get("figure_id") for row in assertion_evidence)
    chunks_by_id = _select_by_ids(session, DocumentChunk, chunk_ids)
    tables_by_id = _select_by_ids(session, DocumentTable, table_ids)
    figures_by_id = _select_by_ids(session, DocumentFigure, figure_ids)
    segments_by_table_id: dict[Any, list[DocumentTableSegment]] = {
        table_id: [] for table_id in tables_by_id
    }
    if table_ids:
        for segment in session.scalars(
            select(DocumentTableSegment)
            .where(DocumentTableSegment.table_id.in_(table_ids))
            .order_by(
                DocumentTableSegment.table_id.asc(),
                DocumentTableSegment.segment_order.asc(),
                DocumentTableSegment.segment_index.asc(),
            )
        ):
            segments_by_table_id.setdefault(segment.table_id, []).append(segment)

    records: list[dict[str, Any]] = []
    for evidence in assertion_evidence:
        chunk_id = _uuid_or_none(evidence.get("chunk_id"))
        table_id = _uuid_or_none(evidence.get("table_id"))
        figure_id = _uuid_or_none(evidence.get("figure_id"))
        table_payload = (
            _table_payload(
                tables_by_id.get(table_id),
                segments=segments_by_table_id.get(table_id, []),
            )
            if table_id is not None
            else None
        )
        records.append(
            {
                "record_kind": "semantic_assertion_source",
                "evidence_id": evidence.get("evidence_id"),
                "source_type": evidence.get("source_type"),
                "source_locator": evidence.get("source_locator"),
                "source_artifact_sha256": evidence.get("source_artifact_sha256"),
                "chunk": _chunk_payload(chunks_by_id.get(chunk_id)) if chunk_id else None,
                "table": table_payload,
                "figure": _figure_payload(figures_by_id.get(figure_id)) if figure_id else None,
            }
        )
    return records


def _report_evidence_card_source_records(
    evidence_cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "record_kind": "technical_report_evidence_card",
            "evidence_card_id": card.get("evidence_card_id"),
            "evidence_kind": card.get("evidence_kind"),
            "source_type": card.get("source_type"),
            "document_id": card.get("document_id"),
            "run_id": card.get("run_id"),
            "page_from": card.get("page_from"),
            "page_to": card.get("page_to"),
            "source_artifact_api_path": card.get("source_artifact_api_path"),
            "evidence_card_sha256": _evidence_card_snapshot(dict(card)).get("evidence_card_sha256"),
            "source_snapshot_sha256s": card.get("source_snapshot_sha256s") or [],
        }
        for card in evidence_cards
    ]


source_record_payloads_from_semantic_trace = _source_record_payloads_from_semantic_trace
report_evidence_card_source_records = _report_evidence_card_source_records
