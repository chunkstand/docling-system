from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile, status

from app.api.errors import api_error
from app.core.config import get_settings


class StorageService:
    def __init__(self, storage_root: Path | None = None) -> None:
        settings = get_settings()
        self.storage_root = (storage_root or settings.storage_root).resolve()
        self.source_root = self.storage_root / "source"
        self.runs_root = self.storage_root / "runs"
        self.staging_root = self.storage_root / "_staging"

        self.source_root.mkdir(parents=True, exist_ok=True)
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.staging_root.mkdir(parents=True, exist_ok=True)

    def _run_dir(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        create: bool,
    ) -> Path:
        path = self.runs_root / str(document_id) / str(run_id)
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _table_dir(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        create: bool,
    ) -> Path:
        path = self._run_dir(document_id, run_id, create=create) / "tables"
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _figure_dir(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        create: bool,
    ) -> Path:
        path = self._run_dir(document_id, run_id, create=create) / "figures"
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _semantic_dir(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID,
        *,
        create: bool,
    ) -> Path:
        path = self._run_dir(document_id, run_id, create=create) / "semantics"
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _agent_task_dir(self, task_id: uuid.UUID, *, create: bool) -> Path:
        path = self.storage_root / "agent_tasks" / str(task_id)
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def _audit_bundle_dir(
        self,
        bundle_kind: str,
        bundle_id: uuid.UUID,
        *,
        create: bool,
    ) -> Path:
        safe_kind = "".join(
            char if char.isalnum() or char in {"-", "_"} else "_" for char in bundle_kind
        )
        path = self.storage_root / "audit_bundles" / safe_kind / str(bundle_id)
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def stage_upload(
        self,
        upload: UploadFile,
        *,
        max_file_bytes: int | None = None,
    ) -> tuple[Path, str]:
        suffix = Path(upload.filename or "upload.pdf").suffix or ".pdf"
        hasher = hashlib.sha256()
        header_prefix = bytearray()
        bytes_written = 0
        staged_path: Path | None = None

        try:
            with NamedTemporaryFile(
                delete=False, dir=self.staging_root, suffix=suffix
            ) as temp_file:
                staged_path = Path(temp_file.name)
                while chunk := upload.file.read(1024 * 1024):
                    if len(header_prefix) < 5:
                        remaining = 5 - len(header_prefix)
                        header_prefix.extend(chunk[:remaining])
                        if len(header_prefix) == 5 and bytes(header_prefix) != b"%PDF-":
                            raise api_error(
                                status.HTTP_400_BAD_REQUEST,
                                "invalid_pdf",
                                "File is not a valid PDF.",
                            )
                    bytes_written += len(chunk)
                    if max_file_bytes is not None and bytes_written > max_file_bytes:
                        raise api_error(
                            status.HTTP_400_BAD_REQUEST,
                            "file_size_limit_exceeded",
                            "File exceeds upload size limit.",
                        )
                    temp_file.write(chunk)
                    hasher.update(chunk)

            if bytes_written < 5 or bytes(header_prefix) != b"%PDF-":
                raise api_error(
                    status.HTTP_400_BAD_REQUEST,
                    "invalid_pdf",
                    "File is not a valid PDF.",
                )
        except Exception:
            if staged_path is not None:
                staged_path.unlink(missing_ok=True)
            raise
        finally:
            upload.file.close()

        return staged_path, hasher.hexdigest()

    def stage_local_file(
        self,
        source_path: Path,
        *,
        max_file_bytes: int | None = None,
        validate_pdf_header: bool = False,
        size_limit_detail: str = "File exceeds local ingest size limit.",
    ) -> tuple[Path, str]:
        suffix = source_path.suffix or ".pdf"
        hasher = hashlib.sha256()
        header_prefix = bytearray()
        bytes_written = 0
        staged_path: Path | None = None

        try:
            with source_path.open("rb") as source_file:
                with NamedTemporaryFile(
                    delete=False, dir=self.staging_root, suffix=suffix
                ) as temp_file:
                    staged_path = Path(temp_file.name)
                    while chunk := source_file.read(1024 * 1024):
                        if validate_pdf_header and len(header_prefix) < 5:
                            remaining = 5 - len(header_prefix)
                            header_prefix.extend(chunk[:remaining])
                            if len(header_prefix) == 5 and bytes(header_prefix) != b"%PDF-":
                                raise api_error(
                                    status.HTTP_400_BAD_REQUEST,
                                    "invalid_pdf",
                                    "File is not a valid PDF.",
                                )
                        bytes_written += len(chunk)
                        if max_file_bytes is not None and bytes_written > max_file_bytes:
                            raise api_error(
                                status.HTTP_400_BAD_REQUEST,
                                "file_size_limit_exceeded",
                                size_limit_detail,
                            )
                        temp_file.write(chunk)
                        hasher.update(chunk)

            if validate_pdf_header and (bytes_written < 5 or bytes(header_prefix) != b"%PDF-"):
                raise api_error(
                    status.HTTP_400_BAD_REQUEST,
                    "invalid_pdf",
                    "File is not a valid PDF.",
                )
        except Exception:
            if staged_path is not None:
                staged_path.unlink(missing_ok=True)
            raise

        return staged_path, hasher.hexdigest()

    def move_source_file(self, document_id: uuid.UUID, staged_path: Path) -> Path:
        destination = self.source_root / f"{document_id}.pdf"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_path), destination)
        return destination

    def get_run_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self._run_dir(document_id, run_id, create=True)

    def build_run_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self._run_dir(document_id, run_id, create=False)

    def get_docling_json_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.get_run_dir(document_id, run_id) / "docling.json"

    def build_docling_json_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.build_run_dir(document_id, run_id) / "docling.json"

    def get_yaml_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.get_run_dir(document_id, run_id) / "document.yaml"

    def build_yaml_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.build_run_dir(document_id, run_id) / "document.yaml"

    def get_table_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self._table_dir(document_id, run_id, create=True)

    def build_table_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self._table_dir(document_id, run_id, create=False)

    def get_table_json_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, table_index: int
    ) -> Path:
        return self.get_table_dir(document_id, run_id) / f"{table_index}.json"

    def build_table_json_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, table_index: int
    ) -> Path:
        return self.build_table_dir(document_id, run_id) / f"{table_index}.json"

    def get_table_yaml_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, table_index: int
    ) -> Path:
        return self.get_table_dir(document_id, run_id) / f"{table_index}.yaml"

    def build_table_yaml_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, table_index: int
    ) -> Path:
        return self.build_table_dir(document_id, run_id) / f"{table_index}.yaml"

    def get_figure_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self._figure_dir(document_id, run_id, create=True)

    def build_figure_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self._figure_dir(document_id, run_id, create=False)

    def get_figure_json_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, figure_index: int
    ) -> Path:
        return self.get_figure_dir(document_id, run_id) / f"{figure_index}.json"

    def build_figure_json_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, figure_index: int
    ) -> Path:
        return self.build_figure_dir(document_id, run_id) / f"{figure_index}.json"

    def get_figure_yaml_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, figure_index: int
    ) -> Path:
        return self.get_figure_dir(document_id, run_id) / f"{figure_index}.yaml"

    def build_figure_yaml_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, figure_index: int
    ) -> Path:
        return self.build_figure_dir(document_id, run_id) / f"{figure_index}.yaml"

    def get_semantic_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self._semantic_dir(document_id, run_id, create=True)

    def build_semantic_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self._semantic_dir(document_id, run_id, create=False)

    def get_semantic_json_path(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID,
        schema_version: str = "1.0",
    ) -> Path:
        major_version = schema_version.split(".", 1)[0] or "1"
        return self.get_semantic_dir(document_id, run_id) / f"semantic-pass.v{major_version}.json"

    def build_semantic_json_path(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID,
        schema_version: str = "1.0",
    ) -> Path:
        major_version = schema_version.split(".", 1)[0] or "1"
        return self.build_semantic_dir(document_id, run_id) / f"semantic-pass.v{major_version}.json"

    def get_semantic_yaml_path(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID,
        schema_version: str = "1.0",
    ) -> Path:
        major_version = schema_version.split(".", 1)[0] or "1"
        return self.get_semantic_dir(document_id, run_id) / f"semantic-pass.v{major_version}.yaml"

    def build_semantic_yaml_path(
        self,
        document_id: uuid.UUID,
        run_id: uuid.UUID,
        schema_version: str = "1.0",
    ) -> Path:
        major_version = schema_version.split(".", 1)[0] or "1"
        return self.build_semantic_dir(document_id, run_id) / f"semantic-pass.v{major_version}.yaml"

    def get_failure_artifact_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.get_run_dir(document_id, run_id) / "failure.json"

    def build_failure_artifact_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.build_run_dir(document_id, run_id) / "failure.json"

    def get_agent_task_dir(self, task_id: uuid.UUID) -> Path:
        return self._agent_task_dir(task_id, create=True)

    def build_agent_task_dir(self, task_id: uuid.UUID) -> Path:
        return self._agent_task_dir(task_id, create=False)

    def get_agent_task_context_json_path(self, task_id: uuid.UUID) -> Path:
        return self.get_agent_task_dir(task_id) / "context.json"

    def build_agent_task_context_json_path(self, task_id: uuid.UUID) -> Path:
        return self.build_agent_task_dir(task_id) / "context.json"

    def get_agent_task_context_yaml_path(self, task_id: uuid.UUID) -> Path:
        return self.get_agent_task_dir(task_id) / "context.yaml"

    def build_agent_task_context_yaml_path(self, task_id: uuid.UUID) -> Path:
        return self.build_agent_task_dir(task_id) / "context.yaml"

    def get_agent_task_failure_artifact_path(self, task_id: uuid.UUID) -> Path:
        return self.get_agent_task_dir(task_id) / "failure.json"

    def build_agent_task_failure_artifact_path(self, task_id: uuid.UUID) -> Path:
        return self.build_agent_task_dir(task_id) / "failure.json"

    def get_audit_bundle_json_path(self, bundle_kind: str, bundle_id: uuid.UUID) -> Path:
        return self._audit_bundle_dir(bundle_kind, bundle_id, create=True) / "bundle.json"

    def build_audit_bundle_json_path(self, bundle_kind: str, bundle_id: uuid.UUID) -> Path:
        return self._audit_bundle_dir(bundle_kind, bundle_id, create=False) / "bundle.json"

    def resolve_existing_path(self, path_value: str | Path | None) -> Path | None:
        if path_value is None:
            return None
        candidate = path_value if isinstance(path_value, Path) else Path(path_value)
        if not candidate.is_absolute():
            candidate = self.storage_root / candidate
        resolved = candidate.resolve()
        if not resolved.is_file():
            return None
        try:
            resolved.relative_to(self.storage_root)
        except ValueError:
            return None
        return resolved

    def delete_file_if_exists(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def delete_tree_if_exists(self, path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)
