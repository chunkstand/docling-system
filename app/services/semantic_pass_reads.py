from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.semantic_pass_source_records as source_record_owner
from app.api.errors import api_error
from app.db.models import (
    DocumentRunSemanticPass,
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
from app.services.document_run_views import get_document_or_404

SEMANTIC_EXCERPT_LIMIT = source_record_owner.SEMANTIC_EXCERPT_LIMIT
SEMANTIC_MATCH_STRATEGY = source_record_owner.SEMANTIC_MATCH_STRATEGY
SemanticAssertionMaterialization = source_record_owner.SemanticAssertionMaterialization
SemanticEvidenceMaterialization = source_record_owner.SemanticEvidenceMaterialization
SemanticReviewOverlay = source_record_owner.SemanticReviewOverlay
SemanticSourceItem = source_record_owner.SemanticSourceItem
_assertion_records = source_record_owner.assertion_records
_build_semantic_sources = source_record_owner.build_semantic_sources
_concept_category_binding_records = source_record_owner.concept_category_binding_records
_details_with_review_overlay = source_record_owner.details_with_review_overlay
_materialize_semantic_assertions = source_record_owner.materialize_semantic_assertions
_source_artifact_api_path = source_record_owner.source_artifact_api_path


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
