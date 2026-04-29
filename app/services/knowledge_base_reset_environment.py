from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.services.knowledge_base_reset_contracts import KnowledgeBaseResetError

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
RESET_SCAN_SELF_PATHS = {
    "app/services/knowledge_base_reset.py",
    "app/services/knowledge_base_reset_environment.py",
}


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def settings_payload() -> dict[str, Any]:
    settings = get_settings()
    return {
        "env": settings.env,
        "database_url": redact_database_url(settings.database_url),
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


def redact_database_url(database_url: str) -> str:
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return "<unparseable>"


def is_local_database_url(database_url: str) -> bool:
    try:
        url = make_url(database_url)
    except Exception:
        return False
    if not url.drivername.startswith("postgresql"):
        return False
    return (url.host or "localhost") in {"localhost", "127.0.0.1", "::1"}


def new_database_url(database_url: str, database_name: str) -> str:
    return make_url(database_url).set(database=database_name).render_as_string(hide_password=False)


def admin_database_url(database_url: str) -> str:
    return make_url(database_url).set(database="postgres").render_as_string(hide_password=False)


def current_database_name(database_url: str) -> str:
    database = make_url(database_url).database
    if not database:
        raise KnowledgeBaseResetError("Database URL does not include a database name.")
    return database


def sanitize_database_name(value: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    if not candidate:
        raise KnowledgeBaseResetError("New database name resolved to an empty value.")
    if len(candidate) > 63:
        candidate = candidate[:63].rstrip("_")
    if not re.match(r"^[a-z_][a-z0-9_]*$", candidate):
        candidate = f"kb_{candidate}"
    return candidate


def generated_database_name(current_name: str, stamp: str) -> str:
    return sanitize_database_name(f"{current_name}_clean_{stamp.lower()}")


def run_command(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        text=True,
        capture_output=True,
    )


def git_sha(project_root: Path) -> str | None:
    result = run_command(["git", "rev-parse", "HEAD"], cwd=project_root)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _running_local_processes() -> list[dict[str, str]]:
    result = run_command(
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
    result = run_command(["docker", "compose", "ps", "--format", "json"], cwd=project_root)
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
            if path.relative_to(project_root).as_posix() in RESET_SCAN_SELF_PATHS:
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
