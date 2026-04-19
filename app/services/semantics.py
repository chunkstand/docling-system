from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.config import get_settings
from app.core.text import collapse_whitespace
from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentFigure,
    DocumentRun,
    DocumentSemanticCategoryReview,
    DocumentSemanticConceptReview,
    DocumentRunSemanticPass,
    DocumentTable,
    SemanticAssertion,
    SemanticAssertionCategoryBinding,
    SemanticAssertionEvidence,
    SemanticAssertionKind,
    SemanticBindingOrigin,
    SemanticCategory,
    SemanticCategoryBindingType,
    SemanticConcept,
    SemanticConceptCategoryBinding,
    SemanticConceptTerm,
    SemanticContextScope,
    SemanticEpistemicStatus,
    SemanticEvaluationStatus,
    SemanticEvidenceSourceType,
    SemanticPassStatus,
    SemanticReviewStatus,
    SemanticTerm,
    SemanticTermKind,
)
from app.schemas.semantics import (
    DocumentSemanticPassResponse,
    SemanticAssertionEvidenceResponse,
    SemanticAssertionResponse,
    SemanticAssertionCategoryBindingResponse,
    SemanticContinuityResponse,
    SemanticConceptCategoryBindingResponse,
    SemanticReviewEventResponse,
)
from app.services.documents import get_document_or_404
from app.services.semantic_registry import (
    SemanticRegistry,
    SemanticRegistryConceptDefinition,
    get_semantic_registry,
    normalize_semantic_text,
)
from app.services.storage import StorageService

SEMANTIC_ARTIFACT_SCHEMA_NAME = "docling.semantic_pass"
SEMANTIC_ARTIFACT_SCHEMA_VERSION = "2.1"
SEMANTIC_EXTRACTOR_VERSION = "semantics_sidecar_v2_1"
SEMANTIC_MATCH_STRATEGY = "normalized_phrase_contains"
SEMANTIC_EVAL_VERSION = 2
SEMANTIC_EXCERPT_LIMIT = 240


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


@dataclass(frozen=True)
class SemanticEvaluationExpectation:
    concept_key: str
    minimum_evidence_count: int
    required_source_types: tuple[str, ...]
    expected_category_keys: tuple[str, ...] = ()
    expected_epistemic_status: str | None = None
    expected_review_status: str | None = None
    expected_category_binding_review_status: str | None = None


@dataclass(frozen=True)
class SemanticConceptCategoryBindingExpectation:
    concept_key: str
    category_key: str
    expected_review_status: str | None = None


@dataclass(frozen=True)
class SemanticEvaluationFixture:
    fixture_name: str
    source_filename: str
    expected_concepts: tuple[SemanticEvaluationExpectation, ...]
    expected_concept_category_bindings: tuple[SemanticConceptCategoryBindingExpectation, ...] = ()


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


def _source_artifact_api_path(
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


def _build_semantic_sources(
    session: Session,
    run_id: UUID,
) -> list[SemanticSourceItem]:
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
        combined_text = collapse_whitespace(" ".join(part for part in [chunk.heading, chunk.text] if part))
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
            " ".join(part for part in [figure.caption, figure.heading, figure.source_figure_ref] if part)
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


def _materialize_semantic_assertions(
    registry: SemanticRegistry,
    sources: list[SemanticSourceItem],
) -> list[SemanticAssertionMaterialization]:
    matches_by_concept: dict[str, SemanticAssertionMaterialization] = {}
    for source in sources:
        if not source.normalized_text:
            continue
        for concept in registry.concepts:
            matched_terms = sorted(
                {
                    term.text
                    for term in concept.terms
                    if term.normalized_text and term.normalized_text in source.normalized_text
                }
            )
            if not matched_terms:
                continue
            materialization = matches_by_concept.setdefault(
                concept.concept_key,
                SemanticAssertionMaterialization(
                    concept_definition=concept,
                    matched_terms=set(),
                    source_types=set(),
                    evidence=[],
                ),
            )
            materialization.matched_terms.update(matched_terms)
            materialization.source_types.add(source.source_type)
            materialization.evidence.append(
                SemanticEvidenceMaterialization(
                    source_item=source,
                    matched_terms=matched_terms,
                )
            )
    return sorted(
        matches_by_concept.values(),
        key=lambda item: item.concept_definition.preferred_label.lower(),
    )


def _latest_concept_review_overlays(
    session: Session,
    document_id: UUID,
    registry_version: str,
) -> dict[str, SemanticReviewOverlay]:
    rows = session.execute(
        select(
            DocumentSemanticConceptReview,
            SemanticConcept,
        )
        .join(
            SemanticConcept,
            SemanticConcept.id == DocumentSemanticConceptReview.concept_id,
        )
        .where(
            DocumentSemanticConceptReview.document_id == document_id,
            SemanticConcept.registry_version == registry_version,
        )
        .order_by(
            SemanticConcept.concept_key,
            DocumentSemanticConceptReview.created_at.desc(),
        )
    ).all()
    overlays: dict[str, SemanticReviewOverlay] = {}
    for review, concept in rows:
        overlays.setdefault(
            concept.concept_key,
            SemanticReviewOverlay(
                review_id=review.id,
                review_status=review.review_status,
                review_note=review.review_note,
                reviewed_by=review.reviewed_by,
                created_at=review.created_at,
            ),
        )
    return overlays


def _latest_category_review_overlays(
    session: Session,
    document_id: UUID,
    registry_version: str,
) -> dict[tuple[str, str], SemanticReviewOverlay]:
    rows = session.execute(
        select(
            DocumentSemanticCategoryReview,
            SemanticConcept,
            SemanticCategory,
        )
        .join(
            SemanticConcept,
            SemanticConcept.id == DocumentSemanticCategoryReview.concept_id,
        )
        .join(
            SemanticCategory,
            SemanticCategory.id == DocumentSemanticCategoryReview.category_id,
        )
        .where(
            DocumentSemanticCategoryReview.document_id == document_id,
            SemanticConcept.registry_version == registry_version,
            SemanticCategory.registry_version == registry_version,
        )
        .order_by(
            SemanticConcept.concept_key,
            SemanticCategory.category_key,
            DocumentSemanticCategoryReview.created_at.desc(),
        )
    ).all()
    overlays: dict[tuple[str, str], SemanticReviewOverlay] = {}
    for review, concept, category in rows:
        overlays.setdefault(
            (concept.concept_key, category.category_key),
            SemanticReviewOverlay(
                review_id=review.id,
                review_status=review.review_status,
                review_note=review.review_note,
                reviewed_by=review.reviewed_by,
                created_at=review.created_at,
            ),
        )
    return overlays


def _details_with_review_overlay(
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


def _sync_registry_definitions(
    session: Session,
    registry: SemanticRegistry,
) -> tuple[
    dict[str, SemanticConcept],
    dict[str, SemanticCategory],
    dict[tuple[str, str], SemanticConceptCategoryBinding],
]:
    now = utcnow()
    concept_rows = {
        row.concept_key: row
        for row in session.execute(
            select(SemanticConcept).where(SemanticConcept.registry_version == registry.registry_version)
        )
        .scalars()
        .all()
    }
    category_rows = {
        row.category_key: row
        for row in session.execute(
            select(SemanticCategory).where(
                SemanticCategory.registry_version == registry.registry_version
            )
        )
        .scalars()
        .all()
    }
    term_rows = {
        row.normalized_text: row
        for row in session.execute(
            select(SemanticTerm).where(SemanticTerm.registry_version == registry.registry_version)
        )
        .scalars()
        .all()
    }

    concept_term_pairs: set[tuple[UUID, UUID]] = set(
        (concept_id, term_id)
        for concept_id, term_id in session.execute(
            select(SemanticConceptTerm.concept_id, SemanticConceptTerm.term_id)
            .join(
                SemanticConcept,
                SemanticConcept.id == SemanticConceptTerm.concept_id,
            )
            .where(SemanticConcept.registry_version == registry.registry_version)
        ).all()
    )
    concept_category_binding_rows = {
        (concept.concept_key, category.category_key): binding
        for binding, concept, category in session.execute(
            select(
                SemanticConceptCategoryBinding,
                SemanticConcept,
                SemanticCategory,
            )
            .join(
                SemanticConcept,
                SemanticConcept.id == SemanticConceptCategoryBinding.concept_id,
            )
            .join(
                SemanticCategory,
                SemanticCategory.id == SemanticConceptCategoryBinding.category_id,
            )
            .where(SemanticConcept.registry_version == registry.registry_version)
        ).all()
    }

    for category_definition in registry.categories:
        category_row = category_rows.get(category_definition.category_key)
        if category_row is None:
            category_row = SemanticCategory(
                category_key=category_definition.category_key,
                preferred_label=category_definition.preferred_label,
                scope_note=category_definition.scope_note,
                registry_version=registry.registry_version,
                metadata_json=category_definition.metadata,
                created_at=now,
                updated_at=now,
            )
            session.add(category_row)
            session.flush()
            category_rows[category_definition.category_key] = category_row
        else:
            category_row.preferred_label = category_definition.preferred_label
            category_row.scope_note = category_definition.scope_note
            category_row.metadata_json = category_definition.metadata
            category_row.updated_at = now

    for concept_definition in registry.concepts:
        concept_row = concept_rows.get(concept_definition.concept_key)
        if concept_row is None:
            concept_row = SemanticConcept(
                concept_key=concept_definition.concept_key,
                preferred_label=concept_definition.preferred_label,
                scope_note=concept_definition.scope_note,
                registry_version=registry.registry_version,
                metadata_json=concept_definition.metadata,
                created_at=now,
                updated_at=now,
            )
            session.add(concept_row)
            session.flush()
            concept_rows[concept_definition.concept_key] = concept_row
        else:
            concept_row.preferred_label = concept_definition.preferred_label
            concept_row.scope_note = concept_definition.scope_note
            concept_row.metadata_json = concept_definition.metadata
            concept_row.updated_at = now

        for term_definition in concept_definition.terms:
            term_row = term_rows.get(term_definition.normalized_text)
            if term_row is None:
                term_row = SemanticTerm(
                    registry_version=registry.registry_version,
                    term_text=term_definition.text,
                    normalized_text=term_definition.normalized_text,
                    term_kind=term_definition.term_kind,
                    metadata_json={},
                    created_at=now,
                )
                session.add(term_row)
                session.flush()
                term_rows[term_definition.normalized_text] = term_row
            elif term_definition.term_kind == SemanticTermKind.PREFERRED_LABEL.value:
                term_row.term_text = term_definition.text
                term_row.term_kind = term_definition.term_kind

            pair = (concept_row.id, term_row.id)
            if pair in concept_term_pairs:
                continue
            session.add(
                SemanticConceptTerm(
                    concept_id=concept_row.id,
                    term_id=term_row.id,
                    mapping_kind=term_definition.term_kind,
                    created_from=SemanticBindingOrigin.REGISTRY.value,
                    review_status=SemanticReviewStatus.APPROVED.value,
                    details_json={},
                    created_at=now,
                )
            )
            concept_term_pairs.add(pair)

        for category_key in concept_definition.category_keys:
            category_row = category_rows[category_key]
            binding_key = (concept_definition.concept_key, category_key)
            binding_row = concept_category_binding_rows.get(binding_key)
            if binding_row is None:
                binding_row = SemanticConceptCategoryBinding(
                    concept_id=concept_row.id,
                    category_id=category_row.id,
                    binding_type=SemanticCategoryBindingType.CONCEPT_CATEGORY.value,
                    created_from=SemanticBindingOrigin.REGISTRY.value,
                    review_status=SemanticReviewStatus.APPROVED.value,
                    details_json={},
                    created_at=now,
                )
                session.add(binding_row)
                session.flush()
                concept_category_binding_rows[binding_key] = binding_row

    return concept_rows, category_rows, concept_category_binding_rows


def _replace_pass_assertions(
    session: Session,
    semantic_pass: DocumentRunSemanticPass,
    concept_rows: dict[str, SemanticConcept],
    category_rows: dict[str, SemanticCategory],
    concept_category_binding_rows: dict[tuple[str, str], SemanticConceptCategoryBinding],
    concept_review_overlays: dict[str, SemanticReviewOverlay],
    category_review_overlays: dict[tuple[str, str], SemanticReviewOverlay],
    materializations: list[SemanticAssertionMaterialization],
) -> None:
    session.query(SemanticAssertion).filter(
        SemanticAssertion.semantic_pass_id == semantic_pass.id
    ).delete()

    now = utcnow()
    for materialization in materializations:
        concept_row = concept_rows[materialization.concept_definition.concept_key]
        concept_overlay = concept_review_overlays.get(
            materialization.concept_definition.concept_key
        )
        assertion = SemanticAssertion(
            semantic_pass_id=semantic_pass.id,
            concept_id=concept_row.id,
            assertion_kind=SemanticAssertionKind.CONCEPT_MENTION.value,
            epistemic_status=SemanticEpistemicStatus.OBSERVED.value,
            context_scope=SemanticContextScope.DOCUMENT_RUN.value,
            review_status=(
                concept_overlay.review_status
                if concept_overlay is not None
                else SemanticReviewStatus.CANDIDATE.value
            ),
            matched_terms_json=sorted(materialization.matched_terms),
            source_types_json=sorted(materialization.source_types),
            evidence_count=len(materialization.evidence),
            confidence=min(1.0, 0.65 + (0.1 * len(materialization.source_types))),
            details_json=_details_with_review_overlay(
                {
                    "scope_note": materialization.concept_definition.scope_note,
                    "match_strategy": SEMANTIC_MATCH_STRATEGY,
                },
                concept_overlay,
            ),
            created_at=now,
        )
        session.add(assertion)
        session.flush()

        for category_key in materialization.concept_definition.category_keys:
            category_row = category_rows[category_key]
            concept_category_binding = concept_category_binding_rows[
                (materialization.concept_definition.concept_key, category_key)
            ]
            category_overlay = category_review_overlays.get(
                (materialization.concept_definition.concept_key, category_key)
            )
            session.add(
                SemanticAssertionCategoryBinding(
                    assertion_id=assertion.id,
                    category_id=category_row.id,
                    concept_category_binding_id=concept_category_binding.id,
                    binding_type=SemanticCategoryBindingType.ASSERTION_CATEGORY.value,
                    created_from=SemanticBindingOrigin.DERIVED.value,
                    review_status=(
                        category_overlay.review_status
                        if category_overlay is not None
                        else SemanticReviewStatus.CANDIDATE.value
                    ),
                    details_json=_details_with_review_overlay(
                        {
                            "inherited_from_concept_category_binding_id": str(
                                concept_category_binding.id
                            ),
                            "concept_category_review_status": concept_category_binding.review_status,
                        },
                        category_overlay,
                    ),
                    created_at=now,
                )
            )

        for evidence_materialization in materialization.evidence:
            source = evidence_materialization.source_item
            session.add(
                SemanticAssertionEvidence(
                    assertion_id=assertion.id,
                    document_id=semantic_pass.document_id,
                    run_id=semantic_pass.run_id,
                    source_type=source.source_type,
                    source_locator=source.source_locator,
                    chunk_id=source.chunk_id,
                    table_id=source.table_id,
                    figure_id=source.figure_id,
                    page_from=source.page_from,
                    page_to=source.page_to,
                    matched_terms_json=evidence_materialization.matched_terms,
                    excerpt=source.excerpt,
                    source_label=source.source_label,
                    source_artifact_path=source.source_artifact_path,
                    source_artifact_sha256=source.source_artifact_sha256,
                    details_json=source.details,
                    created_at=now,
                )
            )
    session.flush()


def _assertion_records(
    session: Session,
    semantic_pass_id: UUID,
) -> list[dict[str, Any]]:
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
                "source_artifact_api_path": _source_artifact_api_path(
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


def _concept_category_binding_records(
    session: Session,
    registry_version: str,
) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            SemanticConceptCategoryBinding,
            SemanticConcept,
            SemanticCategory,
        )
        .join(
            SemanticConcept,
            SemanticConcept.id == SemanticConceptCategoryBinding.concept_id,
        )
        .join(
            SemanticCategory,
            SemanticCategory.id == SemanticConceptCategoryBinding.category_id,
        )
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


def _semantic_summary(
    assertions: list[dict[str, Any]],
    concept_category_bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    source_type_counts = {
        source_type: sum(
            1 for assertion in assertions if source_type in set(assertion.get("source_types") or [])
        )
        for source_type in (
            SemanticEvidenceSourceType.CHUNK.value,
            SemanticEvidenceSourceType.TABLE.value,
            SemanticEvidenceSourceType.FIGURE.value,
        )
    }
    evidence_count = sum(len(assertion.get("evidence") or []) for assertion in assertions)
    category_keys = sorted(
        {
            binding["category_key"]
            for assertion in assertions
            for binding in assertion.get("category_bindings") or []
        }
    )
    review_status_counts = {
        review_status: sum(1 for assertion in assertions if assertion.get("review_status") == review_status)
        for review_status in (
            SemanticReviewStatus.CANDIDATE.value,
            SemanticReviewStatus.APPROVED.value,
            SemanticReviewStatus.REJECTED.value,
        )
    }
    return {
        "assertion_count": len(assertions),
        "evidence_count": evidence_count,
        "concept_keys": [assertion["concept_key"] for assertion in assertions],
        "category_keys": category_keys,
        "concept_category_binding_count": len(concept_category_bindings),
        "source_type_counts": source_type_counts,
        "review_status_counts": review_status_counts,
        "match_strategy": SEMANTIC_MATCH_STRATEGY,
    }


def _semantic_pass_row_for_run(
    session: Session,
    document_id: UUID,
    run_id: UUID,
) -> DocumentRunSemanticPass | None:
    return session.execute(
        select(DocumentRunSemanticPass)
        .where(
            DocumentRunSemanticPass.document_id == document_id,
            DocumentRunSemanticPass.run_id == run_id,
        )
        .order_by(DocumentRunSemanticPass.created_at.desc())
    ).scalars().first()


def _continuity_summary(
    assertions: list[dict[str, Any]],
    *,
    baseline_run_id: UUID | None,
    baseline_semantic_pass: DocumentRunSemanticPass | None,
    baseline_assertions: list[dict[str, Any]],
) -> dict[str, Any]:
    if baseline_run_id is None:
        return {
            "has_baseline": False,
            "reason": "no_prior_active_run",
            "baseline_run_id": None,
            "baseline_semantic_pass_id": None,
            "added_concept_keys": [],
            "removed_concept_keys": [],
            "changed_assertion_review_statuses": [],
            "changed_category_bindings": [],
            "current_assertion_count": len(assertions),
            "baseline_assertion_count": 0,
            "change_count": 0,
        }

    if baseline_semantic_pass is None:
        return {
            "has_baseline": False,
            "reason": "baseline_semantic_pass_not_found",
            "baseline_run_id": str(baseline_run_id),
            "baseline_semantic_pass_id": None,
            "added_concept_keys": [],
            "removed_concept_keys": [],
            "changed_assertion_review_statuses": [],
            "changed_category_bindings": [],
            "current_assertion_count": len(assertions),
            "baseline_assertion_count": 0,
            "change_count": 0,
        }

    current_by_concept = {assertion["concept_key"]: assertion for assertion in assertions}
    baseline_by_concept = {assertion["concept_key"]: assertion for assertion in baseline_assertions}
    current_keys = set(current_by_concept)
    baseline_keys = set(baseline_by_concept)

    added_concept_keys = sorted(current_keys - baseline_keys)
    removed_concept_keys = sorted(baseline_keys - current_keys)
    changed_assertion_review_statuses: list[dict[str, Any]] = []
    changed_category_bindings: list[dict[str, Any]] = []

    for concept_key in sorted(current_keys & baseline_keys):
        current_assertion = current_by_concept[concept_key]
        baseline_assertion = baseline_by_concept[concept_key]
        if current_assertion.get("review_status") != baseline_assertion.get("review_status"):
            changed_assertion_review_statuses.append(
                {
                    "concept_key": concept_key,
                    "baseline_review_status": baseline_assertion.get("review_status"),
                    "current_review_status": current_assertion.get("review_status"),
                }
            )

        current_binding_index = {
            binding["category_key"]: binding
            for binding in current_assertion.get("category_bindings") or []
        }
        baseline_binding_index = {
            binding["category_key"]: binding
            for binding in baseline_assertion.get("category_bindings") or []
        }
        current_binding_keys = set(current_binding_index)
        baseline_binding_keys = set(baseline_binding_index)
        added_category_keys = sorted(current_binding_keys - baseline_binding_keys)
        removed_category_keys = sorted(baseline_binding_keys - current_binding_keys)
        changed_binding_review_statuses = [
            {
                "category_key": category_key,
                "baseline_review_status": baseline_binding_index[category_key].get("review_status"),
                "current_review_status": current_binding_index[category_key].get("review_status"),
            }
            for category_key in sorted(current_binding_keys & baseline_binding_keys)
            if current_binding_index[category_key].get("review_status")
            != baseline_binding_index[category_key].get("review_status")
        ]
        if added_category_keys or removed_category_keys or changed_binding_review_statuses:
            changed_category_bindings.append(
                {
                    "concept_key": concept_key,
                    "added_category_keys": added_category_keys,
                    "removed_category_keys": removed_category_keys,
                    "changed_review_statuses": changed_binding_review_statuses,
                }
            )

    change_count = (
        len(added_concept_keys)
        + len(removed_concept_keys)
        + len(changed_assertion_review_statuses)
        + sum(
            len(item["added_category_keys"])
            + len(item["removed_category_keys"])
            + len(item["changed_review_statuses"])
            for item in changed_category_bindings
        )
    )
    return {
        "has_baseline": True,
        "reason": "baseline_comparison_completed",
        "baseline_run_id": str(baseline_run_id),
        "baseline_semantic_pass_id": str(baseline_semantic_pass.id),
        "added_concept_keys": added_concept_keys,
        "removed_concept_keys": removed_concept_keys,
        "changed_assertion_review_statuses": changed_assertion_review_statuses,
        "changed_category_bindings": changed_category_bindings,
        "current_assertion_count": len(assertions),
        "baseline_assertion_count": len(baseline_assertions),
        "change_count": change_count,
    }


def _load_semantic_evaluation_fixtures(path_value: str) -> tuple[SemanticEvaluationFixture, ...]:
    path = Path(path_value).expanduser().resolve()
    if not path.exists():
        return ()
    payload = yaml.safe_load(path.read_text()) or {}
    if not isinstance(payload, dict):
        raise ValueError("Semantic evaluation corpus must be a mapping.")
    raw_documents = payload.get("documents") or []
    if not isinstance(raw_documents, list):
        raise ValueError("Semantic evaluation corpus documents must be a list.")

    fixtures: list[SemanticEvaluationFixture] = []
    for raw_document in raw_documents:
        if not isinstance(raw_document, dict):
            raise ValueError("Semantic evaluation documents must be mappings.")
        source_filename = Path(str(raw_document.get("source_filename") or "")).name
        if not source_filename:
            raise ValueError("Semantic evaluation fixtures require source_filename.")
        fixture_name = collapse_whitespace(
            str(raw_document.get("fixture_name") or source_filename)
        )
        raw_expectations = raw_document.get("expected_concepts") or []
        if not isinstance(raw_expectations, list):
            raise ValueError("Semantic evaluation expected_concepts must be a list.")
        expectations: list[SemanticEvaluationExpectation] = []
        for raw_expectation in raw_expectations:
            if not isinstance(raw_expectation, dict):
                raise ValueError("Semantic evaluation expectations must be mappings.")
            concept_key = collapse_whitespace(str(raw_expectation.get("concept_key") or ""))
            if not concept_key:
                raise ValueError("Semantic evaluation expectations require concept_key.")
            required_source_types = raw_expectation.get("required_source_types") or []
            if required_source_types and not isinstance(required_source_types, list):
                raise ValueError(
                    "Semantic evaluation required_source_types must be a list when provided."
                )
            expectations.append(
                SemanticEvaluationExpectation(
                    concept_key=concept_key,
                    minimum_evidence_count=int(raw_expectation.get("minimum_evidence_count") or 1),
                    required_source_types=tuple(
                        sorted(
                            collapse_whitespace(str(item or ""))
                            for item in required_source_types
                            if collapse_whitespace(str(item or ""))
                        )
                    ),
                    expected_category_keys=tuple(
                        sorted(
                            collapse_whitespace(str(item or ""))
                            for item in (raw_expectation.get("expected_category_keys") or [])
                            if collapse_whitespace(str(item or ""))
                        )
                    ),
                    expected_epistemic_status=collapse_whitespace(
                        str(raw_expectation.get("expected_epistemic_status") or "")
                    )
                    or None,
                    expected_review_status=collapse_whitespace(
                        str(raw_expectation.get("expected_review_status") or "")
                    )
                    or None,
                    expected_category_binding_review_status=collapse_whitespace(
                        str(raw_expectation.get("expected_category_binding_review_status") or "")
                    )
                    or None,
                )
            )
        raw_concept_category_bindings = raw_document.get("expected_concept_category_bindings") or []
        if raw_concept_category_bindings and not isinstance(raw_concept_category_bindings, list):
            raise ValueError(
                "Semantic evaluation expected_concept_category_bindings must be a list."
            )
        concept_category_binding_expectations: list[SemanticConceptCategoryBindingExpectation] = []
        for raw_binding in raw_concept_category_bindings:
            if not isinstance(raw_binding, dict):
                raise ValueError(
                    "Semantic evaluation expected_concept_category_bindings entries must be mappings."
                )
            concept_key = collapse_whitespace(str(raw_binding.get("concept_key") or ""))
            category_key = collapse_whitespace(str(raw_binding.get("category_key") or ""))
            if not concept_key or not category_key:
                raise ValueError(
                    "Semantic evaluation concept-category binding expectations require concept_key and category_key."
                )
            concept_category_binding_expectations.append(
                SemanticConceptCategoryBindingExpectation(
                    concept_key=concept_key,
                    category_key=category_key,
                    expected_review_status=collapse_whitespace(
                        str(raw_binding.get("expected_review_status") or "")
                    )
                    or None,
                )
            )
        fixtures.append(
            SemanticEvaluationFixture(
                fixture_name=fixture_name,
                source_filename=source_filename,
                expected_concepts=tuple(expectations),
                expected_concept_category_bindings=tuple(concept_category_binding_expectations),
            )
        )
    return tuple(fixtures)


@lru_cache(maxsize=4)
def _load_semantic_evaluation_fixtures_cached(path_value: str) -> tuple[SemanticEvaluationFixture, ...]:
    return _load_semantic_evaluation_fixtures(path_value)


def _semantic_evaluation_result(
    document: Document,
    assertions: list[dict[str, Any]],
    concept_category_bindings: list[dict[str, Any]],
) -> tuple[str, str | None, dict[str, Any]]:
    settings = get_settings()
    fixtures = _load_semantic_evaluation_fixtures_cached(
        str(settings.semantic_evaluation_corpus_path.expanduser().resolve())
    )
    source_filename = Path(document.source_filename).name
    fixture = next((item for item in fixtures if item.source_filename == source_filename), None)
    if fixture is None:
        return (
            SemanticEvaluationStatus.SKIPPED.value,
            None,
            {
                "all_expectations_passed": True,
                "expected_concept_count": 0,
                "passed_expectations": 0,
                "failed_expectations": 0,
                "expectations": [],
                "reason": "no_semantic_fixture",
            },
        )

    assertions_by_concept = {assertion["concept_key"]: assertion for assertion in assertions}
    concept_category_binding_index = {
        (binding["concept_key"], binding["category_key"]): binding
        for binding in concept_category_bindings
    }
    expectation_results: list[dict[str, Any]] = []
    passed_expectations = 0
    for expectation in fixture.expected_concepts:
        assertion = assertions_by_concept.get(expectation.concept_key)
        observed_source_types = sorted(set(assertion.get("source_types") or [])) if assertion else []
        observed_evidence_count = int(assertion.get("evidence_count") or 0) if assertion else 0
        observed_category_keys = sorted(
            {
                binding["category_key"]
                for binding in assertion.get("category_bindings") or []
            }
        ) if assertion else []
        observed_category_binding_review_statuses = sorted(
            {
                binding["review_status"]
                for binding in assertion.get("category_bindings") or []
            }
        ) if assertion else []
        missing_source_types = [
            source_type
            for source_type in expectation.required_source_types
            if source_type not in observed_source_types
        ]
        missing_category_keys = [
            category_key
            for category_key in expectation.expected_category_keys
            if category_key not in observed_category_keys
        ]
        epistemic_status_matches = (
            expectation.expected_epistemic_status is None
            or (assertion is not None and assertion.get("epistemic_status") == expectation.expected_epistemic_status)
        )
        review_status_matches = (
            expectation.expected_review_status is None
            or (assertion is not None and assertion.get("review_status") == expectation.expected_review_status)
        )
        category_binding_review_status_matches = (
            expectation.expected_category_binding_review_status is None
            or (
                assertion is not None
                and expectation.expected_category_binding_review_status
                in observed_category_binding_review_statuses
            )
        )
        passed = (
            assertion is not None
            and observed_evidence_count >= expectation.minimum_evidence_count
            and not missing_source_types
            and not missing_category_keys
            and epistemic_status_matches
            and review_status_matches
            and category_binding_review_status_matches
        )
        if passed:
            passed_expectations += 1
        expectation_results.append(
            {
                "concept_key": expectation.concept_key,
                "minimum_evidence_count": expectation.minimum_evidence_count,
                "required_source_types": list(expectation.required_source_types),
                "observed_evidence_count": observed_evidence_count,
                "observed_source_types": observed_source_types,
                "missing_source_types": missing_source_types,
                "expected_category_keys": list(expectation.expected_category_keys),
                "observed_category_keys": observed_category_keys,
                "missing_category_keys": missing_category_keys,
                "expected_epistemic_status": expectation.expected_epistemic_status,
                "observed_epistemic_status": assertion.get("epistemic_status") if assertion else None,
                "expected_review_status": expectation.expected_review_status,
                "observed_review_status": assertion.get("review_status") if assertion else None,
                "expected_category_binding_review_status": expectation.expected_category_binding_review_status,
                "observed_category_binding_review_statuses": observed_category_binding_review_statuses,
                "passed": passed,
            }
        )

    concept_category_binding_results: list[dict[str, Any]] = []
    passed_concept_category_binding_expectations = 0
    for expectation in fixture.expected_concept_category_bindings:
        binding = concept_category_binding_index.get((expectation.concept_key, expectation.category_key))
        passed = binding is not None and (
            expectation.expected_review_status is None
            or binding.get("review_status") == expectation.expected_review_status
        )
        if passed:
            passed_concept_category_binding_expectations += 1
        concept_category_binding_results.append(
            {
                "concept_key": expectation.concept_key,
                "category_key": expectation.category_key,
                "expected_review_status": expectation.expected_review_status,
                "observed_review_status": binding.get("review_status") if binding else None,
                "passed": passed,
            }
        )

    failed_expectations = len(expectation_results) - passed_expectations
    failed_concept_category_binding_expectations = (
        len(concept_category_binding_results) - passed_concept_category_binding_expectations
    )
    return (
        SemanticEvaluationStatus.COMPLETED.value,
        fixture.fixture_name,
        {
            "all_expectations_passed": (
                failed_expectations == 0 and failed_concept_category_binding_expectations == 0
            ),
            "expected_concept_count": len(expectation_results),
            "passed_expectations": passed_expectations,
            "failed_expectations": failed_expectations,
            "expected_concept_category_binding_count": len(concept_category_binding_results),
            "passed_concept_category_binding_expectations": passed_concept_category_binding_expectations,
            "failed_concept_category_binding_expectations": failed_concept_category_binding_expectations,
            "expectations": expectation_results,
            "concept_category_binding_expectations": concept_category_binding_results,
        },
    )


def _semantic_artifact_payload(
    *,
    document: Document,
    run: DocumentRun,
    semantic_pass: DocumentRunSemanticPass,
    registry: SemanticRegistry,
    assertions: list[dict[str, Any]],
    concept_category_bindings: list[dict[str, Any]],
    summary: dict[str, Any],
    evaluation_status: str,
    evaluation_fixture_name: str | None,
    evaluation_summary: dict[str, Any],
    continuity_summary: dict[str, Any],
    artifact_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_name": SEMANTIC_ARTIFACT_SCHEMA_NAME,
        "schema_version": SEMANTIC_ARTIFACT_SCHEMA_VERSION,
        "artifact_sha256": artifact_sha256,
        "document_id": str(document.id),
        "run_id": str(run.id),
        "semantic_pass_id": str(semantic_pass.id),
        "baseline_run_id": str(semantic_pass.baseline_run_id) if semantic_pass.baseline_run_id else None,
        "baseline_semantic_pass_id": (
            str(semantic_pass.baseline_semantic_pass_id)
            if semantic_pass.baseline_semantic_pass_id
            else None
        ),
        "status": semantic_pass.status,
        "created_at": semantic_pass.created_at.isoformat(),
        "completed_at": semantic_pass.completed_at.isoformat() if semantic_pass.completed_at else None,
        "registry": {
            "name": registry.registry_name,
            "version": registry.registry_version,
            "sha256": registry.sha256,
        },
        "extractor": {
            "version": SEMANTIC_EXTRACTOR_VERSION,
            "match_strategy": SEMANTIC_MATCH_STRATEGY,
        },
        "summary": summary,
        "evaluation": {
            "status": evaluation_status,
            "fixture_name": evaluation_fixture_name,
            "version": SEMANTIC_EVAL_VERSION,
            "summary": evaluation_summary,
        },
        "continuity": continuity_summary,
        "concept_category_bindings": concept_category_bindings,
        "assertions": assertions,
    }


def _persist_semantic_artifacts(
    storage_service: StorageService,
    document: Document,
    run: DocumentRun,
    semantic_pass: DocumentRunSemanticPass,
    registry: SemanticRegistry,
    assertions: list[dict[str, Any]],
    concept_category_bindings: list[dict[str, Any]],
    summary: dict[str, Any],
    evaluation_status: str,
    evaluation_fixture_name: str | None,
    evaluation_summary: dict[str, Any],
    continuity_summary: dict[str, Any],
) -> tuple[Path, Path, str, str]:
    base_payload = _semantic_artifact_payload(
        document=document,
        run=run,
        semantic_pass=semantic_pass,
        registry=registry,
        assertions=assertions,
        concept_category_bindings=concept_category_bindings,
        summary=summary,
        evaluation_status=evaluation_status,
        evaluation_fixture_name=evaluation_fixture_name,
        evaluation_summary=evaluation_summary,
        continuity_summary=continuity_summary,
        artifact_sha256="",
    )
    normalized_base_payload = json.loads(json.dumps(base_payload, default=str))
    artifact_seed = hashlib.sha256(
        json.dumps(normalized_base_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    payload = _semantic_artifact_payload(
        document=document,
        run=run,
        semantic_pass=semantic_pass,
        registry=registry,
        assertions=assertions,
        concept_category_bindings=concept_category_bindings,
        summary=summary,
        evaluation_status=evaluation_status,
        evaluation_fixture_name=evaluation_fixture_name,
        evaluation_summary=evaluation_summary,
        continuity_summary=continuity_summary,
        artifact_sha256=artifact_seed,
    )
    normalized_payload = json.loads(json.dumps(payload, default=str))
    json_path = storage_service.get_semantic_json_path(
        document.id,
        run.id,
        SEMANTIC_ARTIFACT_SCHEMA_VERSION,
    )
    yaml_path = storage_service.get_semantic_yaml_path(
        document.id,
        run.id,
        SEMANTIC_ARTIFACT_SCHEMA_VERSION,
    )
    json_bytes = json.dumps(normalized_payload, indent=2).encode("utf-8")
    yaml_bytes = yaml.safe_dump(normalized_payload, sort_keys=False, allow_unicode=True).encode(
        "utf-8"
    )
    json_path.write_bytes(json_bytes)
    yaml_path.write_bytes(yaml_bytes)
    return (
        json_path,
        yaml_path,
        hashlib.sha256(json_bytes).hexdigest(),
        hashlib.sha256(yaml_bytes).hexdigest(),
    )


def _prepare_semantic_pass_row(
    session: Session,
    document: Document,
    run: DocumentRun,
    registry: SemanticRegistry,
    *,
    baseline_run_id: UUID | None,
) -> DocumentRunSemanticPass:
    semantic_pass = session.execute(
        select(DocumentRunSemanticPass).where(
            DocumentRunSemanticPass.run_id == run.id,
            DocumentRunSemanticPass.registry_version == registry.registry_version,
            DocumentRunSemanticPass.extractor_version == SEMANTIC_EXTRACTOR_VERSION,
            DocumentRunSemanticPass.artifact_schema_version == SEMANTIC_ARTIFACT_SCHEMA_VERSION,
        )
    ).scalar_one_or_none()
    now = utcnow()
    if semantic_pass is None:
        semantic_pass = DocumentRunSemanticPass(
            document_id=document.id,
            run_id=run.id,
            baseline_run_id=baseline_run_id,
            status=SemanticPassStatus.PENDING.value,
            registry_version=registry.registry_version,
            registry_sha256=registry.sha256,
            extractor_version=SEMANTIC_EXTRACTOR_VERSION,
            artifact_schema_version=SEMANTIC_ARTIFACT_SCHEMA_VERSION,
            summary_json={},
            evaluation_status=SemanticEvaluationStatus.PENDING.value,
            evaluation_version=SEMANTIC_EVAL_VERSION,
            evaluation_summary_json={},
            continuity_summary_json={},
            assertion_count=0,
            evidence_count=0,
            created_at=now,
        )
        session.add(semantic_pass)
        session.flush()
    else:
        semantic_pass.baseline_run_id = baseline_run_id
        semantic_pass.baseline_semantic_pass_id = None
        semantic_pass.status = SemanticPassStatus.PENDING.value
        semantic_pass.registry_sha256 = registry.sha256
        semantic_pass.summary_json = {}
        semantic_pass.evaluation_status = SemanticEvaluationStatus.PENDING.value
        semantic_pass.evaluation_fixture_name = None
        semantic_pass.evaluation_summary_json = {}
        semantic_pass.continuity_summary_json = {}
        semantic_pass.error_message = None
        semantic_pass.artifact_json_path = None
        semantic_pass.artifact_yaml_path = None
        semantic_pass.artifact_json_sha256 = None
        semantic_pass.artifact_yaml_sha256 = None
        semantic_pass.assertion_count = 0
        semantic_pass.evidence_count = 0
        semantic_pass.completed_at = None
        session.query(SemanticAssertion).filter(
            SemanticAssertion.semantic_pass_id == semantic_pass.id
        ).delete()
    session.commit()
    return semantic_pass


def execute_semantic_pass(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    baseline_run_id: UUID | None = None,
    storage_service: StorageService,
) -> DocumentRunSemanticPass:
    registry = get_semantic_registry()
    semantic_pass = _prepare_semantic_pass_row(
        session,
        document,
        run,
        registry,
        baseline_run_id=baseline_run_id,
    )

    try:
        semantic_pass = session.get(DocumentRunSemanticPass, semantic_pass.id)
        if semantic_pass is None:
            raise ValueError("Semantic pass row disappeared before processing.")

        (
            concept_rows,
            category_rows,
            concept_category_binding_rows,
        ) = _sync_registry_definitions(session, registry)
        concept_review_overlays = _latest_concept_review_overlays(
            session,
            document.id,
            registry.registry_version,
        )
        category_review_overlays = _latest_category_review_overlays(
            session,
            document.id,
            registry.registry_version,
        )
        sources = _build_semantic_sources(session, run.id)
        materializations = _materialize_semantic_assertions(registry, sources)
        _replace_pass_assertions(
            session,
            semantic_pass,
            concept_rows,
            category_rows,
            concept_category_binding_rows,
            concept_review_overlays,
            category_review_overlays,
            materializations,
        )

        assertions = _assertion_records(session, semantic_pass.id)
        concept_category_bindings = _concept_category_binding_records(
            session,
            registry.registry_version,
        )
        summary = _semantic_summary(assertions, concept_category_bindings)
        evaluation_status, evaluation_fixture_name, evaluation_summary = _semantic_evaluation_result(
            document,
            assertions,
            concept_category_bindings,
        )
        baseline_semantic_pass = (
            _semantic_pass_row_for_run(session, document.id, baseline_run_id)
            if baseline_run_id is not None
            else None
        )
        baseline_assertions = (
            _assertion_records(session, baseline_semantic_pass.id)
            if baseline_semantic_pass is not None
            else []
        )
        continuity_summary = _continuity_summary(
            assertions,
            baseline_run_id=baseline_run_id,
            baseline_semantic_pass=baseline_semantic_pass,
            baseline_assertions=baseline_assertions,
        )

        semantic_pass.baseline_run_id = baseline_run_id
        semantic_pass.baseline_semantic_pass_id = (
            baseline_semantic_pass.id if baseline_semantic_pass is not None else None
        )
        semantic_pass.status = SemanticPassStatus.COMPLETED.value
        semantic_pass.summary_json = summary
        semantic_pass.evaluation_status = evaluation_status
        semantic_pass.evaluation_fixture_name = evaluation_fixture_name
        semantic_pass.evaluation_summary_json = evaluation_summary
        semantic_pass.continuity_summary_json = continuity_summary
        semantic_pass.assertion_count = summary["assertion_count"]
        semantic_pass.evidence_count = summary["evidence_count"]
        semantic_pass.completed_at = utcnow()
        semantic_pass.error_message = None

        (
            json_path,
            yaml_path,
            json_sha256,
            yaml_sha256,
        ) = _persist_semantic_artifacts(
            storage_service,
            document,
            run,
            semantic_pass,
            registry,
            assertions,
            concept_category_bindings,
            summary,
            evaluation_status,
            evaluation_fixture_name,
            evaluation_summary,
            continuity_summary,
        )
        semantic_pass.artifact_json_path = str(json_path)
        semantic_pass.artifact_yaml_path = str(yaml_path)
        semantic_pass.artifact_json_sha256 = json_sha256
        semantic_pass.artifact_yaml_sha256 = yaml_sha256
        session.commit()
        session.refresh(semantic_pass)
        return semantic_pass
    except Exception as exc:
        session.rollback()
        failed_pass = session.get(DocumentRunSemanticPass, semantic_pass.id)
        if failed_pass is None:
            raise
        failed_pass.status = SemanticPassStatus.FAILED.value
        failed_pass.evaluation_status = SemanticEvaluationStatus.FAILED.value
        failed_pass.evaluation_fixture_name = None
        failed_pass.evaluation_summary_json = {
            "all_expectations_passed": False,
            "expected_concept_count": 0,
            "passed_expectations": 0,
            "failed_expectations": 0,
            "expectations": [],
            "reason": "semantic_pass_failed",
        }
        failed_pass.continuity_summary_json = {}
        failed_pass.error_message = str(exc)
        failed_pass.completed_at = utcnow()
        session.commit()
        return failed_pass


def _refresh_semantic_pass_projection(
    session: Session,
    semantic_pass: DocumentRunSemanticPass,
    *,
    storage_service: StorageService,
) -> None:
    document = session.get(Document, semantic_pass.document_id)
    run = session.get(DocumentRun, semantic_pass.run_id)
    if document is None or run is None:
        raise ValueError("Semantic pass refresh requires persisted document and run.")

    registry = get_semantic_registry()
    assertions = _assertion_records(session, semantic_pass.id)
    concept_category_bindings = _concept_category_binding_records(
        session,
        semantic_pass.registry_version,
    )
    summary = _semantic_summary(assertions, concept_category_bindings)
    baseline_semantic_pass = (
        _semantic_pass_row_for_run(session, document.id, semantic_pass.baseline_run_id)
        if semantic_pass.baseline_run_id is not None
        else None
    )
    baseline_assertions = (
        _assertion_records(session, baseline_semantic_pass.id)
        if baseline_semantic_pass is not None
        else []
    )
    continuity_summary = _continuity_summary(
        assertions,
        baseline_run_id=semantic_pass.baseline_run_id,
        baseline_semantic_pass=baseline_semantic_pass,
        baseline_assertions=baseline_assertions,
    )
    semantic_pass.baseline_semantic_pass_id = (
        baseline_semantic_pass.id if baseline_semantic_pass is not None else None
    )
    semantic_pass.summary_json = summary
    semantic_pass.continuity_summary_json = continuity_summary
    semantic_pass.assertion_count = summary["assertion_count"]
    semantic_pass.evidence_count = summary["evidence_count"]
    (
        json_path,
        yaml_path,
        json_sha256,
        yaml_sha256,
    ) = _persist_semantic_artifacts(
        storage_service,
        document,
        run,
        semantic_pass,
        registry,
        assertions,
        concept_category_bindings,
        summary,
        semantic_pass.evaluation_status,
        semantic_pass.evaluation_fixture_name,
        semantic_pass.evaluation_summary_json,
        continuity_summary,
    )
    semantic_pass.artifact_json_path = str(json_path)
    semantic_pass.artifact_yaml_path = str(yaml_path)
    semantic_pass.artifact_json_sha256 = json_sha256
    semantic_pass.artifact_yaml_sha256 = yaml_sha256
    session.flush()


def _assertion_or_404(
    session: Session,
    document_id: UUID,
    assertion_id: UUID,
) -> tuple[DocumentRunSemanticPass, SemanticAssertion, SemanticConcept]:
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            404,
            "semantic_pass_not_found",
            "Semantic pass not found.",
            document_id=str(document_id),
        )
    assertion = session.get(SemanticAssertion, assertion_id)
    if assertion is None or assertion.semantic_pass_id != semantic_pass.id:
        raise api_error(
            404,
            "semantic_assertion_not_found",
            "Semantic assertion not found.",
            document_id=str(document_id),
            assertion_id=str(assertion_id),
        )
    concept = session.get(SemanticConcept, assertion.concept_id)
    if concept is None:
        raise ValueError("Semantic assertion concept disappeared.")
    return semantic_pass, assertion, concept


def _assertion_category_binding_or_404(
    session: Session,
    document_id: UUID,
    binding_id: UUID,
) -> tuple[
    DocumentRunSemanticPass,
    SemanticAssertionCategoryBinding,
    SemanticAssertion,
    SemanticConcept,
    SemanticCategory,
]:
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            404,
            "semantic_pass_not_found",
            "Semantic pass not found.",
            document_id=str(document_id),
        )
    binding = session.get(SemanticAssertionCategoryBinding, binding_id)
    assertion = session.get(SemanticAssertion, binding.assertion_id) if binding is not None else None
    if (
        binding is None
        or assertion is None
        or assertion.semantic_pass_id != semantic_pass.id
    ):
        raise api_error(
            404,
            "semantic_assertion_category_binding_not_found",
            "Semantic assertion category binding not found.",
            document_id=str(document_id),
            binding_id=str(binding_id),
        )
    concept = session.get(SemanticConcept, assertion.concept_id)
    category = session.get(SemanticCategory, binding.category_id)
    if concept is None or category is None:
        raise ValueError("Semantic assertion category binding dependencies disappeared.")
    return semantic_pass, binding, assertion, concept, category


def review_active_semantic_assertion(
    session: Session,
    document_id: UUID,
    assertion_id: UUID,
    *,
    review_status: str,
    review_note: str | None,
    reviewed_by: str | None,
    storage_service: StorageService,
) -> SemanticReviewEventResponse:
    semantic_pass, assertion, concept = _assertion_or_404(session, document_id, assertion_id)
    review_event = DocumentSemanticConceptReview(
        document_id=document_id,
        concept_id=concept.id,
        review_status=review_status,
        review_note=review_note,
        reviewed_by=reviewed_by,
        created_at=utcnow(),
    )
    session.add(review_event)
    session.flush()
    assertion.review_status = review_status
    assertion.details_json = _details_with_review_overlay(
        assertion.details_json or {},
        SemanticReviewOverlay(
            review_id=review_event.id,
            review_status=review_status,
            review_note=review_note,
            reviewed_by=reviewed_by,
            created_at=review_event.created_at,
        ),
    )
    _refresh_semantic_pass_projection(session, semantic_pass, storage_service=storage_service)
    session.commit()
    session.refresh(semantic_pass)
    return SemanticReviewEventResponse(
        review_id=review_event.id,
        scope="assertion",
        document_id=document_id,
        semantic_pass_id=semantic_pass.id,
        assertion_id=assertion.id,
        binding_id=None,
        concept_key=concept.concept_key,
        category_key=None,
        review_status=review_status,
        review_note=review_note,
        reviewed_by=reviewed_by,
        created_at=review_event.created_at,
    )


def review_active_semantic_assertion_category_binding(
    session: Session,
    document_id: UUID,
    binding_id: UUID,
    *,
    review_status: str,
    review_note: str | None,
    reviewed_by: str | None,
    storage_service: StorageService,
) -> SemanticReviewEventResponse:
    semantic_pass, binding, assertion, concept, category = _assertion_category_binding_or_404(
        session,
        document_id,
        binding_id,
    )
    review_event = DocumentSemanticCategoryReview(
        document_id=document_id,
        concept_id=concept.id,
        category_id=category.id,
        review_status=review_status,
        review_note=review_note,
        reviewed_by=reviewed_by,
        created_at=utcnow(),
    )
    session.add(review_event)
    session.flush()
    binding.review_status = review_status
    binding.details_json = _details_with_review_overlay(
        binding.details_json or {},
        SemanticReviewOverlay(
            review_id=review_event.id,
            review_status=review_status,
            review_note=review_note,
            reviewed_by=reviewed_by,
            created_at=review_event.created_at,
        ),
    )
    _refresh_semantic_pass_projection(session, semantic_pass, storage_service=storage_service)
    session.commit()
    session.refresh(semantic_pass)
    return SemanticReviewEventResponse(
        review_id=review_event.id,
        scope="assertion_category_binding",
        document_id=document_id,
        semantic_pass_id=semantic_pass.id,
        assertion_id=assertion.id,
        binding_id=binding.id,
        concept_key=concept.concept_key,
        category_key=category.category_key,
        review_status=review_status,
        review_note=review_note,
        reviewed_by=reviewed_by,
        created_at=review_event.created_at,
    )


def get_active_semantic_pass_row(
    session: Session,
    document_id: UUID,
) -> DocumentRunSemanticPass | None:
    document = get_document_or_404(session, document_id)
    if document.active_run_id is None:
        return None
    return session.execute(
        select(DocumentRunSemanticPass)
        .where(
            DocumentRunSemanticPass.document_id == document_id,
            DocumentRunSemanticPass.run_id == document.active_run_id,
        )
        .order_by(DocumentRunSemanticPass.created_at.desc())
    ).scalars().first()


def get_active_semantic_pass_detail(
    session: Session,
    document_id: UUID,
) -> DocumentSemanticPassResponse:
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            404,
            "semantic_pass_not_found",
            "Semantic pass not found.",
            document_id=str(document_id),
        )

    assertions = _assertion_records(session, semantic_pass.id)
    concept_category_bindings = _concept_category_binding_records(
        session,
        semantic_pass.registry_version,
    )
    return DocumentSemanticPassResponse(
        semantic_pass_id=semantic_pass.id,
        document_id=semantic_pass.document_id,
        run_id=semantic_pass.run_id,
        status=semantic_pass.status,
        registry_version=semantic_pass.registry_version,
        registry_sha256=semantic_pass.registry_sha256,
        extractor_version=semantic_pass.extractor_version,
        artifact_schema_version=semantic_pass.artifact_schema_version,
        baseline_run_id=semantic_pass.baseline_run_id,
        baseline_semantic_pass_id=semantic_pass.baseline_semantic_pass_id,
        has_json_artifact=bool(semantic_pass.artifact_json_path),
        has_yaml_artifact=bool(semantic_pass.artifact_yaml_path),
        artifact_json_sha256=semantic_pass.artifact_json_sha256,
        artifact_yaml_sha256=semantic_pass.artifact_yaml_sha256,
        assertion_count=semantic_pass.assertion_count,
        evidence_count=semantic_pass.evidence_count,
        summary=semantic_pass.summary_json,
        evaluation_status=semantic_pass.evaluation_status,
        evaluation_fixture_name=semantic_pass.evaluation_fixture_name,
        evaluation_version=semantic_pass.evaluation_version,
        evaluation_summary=semantic_pass.evaluation_summary_json,
        continuity_summary=semantic_pass.continuity_summary_json,
        error_message=semantic_pass.error_message,
        created_at=semantic_pass.created_at,
        completed_at=semantic_pass.completed_at,
        concept_category_bindings=[
            SemanticConceptCategoryBindingResponse(
                binding_id=binding["binding_id"],
                concept_key=binding["concept_key"],
                category_key=binding["category_key"],
                category_label=binding["category_label"],
                binding_type=binding["binding_type"],
                created_from=binding["created_from"],
                review_status=binding["review_status"],
                details=binding["details"],
            )
            for binding in concept_category_bindings
        ],
        assertions=[
            SemanticAssertionResponse(
                assertion_id=assertion["assertion_id"],
                concept_key=assertion["concept_key"],
                preferred_label=assertion["preferred_label"],
                scope_note=assertion["scope_note"],
                assertion_kind=assertion["assertion_kind"],
                epistemic_status=assertion["epistemic_status"],
                context_scope=assertion["context_scope"],
                review_status=assertion["review_status"],
                matched_terms=list(assertion["matched_terms"]),
                source_types=list(assertion["source_types"]),
                evidence_count=assertion["evidence_count"],
                confidence=assertion["confidence"],
                details=assertion["details"],
                category_bindings=[
                    SemanticAssertionCategoryBindingResponse(
                        binding_id=binding["binding_id"],
                        category_key=binding["category_key"],
                        category_label=binding["category_label"],
                        binding_type=binding["binding_type"],
                        created_from=binding["created_from"],
                        review_status=binding["review_status"],
                        details=binding["details"],
                    )
                    for binding in assertion["category_bindings"]
                ],
                evidence=[
                    SemanticAssertionEvidenceResponse(
                        evidence_id=evidence["evidence_id"],
                        source_type=evidence["source_type"],
                        chunk_id=evidence["chunk_id"],
                        table_id=evidence["table_id"],
                        figure_id=evidence["figure_id"],
                        page_from=evidence["page_from"],
                        page_to=evidence["page_to"],
                        matched_terms=list(evidence["matched_terms"]),
                        excerpt=evidence["excerpt"],
                        source_label=evidence["source_label"],
                        source_artifact_api_path=evidence["source_artifact_api_path"],
                        source_artifact_sha256=evidence["source_artifact_sha256"],
                        details=evidence["details"],
                    )
                    for evidence in assertion["evidence"]
                ],
            )
            for assertion in assertions
        ],
    )


def get_active_semantic_continuity(
    session: Session,
    document_id: UUID,
) -> SemanticContinuityResponse:
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            404,
            "semantic_pass_not_found",
            "Semantic pass not found.",
            document_id=str(document_id),
        )
    return SemanticContinuityResponse(
        semantic_pass_id=semantic_pass.id,
        document_id=semantic_pass.document_id,
        run_id=semantic_pass.run_id,
        baseline_run_id=semantic_pass.baseline_run_id,
        baseline_semantic_pass_id=semantic_pass.baseline_semantic_pass_id,
        summary=semantic_pass.continuity_summary_json,
    )
