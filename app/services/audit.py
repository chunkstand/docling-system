from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentChunk,
    DocumentFigure,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentTable,
    RunStatus,
)

KNOWN_FAILURE_STAGES = {
    "artifact_write",
    "chunk_persist",
    "embedding",
    "figure_persist",
    "parse",
    "promotion",
    "run_persist",
    "stale_lease",
    "table_persist",
    "validation",
}
REQUIRED_FAILURE_ARTIFACT_FIELDS = {
    "attempts",
    "created_at",
    "document_id",
    "error_message",
    "failure_stage",
    "failure_type",
    "run_id",
    "schema_version",
    "status",
    "validation_results",
}


@dataclass
class AuditViolation:
    code: str
    message: str
    document_id: UUID | None = None
    run_id: UUID | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "document_id": str(self.document_id) if self.document_id else None,
            "run_id": str(self.run_id) if self.run_id else None,
        }


@dataclass
class AuditContext:
    documents: list[object]
    runs: list[object]
    chunks: list[object]
    tables: list[object]
    figures: list[object]
    evaluations: list[object]


def _load_audit_context(session: Session) -> AuditContext:
    return AuditContext(
        documents=session.execute(select(Document)).scalars().all(),
        runs=session.execute(select(DocumentRun)).scalars().all(),
        chunks=session.execute(select(DocumentChunk)).scalars().all(),
        tables=session.execute(select(DocumentTable)).scalars().all(),
        figures=session.execute(select(DocumentFigure)).scalars().all(),
        evaluations=session.execute(select(DocumentRunEvaluation)).scalars().all(),
    )


def _path_exists(path_value: str | None) -> bool:
    return bool(path_value and Path(path_value).exists())


def _missing_failure_artifact_fields(payload: dict[str, object]) -> list[str]:
    missing: list[str] = []
    for field in sorted(REQUIRED_FAILURE_ARTIFACT_FIELDS):
        if field not in payload:
            missing.append(field)
            continue
        value = payload[field]
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field)
    return missing


def _load_failure_artifact(path_value: str) -> tuple[dict[str, object] | None, str | None]:
    try:
        payload = json.loads(Path(path_value).read_text())
    except FileNotFoundError:
        return None, "missing"
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(payload, dict):
        return None, "invalid_shape"
    return payload, None


def _latest_evaluations_by_run(evaluations: list[object]) -> dict[UUID, object]:
    latest_by_run: dict[UUID, object] = {}
    for evaluation in evaluations:
        run_id = evaluation.run_id
        current = latest_by_run.get(run_id)
        if current is None or evaluation.created_at > current.created_at:
            latest_by_run[run_id] = evaluation
    return latest_by_run


def build_integrity_audit(context: AuditContext) -> dict[str, object]:
    documents = context.documents
    runs = context.runs
    chunks = context.chunks
    tables = context.tables
    figures = context.figures
    evaluations = context.evaluations
    violations: list[AuditViolation] = []

    run_by_id = {run.id: run for run in runs}
    latest_evaluation_by_run = _latest_evaluations_by_run(evaluations)
    chunk_counts = Counter(chunk.run_id for chunk in chunks)
    table_counts = Counter(table.run_id for table in tables)
    figure_counts = Counter(figure.run_id for figure in figures)

    for document in documents:
        if document.active_run_id is None:
            active_run = None
        else:
            active_run = run_by_id.get(document.active_run_id)
            if active_run is None:
                violations.append(
                    AuditViolation(
                        code="missing_active_run",
                        message="Document references a missing active run.",
                        document_id=document.id,
                        run_id=document.active_run_id,
                    )
                )
                active_run = None

        if active_run is not None:
            if active_run.document_id != document.id:
                violations.append(
                    AuditViolation(
                        code="active_run_wrong_document",
                        message="Active run does not belong to the document.",
                        document_id=document.id,
                        run_id=active_run.id,
                    )
                )

            if active_run.status != RunStatus.COMPLETED.value:
                violations.append(
                    AuditViolation(
                        code="active_run_not_completed",
                        message="Active run is not completed.",
                        document_id=document.id,
                        run_id=active_run.id,
                    )
                )

            if active_run.validation_status != "passed":
                violations.append(
                    AuditViolation(
                        code="active_run_not_validated",
                        message="Active run does not have passed validation.",
                        document_id=document.id,
                        run_id=active_run.id,
                    )
                )

        latest_run = run_by_id.get(getattr(document, "latest_run_id", None))
        if latest_run is not None and latest_run.status == RunStatus.COMPLETED.value:
            if latest_evaluation_by_run.get(latest_run.id) is None:
                violations.append(
                    AuditViolation(
                        code="completed_latest_run_missing_evaluation",
                        message="Completed latest run is missing a persisted evaluation row.",
                        document_id=document.id,
                        run_id=latest_run.id,
                    )
                )

    for run in runs:
        if run.status == RunStatus.COMPLETED.value:
            if not run.docling_json_path or not Path(run.docling_json_path).exists():
                violations.append(
                    AuditViolation(
                        code="completed_run_missing_json_artifact",
                        message="Completed run is missing docling JSON artifact.",
                        document_id=run.document_id,
                        run_id=run.id,
                    )
                )
            if not run.yaml_path or not Path(run.yaml_path).exists():
                violations.append(
                    AuditViolation(
                        code="completed_run_missing_yaml_artifact",
                        message="Completed run is missing YAML artifact.",
                        document_id=run.document_id,
                        run_id=run.id,
                    )
                )

        actual_chunk_count = chunk_counts.get(run.id, 0)
        if (
            run.status == RunStatus.COMPLETED.value
            or run.chunk_count is not None
            or actual_chunk_count > 0
        ) and run.chunk_count != actual_chunk_count:
            violations.append(
                AuditViolation(
                    code="run_chunk_count_mismatch",
                    message=(
                        f"Run chunk_count ({run.chunk_count}) does not match persisted chunks "
                        f"({actual_chunk_count})."
                    ),
                    document_id=run.document_id,
                    run_id=run.id,
                )
            )

        actual_table_count = table_counts.get(run.id, 0)
        if (
            run.status == RunStatus.COMPLETED.value
            or run.table_count is not None
            or actual_table_count > 0
        ) and run.table_count != actual_table_count:
            violations.append(
                AuditViolation(
                    code="run_table_count_mismatch",
                    message=(
                        f"Run table_count ({run.table_count}) does not match persisted tables "
                        f"({actual_table_count})."
                    ),
                    document_id=run.document_id,
                    run_id=run.id,
                )
            )

        actual_figure_count = figure_counts.get(run.id, 0)
        if (
            run.status == RunStatus.COMPLETED.value
            or run.figure_count is not None
            or actual_figure_count > 0
        ) and run.figure_count != actual_figure_count:
            violations.append(
                AuditViolation(
                    code="run_figure_count_mismatch",
                    message=(
                        f"Run figure_count ({run.figure_count}) does not match persisted figures "
                        f"({actual_figure_count})."
                    ),
                    document_id=run.document_id,
                    run_id=run.id,
                )
            )

        if run.status == RunStatus.FAILED.value:
            if not run.failure_stage:
                violations.append(
                    AuditViolation(
                        code="failed_run_missing_failure_stage",
                        message="Failed run is missing failure stage metadata.",
                        document_id=run.document_id,
                        run_id=run.id,
                    )
                )
            elif run.failure_stage not in KNOWN_FAILURE_STAGES:
                violations.append(
                    AuditViolation(
                        code="failed_run_unknown_failure_stage",
                        message=f"Failed run uses unknown failure stage '{run.failure_stage}'.",
                        document_id=run.document_id,
                        run_id=run.id,
                    )
                )
            if not run.failure_artifact_path or not Path(run.failure_artifact_path).exists():
                violations.append(
                    AuditViolation(
                        code="failed_run_missing_failure_artifact",
                        message="Failed run is missing replayable failure artifact.",
                        document_id=run.document_id,
                        run_id=run.id,
                    )
                )
            else:
                payload, error = _load_failure_artifact(run.failure_artifact_path)
                if error is not None:
                    violations.append(
                        AuditViolation(
                            code=f"failed_run_failure_artifact_{error}",
                            message=(
                                "Failed run replay artifact is unreadable."
                                if error == "missing"
                                else "Failed run replay artifact has invalid JSON."
                            ),
                            document_id=run.document_id,
                            run_id=run.id,
                        )
                    )
                else:
                    missing_fields = _missing_failure_artifact_fields(payload)
                    if missing_fields:
                        violations.append(
                            AuditViolation(
                                code="failed_run_failure_artifact_missing_fields",
                                message=(
                                    "Failed run replay artifact is missing required fields: "
                                    + ", ".join(missing_fields)
                                ),
                                document_id=run.document_id,
                                run_id=run.id,
                            )
                        )

        if (
            run.status != RunStatus.FAILED.value
            and run.failure_stage
            and run.failure_stage not in KNOWN_FAILURE_STAGES
        ):
            violations.append(
                AuditViolation(
                    code="run_unknown_failure_stage",
                    message=f"Run uses unknown failure stage '{run.failure_stage}'.",
                    document_id=run.document_id,
                    run_id=run.id,
                )
            )

    for table in tables:
        if getattr(table, "json_path", None) and not _path_exists(table.json_path):
            violations.append(
                AuditViolation(
                    code="table_missing_json_artifact",
                    message="Table row claims a JSON artifact path that does not exist.",
                    document_id=table.document_id,
                    run_id=table.run_id,
                )
            )
        if getattr(table, "yaml_path", None) and not _path_exists(table.yaml_path):
            violations.append(
                AuditViolation(
                    code="table_missing_yaml_artifact",
                    message="Table row claims a YAML artifact path that does not exist.",
                    document_id=table.document_id,
                    run_id=table.run_id,
                )
            )

    for figure in figures:
        if getattr(figure, "json_path", None) and not _path_exists(figure.json_path):
            violations.append(
                AuditViolation(
                    code="figure_missing_json_artifact",
                    message="Figure row claims a JSON artifact path that does not exist.",
                    document_id=figure.document_id,
                    run_id=figure.run_id,
                )
            )
        if getattr(figure, "yaml_path", None) and not _path_exists(figure.yaml_path):
            violations.append(
                AuditViolation(
                    code="figure_missing_yaml_artifact",
                    message="Figure row claims a YAML artifact path that does not exist.",
                    document_id=figure.document_id,
                    run_id=figure.run_id,
                )
            )

    violation_counts_by_code = dict(sorted(Counter(item.code for item in violations).items()))

    return {
        "checked_documents": len(documents),
        "checked_runs": len(runs),
        "checked_evaluations": len(evaluations),
        "checked_tables": len(tables),
        "checked_figures": len(figures),
        "violation_count": len(violations),
        "violation_counts_by_code": violation_counts_by_code,
        "violations": [violation.to_dict() for violation in violations],
    }


def run_integrity_audit(session: Session) -> dict[str, object]:
    return build_integrity_audit(_load_audit_context(session))
