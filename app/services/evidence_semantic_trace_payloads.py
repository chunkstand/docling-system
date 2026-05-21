# ruff: noqa: E501
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.public.semantic_memory import (
    SemanticAssertion,
    SemanticAssertionEvidence,
    SemanticFact,
    SemanticFactEvidence,
)
from app.services.evidence_records import select_by_ids as _select_by_ids


def _semantic_assertion_payload(row: SemanticAssertion) -> dict[str, Any]:
    return {
        "assertion_id": row.id,
        "semantic_pass_id": row.semantic_pass_id,
        "concept_id": row.concept_id,
        "assertion_kind": row.assertion_kind,
        "epistemic_status": row.epistemic_status,
        "context_scope": row.context_scope,
        "review_status": row.review_status,
        "matched_terms": row.matched_terms_json or [],
        "source_types": row.source_types_json or [],
        "evidence_count": row.evidence_count,
        "confidence": row.confidence,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_assertion_evidence_payload(row: SemanticAssertionEvidence) -> dict[str, Any]:
    return {
        "evidence_id": row.id,
        "assertion_id": row.assertion_id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "source_type": row.source_type,
        "source_locator": row.source_locator,
        "chunk_id": row.chunk_id,
        "table_id": row.table_id,
        "figure_id": row.figure_id,
        "page_from": row.page_from,
        "page_to": row.page_to,
        "matched_terms": row.matched_terms_json or [],
        "excerpt": row.excerpt,
        "source_label": row.source_label,
        "source_artifact_path": row.source_artifact_path,
        "source_artifact_sha256": row.source_artifact_sha256,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_fact_payload(row: SemanticFact) -> dict[str, Any]:
    return {
        "fact_id": row.id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "semantic_pass_id": row.semantic_pass_id,
        "ontology_snapshot_id": row.ontology_snapshot_id,
        "subject_entity_id": row.subject_entity_id,
        "relation_key": row.relation_key,
        "relation_label": row.relation_label,
        "object_entity_id": row.object_entity_id,
        "object_value_text": row.object_value_text,
        "source_assertion_id": row.source_assertion_id,
        "review_status": row.review_status,
        "confidence": row.confidence,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_fact_evidence_payload(row: SemanticFactEvidence) -> dict[str, Any]:
    return {
        "fact_evidence_id": row.id,
        "fact_id": row.fact_id,
        "assertion_id": row.assertion_id,
        "assertion_evidence_id": row.assertion_evidence_id,
        "created_at": row.created_at,
    }


def _semantic_trace_payload(
    session: Session,
    *,
    assertion_ids: list[UUID],
    fact_ids: list[UUID],
    evidence_ids: list[UUID],
) -> dict[str, Any]:
    assertions_by_id = _select_by_ids(session, SemanticAssertion, assertion_ids)
    facts_by_id = _select_by_ids(session, SemanticFact, fact_ids)
    assertion_evidence_by_id: dict[UUID, SemanticAssertionEvidence] = {}
    if evidence_ids:
        assertion_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticAssertionEvidence)
                    .where(SemanticAssertionEvidence.id.in_(evidence_ids))
                    .order_by(SemanticAssertionEvidence.created_at, SemanticAssertionEvidence.id)
                )
            }
        )
    if assertion_ids:
        assertion_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticAssertionEvidence)
                    .where(SemanticAssertionEvidence.assertion_id.in_(assertion_ids))
                    .order_by(SemanticAssertionEvidence.created_at, SemanticAssertionEvidence.id)
                )
            }
        )

    fact_evidence_by_id: dict[UUID, SemanticFactEvidence] = {}
    if fact_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.fact_id.in_(fact_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )
    if assertion_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.assertion_id.in_(assertion_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )
    if evidence_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.assertion_evidence_id.in_(evidence_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )

    return {
        "assertions": [
            _semantic_assertion_payload(row)
            for row in sorted(assertions_by_id.values(), key=lambda item: str(item.id))
        ],
        "facts": [
            _semantic_fact_payload(row)
            for row in sorted(facts_by_id.values(), key=lambda item: str(item.id))
        ],
        "assertion_evidence": [
            _semantic_assertion_evidence_payload(row)
            for row in sorted(assertion_evidence_by_id.values(), key=lambda item: str(item.id))
        ],
        "fact_evidence": [
            _semantic_fact_evidence_payload(row)
            for row in sorted(fact_evidence_by_id.values(), key=lambda item: str(item.id))
        ],
    }


semantic_assertion_payload = _semantic_assertion_payload
semantic_assertion_evidence_payload = _semantic_assertion_evidence_payload
semantic_fact_payload = _semantic_fact_payload
semantic_fact_evidence_payload = _semantic_fact_evidence_payload
semantic_trace_payload = _semantic_trace_payload
