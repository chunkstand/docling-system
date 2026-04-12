from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentRun, RunStatus


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


def run_integrity_audit(session: Session) -> dict[str, object]:
    documents = session.execute(select(Document)).scalars().all()
    runs = session.execute(select(DocumentRun)).scalars().all()
    violations: list[AuditViolation] = []

    run_by_id = {run.id: run for run in runs}

    for document in documents:
        if document.active_run_id is None:
            continue

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
            continue

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
            if not run.failure_artifact_path or not Path(run.failure_artifact_path).exists():
                violations.append(
                    AuditViolation(
                        code="failed_run_missing_failure_artifact",
                        message="Failed run is missing replayable failure artifact.",
                        document_id=run.document_id,
                        run_id=run.id,
                    )
                )

    return {
        "checked_documents": len(documents),
        "checked_runs": len(runs),
        "violation_count": len(violations),
        "violations": [violation.to_dict() for violation in violations],
    }
