from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from app.services import knowledge_base_reset
from app.services.knowledge_base_reset import (
    KnowledgeBaseResetError,
    KnowledgeBaseResetOptions,
    _backup_and_update_env,
    _pg_dump_command_and_env,
    _post_reset_checks,
    _require_safe_to_execute,
    _write_empty_auto_corpus,
    scan_old_data_references,
)


def _safe_manifest(tmp_path: Path) -> dict:
    return {
        "database": {
            "old_name": "docling_system",
            "new_name": "docling_system_clean",
            "is_local_postgres": True,
            "alembic_current": "head_rev",
            "alembic_heads": ["head_rev"],
        },
        "storage": {
            "old_root": str(tmp_path / "storage"),
            "archive_root": str(tmp_path / "reset-archives" / "stamp"),
        },
        "running_services": [],
        "active_work_counts": {"document_runs": 0, "agent_tasks": 0},
    }


def test_pg_dump_command_keeps_password_out_of_process_args(tmp_path) -> None:
    dump_path = tmp_path / "db.dump"

    args, env = _pg_dump_command_and_env(
        "postgresql+psycopg://docling:secret@localhost:5432/docling_system",
        dump_path,
    )

    assert "secret" not in " ".join(args)
    assert env["PGPASSWORD"] == "secret"
    assert args[-1] == "docling_system"


def test_execute_requires_confirmation(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        knowledge_base_reset,
        "get_settings",
        lambda: SimpleNamespace(env="development"),
    )
    manifest = _safe_manifest(tmp_path)

    with pytest.raises(KnowledgeBaseResetError, match="--confirm CLEAR_KNOWLEDGE_BASE"):
        _require_safe_to_execute(KnowledgeBaseResetOptions(execute=True), manifest)


def test_execute_refuses_running_services_without_override(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        knowledge_base_reset,
        "get_settings",
        lambda: SimpleNamespace(env="development"),
    )
    manifest = _safe_manifest(tmp_path)
    manifest["running_services"] = [
        {"kind": "compose", "service": "worker", "state": "running"}
    ]

    with pytest.raises(KnowledgeBaseResetError, match="services are running"):
        _require_safe_to_execute(
            KnowledgeBaseResetOptions(
                execute=True,
                confirm="CLEAR_KNOWLEDGE_BASE",
            ),
            manifest,
        )


def test_execute_refuses_archive_root_inside_storage(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        knowledge_base_reset,
        "get_settings",
        lambda: SimpleNamespace(env="development"),
    )
    manifest = _safe_manifest(tmp_path)
    manifest["storage"]["archive_root"] = str(tmp_path / "storage" / "resets" / "stamp")

    with pytest.raises(KnowledgeBaseResetError, match="Archive root"):
        _require_safe_to_execute(
            KnowledgeBaseResetOptions(
                execute=True,
                confirm="CLEAR_KNOWLEDGE_BASE",
            ),
            manifest,
        )


def test_execute_refuses_current_database_as_target(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        knowledge_base_reset,
        "get_settings",
        lambda: SimpleNamespace(env="development"),
    )
    manifest = _safe_manifest(tmp_path)
    manifest["database"]["new_name"] = manifest["database"]["old_name"]

    with pytest.raises(KnowledgeBaseResetError, match="must differ"):
        _require_safe_to_execute(
            KnowledgeBaseResetOptions(
                execute=True,
                confirm="CLEAR_KNOWLEDGE_BASE",
            ),
            manifest,
        )


def test_old_data_scan_excludes_tests_and_reset_pattern_catalog(tmp_path) -> None:
    (tmp_path / "app" / "services").mkdir(parents=True)
    (tmp_path / "config").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "app" / "services" / "knowledge_base_reset.py").write_text(
        'OLD_DATA_PATTERNS = ("UPC",)\n'
    )
    (tmp_path / "config" / "stale.yaml").write_text("source_filename: TEST_PDF.pdf\n")
    (tmp_path / "tests" / "legacy.yaml").write_text("source_filename: UPC_CH_5.pdf\n")

    hits = scan_old_data_references(tmp_path)

    assert hits["UPC"] == []
    assert hits["TEST_PDF"] == [
        {
            "path": "config/stale.yaml",
            "line": 1,
            "text": "source_filename: TEST_PDF.pdf",
        }
    ]


def test_empty_auto_corpus_uses_current_embedding_contract(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        knowledge_base_reset,
        "get_settings",
        lambda: SimpleNamespace(
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        ),
    )

    _write_empty_auto_corpus(tmp_path)

    payload = yaml.safe_load((tmp_path / "evaluation_corpus.auto.yaml").read_text())
    assert payload == {
        "rollout_mode": "auto_generated_append_only",
        "embedding_contract": {
            "model": "text-embedding-3-small",
            "dimension": 1536,
        },
        "documents": [],
    }


def test_backup_and_update_env_updates_compose_db(monkeypatch, tmp_path) -> None:
    project_root = tmp_path / "project"
    archive_root = tmp_path / "archive"
    project_root.mkdir()
    env_path = project_root / ".env"
    env_path.write_text(
        "\n".join(
            [
                "DOCLING_SYSTEM_ENV=development",
                "DOCLING_SYSTEM_DATABASE_URL=postgresql+psycopg://docling:secret@localhost:5432/docling_system",
                "DOCLING_SYSTEM_POSTGRES_DB=docling_system",
                "DOCLING_SYSTEM_HOST_STORAGE_ROOT=./storage",
            ]
        )
        + "\n"
    )
    def fake_get_settings() -> SimpleNamespace:
        return SimpleNamespace(
            database_url=(
                "postgresql+psycopg://docling:secret@localhost:5432/docling_system"
            ),
        )

    fake_get_settings.cache_clear = lambda: None  # type: ignore[attr-defined]
    monkeypatch.setattr(knowledge_base_reset, "get_settings", fake_get_settings)

    _backup_and_update_env(project_root, archive_root, "docling_system_clean")

    assert (archive_root / ".env.before-reset").read_text() == (
        "DOCLING_SYSTEM_ENV=development\n"
        "DOCLING_SYSTEM_DATABASE_URL=postgresql+psycopg://docling:secret@localhost:5432/docling_system\n"
        "DOCLING_SYSTEM_POSTGRES_DB=docling_system\n"
        "DOCLING_SYSTEM_HOST_STORAGE_ROOT=./storage\n"
    )
    updated = env_path.read_text()
    assert (
        "DOCLING_SYSTEM_DATABASE_URL=postgresql+psycopg://docling:secret@localhost:5432/"
        "docling_system_clean"
    ) in updated
    assert "DOCLING_SYSTEM_POSTGRES_DB=docling_system_clean" in updated
    assert "DOCLING_SYSTEM_HOST_STORAGE_ROOT=./storage" in updated


def test_post_reset_checks_require_only_generic_ontology_rows(tmp_path) -> None:
    storage_root = tmp_path / "storage"
    for name in ("source", "runs", "_staging", "agent_tasks", "audit_bundles", "resets"):
        (storage_root / name).mkdir(parents=True)
    (storage_root / "evaluation_corpus.auto.yaml").write_text("documents: []\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "evaluation_corpus.yaml").write_text("documents: []\n")
    (tmp_path / "docs" / "semantic_evaluation_corpus.yaml").write_text("documents: []\n")

    checks = _post_reset_checks(
        table_counts={
            "documents": 0,
            "document_runs": 0,
            "semantic_assertions": 0,
            "semantic_entities": 0,
            "semantic_facts": 0,
            "semantic_graph_snapshots": 0,
            "workspace_semantic_graph_state": 0,
            "semantic_ontology_snapshots": 1,
            "workspace_semantic_state": 1,
            "semantic_governance_events": 2,
        },
        storage_root=storage_root,
        project_root=tmp_path,
    )

    assert checks["passed"] is True
    assert checks["database_at_head"] is True
    assert checks["unexpected_non_empty_tables"] == {}


def test_post_reset_checks_fail_when_runtime_rows_remain(tmp_path) -> None:
    storage_root = tmp_path / "storage"
    for name in ("source", "runs", "_staging", "agent_tasks", "audit_bundles", "resets"):
        (storage_root / name).mkdir(parents=True)
    (storage_root / "evaluation_corpus.auto.yaml").write_text("documents: []\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "evaluation_corpus.yaml").write_text("documents: []\n")
    (tmp_path / "docs" / "semantic_evaluation_corpus.yaml").write_text("documents: []\n")

    checks = _post_reset_checks(
        table_counts={
            "documents": 1,
            "semantic_assertions": 0,
            "semantic_entities": 0,
            "semantic_facts": 0,
            "semantic_graph_snapshots": 0,
            "workspace_semantic_graph_state": 0,
            "semantic_ontology_snapshots": 1,
            "workspace_semantic_state": 1,
        },
        storage_root=storage_root,
        project_root=tmp_path,
    )

    assert checks["passed"] is False
    assert checks["unexpected_non_empty_tables"] == {"documents": 1}


def test_post_reset_checks_fail_when_database_is_not_at_head(tmp_path) -> None:
    storage_root = tmp_path / "storage"
    for name in ("source", "runs", "_staging", "agent_tasks", "audit_bundles", "resets"):
        (storage_root / name).mkdir(parents=True)
    (storage_root / "evaluation_corpus.auto.yaml").write_text("documents: []\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "evaluation_corpus.yaml").write_text("documents: []\n")
    (tmp_path / "docs" / "semantic_evaluation_corpus.yaml").write_text("documents: []\n")

    checks = _post_reset_checks(
        table_counts={
            "documents": 0,
            "semantic_assertions": 0,
            "semantic_entities": 0,
            "semantic_facts": 0,
            "semantic_graph_snapshots": 0,
            "workspace_semantic_graph_state": 0,
            "semantic_ontology_snapshots": 1,
            "workspace_semantic_state": 1,
        },
        storage_root=storage_root,
        project_root=tmp_path,
        database_at_head=False,
    )

    assert checks["passed"] is False
    assert checks["database_at_head"] is False
