from __future__ import annotations

import os

import pytest
from sqlalchemy import text

import app.db.models  # noqa: F401
from tests.db_model_contract import SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS.items(),
)
def test_postgres_create_all_preserves_semantic_memory_domain_table_contract(
    postgres_schema_engine,
    table_name: str,
    expected_columns: frozenset[str],
) -> None:
    engine, schema_name = postgres_schema_engine

    with engine.connect() as connection:
        column_names = frozenset(
            connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = :schema_name
                    AND table_name = :table_name
                    """
                ),
                {"schema_name": schema_name, "table_name": table_name},
            ).scalars()
        )

    assert column_names == expected_columns
