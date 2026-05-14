from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.config import get_settings, semantics_feature_enabled
from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentRun,
    DocumentRunSemanticPass,
    DocumentSemanticCategoryReview,
    DocumentSemanticConceptReview,
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
    SemanticPassStatus,
    SemanticReviewStatus,
    SemanticTerm,
    SemanticTermKind,
)
from app.schemas.semantics import SemanticReviewEventResponse
from app.services.semantic_pass_reads import (
    SemanticAssertionMaterialization,
    SemanticReviewOverlay,
    assertion_records,
    build_semantic_sources,
    concept_category_binding_records,
    details_with_review_overlay,
    get_active_semantic_pass_row,
    materialize_semantic_assertions,
    semantic_pass_row_for_run,
    semantic_summary,
)
from app.services.semantic_pass_reads import (
    continuity_summary as build_continuity_summary,
)
from app.services.semantic_registry import SemanticRegistry, get_semantic_registry
from app.services.semantic_registry_preview import semantic_evaluation_result
from app.services.storage import StorageService

SEMANTIC_ARTIFACT_SCHEMA_NAME = "docling.semantic_pass"
SEMANTIC_ARTIFACT_SCHEMA_VERSION = "2.1"
SEMANTIC_EXTRACTOR_VERSION = "semantics_sidecar_v2_1"
SEMANTIC_MATCH_STRATEGY = "normalized_phrase_contains"
SEMANTIC_EVAL_VERSION = 2


def _latest_concept_review_overlays(
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


def _latest_category_review_overlays(
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
            select(SemanticConcept).where(
                SemanticConcept.registry_version == registry.registry_version
            )
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
            .join(SemanticConcept, SemanticConcept.id == SemanticConceptTerm.concept_id)
            .where(SemanticConcept.registry_version == registry.registry_version)
        ).all()
    )
    concept_category_binding_rows = {
        (concept.concept_key, category.category_key): binding
        for binding, concept, category in session.execute(
            select(SemanticConceptCategoryBinding, SemanticConcept, SemanticCategory)
            .join(SemanticConcept, SemanticConcept.id == SemanticConceptCategoryBinding.concept_id)
            .join(
                SemanticCategory, SemanticCategory.id == SemanticConceptCategoryBinding.category_id
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
            details_json=details_with_review_overlay(
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
                    details_json=details_with_review_overlay(
                        {
                            "inherited_from_concept_category_binding_id": str(
                                concept_category_binding.id
                            ),
                            "concept_category_review_status": (
                                concept_category_binding.review_status
                            ),
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
        "ontology_snapshot_id": (
            str(semantic_pass.ontology_snapshot_id) if semantic_pass.ontology_snapshot_id else None
        ),
        "baseline_run_id": str(semantic_pass.baseline_run_id)
        if semantic_pass.baseline_run_id
        else None,
        "baseline_semantic_pass_id": (
            str(semantic_pass.baseline_semantic_pass_id)
            if semantic_pass.baseline_semantic_pass_id
            else None
        ),
        "status": semantic_pass.status,
        "created_at": semantic_pass.created_at.isoformat(),
        "completed_at": semantic_pass.completed_at.isoformat()
        if semantic_pass.completed_at
        else None,
        "registry": {
            "name": registry.registry_name,
            "version": registry.registry_version,
            "sha256": registry.sha256,
            "upper_ontology_version": registry.upper_ontology_version,
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
            ontology_snapshot_id=registry.snapshot_id,
            upper_ontology_version=registry.upper_ontology_version,
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
        semantic_pass.ontology_snapshot_id = registry.snapshot_id
        semantic_pass.upper_ontology_version = registry.upper_ontology_version
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
    settings = get_settings()
    if not semantics_feature_enabled(settings):
        raise ValueError("Semantic layer is disabled by configuration.")
    registry = get_semantic_registry(session)
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
        sources = build_semantic_sources(session, run.id)
        materializations = materialize_semantic_assertions(registry, sources)
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
        assertions = assertion_records(session, semantic_pass.id)
        concept_category_bindings = concept_category_binding_records(
            session,
            registry.registry_version,
        )
        summary = semantic_summary(assertions, concept_category_bindings)
        evaluation_status, evaluation_fixture_name, evaluation_summary = semantic_evaluation_result(
            document,
            assertions,
            concept_category_bindings,
        )
        baseline_semantic_pass = (
            semantic_pass_row_for_run(session, document.id, baseline_run_id)
            if baseline_run_id is not None
            else None
        )
        baseline_assertions = (
            assertion_records(session, baseline_semantic_pass.id)
            if baseline_semantic_pass is not None
            else []
        )
        continuity_summary = build_continuity_summary(
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
    registry = get_semantic_registry(session)
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


latest_category_review_overlays = _latest_category_review_overlays
latest_concept_review_overlays = _latest_concept_review_overlays
