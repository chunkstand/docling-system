from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.public.ingest import Document, DocumentRun
from app.db.public.semantic_memory import (
    DocumentRunSemanticPass,
    DocumentSemanticCategoryReview,
    DocumentSemanticConceptReview,
    SemanticAssertion,
    SemanticAssertionCategoryBinding,
    SemanticCategory,
    SemanticConcept,
)
from app.schemas.semantics import SemanticReviewEventResponse
from app.services.semantic_pass_reads import (
    SemanticReviewOverlay,
    assertion_records,
    concept_category_binding_records,
    details_with_review_overlay,
    get_active_semantic_pass_row,
    semantic_pass_row_for_run,
    semantic_summary,
)
from app.services.semantic_pass_reads import (
    continuity_summary as build_continuity_summary,
)
from app.services.semantic_registry import SemanticRegistry
from app.services.storage import StorageService

LoadRegistryFn = Callable[[Session], SemanticRegistry]
PersistArtifactsFn = Callable[..., tuple[Path, Path, str, str]]

_load_registry_fn: LoadRegistryFn | None = None
_persist_artifacts_fn: PersistArtifactsFn | None = None


def configure_semantic_pass_review_projection(
    *,
    load_registry: LoadRegistryFn,
    persist_artifacts: PersistArtifactsFn,
) -> None:
    global _load_registry_fn, _persist_artifacts_fn

    _load_registry_fn = load_registry
    _persist_artifacts_fn = persist_artifacts


def _configured_load_registry() -> LoadRegistryFn:
    if _load_registry_fn is None:
        raise RuntimeError("Semantic pass review owner is missing registry loader configuration.")
    return _load_registry_fn


def _configured_persist_artifacts() -> PersistArtifactsFn:
    if _persist_artifacts_fn is None:
        raise RuntimeError(
            "Semantic pass review owner is missing artifact persistence configuration."
        )
    return _persist_artifacts_fn


def latest_concept_review_overlays(
    session: Session,
    document_id: UUID,
    registry_version: str,
) -> dict[str, SemanticReviewOverlay]:
    del registry_version
    rows = session.execute(
        select(DocumentSemanticConceptReview, SemanticConcept)
        .join(SemanticConcept, SemanticConcept.id == DocumentSemanticConceptReview.concept_id)
        .where(DocumentSemanticConceptReview.document_id == document_id)
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


def latest_category_review_overlays(
    session: Session,
    document_id: UUID,
    registry_version: str,
) -> dict[tuple[str, str], SemanticReviewOverlay]:
    del registry_version
    rows = session.execute(
        select(DocumentSemanticCategoryReview, SemanticConcept, SemanticCategory)
        .join(SemanticConcept, SemanticConcept.id == DocumentSemanticCategoryReview.concept_id)
        .join(SemanticCategory, SemanticCategory.id == DocumentSemanticCategoryReview.category_id)
        .where(DocumentSemanticCategoryReview.document_id == document_id)
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


def refresh_semantic_pass_projection(
    session: Session,
    semantic_pass: DocumentRunSemanticPass,
    *,
    storage_service: StorageService,
) -> None:
    document = session.get(Document, semantic_pass.document_id)
    run = session.get(DocumentRun, semantic_pass.run_id)
    if document is None or run is None:
        raise ValueError("Semantic pass refresh requires persisted document and run.")
    registry = _configured_load_registry()(session)
    assertions = assertion_records(session, semantic_pass.id)
    concept_category_bindings = concept_category_binding_records(
        session,
        semantic_pass.registry_version,
    )
    summary = semantic_summary(assertions, concept_category_bindings)
    baseline_semantic_pass = (
        semantic_pass_row_for_run(session, document.id, semantic_pass.baseline_run_id)
        if semantic_pass.baseline_run_id is not None
        else None
    )
    baseline_assertions = (
        assertion_records(session, baseline_semantic_pass.id)
        if baseline_semantic_pass is not None
        else []
    )
    continuity_summary = build_continuity_summary(
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
    ) = _configured_persist_artifacts()(
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
    assertion = (
        session.get(SemanticAssertion, binding.assertion_id) if binding is not None else None
    )
    if binding is None or assertion is None or assertion.semantic_pass_id != semantic_pass.id:
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
    assertion.details_json = details_with_review_overlay(
        assertion.details_json or {},
        SemanticReviewOverlay(
            review_id=review_event.id,
            review_status=review_status,
            review_note=review_note,
            reviewed_by=reviewed_by,
            created_at=review_event.created_at,
        ),
    )
    refresh_semantic_pass_projection(session, semantic_pass, storage_service=storage_service)
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
    binding.details_json = details_with_review_overlay(
        binding.details_json or {},
        SemanticReviewOverlay(
            review_id=review_event.id,
            review_status=review_status,
            review_note=review_note,
            reviewed_by=reviewed_by,
            created_at=review_event.created_at,
        ),
    )
    refresh_semantic_pass_projection(session, semantic_pass, storage_service=storage_service)
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
