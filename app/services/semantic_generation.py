from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.services.semantic_candidates import collect_shadow_candidates_for_brief
from app.services.semantic_facts import list_document_semantic_facts
from app.services.semantic_generation_brief import (
    prepare_semantic_generation_brief as _prepare_semantic_generation_brief_impl,
)
from app.services.semantic_generation_draft import (
    draft_semantic_grounded_document as _draft_semantic_grounded_document_impl,
)
from app.services.semantic_generation_shared import (
    DOCUMENT_KIND_KNOWLEDGE_BRIEF as DOCUMENT_KIND_KNOWLEDGE_BRIEF,
)
from app.services.semantic_generation_shared import (
    TARGET_LENGTH_EVIDENCE_LIMIT as TARGET_LENGTH_EVIDENCE_LIMIT,
)
from app.services.semantic_generation_shared import (
    SemanticGroundedDocumentVerificationOutcome as SemanticGroundedDocumentVerificationOutcome,
)
from app.services.semantic_generation_verify import (
    verify_semantic_grounded_document as _verify_semantic_grounded_document_impl,
)
from app.services.semantic_graph import graph_memory_for_brief
from app.services.semantics import get_active_semantic_pass_detail


def prepare_semantic_generation_brief(
    session: Session,
    *,
    title: str,
    goal: str,
    audience: str | None,
    document_ids: list[UUID],
    concept_keys: list[str],
    category_keys: list[str],
    target_length: str,
    review_policy: str,
    include_shadow_candidates: bool = False,
    candidate_extractor_name: str = "concept_ranker_v1",
    candidate_score_threshold: float = 0.34,
    max_shadow_candidates: int = 8,
) -> dict:
    return _prepare_semantic_generation_brief_impl(
        session,
        title=title,
        goal=goal,
        audience=audience,
        document_ids=document_ids,
        concept_keys=concept_keys,
        category_keys=category_keys,
        target_length=target_length,
        review_policy=review_policy,
        include_shadow_candidates=include_shadow_candidates,
        candidate_extractor_name=candidate_extractor_name,
        candidate_score_threshold=candidate_score_threshold,
        max_shadow_candidates=max_shadow_candidates,
        get_active_semantic_pass_detail_fn=get_active_semantic_pass_detail,
        list_document_semantic_facts_fn=list_document_semantic_facts,
        graph_memory_for_brief_fn=graph_memory_for_brief,
        collect_shadow_candidates_for_brief_fn=collect_shadow_candidates_for_brief,
    )


def draft_semantic_grounded_document(
    brief_payload: dict,
    *,
    brief_task_id: UUID,
) -> dict:
    return _draft_semantic_grounded_document_impl(
        brief_payload,
        brief_task_id=brief_task_id,
    )


def verify_semantic_grounded_document(
    draft_payload: dict,
    *,
    max_unsupported_claim_count: int = 0,
    require_full_claim_traceability: bool = True,
    require_full_concept_coverage: bool = True,
) -> SemanticGroundedDocumentVerificationOutcome:
    return _verify_semantic_grounded_document_impl(
        draft_payload,
        max_unsupported_claim_count=max_unsupported_claim_count,
        require_full_claim_traceability=require_full_claim_traceability,
        require_full_concept_coverage=require_full_concept_coverage,
    )
