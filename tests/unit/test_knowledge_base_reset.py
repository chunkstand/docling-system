from __future__ import annotations

from types import SimpleNamespace

import pytest
import yaml

from app.services import knowledge_base_reset
from app.services.knowledge_base_reset import (
    KnowledgeBaseResetError,
    KnowledgeBaseResetOptions,
    _pg_dump_command_and_env,
    _require_safe_to_execute,
    _write_empty_auto_corpus,
    scan_old_data_references,
)


def test_pg_dump_command_keeps_password_out_of_process_args(tmp_path) -> None:
    dump_path = tmp_path / "db.dump"

    args, env = _pg_dump_command_and_env(
        "postgresql+psycopg://docling:secret@localhost:5432/docling_system",
        dump_path,
    )

    assert "secret" not in " ".join(args)
    assert env["PGPASSWORD"] == "secret"
    assert args[-1] == "docling_system"


def test_execute_requires_confirmation(monkeypatch) -> None:
    monkeypatch.setattr(
        knowledge_base_reset,
        "get_settings",
        lambda: SimpleNamespace(env="development"),
    )
    manifest = {
        "database": {
            "is_local_postgres": True,
            "alembic_current": "head_rev",
            "alembic_heads": ["head_rev"],
        },
        "running_services": [],
        "active_work_counts": {"document_runs": 0, "agent_tasks": 0},
    }

    with pytest.raises(KnowledgeBaseResetError, match="--confirm CLEAR_KNOWLEDGE_BASE"):
        _require_safe_to_execute(KnowledgeBaseResetOptions(execute=True), manifest)


def test_execute_refuses_running_services_without_override(monkeypatch) -> None:
    monkeypatch.setattr(
        knowledge_base_reset,
        "get_settings",
        lambda: SimpleNamespace(env="development"),
    )
    manifest = {
        "database": {
            "is_local_postgres": True,
            "alembic_current": "head_rev",
            "alembic_heads": ["head_rev"],
        },
        "running_services": [{"kind": "compose", "service": "worker", "state": "running"}],
        "active_work_counts": {"document_runs": 0, "agent_tasks": 0},
    }

    with pytest.raises(KnowledgeBaseResetError, match="services are running"):
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
