from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings, semantics_feature_enabled
from app.core.logging import get_logger
from app.db.models import Document, DocumentRun
from app.services import run_persistence as _run_persistence
from app.services import run_post_promotion as _run_post_promotion
from app.services.docling_parser import DoclingParser, ParsedDocument
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.evaluations import (
    evaluate_run,
    resolve_baseline_run_id,
)
from app.services.retrieval_spans import rebuild_retrieval_evidence_spans
from app.services.run_leases import (
    claim_next_run as claim_next_run,
)
from app.services.run_leases import (
    heartbeat_run as heartbeat_run,
)
from app.services.run_leases import (
    is_retryable_error as is_retryable_error,
)
from app.services.run_leases import (
    requeue_stale_runs as requeue_stale_runs,
)
from app.services.run_leases import (
    run_lease_heartbeat as run_lease_heartbeat,
)
from app.services.run_post_promotion import (
    finalize_run_failure as finalize_run_failure,
)
from app.services.run_post_promotion import (
    finalize_run_success as finalize_run_success,
)
from app.services.runtime import (
    get_process_identity,
    runtime_code_is_current,
    runtime_process_heartbeat,
)
from app.services.semantics import execute_semantic_pass
from app.services.storage import StorageService
from app.services.telemetry import increment
from app.services.validation import ValidationReport, validate_persisted_run


class ValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        super().__init__(report.summary)
        self.report = report


logger = get_logger(__name__)
_apply_embeddings = _run_persistence._apply_embeddings
_build_lineage_assignments = _run_persistence._build_lineage_assignments
_persist_parsed_artifacts = _run_persistence._persist_parsed_artifacts
_replace_run_chunks = _run_persistence._replace_run_chunks
_replace_run_tables = _run_persistence._replace_run_tables
_replace_run_figures = _run_persistence._replace_run_figures
_mark_run_persisted = _run_persistence._mark_run_persisted
_mark_run_validating = _run_persistence._mark_run_validating


def _evaluate_promoted_run(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    baseline_run_id: UUID | None,
) -> None:
    _run_post_promotion.evaluate_promoted_run(
        session,
        document,
        run,
        baseline_run_id=baseline_run_id,
        evaluate_run_fn=evaluate_run,
    )


def _run_post_promotion_semantics(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    baseline_run_id: UUID | None,
    storage_service: StorageService,
) -> None:
    _run_post_promotion.run_post_promotion_semantics(
        session,
        document,
        run,
        baseline_run_id=baseline_run_id,
        storage_service=storage_service,
        execute_semantic_pass_fn=execute_semantic_pass,
    )


class RunProcessingStage(StrEnum):
    PARSE = "parse"
    EMBEDDING = "embedding"
    ARTIFACT_WRITE = "artifact_write"
    CHUNK_PERSIST = "chunk_persist"
    TABLE_PERSIST = "table_persist"
    FIGURE_PERSIST = "figure_persist"
    RETRIEVAL_SPAN_PERSIST = "retrieval_span_persist"
    RUN_PERSIST = "run_persist"
    VALIDATION = "validation"
    PROMOTION = "promotion"
    POST_PROMOTION_EVALUATION = "post_promotion_evaluation"
    POST_PROMOTION_SEMANTICS = "post_promotion_semantics"


@dataclass
class RunProcessor:
    session: Session
    run: DocumentRun
    document: Document
    storage_service: StorageService
    parser: DoclingParser
    embedding_provider: EmbeddingProvider | None
    prior_active_run_id: UUID | None
    parsed: ParsedDocument | None = None
    json_path: Path | None = None
    yaml_path: Path | None = None
    lineage_assignments: dict = field(default_factory=dict)
    report: ValidationReport | None = None

    def process(self) -> None:
        with run_lease_heartbeat(self.run.id, worker_id=self.run.locked_by):
            failure_stage = RunProcessingStage.PARSE.value
            try:
                logger.info(
                    "run_processing_started",
                    run_id=str(self.run.id),
                    document_id=str(self.document.id),
                )
                for stage in self._stages():
                    failure_stage = stage.value
                    self._run_stage(stage)
            except Exception as exc:
                self.session.rollback()
                run = self.session.get(DocumentRun, self.run.id)
                if run is None:
                    raise
                report = exc.report if isinstance(exc, ValidationError) else None
                finalize_run_failure(
                    self.session,
                    run,
                    exc,
                    report=report,
                    failure_stage=failure_stage,
                    storage_service=self.storage_service,
                    document=self.document,
                )
                logger.exception(
                    "run_processing_failed",
                    run_id=str(run.id),
                    document_id=str(self.document.id),
                    error=str(exc),
                    failure_stage=failure_stage,
                )

    def _stages(self) -> tuple[RunProcessingStage, ...]:
        settings = get_settings()
        stages = [
            RunProcessingStage.PARSE,
            RunProcessingStage.EMBEDDING,
            RunProcessingStage.ARTIFACT_WRITE,
            RunProcessingStage.CHUNK_PERSIST,
            RunProcessingStage.TABLE_PERSIST,
            RunProcessingStage.FIGURE_PERSIST,
            RunProcessingStage.RETRIEVAL_SPAN_PERSIST,
            RunProcessingStage.RUN_PERSIST,
            RunProcessingStage.VALIDATION,
            RunProcessingStage.PROMOTION,
            RunProcessingStage.POST_PROMOTION_EVALUATION,
        ]
        if semantics_feature_enabled(settings):
            stages.append(RunProcessingStage.POST_PROMOTION_SEMANTICS)
        return tuple(stages)

    def _run_stage(self, stage: RunProcessingStage) -> None:
        if stage == RunProcessingStage.PARSE:
            heartbeat_run(self.session, self.run)
            parse_kwargs: dict[str, str] = {}
            source_filename = getattr(self.document, "source_filename", None)
            if source_filename is not None:
                parse_kwargs["source_filename"] = source_filename
            self.parsed = self.parser.parse_pdf(Path(self.document.source_path), **parse_kwargs)
            increment("tables_detected_total", len(self.parsed.raw_table_segments))
            heartbeat_run(self.session, self.run)
            return

        if stage == RunProcessingStage.EMBEDDING:
            assert self.parsed is not None
            _apply_embeddings(self.parsed, self.embedding_provider, self.run)
            self.lineage_assignments = _build_lineage_assignments(
                self.session,
                self.document,
                self.parsed,
            )
            return

        if stage == RunProcessingStage.ARTIFACT_WRITE:
            assert self.parsed is not None
            self.json_path, self.yaml_path = _persist_parsed_artifacts(
                self.storage_service,
                self.document,
                self.run,
                self.parsed,
            )
            return

        if stage == RunProcessingStage.CHUNK_PERSIST:
            assert self.parsed is not None
            _replace_run_chunks(self.session, self.document, self.run, self.parsed)
            return

        if stage == RunProcessingStage.TABLE_PERSIST:
            assert self.parsed is not None
            _replace_run_tables(
                self.session,
                self.document,
                self.run,
                self.parsed,
                self.storage_service,
                self.lineage_assignments,
            )
            return

        if stage == RunProcessingStage.FIGURE_PERSIST:
            assert self.parsed is not None
            _replace_run_figures(
                self.session,
                self.document,
                self.run,
                self.parsed,
                self.storage_service,
            )
            return

        if stage == RunProcessingStage.RETRIEVAL_SPAN_PERSIST:
            summary = rebuild_retrieval_evidence_spans(
                self.session,
                self.run,
                embedding_provider=self.embedding_provider,
            )
            logger.info(
                "retrieval_evidence_spans_rebuilt",
                run_id=str(self.run.id),
                document_id=str(self.document.id),
                span_count=summary["span_count"],
                embedding_status=summary["embedding_status"],
            )
            return

        if stage == RunProcessingStage.RUN_PERSIST:
            assert self.parsed is not None
            assert self.json_path is not None
            assert self.yaml_path is not None
            _mark_run_persisted(
                self.session,
                self.document,
                self.run,
                self.parsed,
                self.json_path,
                self.yaml_path,
            )
            return

        if stage == RunProcessingStage.VALIDATION:
            assert self.parsed is not None
            _mark_run_validating(self.session, self.run)
            heartbeat_run(self.session, self.run)
            self.report = validate_persisted_run(self.session, self.document, self.run, self.parsed)
            if not self.report.passed:
                raise ValidationError(self.report)
            return

        if stage == RunProcessingStage.PROMOTION:
            assert self.parsed is not None
            assert self.report is not None
            finalize_run_success(
                self.session,
                self.document,
                self.run,
                self.parsed,
                self.report,
                storage_service=self.storage_service,
            )
            logger.info(
                "run_processing_completed",
                run_id=str(self.run.id),
                document_id=str(self.document.id),
                chunk_count=len(self.parsed.chunks),
                table_count=len(self.parsed.tables),
                figure_count=len(self.parsed.figures),
                page_count=self.parsed.page_count,
            )
            return

        if stage == RunProcessingStage.POST_PROMOTION_EVALUATION:
            _evaluate_promoted_run(
                self.session,
                self.document,
                self.run,
                baseline_run_id=resolve_baseline_run_id(self.run.id, self.prior_active_run_id),
            )
            return

        if stage == RunProcessingStage.POST_PROMOTION_SEMANTICS:
            _run_post_promotion_semantics(
                self.session,
                self.document,
                self.run,
                baseline_run_id=resolve_baseline_run_id(self.run.id, self.prior_active_run_id),
                storage_service=self.storage_service,
            )
            return

        raise ValueError(f"Unsupported run processing stage: {stage}")


def process_run(
    session: Session,
    run_id: UUID,
    storage_service: StorageService,
    parser: DoclingParser,
    embedding_provider: EmbeddingProvider | None = None,
) -> None:
    run = session.get(DocumentRun, run_id)
    if run is None:
        raise ValueError(f"Run {run_id} does not exist.")

    document = session.get(Document, run.document_id)
    if document is None:
        raise ValueError(f"Document {run.document_id} does not exist.")
    if not Path(document.source_path).exists():
        raise ValueError("Source file missing before worker pickup.")
    RunProcessor(
        session=session,
        run=run,
        document=document,
        storage_service=storage_service,
        parser=parser,
        embedding_provider=embedding_provider,
        prior_active_run_id=document.active_run_id,
    ).process()


def run_worker_loop() -> None:
    from app.db.session import get_session_factory

    settings = get_settings()
    session_factory = get_session_factory()
    storage_service = StorageService()
    parser = DoclingParser()
    try:
        embedding_provider = get_embedding_provider()
    except Exception as exc:
        embedding_provider = None
        logger.warning("embedding_provider_unavailable", error=str(exc))
    worker_id = get_process_identity()
    with runtime_process_heartbeat(
        "worker",
        worker_id,
        heartbeat_interval_seconds=max(getattr(settings, "worker_heartbeat_seconds", 30), 1),
    ) as registration:
        logger.info(
            "worker_runtime_registered",
            worker_id=worker_id,
            code_fingerprint=registration.startup_code_fingerprint,
        )

        while True:
            if not runtime_code_is_current(registration.startup_code_fingerprint):
                logger.warning(
                    "worker_exiting_stale_code",
                    worker_id=worker_id,
                    code_fingerprint=registration.startup_code_fingerprint,
                )
                return
            with session_factory() as session:
                requeue_stale_runs(session, storage_service=storage_service)
                run = claim_next_run(session, worker_id)
                if run is None:
                    time.sleep(settings.worker_poll_seconds)
                    continue

                process_run(
                    session=session,
                    run_id=run.id,
                    storage_service=storage_service,
                    parser=parser,
                    embedding_provider=embedding_provider,
                )
