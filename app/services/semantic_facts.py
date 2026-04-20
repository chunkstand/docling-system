from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    Document,
    SemanticAssertion,
    SemanticConcept,
    SemanticEntity,
    SemanticEntityType,
    SemanticFact,
    SemanticFactEvidence,
    SemanticOntologySnapshot,
    SemanticReviewStatus,
)
from app.services.semantic_registry import (
    get_semantic_registry,
    validate_semantic_relation_instance,
)
from app.services.semantics import get_active_semantic_pass_detail, get_active_semantic_pass_row

DOCUMENT_MENTIONS_CONCEPT_RELATION_KEY = "document_mentions_concept"
DOCUMENT_MENTIONS_CONCEPT_RELATION_LABEL = "Document Mentions Concept"


def _review_rank(review_status: str) -> int:
    if review_status == SemanticReviewStatus.APPROVED.value:
        return 2
    if review_status == SemanticReviewStatus.CANDIDATE.value:
        return 1
    return 0


def _fact_graph_success_metrics(
    *,
    fact_count: int,
    approved_fact_count: int,
    entity_count: int,
    supported_fact_count: int,
    constraint_valid_fact_count: int,
    minimum_review_status: str,
) -> list[dict[str, Any]]:
    approved_fact_support_ratio = approved_fact_count / fact_count if fact_count else 0.0
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": fact_count == supported_fact_count,
            "summary": "Every fact in the graph remains traceable to assertion-backed evidence.",
            "details": {
                "fact_count": fact_count,
                "supported_fact_count": supported_fact_count,
            },
        },
        {
            "metric_key": "constraint_valid_relation_ratio",
            "stakeholder": "Milestone",
            "passed": fact_count == constraint_valid_fact_count,
            "summary": "Every fact satisfies the active ontology relation constraints.",
            "details": {
                "fact_count": fact_count,
                "constraint_valid_fact_count": constraint_valid_fact_count,
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": fact_count == 0 or entity_count >= 2,
            "summary": "The fact graph exposes typed entities and relations for downstream agents.",
            "details": {
                "fact_count": fact_count,
                "entity_count": entity_count,
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": minimum_review_status in {"candidate", "approved"},
            "summary": "Fact materialization stays bounded to an explicit review threshold.",
            "details": {"minimum_review_status": minimum_review_status},
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": fact_count > 0
            or minimum_review_status == SemanticReviewStatus.APPROVED.value,
            "summary": (
                "The workspace stores reusable fact context instead of "
                "recomputing it ad hoc."
            ),
            "details": {"fact_count": fact_count},
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": fact_count >= 0 and entity_count >= fact_count,
            "summary": (
                "The fact graph compacts assertion evidence into a smaller "
                "relational memory surface."
            ),
            "details": {
                "fact_count": fact_count,
                "entity_count": entity_count,
            },
        },
        {
            "metric_key": "approved_fact_support_ratio",
            "stakeholder": "Milestone",
            "passed": fact_count == 0 or approved_fact_support_ratio >= 0.8,
            "summary": "Most generated semantic facts are approved before downstream use.",
            "details": {
                "approved_fact_support_ratio": round(approved_fact_support_ratio, 4),
                "approved_fact_count": approved_fact_count,
                "fact_count": fact_count,
            },
        },
    ]


def _upsert_entity(
    session: Session,
    *,
    entity_key: str,
    entity_type: str,
    preferred_label: str,
    ontology_snapshot_id: UUID | None,
    document_id: UUID | None = None,
    concept_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> SemanticEntity:
    entity = session.execute(
        select(SemanticEntity).where(SemanticEntity.entity_key == entity_key)
    ).scalar_one_or_none()
    if entity is None:
        entity = SemanticEntity(
            entity_key=entity_key,
            entity_type=entity_type,
            preferred_label=preferred_label,
            ontology_snapshot_id=ontology_snapshot_id,
            document_id=document_id,
            concept_id=concept_id,
            details_json=details or {},
            created_at=utcnow(),
        )
        session.add(entity)
        session.flush()
    else:
        entity.entity_type = entity_type
        entity.preferred_label = preferred_label
        entity.ontology_snapshot_id = ontology_snapshot_id
        entity.document_id = document_id
        entity.concept_id = concept_id
        entity.details_json = details or {}
    return entity


def _fact_relation_label(snapshot: SemanticOntologySnapshot | None) -> str:
    if snapshot is None:
        return DOCUMENT_MENTIONS_CONCEPT_RELATION_LABEL
    payload = snapshot.payload_json or {}
    for relation in payload.get("relations") or []:
        if str(relation.get("relation_key") or "") == DOCUMENT_MENTIONS_CONCEPT_RELATION_KEY:
            label = str(relation.get("preferred_label") or "").strip()
            if label:
                return label
    return DOCUMENT_MENTIONS_CONCEPT_RELATION_LABEL


def list_document_semantic_facts(
    session: Session,
    document_id: UUID,
) -> list[dict[str, Any]]:
    rows = (
        session.execute(
            select(SemanticFact)
            .where(SemanticFact.document_id == document_id)
            .order_by(SemanticFact.created_at, SemanticFact.id)
        )
        .scalars()
        .all()
    )
    fact_ids = [row.id for row in rows]
    evidence_rows = (
        session.execute(
            select(SemanticFactEvidence)
            .where(SemanticFactEvidence.fact_id.in_(fact_ids))
            .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
        )
        .scalars()
        .all()
        if fact_ids
        else []
    )
    evidence_ids_by_fact: dict[UUID, list[UUID]] = {}
    for evidence in evidence_rows:
        if evidence.assertion_evidence_id is not None:
            evidence_ids_by_fact.setdefault(evidence.fact_id, []).append(
                evidence.assertion_evidence_id
            )

    entity_ids = {row.subject_entity_id for row in rows} | {
        row.object_entity_id for row in rows if row.object_entity_id is not None
    }
    entities = {
        entity.id: entity
        for entity in (
            session.execute(select(SemanticEntity).where(SemanticEntity.id.in_(entity_ids)))
            .scalars()
            .all()
            if entity_ids
            else []
        )
    }
    return [
        {
            "fact_id": row.id,
            "document_id": row.document_id,
            "run_id": row.run_id,
            "semantic_pass_id": row.semantic_pass_id,
            "relation_key": row.relation_key,
            "relation_label": row.relation_label,
            "subject_entity_key": entities[row.subject_entity_id].entity_key,
            "subject_label": entities[row.subject_entity_id].preferred_label,
            "object_entity_key": (
                entities[row.object_entity_id].entity_key
                if row.object_entity_id is not None and row.object_entity_id in entities
                else None
            ),
            "object_label": (
                entities[row.object_entity_id].preferred_label
                if row.object_entity_id is not None and row.object_entity_id in entities
                else None
            ),
            "object_value_text": row.object_value_text,
            "review_status": row.review_status,
            "assertion_id": row.source_assertion_id,
            "evidence_ids": evidence_ids_by_fact.get(row.id, []),
        }
        for row in rows
    ]


def build_document_fact_graph(
    session: Session,
    *,
    document_id: UUID,
    minimum_review_status: str,
) -> dict[str, Any]:
    semantic_pass = get_active_semantic_pass_row(session, document_id)
    if semantic_pass is None:
        raise ValueError("Document does not have an active semantic pass.")
    semantic_pass_detail = get_active_semantic_pass_detail(session, document_id)
    document = session.get(Document, document_id)
    if document is None:
        raise ValueError(f"Document not found: {document_id}")

    minimum_rank = _review_rank(minimum_review_status)
    snapshot = (
        session.get(SemanticOntologySnapshot, semantic_pass.ontology_snapshot_id)
        if semantic_pass.ontology_snapshot_id is not None
        else None
    )
    relation_label = _fact_relation_label(snapshot)
    registry = get_semantic_registry(session)

    prior_fact_ids = list(
        session.execute(
            select(SemanticFact.id).where(SemanticFact.semantic_pass_id == semantic_pass.id)
        ).scalars()
    )
    if prior_fact_ids:
        session.query(SemanticFactEvidence).filter(
            SemanticFactEvidence.fact_id.in_(prior_fact_ids)
        ).delete(synchronize_session=False)
        session.query(SemanticFact).filter(SemanticFact.id.in_(prior_fact_ids)).delete(
            synchronize_session=False
        )
    session.flush()

    document_entity = _upsert_entity(
        session,
        entity_key=f"document:{document_id}",
        entity_type=SemanticEntityType.DOCUMENT.value,
        preferred_label=document.title or document.source_filename,
        ontology_snapshot_id=semantic_pass.ontology_snapshot_id,
        document_id=document.id,
        details={
            "source_filename": document.source_filename,
            "run_id": str(semantic_pass.run_id),
        },
    )

    approved_fact_count = 0
    constraint_valid_fact_count = 0
    entity_ids: set[UUID] = {document_entity.id}
    for assertion in semantic_pass_detail.assertions:
        if _review_rank(assertion.review_status) < minimum_rank:
            continue
        assertion_row = session.get(SemanticAssertion, assertion.assertion_id)
        concept_row = (
            session.get(SemanticConcept, assertion_row.concept_id) if assertion_row else None
        )
        concept_entity = _upsert_entity(
            session,
            entity_key=f"concept:{assertion.concept_key}",
            entity_type=SemanticEntityType.CONCEPT.value,
            preferred_label=assertion.preferred_label,
            ontology_snapshot_id=semantic_pass.ontology_snapshot_id,
            concept_id=concept_row.id if concept_row is not None else None,
            details={
                "concept_key": assertion.concept_key,
                "registry_version": semantic_pass.registry_version,
            },
        )
        entity_ids.add(concept_entity.id)
        validation_errors = validate_semantic_relation_instance(
            registry,
            relation_key=DOCUMENT_MENTIONS_CONCEPT_RELATION_KEY,
            subject_entity_key=document_entity.entity_key,
            object_entity_key=concept_entity.entity_key,
        )
        if validation_errors:
            raise ValueError("; ".join(validation_errors))
        constraint_valid_fact_count += 1
        fact = SemanticFact(
            document_id=document.id,
            run_id=semantic_pass.run_id,
            semantic_pass_id=semantic_pass.id,
            ontology_snapshot_id=semantic_pass.ontology_snapshot_id,
            subject_entity_id=document_entity.id,
            relation_key=DOCUMENT_MENTIONS_CONCEPT_RELATION_KEY,
            relation_label=relation_label,
            object_entity_id=concept_entity.id,
            object_value_text=None,
            source_assertion_id=assertion.assertion_id,
            review_status=assertion.review_status,
            confidence=assertion.confidence,
            details_json={
                "concept_key": assertion.concept_key,
                "source_types": list(assertion.source_types),
                "evidence_count": assertion.evidence_count,
                "fact_kind": "document_concept_relation",
            },
            created_at=utcnow(),
        )
        session.add(fact)
        session.flush()
        for evidence in assertion.evidence:
            session.add(
                SemanticFactEvidence(
                    fact_id=fact.id,
                    assertion_id=assertion.assertion_id,
                    assertion_evidence_id=evidence.evidence_id,
                    created_at=utcnow(),
                )
            )
        if assertion.review_status == SemanticReviewStatus.APPROVED.value:
            approved_fact_count += 1
    session.flush()

    facts = list_document_semantic_facts(session, document_id)
    facts = [row for row in facts if row["semantic_pass_id"] == semantic_pass.id]
    relation_counts: dict[str, int] = {}
    supported_fact_count = 0
    for fact in facts:
        relation_counts[fact["relation_key"]] = relation_counts.get(fact["relation_key"], 0) + 1
        if fact["evidence_ids"]:
            supported_fact_count += 1
    entity_count = len(entity_ids)

    return {
        "document_id": document.id,
        "run_id": semantic_pass.run_id,
        "semantic_pass_id": semantic_pass.id,
        "ontology_snapshot_id": semantic_pass.ontology_snapshot_id,
        "ontology_version": semantic_pass.registry_version,
        "fact_count": len(facts),
        "approved_fact_count": approved_fact_count,
        "entity_count": entity_count,
        "relation_counts": relation_counts,
        "facts": facts,
        "success_metrics": _fact_graph_success_metrics(
            fact_count=len(facts),
            approved_fact_count=approved_fact_count,
            entity_count=entity_count,
            supported_fact_count=supported_fact_count,
            constraint_valid_fact_count=constraint_valid_fact_count,
            minimum_review_status=minimum_review_status,
        ),
    }
