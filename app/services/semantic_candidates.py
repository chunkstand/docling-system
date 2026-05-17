from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.semantic_candidate_core import (
    DEFAULT_BASELINE_EXTRACTOR as DEFAULT_BASELINE_EXTRACTOR,
)
from app.services.semantic_candidate_core import (
    DEFAULT_CANDIDATE_EXTRACTOR as DEFAULT_CANDIDATE_EXTRACTOR,
)
from app.services.semantic_candidate_core import (
    DEFAULT_CANDIDATE_SCORE_THRESHOLD as DEFAULT_CANDIDATE_SCORE_THRESHOLD,
)
from app.services.semantic_candidate_core import (
    DEFAULT_MAX_CANDIDATES_PER_SOURCE as DEFAULT_MAX_CANDIDATES_PER_SOURCE,
)
from app.services.semantic_candidate_core import (
    CandidateConceptScore as CandidateConceptScore,
)
from app.services.semantic_candidate_core import (
    CandidateExtractionResult as CandidateExtractionResult,
)
from app.services.semantic_candidate_core import (
    CandidateExtractorDescriptor as CandidateExtractorDescriptor,
)
from app.services.semantic_candidate_core import (
    CandidateSourcePrediction as CandidateSourcePrediction,
)
from app.services.semantic_candidate_core import cosine_similarity as cosine_similarity
from app.services.semantic_candidate_core import embedding_vector as embedding_vector
from app.services.semantic_candidate_core import tokenize as tokenize
from app.services.semantic_candidate_core import unique_document_ids as unique_document_ids
from app.services.semantic_candidate_evaluation import (
    evaluate_semantic_candidate_extractor as _evaluate_semantic_candidate_extractor_impl,
)
from app.services.semantic_candidate_export import (
    export_semantic_supervision_corpus as _export_semantic_supervision_corpus_impl,
)
from app.services.semantic_candidate_triage import (
    collect_shadow_candidates_for_brief as _collect_shadow_candidates_for_brief_impl,
)
from app.services.semantic_candidate_triage import (
    triage_semantic_candidate_disagreements as triage_semantic_candidate_disagreements,
)
from app.services.semantic_registry import get_semantic_registry
from app.services.semantics import (
    build_semantic_sources,
    get_active_semantic_pass_detail,
    latest_category_review_overlays,
    latest_concept_review_overlays,
    semantic_evaluation_result,
)


def export_semantic_supervision_corpus(
    session: Session,
    *,
    document_ids: list[UUID],
    reviewed_only: bool,
    include_generation_verifications: bool,
    output_path: Path,
) -> dict:
    return _export_semantic_supervision_corpus_impl(
        session,
        document_ids=document_ids,
        reviewed_only=reviewed_only,
        include_generation_verifications=include_generation_verifications,
        output_path=output_path,
        get_active_semantic_pass_detail_fn=get_active_semantic_pass_detail,
    )


def evaluate_semantic_candidate_extractor(
    session: Session,
    *,
    document_ids: list[UUID],
    baseline_extractor_name: str,
    candidate_extractor_name: str,
    score_threshold: float,
    max_candidates_per_source: int,
) -> dict:
    return _evaluate_semantic_candidate_extractor_impl(
        session,
        document_ids=document_ids,
        baseline_extractor_name=baseline_extractor_name,
        candidate_extractor_name=candidate_extractor_name,
        score_threshold=score_threshold,
        max_candidates_per_source=max_candidates_per_source,
        get_semantic_registry_fn=get_semantic_registry,
        get_active_semantic_pass_detail_fn=get_active_semantic_pass_detail,
        build_semantic_sources_fn=build_semantic_sources,
        latest_concept_review_overlays_fn=latest_concept_review_overlays,
        latest_category_review_overlays_fn=latest_category_review_overlays,
        semantic_evaluation_result_fn=semantic_evaluation_result,
    )


def collect_shadow_candidates_for_brief(
    session: Session,
    *,
    document_ids: list[UUID],
    candidate_extractor_name: str,
    score_threshold: float,
    requested_concept_keys: set[str],
    requested_category_keys: set[str],
    max_shadow_candidates: int,
) -> tuple[list[dict], dict]:
    return _collect_shadow_candidates_for_brief_impl(
        session,
        document_ids=document_ids,
        candidate_extractor_name=candidate_extractor_name,
        score_threshold=score_threshold,
        requested_concept_keys=requested_concept_keys,
        requested_category_keys=requested_category_keys,
        max_shadow_candidates=max_shadow_candidates,
        evaluate_semantic_candidate_extractor_fn=evaluate_semantic_candidate_extractor,
    )
