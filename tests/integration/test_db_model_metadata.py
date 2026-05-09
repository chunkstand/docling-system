from __future__ import annotations

import os

import pytest
from sqlalchemy import text

import app.db.models  # noqa: F401
from tests.db_model_contract import (
    EXPECTED_TABLE_NAMES,
    PLATFORM_SUPPORT_TABLE_COLUMNS,
    REQUIRED_TABLE_INDEX_NAMES,
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_postgres_create_all_registers_expected_model_tables(
    postgres_schema_engine,
) -> None:
    engine, schema_name = postgres_schema_engine

    with engine.connect() as connection:
        table_names = frozenset(
            connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = :schema_name
                    AND table_type = 'BASE TABLE'
                    """
                ),
                {"schema_name": schema_name},
            ).scalars()
        )

    assert table_names == EXPECTED_TABLE_NAMES


def test_postgres_create_all_preserves_first_platform_support_table_contract(
    postgres_schema_engine,
) -> None:
    engine, schema_name = postgres_schema_engine
    expected_columns = PLATFORM_SUPPORT_TABLE_COLUMNS["api_idempotency_keys"]

    with engine.connect() as connection:
        column_names = frozenset(
            connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = :schema_name
                    AND table_name = 'api_idempotency_keys'
                    """
                ),
                {"schema_name": schema_name},
            ).scalars()
        )

    assert column_names == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_index_names"),
    REQUIRED_TABLE_INDEX_NAMES.items(),
)
def test_postgres_create_all_preserves_required_model_indexes(
    postgres_schema_engine,
    table_name: str,
    expected_index_names: frozenset[str],
) -> None:
    engine, schema_name = postgres_schema_engine

    with engine.connect() as connection:
        index_names = frozenset(
            connection.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = :schema_name
                    AND tablename = :table_name
                    """
                ),
                {"schema_name": schema_name, "table_name": table_name},
            ).scalars()
        )

    assert index_names >= expected_index_names


@pytest.mark.parametrize(
    ("table_name", "expected_constraint_names"),
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES.items(),
)
def test_postgres_create_all_preserves_required_unique_constraints(
    postgres_schema_engine,
    table_name: str,
    expected_constraint_names: frozenset[str],
) -> None:
    engine, schema_name = postgres_schema_engine

    with engine.connect() as connection:
        constraint_names = frozenset(
            connection.execute(
                text(
                    """
                    SELECT con.conname
                    FROM pg_constraint con
                    JOIN pg_class cls ON cls.oid = con.conrelid
                    JOIN pg_namespace ns ON ns.oid = cls.relnamespace
                    WHERE ns.nspname = :schema_name
                    AND cls.relname = :table_name
                    AND con.contype = 'u'
                    """
                ),
                {"schema_name": schema_name, "table_name": table_name},
            ).scalars()
        )

    assert constraint_names >= expected_constraint_names
