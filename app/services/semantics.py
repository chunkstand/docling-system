from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

import app.services.semantic_pass_lifecycle as _semantic_pass_lifecycle
import app.services.semantic_pass_reads as _semantic_pass_reads
import app.services.semantic_registry_preview as _semantic_registry_preview
from app.services.semantic_pass_lifecycle import (
    review_active_semantic_assertion as review_active_semantic_assertion,
)
from app.services.semantic_pass_lifecycle import (
    review_active_semantic_assertion_category_binding as _review_active_binding,
)

SEMANTIC_ARTIFACT_SCHEMA_NAME = _semantic_pass_lifecycle.SEMANTIC_ARTIFACT_SCHEMA_NAME
SEMANTIC_ARTIFACT_SCHEMA_VERSION = _semantic_pass_lifecycle.SEMANTIC_ARTIFACT_SCHEMA_VERSION
SEMANTIC_EVAL_VERSION = _semantic_pass_lifecycle.SEMANTIC_EVAL_VERSION
SEMANTIC_EXTRACTOR_VERSION = _semantic_pass_lifecycle.SEMANTIC_EXTRACTOR_VERSION
SEMANTIC_EXCERPT_LIMIT = _semantic_pass_reads.SEMANTIC_EXCERPT_LIMIT
SEMANTIC_MATCH_STRATEGY = _semantic_pass_reads.SEMANTIC_MATCH_STRATEGY
SemanticAssertionMaterialization = _semantic_pass_reads.SemanticAssertionMaterialization
SemanticEvidenceMaterialization = _semantic_pass_reads.SemanticEvidenceMaterialization
SemanticReviewOverlay = _semantic_pass_reads.SemanticReviewOverlay
SemanticSourceItem = _semantic_pass_reads.SemanticSourceItem
build_semantic_sources = _semantic_pass_reads.build_semantic_sources
execute_semantic_pass = _semantic_pass_lifecycle.execute_semantic_pass
get_active_semantic_continuity = _semantic_pass_reads.get_active_semantic_continuity
get_active_semantic_pass_detail = _semantic_pass_reads.get_active_semantic_pass_detail
get_active_semantic_pass_row = _semantic_pass_reads.get_active_semantic_pass_row
latest_category_review_overlays = _semantic_pass_lifecycle.latest_category_review_overlays
latest_concept_review_overlays = _semantic_pass_lifecycle.latest_concept_review_overlays
materialize_semantic_assertions = _semantic_pass_reads.materialize_semantic_assertions
preview_assertions = _semantic_registry_preview.preview_assertions
preview_concept_category_bindings = _semantic_registry_preview.preview_concept_category_bindings
review_active_semantic_assertion_category_binding = _review_active_binding
semantic_evaluation_result = _semantic_registry_preview.semantic_evaluation_result
source_artifact_api_path = _semantic_pass_reads.source_artifact_api_path


def preview_semantic_registry_update_for_document(
    session: Session,
    document_id: UUID,
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    return _semantic_registry_preview.preview_semantic_registry_update_for_document(
        session,
        document_id,
        registry_payload,
        latest_concept_review_overlays_fn=_semantic_pass_lifecycle.latest_concept_review_overlays,
        latest_category_review_overlays_fn=_semantic_pass_lifecycle.latest_category_review_overlays,
    )
