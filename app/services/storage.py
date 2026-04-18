from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import UploadFile

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

    def stage_upload(self, upload: UploadFile) -> tuple[Path, str]:
        suffix = Path(upload.filename or "upload.pdf").suffix or ".pdf"
        hasher = hashlib.sha256()

        with NamedTemporaryFile(delete=False, dir=self.staging_root, suffix=suffix) as temp_file:
            while chunk := upload.file.read(1024 * 1024):
                temp_file.write(chunk)
                hasher.update(chunk)
            staged_path = Path(temp_file.name)

        upload.file.close()
        return staged_path, hasher.hexdigest()

    def stage_local_file(self, source_path: Path) -> tuple[Path, str]:
        suffix = source_path.suffix or ".pdf"
        hasher = hashlib.sha256()

        with source_path.open("rb") as source_file:
            with NamedTemporaryFile(
                delete=False, dir=self.staging_root, suffix=suffix
            ) as temp_file:
                while chunk := source_file.read(1024 * 1024):
                    temp_file.write(chunk)
                    hasher.update(chunk)
                staged_path = Path(temp_file.name)

        return staged_path, hasher.hexdigest()

    def move_source_file(self, document_id: uuid.UUID, staged_path: Path) -> Path:
        destination = self.source_root / f"{document_id}.pdf"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_path), destination)
        return destination

    def get_run_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        path = self.runs_root / str(document_id) / str(run_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_docling_json_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.get_run_dir(document_id, run_id) / "docling.json"

    def get_yaml_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.get_run_dir(document_id, run_id) / "document.yaml"

    def get_table_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        path = self.get_run_dir(document_id, run_id) / "tables"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_table_json_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, table_index: int
    ) -> Path:
        return self.get_table_dir(document_id, run_id) / f"{table_index}.json"

    def get_table_yaml_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, table_index: int
    ) -> Path:
        return self.get_table_dir(document_id, run_id) / f"{table_index}.yaml"

    def get_figure_dir(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        path = self.get_run_dir(document_id, run_id) / "figures"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_figure_json_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, figure_index: int
    ) -> Path:
        return self.get_figure_dir(document_id, run_id) / f"{figure_index}.json"

    def get_figure_yaml_path(
        self, document_id: uuid.UUID, run_id: uuid.UUID, figure_index: int
    ) -> Path:
        return self.get_figure_dir(document_id, run_id) / f"{figure_index}.yaml"

    def get_failure_artifact_path(self, document_id: uuid.UUID, run_id: uuid.UUID) -> Path:
        return self.get_run_dir(document_id, run_id) / "failure.json"

    def get_agent_task_dir(self, task_id: uuid.UUID) -> Path:
        path = self.storage_root / "agent_tasks" / str(task_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_agent_task_context_json_path(self, task_id: uuid.UUID) -> Path:
        return self.get_agent_task_dir(task_id) / "context.json"

    def get_agent_task_context_yaml_path(self, task_id: uuid.UUID) -> Path:
        return self.get_agent_task_dir(task_id) / "context.yaml"

    def get_agent_task_failure_artifact_path(self, task_id: uuid.UUID) -> Path:
        return self.get_agent_task_dir(task_id) / "failure.json"

    def delete_file_if_exists(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def delete_tree_if_exists(self, path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)
