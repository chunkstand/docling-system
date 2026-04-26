from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings, semantics_feature_enabled
from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentRun,
    DocumentRunSemanticPass,
    RunStatus,
    SemanticEntity,
    SemanticFact,
    SemanticPassStatus,
)
from app.schemas.semantic_backfill import (
    SemanticBackfillDocumentResult,
    SemanticBackfillGraphStatus,
    SemanticBackfillReadiness,
    SemanticBackfillRegistryStatus,
    SemanticBackfillRequest,
    SemanticBackfillRunResponse,
    SemanticBackfillStatusResponse,
)
from app.services.evaluations import resolve_baseline_run_id
from app.services.semantic_facts import build_document_fact_graph
from app.services.semantic_graph import get_active_semantic_graph_snapshot
from app.services.semantic_ontology import initialize_workspace_ontology
from app.services.semantic_registry import get_semantic_registry
from app.services.semantics import (
    SEMANTIC_ARTIFACT_SCHEMA_VERSION,
    SEMANTIC_EXTRACTOR_VERSION,
    execute_semantic_pass,
)
from app.services.storage import StorageService


@dataclass(frozen=True)
class _ActiveDocumentRun:
    document: Document
    run: DocumentRun | None
    current_pass: DocumentRunSemanticPass | None
    latest_pass: DocumentRunSemanticPass | None
    current_fact_count: int = 0


def _current_semantic_pass_for_run(
    passes: list[DocumentRunSemanticPass],
    *,
    registry_version: str,
    registry_sha256: str,
) -> DocumentRunSemanticPass | None:
    for semantic_pass in passes:
        if (
            semantic_pass.registry_version == registry_version
            and semantic_pass.registry_sha256 == registry_sha256
            and semantic_pass.extractor_version == SEMANTIC_EXTRACTOR_VERSION
            and semantic_pass.artifact_schema_version == SEMANTIC_ARTIFACT_SCHEMA_VERSION
        ):
            return semantic_pass
    return None


def _load_active_document_runs(
    session: Session,
    *,
    registry_version: str,
    registry_sha256: str,
    document_ids: list[UUID] | None = None,
    limit: int | None = None,
) -> list[_ActiveDocumentRun]:
    statement = select(Document).where(Document.active_run_id.is_not(None)).order_by(
        Document.updated_at.desc(), Document.id
    )
    if document_ids:
        statement = statement.where(Document.id.in_(document_ids))
    if limit is not None:
        statement = statement.limit(limit)
    documents = session.execute(statement).scalars().all()
    run_ids = [document.active_run_id for document in documents if document.active_run_id]
    runs_by_id = {
        run.id: run
        for run in (
            session.execute(select(DocumentRun).where(DocumentRun.id.in_(run_ids)))
            .scalars()
            .all()
            if run_ids
            else []
        )
    }

    pass_rows = (
        session.execute(
            select(DocumentRunSemanticPass)
            .where(DocumentRunSemanticPass.run_id.in_(run_ids))
            .order_by(DocumentRunSemanticPass.created_at.desc())
        )
        .scalars()
        .all()
        if run_ids
        else []
    )
    passes_by_run_id: dict[UUID, list[DocumentRunSemanticPass]] = {}
    for semantic_pass in pass_rows:
        passes_by_run_id.setdefault(semantic_pass.run_id, []).append(semantic_pass)

    current_pass_ids = [
        current_pass.id
        for passes in passes_by_run_id.values()
        if (
            current_pass := _current_semantic_pass_for_run(
                passes,
                registry_version=registry_version,
                registry_sha256=registry_sha256,
            )
        )
        is not None
    ]
    fact_counts_by_pass_id: dict[UUID, int] = {
        semantic_pass_id: int(fact_count)
        for semantic_pass_id, fact_count in (
            session.execute(
                select(SemanticFact.semantic_pass_id, func.count())
                .where(SemanticFact.semantic_pass_id.in_(current_pass_ids))
                .group_by(SemanticFact.semantic_pass_id)
            ).all()
            if current_pass_ids
            else []
        )
    }

    rows: list[_ActiveDocumentRun] = []
    for document in documents:
        run = runs_by_id.get(document.active_run_id)
        passes = passes_by_run_id.get(document.active_run_id, [])
        current_pass = _current_semantic_pass_for_run(
            passes,
            registry_version=registry_version,
            registry_sha256=registry_sha256,
        )
        rows.append(
            _ActiveDocumentRun(
                document=document,
                run=run,
                current_pass=current_pass,
                latest_pass=passes[0] if passes else None,
                current_fact_count=(
                    int(fact_counts_by_pass_id.get(current_pass.id, 0))
                    if current_pass is not None
                    else 0
                ),
            )
        )
    return rows


def _registry_status(registry) -> SemanticBackfillRegistryStatus:
    return SemanticBackfillRegistryStatus(
        snapshot_id=registry.snapshot_id,
        registry_name=registry.registry_name,
        registry_version=registry.registry_version,
        registry_sha256=registry.sha256,
        upper_ontology_version=registry.upper_ontology_version,
        concept_count=len(registry.concepts),
        category_count=len(registry.categories),
        relation_count=len(registry.relations),
        relation_keys=sorted(relation.relation_key for relation in registry.relations),
    )


def _active_graph_status(session: Session) -> SemanticBackfillGraphStatus:
    graph = get_active_semantic_graph_snapshot(session)
    if graph is None:
        return SemanticBackfillGraphStatus()
    payload = graph.payload_json or {}
    return SemanticBackfillGraphStatus(
        active_snapshot_id=graph.id,
        graph_version=graph.graph_version,
        edge_count=int(payload.get("edge_count") or len(payload.get("edges") or [])),
        node_count=int(payload.get("node_count") or len(payload.get("nodes") or [])),
        ontology_snapshot_id=graph.ontology_snapshot_id,
    )


def _readiness(
    *,
    semantics_enabled: bool,
    active_document_count: int,
    registry_status: SemanticBackfillRegistryStatus,
    missing_current_pass_count: int,
    assertion_count: int,
    fact_count: int,
    graph_status: SemanticBackfillGraphStatus,
) -> SemanticBackfillReadiness:
    blocked_reasons: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []
    if not semantics_enabled:
        blocked_reasons.append(
            "Semantic execution is disabled. Set DOCLING_SYSTEM_SEMANTICS_ENABLED=1 "
            "before running backfill."
        )
    if active_document_count == 0:
        blocked_reasons.append("No active documents are available for semantic backfill.")
    if registry_status.concept_count == 0:
        warnings.append(
            "The active ontology has no governed concepts, so semantic passes will "
            "not emit assertions."
        )
        next_actions.append(
            "Run bootstrap discovery, review corpus-derived concepts, and apply a "
            "verified ontology extension."
        )
    if "document_mentions_concept" not in set(registry_status.relation_keys):
        warnings.append(
            "The active ontology is missing document_mentions_concept, so document "
            "fact graphs cannot be built."
        )
        next_actions.append(
            "Apply an ontology snapshot that includes the portable fact-graph relations."
        )
    if missing_current_pass_count:
        next_actions.append("Run semantic backfill over active runs.")
    if assertion_count and not fact_count:
        next_actions.append("Build document fact graphs for completed semantic passes.")
    if fact_count and graph_status.edge_count == 0:
        next_actions.append("Build, evaluate, and promote cross-document graph memory.")
    if not next_actions and not blocked_reasons:
        next_actions.append("Keep monitoring semantic status and report-harness graph usage.")
    return SemanticBackfillReadiness(
        ready=not blocked_reasons,
        blocked_reasons=blocked_reasons,
        warnings=warnings,
        next_actions=next_actions,
    )


def get_semantic_backfill_status(session: Session) -> SemanticBackfillStatusResponse:
    settings = get_settings()
    semantics_enabled = semantics_feature_enabled(settings)
    registry = get_semantic_registry(session)
    registry_status = _registry_status(registry)
    active_rows = _load_active_document_runs(
        session,
        registry_version=registry.registry_version,
        registry_sha256=registry.sha256,
    )
    active_run_count = sum(1 for row in active_rows if row.run is not None)
    current_completed_rows = [
        row
        for row in active_rows
        if row.current_pass is not None
        and row.current_pass.status == SemanticPassStatus.COMPLETED.value
    ]
    missing_current_rows = [
        row
        for row in active_rows
        if row.current_pass is None
        or row.current_pass.status != SemanticPassStatus.COMPLETED.value
    ]
    stale_or_failed_count = sum(
        1 for row in active_rows if row.latest_pass and row in missing_current_rows
    )
    pass_counts: dict[str, int] = {}
    active_run_ids = [
        row.document.active_run_id for row in active_rows if row.document.active_run_id
    ]
    if active_run_ids:
        for status, count in session.execute(
            select(DocumentRunSemanticPass.status, func.count())
            .where(DocumentRunSemanticPass.run_id.in_(active_run_ids))
            .group_by(DocumentRunSemanticPass.status)
        ):
            pass_counts[str(status)] = int(count)

    current_pass_ids = [row.current_pass.id for row in current_completed_rows if row.current_pass]
    fact_count = (
        int(
            session.execute(
                select(func.count())
                .select_from(SemanticFact)
                .where(SemanticFact.semantic_pass_id.in_(current_pass_ids))
            ).scalar_one()
        )
        if current_pass_ids
        else 0
    )
    entity_count = int(
        session.execute(select(func.count()).select_from(SemanticEntity)).scalar_one()
    )
    assertion_count = sum(
        int(row.current_pass.assertion_count or 0) for row in current_completed_rows
    )
    evidence_count = sum(
        int(row.current_pass.evidence_count or 0) for row in current_completed_rows
    )
    graph_status = _active_graph_status(session)

    return SemanticBackfillStatusResponse(
        semantics_enabled=semantics_enabled,
        active_document_count=len(active_rows),
        active_run_count=active_run_count,
        current_registry=registry_status,
        semantic_pass_counts=pass_counts,
        active_current_pass_count=len(current_completed_rows),
        missing_current_pass_count=len(missing_current_rows),
        stale_or_failed_pass_count=stale_or_failed_count,
        assertion_count=assertion_count,
        evidence_count=evidence_count,
        fact_count=fact_count,
        entity_count=entity_count,
        graph=graph_status,
        readiness=_readiness(
            semantics_enabled=semantics_enabled,
            active_document_count=len(active_rows),
            registry_status=registry_status,
            missing_current_pass_count=len(missing_current_rows),
            assertion_count=assertion_count,
            fact_count=fact_count,
            graph_status=graph_status,
        ),
        sample_missing_documents=[
            {
                "document_id": row.document.id,
                "source_filename": row.document.source_filename,
                "active_run_id": row.document.active_run_id,
                "latest_semantic_status": row.latest_pass.status if row.latest_pass else None,
                "latest_registry_version": row.latest_pass.registry_version
                if row.latest_pass
                else None,
            }
            for row in missing_current_rows[:10]
        ],
        updated_at=utcnow(),
    )


def _backfill_action(row: _ActiveDocumentRun, *, force: bool, build_fact_graphs: bool) -> str:
    if row.run is None:
        return "skip_missing_run"
    if row.run.status != RunStatus.COMPLETED.value:
        return "skip_run_not_completed"
    if force:
        return "semantic_pass"
    if row.current_pass is None or row.current_pass.status != SemanticPassStatus.COMPLETED.value:
        return "semantic_pass"
    if (
        build_fact_graphs
        and row.current_pass.assertion_count > 0
        and row.current_fact_count == 0
    ):
        return "fact_graph"
    return "skip_current"


def run_semantic_backfill(
    session: Session,
    request: SemanticBackfillRequest,
    *,
    storage_service: StorageService,
) -> SemanticBackfillRunResponse:
    if request.initialize_ontology:
        initialize_workspace_ontology(session)
        session.commit()

    settings = get_settings()
    if not request.dry_run and not semantics_feature_enabled(settings):
        raise ValueError(
            "Semantic backfill requires DOCLING_SYSTEM_SEMANTICS_ENABLED=1 for execution."
        )

    registry = get_semantic_registry(session)
    rows = _load_active_document_runs(
        session,
        registry_version=registry.registry_version,
        registry_sha256=registry.sha256,
        document_ids=list(request.document_ids),
        limit=request.limit,
    )

    documents: list[SemanticBackfillDocumentResult] = []
    processed_document_count = 0
    skipped_document_count = 0
    failed_document_count = 0
    semantic_pass_count = 0
    fact_graph_count = 0
    assertion_count = 0
    fact_count = 0

    for row in rows:
        action = _backfill_action(
            row,
            force=request.force,
            build_fact_graphs=request.build_fact_graphs,
        )
        semantic_pass = row.current_pass
        result_status = "planned" if request.dry_run else "skipped"
        result_fact_count = row.current_fact_count
        error_message: str | None = None
        if request.dry_run:
            pass
        elif action == "semantic_pass":
            try:
                assert row.run is not None
                semantic_pass = execute_semantic_pass(
                    session,
                    row.document,
                    row.run,
                    baseline_run_id=resolve_baseline_run_id(row.run.id, None),
                    storage_service=storage_service,
                )
                semantic_pass_count += 1
                processed_document_count += 1
                result_status = semantic_pass.status
                if semantic_pass.status == SemanticPassStatus.COMPLETED.value:
                    assertion_count += int(semantic_pass.assertion_count or 0)
                    if request.build_fact_graphs and semantic_pass.assertion_count > 0:
                        try:
                            graph_payload = build_document_fact_graph(
                                session,
                                document_id=row.document.id,
                                minimum_review_status=request.minimum_review_status,
                            )
                            session.commit()
                            result_fact_count = int(graph_payload.get("fact_count") or 0)
                            fact_count += result_fact_count
                            fact_graph_count += 1
                        except Exception as exc:
                            session.rollback()
                            failed_document_count += 1
                            result_status = "fact_graph_failed"
                            error_message = str(exc)
                else:
                    failed_document_count += 1
            except Exception as exc:
                session.rollback()
                failed_document_count += 1
                result_status = "failed"
                error_message = str(exc)
        elif action == "fact_graph":
            try:
                graph_payload = build_document_fact_graph(
                    session,
                    document_id=row.document.id,
                    minimum_review_status=request.minimum_review_status,
                )
                session.commit()
                processed_document_count += 1
                fact_graph_count += 1
                result_status = "completed"
                result_fact_count = int(graph_payload.get("fact_count") or 0)
                fact_count += result_fact_count
                assertion_count += int(semantic_pass.assertion_count or 0) if semantic_pass else 0
            except Exception as exc:
                session.rollback()
                failed_document_count += 1
                result_status = "failed"
                error_message = str(exc)
        else:
            skipped_document_count += 1

        documents.append(
            SemanticBackfillDocumentResult(
                document_id=row.document.id,
                source_filename=row.document.source_filename,
                run_id=row.run.id if row.run else row.document.active_run_id,
                semantic_pass_id=semantic_pass.id if semantic_pass else None,
                action=action,
                status=result_status,
                assertion_count=int(semantic_pass.assertion_count or 0) if semantic_pass else 0,
                evidence_count=int(semantic_pass.evidence_count or 0) if semantic_pass else 0,
                fact_count=result_fact_count,
                error_message=error_message,
            )
        )

    return SemanticBackfillRunResponse(
        dry_run=request.dry_run,
        selected_document_count=len(rows),
        processed_document_count=processed_document_count,
        skipped_document_count=skipped_document_count,
        failed_document_count=failed_document_count,
        semantic_pass_count=semantic_pass_count,
        fact_graph_count=fact_graph_count,
        assertion_count=assertion_count,
        fact_count=fact_count,
        documents=documents,
        status_after=None if request.dry_run else get_semantic_backfill_status(session),
        completed_at=utcnow(),
    )
