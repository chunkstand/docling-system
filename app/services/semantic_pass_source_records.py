from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.db.public.document_artifacts import DocumentChunk, DocumentFigure, DocumentTable
from app.db.public.semantic_memory import (
    SemanticAssertion,
    SemanticAssertionCategoryBinding,
    SemanticAssertionEvidence,
    SemanticCategory,
    SemanticConcept,
    SemanticConceptCategoryBinding,
    SemanticEvidenceSourceType,
)
from app.services.semantic_registry import (
    SemanticRegistry,
    SemanticRegistryConceptDefinition,
    normalize_semantic_text,
)

SEMANTIC_EXCERPT_LIMIT = 240
SEMANTIC_MATCH_STRATEGY = "normalized_phrase_contains"


@dataclass(frozen=True)
class SemanticSourceItem:
    source_type: str
    source_locator: str
    chunk_id: UUID | None
    table_id: UUID | None
    figure_id: UUID | None
    page_from: int | None
    page_to: int | None
    normalized_text: str
    excerpt: str | None
    source_label: str | None
    source_artifact_path: str | None
    source_artifact_sha256: str | None
    details: dict[str, Any]


@dataclass
class SemanticEvidenceMaterialization:
    source_item: SemanticSourceItem
    matched_terms: list[str]


@dataclass
class SemanticAssertionMaterialization:
    concept_definition: SemanticRegistryConceptDefinition
    matched_terms: set[str]
    source_types: set[str]
    evidence: list[SemanticEvidenceMaterialization]


@dataclass(frozen=True)
class SemanticReviewOverlay:
    review_id: UUID
    review_status: str
    review_note: str | None
    reviewed_by: str | None
    created_at: datetime


def _truncate_excerpt(value: str | None) -> str | None:
    excerpt = collapse_whitespace(value)
    if not excerpt:
        return None
    return excerpt[:SEMANTIC_EXCERPT_LIMIT]


def _table_source_artifact_sha256(table: DocumentTable) -> str | None:
    audit = (table.metadata_json or {}).get("audit") or {}
    return audit.get("json_artifact_sha256")


def _figure_source_artifact_sha256(figure: DocumentFigure) -> str | None:
    audit = (figure.metadata_json or {}).get("audit") or {}
    return audit.get("json_artifact_sha256")


def _content_sha256(value: str | None) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def source_artifact_api_path(
    document_id: UUID,
    *,
    source_type: str,
    table_id: UUID | None,
    figure_id: UUID | None,
) -> str | None:
    if source_type == SemanticEvidenceSourceType.TABLE.value and table_id is not None:
        return f"/documents/{document_id}/tables/{table_id}/artifacts/json"
    if source_type == SemanticEvidenceSourceType.FIGURE.value and figure_id is not None:
        return f"/documents/{document_id}/figures/{figure_id}/artifacts/json"
    return None


def build_semantic_sources(session: Session, run_id: UUID) -> list[SemanticSourceItem]:
    sources: list[SemanticSourceItem] = []
    chunks = (
        session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.run_id == run_id)
            .order_by(DocumentChunk.chunk_index)
        )
        .scalars()
        .all()
    )
    for chunk in chunks:
        combined_text = collapse_whitespace(
            " ".join(part for part in [chunk.heading, chunk.text] if part)
        )
        sources.append(
            SemanticSourceItem(
                source_type=SemanticEvidenceSourceType.CHUNK.value,
                source_locator=str(chunk.id),
                chunk_id=chunk.id,
                table_id=None,
                figure_id=None,
                page_from=chunk.page_from,
                page_to=chunk.page_to,
                normalized_text=normalize_semantic_text(combined_text),
                excerpt=_truncate_excerpt(chunk.text),
                source_label=chunk.heading or _truncate_excerpt(chunk.text),
                source_artifact_path=None,
                source_artifact_sha256=None,
                details={
                    "chunk_index": chunk.chunk_index,
                    "source_content_sha256": _content_sha256(combined_text),
                    "metadata": chunk.metadata_json,
                },
            )
        )
    tables = (
        session.execute(
            select(DocumentTable)
            .where(DocumentTable.run_id == run_id)
            .order_by(DocumentTable.table_index)
        )
        .scalars()
        .all()
    )
    for table in tables:
        combined_text = collapse_whitespace(
            " ".join(part for part in [table.title, table.heading, table.search_text] if part)
        )
        sources.append(
            SemanticSourceItem(
                source_type=SemanticEvidenceSourceType.TABLE.value,
                source_locator=str(table.id),
                chunk_id=None,
                table_id=table.id,
                figure_id=None,
                page_from=table.page_from,
                page_to=table.page_to,
                normalized_text=normalize_semantic_text(combined_text),
                excerpt=_truncate_excerpt(table.preview_text),
                source_label=table.title or table.heading or _truncate_excerpt(table.preview_text),
                source_artifact_path=table.json_path,
                source_artifact_sha256=_table_source_artifact_sha256(table),
                details={
                    "table_index": table.table_index,
                    "logical_table_key": table.logical_table_key,
                    "source_content_sha256": _content_sha256(combined_text),
                    "metadata": table.metadata_json,
                    "artifact_formats": [
                        artifact_format
                        for artifact_format, artifact_path in (
                            ("json", table.json_path),
                            ("yaml", table.yaml_path),
                        )
                        if artifact_path
                    ],
                },
            )
        )
    figures = (
        session.execute(
            select(DocumentFigure)
            .where(DocumentFigure.run_id == run_id)
            .order_by(DocumentFigure.figure_index)
        )
        .scalars()
        .all()
    )
    for figure in figures:
        combined_text = collapse_whitespace(
            " ".join(
                part for part in [figure.caption, figure.heading, figure.source_figure_ref] if part
            )
        )
        sources.append(
            SemanticSourceItem(
                source_type=SemanticEvidenceSourceType.FIGURE.value,
                source_locator=str(figure.id),
                chunk_id=None,
                table_id=None,
                figure_id=figure.id,
                page_from=figure.page_from,
                page_to=figure.page_to,
                normalized_text=normalize_semantic_text(combined_text),
                excerpt=_truncate_excerpt(figure.caption or figure.heading),
                source_label=figure.caption or figure.heading or figure.source_figure_ref,
                source_artifact_path=figure.json_path,
                source_artifact_sha256=_figure_source_artifact_sha256(figure),
                details={
                    "figure_index": figure.figure_index,
                    "source_figure_ref": figure.source_figure_ref,
                    "source_content_sha256": _content_sha256(combined_text),
                    "metadata": figure.metadata_json,
                    "artifact_formats": [
                        artifact_format
                        for artifact_format, artifact_path in (
                            ("json", figure.json_path),
                            ("yaml", figure.yaml_path),
                        )
                        if artifact_path
                    ],
                },
            )
        )
    return sources


def materialize_semantic_assertions(
    registry: SemanticRegistry,
    sources: list[SemanticSourceItem],
) -> list[SemanticAssertionMaterialization]:
    matches_by_concept: dict[str, SemanticAssertionMaterialization] = {}
    for source in sources:
        if not source.normalized_text:
            continue
        for concept_definition in registry.concepts:
            matched_terms = sorted(
                {
                    term.text
                    for term in concept_definition.terms
                    if term.normalized_text and term.normalized_text in source.normalized_text
                }
            )
            if not matched_terms:
                continue
            materialization = matches_by_concept.setdefault(
                concept_definition.concept_key,
                SemanticAssertionMaterialization(
                    concept_definition=concept_definition,
                    matched_terms=set(),
                    source_types=set(),
                    evidence=[],
                ),
            )
            materialization.matched_terms.update(matched_terms)
            materialization.source_types.add(source.source_type)
            materialization.evidence.append(
                SemanticEvidenceMaterialization(source_item=source, matched_terms=matched_terms)
            )
    return sorted(
        matches_by_concept.values(),
        key=lambda item: item.concept_definition.preferred_label.lower(),
    )


def details_with_review_overlay(
    details: dict[str, Any],
    overlay: SemanticReviewOverlay | None,
) -> dict[str, Any]:
    payload = dict(details or {})
    if overlay is None:
        payload.pop("review_overlay", None)
        return payload
    payload["review_overlay"] = {
        "review_id": str(overlay.review_id),
        "review_status": overlay.review_status,
        "review_note": overlay.review_note,
        "reviewed_by": overlay.reviewed_by,
        "created_at": overlay.created_at.isoformat(),
    }
    return payload


def assertion_records(session: Session, semantic_pass_id: UUID) -> list[dict[str, Any]]:
    assertion_rows = session.execute(
        select(SemanticAssertion, SemanticConcept)
        .join(SemanticConcept, SemanticConcept.id == SemanticAssertion.concept_id)
        .where(SemanticAssertion.semantic_pass_id == semantic_pass_id)
        .order_by(SemanticConcept.preferred_label, SemanticAssertion.created_at)
    ).all()
    assertion_ids = [assertion.id for assertion, _concept in assertion_rows]
    assertion_category_binding_rows = (
        session.execute(
            select(
                SemanticAssertionCategoryBinding,
                SemanticCategory,
            )
            .join(
                SemanticCategory,
                SemanticCategory.id == SemanticAssertionCategoryBinding.category_id,
            )
            .where(SemanticAssertionCategoryBinding.assertion_id.in_(assertion_ids))
            .order_by(SemanticCategory.preferred_label, SemanticAssertionCategoryBinding.created_at)
        ).all()
        if assertion_ids
        else []
    )
    evidence_rows = (
        session.execute(
            select(SemanticAssertionEvidence)
            .where(SemanticAssertionEvidence.assertion_id.in_(assertion_ids))
            .order_by(
                SemanticAssertionEvidence.source_type,
                SemanticAssertionEvidence.page_from,
                SemanticAssertionEvidence.page_to,
            )
        )
        .scalars()
        .all()
        if assertion_ids
        else []
    )
    assertion_category_bindings_by_assertion: dict[UUID, list[dict[str, Any]]] = {}
    for binding, category in assertion_category_binding_rows:
        assertion_category_bindings_by_assertion.setdefault(binding.assertion_id, []).append(
            {
                "binding_id": binding.id,
                "category_key": category.category_key,
                "category_label": category.preferred_label,
                "binding_type": binding.binding_type,
                "created_from": binding.created_from,
                "review_status": binding.review_status,
                "details": binding.details_json or {},
            }
        )
    evidence_by_assertion: dict[UUID, list[dict[str, Any]]] = {}
    for evidence in evidence_rows:
        evidence_by_assertion.setdefault(evidence.assertion_id, []).append(
            {
                "evidence_id": evidence.id,
                "source_type": evidence.source_type,
                "chunk_id": evidence.chunk_id,
                "table_id": evidence.table_id,
                "figure_id": evidence.figure_id,
                "page_from": evidence.page_from,
                "page_to": evidence.page_to,
                "matched_terms": list(evidence.matched_terms_json or []),
                "excerpt": evidence.excerpt,
                "source_label": evidence.source_label,
                "source_artifact_api_path": source_artifact_api_path(
                    evidence.document_id,
                    source_type=evidence.source_type,
                    table_id=evidence.table_id,
                    figure_id=evidence.figure_id,
                ),
                "source_artifact_sha256": evidence.source_artifact_sha256,
                "details": evidence.details_json or {},
            }
        )
    records: list[dict[str, Any]] = []
    for assertion, concept in assertion_rows:
        records.append(
            {
                "assertion_id": assertion.id,
                "concept_key": concept.concept_key,
                "preferred_label": concept.preferred_label,
                "scope_note": concept.scope_note,
                "assertion_kind": assertion.assertion_kind,
                "epistemic_status": assertion.epistemic_status,
                "context_scope": assertion.context_scope,
                "review_status": assertion.review_status,
                "matched_terms": list(assertion.matched_terms_json or []),
                "source_types": list(assertion.source_types_json or []),
                "evidence_count": assertion.evidence_count,
                "confidence": assertion.confidence,
                "details": assertion.details_json or {},
                "category_bindings": assertion_category_bindings_by_assertion.get(assertion.id, []),
                "evidence": evidence_by_assertion.get(assertion.id, []),
            }
        )
    return records


def concept_category_binding_records(
    session: Session, registry_version: str
) -> list[dict[str, Any]]:
    rows = session.execute(
        select(SemanticConceptCategoryBinding, SemanticConcept, SemanticCategory)
        .join(SemanticConcept, SemanticConcept.id == SemanticConceptCategoryBinding.concept_id)
        .join(SemanticCategory, SemanticCategory.id == SemanticConceptCategoryBinding.category_id)
        .where(SemanticConcept.registry_version == registry_version)
        .order_by(SemanticConcept.preferred_label, SemanticCategory.preferred_label)
    ).all()
    return [
        {
            "binding_id": binding.id,
            "concept_key": concept.concept_key,
            "category_key": category.category_key,
            "category_label": category.preferred_label,
            "binding_type": binding.binding_type,
            "created_from": binding.created_from,
            "review_status": binding.review_status,
            "details": binding.details_json or {},
        }
        for binding, concept, category in rows
    ]
