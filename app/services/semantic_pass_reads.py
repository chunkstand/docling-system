from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.text import collapse_whitespace
from app.db.models import (
    DocumentChunk,
    DocumentFigure,
    DocumentRunSemanticPass,
    DocumentTable,
    SemanticAssertion,
    SemanticAssertionCategoryBinding,
    SemanticAssertionEvidence,
    SemanticCategory,
    SemanticConcept,
    SemanticConceptCategoryBinding,
    SemanticEvidenceSourceType,
    SemanticFact,
    SemanticReviewStatus,
)
from app.schemas.semantics import (
    DocumentSemanticPassResponse,
    SemanticAssertionCategoryBindingResponse,
    SemanticAssertionEvidenceResponse,
    SemanticAssertionResponse,
    SemanticConceptCategoryBindingResponse,
    SemanticContinuityResponse,
)
from app.services.documents import get_document_or_404
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


def _build_semantic_sources(session: Session, run_id: UUID) -> list[SemanticSourceItem]:
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


def _materialize_semantic_assertions(
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


def _assertion_records(session: Session, semantic_pass_id: UUID) -> list[dict[str, Any]]:
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


def _semantic_summary(
    assertions: list[dict[str, Any]], concept_category_bindings: list[dict[str, Any]]
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
        review_status: sum(
            1 for assertion in assertions if assertion.get("review_status") == review_status
        )
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
    return (
        session.execute(
            select(DocumentRunSemanticPass)
            .where(
                DocumentRunSemanticPass.document_id == document_id,
                DocumentRunSemanticPass.run_id == run_id,
            )
            .order_by(DocumentRunSemanticPass.created_at.desc())
        )
        .scalars()
        .first()
    )


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


def get_active_semantic_pass_row(
    session: Session, document_id: UUID
) -> DocumentRunSemanticPass | None:
    document = get_document_or_404(session, document_id)
    if document.active_run_id is None:
        return None
    return (
        session.execute(
            select(DocumentRunSemanticPass)
            .where(
                DocumentRunSemanticPass.document_id == document_id,
                DocumentRunSemanticPass.run_id == document.active_run_id,
            )
            .order_by(DocumentRunSemanticPass.created_at.desc())
        )
        .scalars()
        .first()
    )


def get_active_semantic_pass_detail(
    session: Session, document_id: UUID
) -> DocumentSemanticPassResponse:
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            404, "semantic_pass_not_found", "Semantic pass not found.", document_id=str(document_id)
        )
    assertions = _assertion_records(session, semantic_pass.id)
    concept_category_bindings = _concept_category_binding_records(
        session, semantic_pass.registry_version
    )
    fact_count = (
        session.execute(
            select(SemanticFact.id).where(SemanticFact.semantic_pass_id == semantic_pass.id)
        )
        .scalars()
        .all()
    )
    return DocumentSemanticPassResponse(
        semantic_pass_id=semantic_pass.id,
        document_id=semantic_pass.document_id,
        run_id=semantic_pass.run_id,
        ontology_snapshot_id=semantic_pass.ontology_snapshot_id,
        upper_ontology_version=semantic_pass.upper_ontology_version,
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
        fact_count=len(fact_count),
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
    session: Session, document_id: UUID
) -> SemanticContinuityResponse:
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise api_error(
            404, "semantic_pass_not_found", "Semantic pass not found.", document_id=str(document_id)
        )
    return SemanticContinuityResponse(
        semantic_pass_id=semantic_pass.id,
        document_id=semantic_pass.document_id,
        run_id=semantic_pass.run_id,
        baseline_run_id=semantic_pass.baseline_run_id,
        baseline_semantic_pass_id=semantic_pass.baseline_semantic_pass_id,
        summary=semantic_pass.continuity_summary_json,
    )


build_semantic_sources = _build_semantic_sources
assertion_records = _assertion_records
concept_category_binding_records = _concept_category_binding_records
continuity_summary = _continuity_summary
details_with_review_overlay = _details_with_review_overlay
materialize_semantic_assertions = _materialize_semantic_assertions
semantic_pass_row_for_run = _semantic_pass_row_for_run
semantic_summary = _semantic_summary
source_artifact_api_path = _source_artifact_api_path
