from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import AgentTask, AgentTaskStatus, DocumentRun, RunStatus
from app.db.session import get_engine, get_session_factory
from app.services.evaluations import AUTO_CORPUS_FILENAME
from app.services.semantic_ontology import initialize_workspace_ontology

RESET_CONFIRMATION = "CLEAR_KNOWLEDGE_BASE"
OLD_DATA_PATTERNS = (
    "UPC",
    "The Bitter Lesson",
    "TEST_PDF",
    "debug.pdf",
    "integration-report",
    "integration_threshold",
    "system_diagram",
)
RUNTIME_SCAN_PATHS = (
    "app",
    "config",
    "docs",
    "README.md",
    "SYSTEM_PLAN.md",
    "AGENTS.md",
)
RUNNING_TASK_STATUSES = (
    AgentTaskStatus.QUEUED.value,
    AgentTaskStatus.PROCESSING.value,
    AgentTaskStatus.RETRY_WAIT.value,
    AgentTaskStatus.AWAITING_APPROVAL.value,
)
RUNNING_RUN_STATUSES = (
    RunStatus.QUEUED.value,
    RunStatus.PROCESSING.value,
    RunStatus.VALIDATING.value,
    RunStatus.RETRY_WAIT.value,
)


class KnowledgeBaseResetError(RuntimeError):
    pass


@dataclass(frozen=True)
class KnowledgeBaseResetOptions:
    execute: bool = False
    confirm: str | None = None
    allow_running_services: bool = False
    allow_active_work: bool = False
    allow_non_development: bool = False
    skip_pg_dump: bool = False
    archive_root: Path | None = None
    new_database_name: str | None = None
    project_root: Path = Path.cwd()


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _settings_payload() -> dict[str, Any]:
    settings = get_settings()
    return {
        "env": settings.env,
        "database_url": _redact_database_url(settings.database_url),
        "storage_root": str(settings.storage_root.expanduser().resolve()),
        "embedding_contract": {
            "model": settings.openai_embedding_model,
            "dimension": settings.embedding_dim,
        },
        "semantics_enabled": bool(settings.semantics_enabled),
        "upper_ontology_path": str(settings.upper_ontology_path),
        "semantic_registry_path": str(settings.semantic_registry_path)
        if settings.semantic_registry_path
        else None,
    }


def _redact_database_url(database_url: str) -> str:
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return "<unparseable>"


def _is_local_database_url(database_url: str) -> bool:
    try:
        url = make_url(database_url)
    except Exception:
        return False
    if not url.drivername.startswith("postgresql"):
        return False
    return (url.host or "localhost") in {"localhost", "127.0.0.1", "::1"}


def _libpq_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername.startswith("postgresql"):
        url = url.set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


def _new_database_url(database_url: str, database_name: str) -> str:
    return make_url(database_url).set(database=database_name).render_as_string(hide_password=False)


def _admin_database_url(database_url: str) -> str:
    return make_url(database_url).set(database="postgres").render_as_string(hide_password=False)


def _current_database_name(database_url: str) -> str:
    database = make_url(database_url).database
    if not database:
        raise KnowledgeBaseResetError("Database URL does not include a database name.")
    return database


def _sanitize_database_name(value: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    if not candidate:
        raise KnowledgeBaseResetError("New database name resolved to an empty value.")
    if len(candidate) > 63:
        candidate = candidate[:63].rstrip("_")
    if not re.match(r"^[a-z_][a-z0-9_]*$", candidate):
        candidate = f"kb_{candidate}"
    return candidate


def _generated_database_name(current_name: str, stamp: str) -> str:
    return _sanitize_database_name(f"{current_name}_clean_{stamp.lower()}")


def _count_rows(session: Session) -> dict[str, int | None]:
    counts: dict[str, int | None] = {}
    inspector = inspect(session.bind)
    existing_tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            counts[table.name] = None
            continue
        counts[table.name] = int(session.scalar(select(func.count()).select_from(table)) or 0)
    return counts


def _active_work_counts(session: Session) -> dict[str, int]:
    inspector = inspect(session.bind)
    existing_tables = set(inspector.get_table_names())
    run_count = 0
    if DocumentRun.__tablename__ in existing_tables:
        run_count = int(
            session.scalar(
                select(func.count())
                .select_from(DocumentRun)
                .where(DocumentRun.status.in_(RUNNING_RUN_STATUSES))
            )
            or 0
        )
    task_count = 0
    if "agent_tasks" in inspector.get_table_names():
        task_count = int(
            session.scalar(
                select(func.count())
                .select_from(AgentTask)
                .where(AgentTask.status.in_(RUNNING_TASK_STATUSES))
            )
            or 0
        )
    return {"document_runs": run_count, "agent_tasks": task_count}


def _run_command(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        text=True,
        capture_output=True,
    )


def _git_sha(project_root: Path) -> str | None:
    result = _run_command(["git", "rev-parse", "HEAD"], cwd=project_root)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _running_local_processes() -> list[dict[str, str]]:
    result = _run_command(
        ["pgrep", "-fl", r"docling-system-(api|worker|agent-worker)"],
    )
    if result.returncode not in {0, 1}:
        return []
    processes: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip() or "docling-system-knowledge-base-reset" in line:
            continue
        pid, _, command_line = line.partition(" ")
        processes.append({"kind": "process", "pid": pid, "command": command_line})
    return processes


def _running_compose_services(project_root: Path) -> list[dict[str, str]]:
    compose_file = project_root / "docker-compose.yml"
    if not compose_file.exists():
        return []
    result = _run_command(["docker", "compose", "ps", "--format", "json"], cwd=project_root)
    if result.returncode != 0:
        return []
    rows: list[dict[str, Any]] = []
    raw = result.stdout.strip()
    if not raw:
        return []
    try:
        decoded = json.loads(raw)
        rows = decoded if isinstance(decoded, list) else [decoded]
    except json.JSONDecodeError:
        for line in raw.splitlines():
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                rows.append(decoded)
    services: list[dict[str, str]] = []
    for row in rows:
        service = str(row.get("Service") or row.get("Name") or "")
        state = str(row.get("State") or row.get("Status") or "").lower()
        if service in {"api", "worker", "agent-worker"} and "running" in state:
            services.append({"kind": "compose", "service": service, "state": state})
    return services


def running_service_reports(project_root: Path) -> list[dict[str, str]]:
    return [*_running_local_processes(), *_running_compose_services(project_root)]


def scan_old_data_references(project_root: Path) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = {pattern: [] for pattern in OLD_DATA_PATTERNS}
    for relative in RUNTIME_SCAN_PATHS:
        root = project_root / relative
        if not root.exists():
            continue
        paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        for path in paths:
            if path.parts and "__pycache__" in path.parts:
                continue
            try:
                text_value = path.read_text(errors="ignore")
            except OSError:
                continue
            if path.relative_to(project_root).as_posix() == "app/services/knowledge_base_reset.py":
                continue
            for line_number, line in enumerate(text_value.splitlines(), start=1):
                for pattern in OLD_DATA_PATTERNS:
                    if pattern in line:
                        results[pattern].append(
                            {
                                "path": str(path.relative_to(project_root)),
                                "line": line_number,
                                "text": line.strip()[:220],
                            }
                        )
    return results


def _alembic_current(project_root: Path) -> str | None:
    result = _run_command(["uv", "run", "alembic", "current"], cwd=project_root)
    if result.returncode != 0:
        return None
    for line in reversed(result.stdout.splitlines()):
        stripped = line.strip()
        if stripped and not stripped.startswith("INFO"):
            return stripped.split(" ", 1)[0]
    return None


def _alembic_heads(project_root: Path) -> list[str]:
    result = _run_command(["uv", "run", "alembic", "heads"], cwd=project_root)
    if result.returncode != 0:
        return []
    return [
        line.strip().split(" ", 1)[0]
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]


def build_reset_manifest(options: KnowledgeBaseResetOptions, *, stamp: str | None = None) -> dict:
    stamp = stamp or _utc_stamp()
    settings = get_settings()
    storage_root = settings.storage_root.expanduser().resolve()
    database_url = settings.database_url
    current_database_name = _current_database_name(database_url)
    new_database_name = (
        _sanitize_database_name(options.new_database_name)
        if options.new_database_name
        else _generated_database_name(current_database_name, stamp)
    )
    archive_root = (
        options.archive_root.expanduser().resolve()
        if options.archive_root is not None
        else (storage_root.parent / "reset-archives" / stamp).resolve()
    )
    with get_session_factory()() as session:
        table_counts = _count_rows(session)
        active_work = _active_work_counts(session)
    return {
        "schema_name": "knowledge_base_reset_manifest",
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "execute" if options.execute else "dry_run",
        "project_root": str(options.project_root.resolve()),
        "git_sha": _git_sha(options.project_root),
        "settings": _settings_payload(),
        "database": {
            "old_url": _redact_database_url(database_url),
            "old_name": current_database_name,
            "new_url": _redact_database_url(_new_database_url(database_url, new_database_name)),
            "new_name": new_database_name,
            "is_local_postgres": _is_local_database_url(database_url),
            "alembic_current": _alembic_current(options.project_root),
            "alembic_heads": _alembic_heads(options.project_root),
        },
        "storage": {
            "old_root": str(storage_root),
            "new_root": str(storage_root),
            "archive_root": str(archive_root),
            "old_root_exists": storage_root.exists(),
        },
        "archive_paths": {
            "database_dump": str(archive_root / f"{current_database_name}.{stamp}.dump"),
            "env_backup": str(archive_root / ".env.before-reset"),
            "storage_archive": str(archive_root / "storage"),
            "manifest": str(archive_root / "manifest.json"),
        },
        "table_counts": table_counts,
        "active_work_counts": active_work,
        "running_services": running_service_reports(options.project_root),
        "old_data_reference_hits": scan_old_data_references(options.project_root),
    }


def _require_safe_to_execute(options: KnowledgeBaseResetOptions, manifest: dict) -> None:
    settings = get_settings()
    if options.confirm != RESET_CONFIRMATION:
        raise KnowledgeBaseResetError(f"Execution requires --confirm {RESET_CONFIRMATION}.")
    if settings.env != "development" and not options.allow_non_development:
        raise KnowledgeBaseResetError("Knowledge base reset is only allowed in development.")
    if not manifest["database"]["is_local_postgres"]:
        raise KnowledgeBaseResetError(
            "Knowledge base reset requires a local Postgres database URL."
        )
    if manifest["database"]["alembic_current"] not in manifest["database"]["alembic_heads"]:
        raise KnowledgeBaseResetError("Current database is not at the Alembic head.")
    if manifest["running_services"] and not options.allow_running_services:
        raise KnowledgeBaseResetError("API/worker services are running; stop them before reset.")
    if any(manifest["active_work_counts"].values()) and not options.allow_active_work:
        raise KnowledgeBaseResetError("Queued or in-flight work exists; drain it before reset.")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def _write_empty_auto_corpus(storage_root: Path) -> None:
    settings = get_settings()
    payload = {
        "rollout_mode": "auto_generated_append_only",
        "embedding_contract": {
            "model": settings.openai_embedding_model,
            "dimension": settings.embedding_dim,
        },
        "documents": [],
    }
    path = storage_root / AUTO_CORPUS_FILENAME
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


def _backup_and_update_env(project_root: Path, archive_root: Path, new_database_name: str) -> None:
    env_path = project_root / ".env"
    if env_path.exists():
        archive_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(env_path, archive_root / ".env.before-reset")
        lines = env_path.read_text().splitlines()
    else:
        lines = []

    database_url = get_settings().database_url
    new_database_url = _new_database_url(database_url, new_database_name)
    updates = {
        "DOCLING_SYSTEM_DATABASE_URL": new_database_url,
        "DOCLING_SYSTEM_POSTGRES_DB": new_database_name,
    }
    seen: set[str] = set()
    updated_lines: list[str] = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            updated_lines.append(line)
            continue
        key, _value = line.split("=", 1)
        if key in updates:
            updated_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            updated_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            updated_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(updated_lines).rstrip() + "\n")
    os.environ["DOCLING_SYSTEM_DATABASE_URL"] = new_database_url
    os.environ["DOCLING_SYSTEM_POSTGRES_DB"] = new_database_name
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def _create_database(database_url: str, database_name: str) -> None:
    admin_engine = create_engine(
        _admin_database_url(database_url),
        future=True,
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            )
            if exists:
                raise KnowledgeBaseResetError(f"Target database already exists: {database_name}")
            quoted = '"' + database_name.replace('"', '""') + '"'
            connection.execute(text(f"CREATE DATABASE {quoted}"))
    finally:
        admin_engine.dispose()


def _pg_dump_command_and_env(
    database_url: str,
    dump_path: Path,
) -> tuple[list[str], dict[str, str]]:
    url = make_url(database_url)
    command_args = [
        "pg_dump",
        "--format=custom",
        "--file",
        str(dump_path),
    ]
    if url.host:
        command_args.extend(["--host", url.host])
    if url.port:
        command_args.extend(["--port", str(url.port)])
    if url.username:
        command_args.extend(["--username", url.username])
    if url.database:
        command_args.append(url.database)
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password
    return command_args, env


def _run_pg_dump(database_url: str, dump_path: Path) -> None:
    if shutil.which("pg_dump") is None:
        raise KnowledgeBaseResetError("pg_dump is required for reset archives but was not found.")
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    command_args, env = _pg_dump_command_and_env(database_url, dump_path)
    result = subprocess.run(
        command_args,
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    if result.returncode != 0:
        raise KnowledgeBaseResetError(f"pg_dump failed: {result.stderr.strip()}")


def _run_alembic_upgrade(project_root: Path) -> None:
    config = Config(str(project_root / "alembic.ini"))
    command.upgrade(config, "head")


def _recreate_storage_root(storage_root: Path, archive_root: Path) -> None:
    archive_storage = archive_root / "storage"
    if archive_root == storage_root or archive_root.is_relative_to(storage_root):
        raise KnowledgeBaseResetError("Archive root must not be inside the storage root.")
    if archive_storage.exists():
        raise KnowledgeBaseResetError(f"Storage archive already exists: {archive_storage}")
    archive_root.mkdir(parents=True, exist_ok=True)
    if storage_root.exists():
        shutil.move(str(storage_root), str(archive_storage))
    for name in ("source", "runs", "_staging", "agent_tasks", "audit_bundles", "resets"):
        (storage_root / name).mkdir(parents=True, exist_ok=True)
    _write_empty_auto_corpus(storage_root)


def _initialize_generic_ontology() -> dict[str, Any]:
    with get_session_factory()() as session:
        return initialize_workspace_ontology(session)


def execute_knowledge_base_reset(options: KnowledgeBaseResetOptions) -> dict[str, Any]:
    stamp = _utc_stamp()
    manifest = build_reset_manifest(options, stamp=stamp)
    if not options.execute:
        return manifest
    _require_safe_to_execute(options, manifest)

    settings = get_settings()
    database_url = settings.database_url
    storage_root = settings.storage_root.expanduser().resolve()
    archive_root = Path(manifest["storage"]["archive_root"])
    new_database_name = manifest["database"]["new_name"]

    archive_root.mkdir(parents=True, exist_ok=True)
    if options.skip_pg_dump:
        manifest["archive_paths"]["database_dump"] = None
    _write_json(archive_root / "manifest.json", manifest)
    if not options.skip_pg_dump:
        _run_pg_dump(database_url, Path(manifest["archive_paths"]["database_dump"]))
    _create_database(database_url, new_database_name)
    _backup_and_update_env(options.project_root, archive_root, new_database_name)
    _run_alembic_upgrade(options.project_root)
    _recreate_storage_root(storage_root, archive_root)
    ontology_payload = _initialize_generic_ontology()

    final_manifest = build_reset_manifest(options, stamp=stamp)
    final_manifest["ontology_initialization"] = ontology_payload
    final_manifest["archive_paths"] = manifest["archive_paths"]
    final_manifest["mode"] = "executed"
    reset_manifest_path = storage_root / "resets" / stamp / "manifest.json"
    _write_json(reset_manifest_path, final_manifest)
    _write_json(archive_root / "manifest.after.json", final_manifest)
    return final_manifest
