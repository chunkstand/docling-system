from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.services.semantic_governance import record_semantic_graph_snapshot_governance_events
from app.services.semantic_graph_build import (
    build_shadow_semantic_graph as _build_shadow_semantic_graph_impl,
)
from app.services.semantic_graph_core import (
    get_active_semantic_graph_payload as get_active_semantic_graph_payload,
)
from app.services.semantic_graph_core import (
    get_active_semantic_graph_snapshot as get_active_semantic_graph_snapshot,
)
from app.services.semantic_graph_evaluation import (
    evaluate_semantic_relation_extractor as _evaluate_semantic_relation_extractor_impl,
)
from app.services.semantic_graph_evaluation import (
    triage_semantic_graph_disagreements as triage_semantic_graph_disagreements,
)
from app.services.semantic_graph_memory import (
    graph_memory_for_brief as _graph_memory_for_brief_impl,
)
from app.services.semantic_graph_promotions import (
    draft_graph_promotions as _draft_graph_promotions_impl,
)
from app.services.semantic_graph_promotions import (
    verify_draft_graph_promotions as _verify_draft_graph_promotions_impl,
)
from app.services.semantic_graph_snapshot_lifecycle import (
    apply_graph_promotions as _apply_graph_promotions_impl,
)
from app.services.semantic_graph_snapshot_lifecycle import (
    persist_semantic_graph_snapshot as _persist_semantic_graph_snapshot_impl,
)
from app.services.semantic_registry import get_active_semantic_ontology_snapshot
from app.services.semantics import get_active_semantic_pass_detail


def build_shadow_semantic_graph(
    session: Session,
    *,
    document_ids: list[UUID],
    relation_extractor_name: str,
    minimum_review_status: str,
    min_shared_documents: int,
    score_threshold: float,
) -> dict:
    return _build_shadow_semantic_graph_impl(
        session,
        document_ids=document_ids,
        relation_extractor_name=relation_extractor_name,
        minimum_review_status=minimum_review_status,
        min_shared_documents=min_shared_documents,
        score_threshold=score_threshold,
        get_active_semantic_ontology_snapshot_fn=get_active_semantic_ontology_snapshot,
        get_active_semantic_pass_detail_fn=get_active_semantic_pass_detail,
    )


def evaluate_semantic_relation_extractor(
    session: Session,
    *,
    document_ids: list[UUID],
    baseline_extractor_name: str,
    candidate_extractor_name: str,
    minimum_review_status: str,
    baseline_min_shared_documents: int,
    candidate_score_threshold: float,
    expected_min_shared_documents: int,
) -> dict:
    return _evaluate_semantic_relation_extractor_impl(
        session,
        document_ids=document_ids,
        baseline_extractor_name=baseline_extractor_name,
        candidate_extractor_name=candidate_extractor_name,
        minimum_review_status=minimum_review_status,
        baseline_min_shared_documents=baseline_min_shared_documents,
        candidate_score_threshold=candidate_score_threshold,
        expected_min_shared_documents=expected_min_shared_documents,
        get_active_semantic_ontology_snapshot_fn=get_active_semantic_ontology_snapshot,
        get_active_semantic_pass_detail_fn=get_active_semantic_pass_detail,
        get_active_semantic_graph_payload_fn=get_active_semantic_graph_payload,
    )


def draft_graph_promotions(
    session: Session,
    *,
    source_payload: dict,
    source_task_id: UUID,
    source_task_type: str,
    proposed_graph_version: str | None,
    rationale: str | None,
    edge_ids: list[str],
    min_score: float,
) -> dict:
    return _draft_graph_promotions_impl(
        session,
        source_payload=source_payload,
        source_task_id=source_task_id,
        source_task_type=source_task_type,
        proposed_graph_version=proposed_graph_version,
        rationale=rationale,
        edge_ids=edge_ids,
        min_score=min_score,
        get_active_semantic_ontology_snapshot_fn=get_active_semantic_ontology_snapshot,
        get_active_semantic_graph_snapshot_fn=get_active_semantic_graph_snapshot,
    )


def verify_draft_graph_promotions(
    session: Session,
    draft: dict,
    *,
    min_supporting_document_count: int,
    max_conflict_count: int,
    require_current_ontology_snapshot: bool,
) -> tuple[dict, dict, list[str], str, list[dict]]:
    return _verify_draft_graph_promotions_impl(
        session,
        draft,
        min_supporting_document_count=min_supporting_document_count,
        max_conflict_count=max_conflict_count,
        require_current_ontology_snapshot=require_current_ontology_snapshot,
        get_active_semantic_ontology_snapshot_fn=get_active_semantic_ontology_snapshot,
    )


def persist_semantic_graph_snapshot(
    session: Session,
    payload: dict,
    *,
    source_kind: str,
    source_task_id: UUID | None = None,
    source_task_type: str | None = None,
    parent_snapshot_id: UUID | None = None,
    activate: bool = False,
):
    return _persist_semantic_graph_snapshot_impl(
        session,
        payload,
        source_kind=source_kind,
        source_task_id=source_task_id,
        source_task_type=source_task_type,
        parent_snapshot_id=parent_snapshot_id,
        activate=activate,
        record_semantic_graph_snapshot_governance_events_fn=record_semantic_graph_snapshot_governance_events,
    )


def apply_graph_promotions(
    session: Session,
    draft: dict,
    *,
    source_task_id: UUID,
    source_task_type: str,
    reason: str | None,
) -> dict:
    return _apply_graph_promotions_impl(
        session,
        draft,
        source_task_id=source_task_id,
        source_task_type=source_task_type,
        reason=reason,
        record_semantic_graph_snapshot_governance_events_fn=record_semantic_graph_snapshot_governance_events,
    )


def graph_memory_for_brief(
    session: Session,
    *,
    document_ids: list[UUID],
    requested_concept_keys: set[str],
    available_concept_keys: set[str],
) -> tuple[list[str], list[dict], dict, list[str]]:
    return _graph_memory_for_brief_impl(
        session,
        document_ids=document_ids,
        requested_concept_keys=requested_concept_keys,
        available_concept_keys=available_concept_keys,
        get_active_semantic_graph_snapshot_fn=get_active_semantic_graph_snapshot,
    )
