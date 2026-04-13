from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.main import app
from app.db.base import Base
from app.db.session import get_db_session
from app.services.runs import claim_next_run, process_run
from app.services.storage import StorageService


def _create_schema_scoped_engine(database_url: str, schema_name: str) -> tuple[Engine, Engine]:
    admin_engine = create_engine(database_url, future=True)
    with admin_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

    base_engine = create_engine(database_url, future=True)
    engine = base_engine.execution_options(schema_translate_map={None: schema_name})
    Base.metadata.create_all(engine)
    return admin_engine, engine


@dataclass
class PostgresIntegrationHarness:
    client: TestClient
    session_factory: sessionmaker[Session]
    storage_service: StorageService

    def process_next_run(self, parser, *, worker_id: str = "integration-worker") -> UUID:
        with self.session_factory() as session:
            run = claim_next_run(session, worker_id)
            assert run is not None, "Expected a queued run to be available for processing."
            process_run(
                session=session,
                run_id=run.id,
                storage_service=self.storage_service,
                parser=parser,
                embedding_provider=None,
            )
            return run.id


@pytest.fixture
def postgres_integration_harness(monkeypatch, tmp_path) -> Generator[PostgresIntegrationHarness]:
    schema_name = f"test_{uuid4().hex}"
    database_url = "postgresql+psycopg://docling:docling@localhost:5432/docling_system"
    admin_engine, engine = _create_schema_scoped_engine(database_url, schema_name)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    storage_root = tmp_path / "storage"
    storage_service = StorageService(storage_root=storage_root)

    settings_stub = SimpleNamespace(
        storage_root=storage_root,
        openai_embedding_model="text-embedding-3-small",
        embedding_dim=1536,
        local_ingest_max_pages=750,
    )

    monkeypatch.setattr("app.api.main.get_storage_service", lambda: storage_service)
    monkeypatch.setattr("app.services.evaluations.get_settings", lambda: settings_stub)
    monkeypatch.setattr("app.services.validation.get_settings", lambda: settings_stub)
    monkeypatch.setattr("app.services.search.get_embedding_provider", lambda: None)
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    monkeypatch.setattr("app.services.storage.get_settings", lambda: settings_stub)

    def override_db_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    try:
        yield PostgresIntegrationHarness(
            client=client,
            session_factory=session_factory,
            storage_service=storage_service,
        )
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        admin_engine.dispose()
