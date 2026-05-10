from __future__ import annotations

import os

import pytest
from sqlalchemy import text

import app.db.models  # noqa: F401
from tests.db_model_contract import (
    DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS,
    EXPECTED_TABLE_NAMES,
    INGEST_DOMAIN_TABLE_COLUMNS,
    PLATFORM_SUPPORT_TABLE_COLUMNS,
    REQUIRED_TABLE_INDEX_COLUMNS,
    REQUIRED_TABLE_INDEX_NAMES,
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    REQUIRED_VECTOR_DIMENSIONS,
    RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS,
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
    ("table_name", "expected_columns"),
    INGEST_DOMAIN_TABLE_COLUMNS.items(),
)
def test_postgres_create_all_preserves_ingest_domain_table_contract(
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


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS.items(),
)
def test_postgres_create_all_preserves_document_artifact_domain_table_contract(
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


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS.items(),
)
def test_postgres_create_all_preserves_retrieval_interaction_domain_table_contract(
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
    ("table_name", "index_columns_by_name"),
    REQUIRED_TABLE_INDEX_COLUMNS.items(),
)
def test_postgres_create_all_preserves_required_index_columns(
    postgres_schema_engine,
    table_name: str,
    index_columns_by_name: dict[str, tuple[str, ...]],
) -> None:
    engine, schema_name = postgres_schema_engine

    for index_name, expected_columns in index_columns_by_name.items():
        with engine.connect() as connection:
            column_names = tuple(
                connection.execute(
                    text(
                        """
                        SELECT attr.attname
                        FROM pg_class table_cls
                        JOIN pg_namespace namespace
                            ON namespace.oid = table_cls.relnamespace
                        JOIN pg_index index_record
                            ON index_record.indrelid = table_cls.oid
                        JOIN pg_class index_cls
                            ON index_cls.oid = index_record.indexrelid
                        JOIN LATERAL unnest(index_record.indkey)
                            WITH ORDINALITY AS index_key(attnum, position)
                            ON true
                        JOIN pg_attribute attr
                            ON attr.attrelid = table_cls.oid
                            AND attr.attnum = index_key.attnum
                        WHERE namespace.nspname = :schema_name
                        AND table_cls.relname = :table_name
                        AND index_cls.relname = :index_name
                        ORDER BY index_key.position
                        """
                    ),
                    {
                        "schema_name": schema_name,
                        "table_name": table_name,
                        "index_name": index_name,
                    },
                ).scalars()
            )

        assert column_names == expected_columns


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


@pytest.mark.parametrize(
    ("table_name", "constraint_columns_by_name"),
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS.items(),
)
def test_postgres_create_all_preserves_required_unique_constraint_columns(
    postgres_schema_engine,
    table_name: str,
    constraint_columns_by_name: dict[str, tuple[str, ...]],
) -> None:
    engine, schema_name = postgres_schema_engine

    for constraint_name, expected_columns in constraint_columns_by_name.items():
        with engine.connect() as connection:
            column_names = tuple(
                connection.execute(
                    text(
                        """
                        SELECT attr.attname
                        FROM pg_constraint constraint_record
                        JOIN pg_class table_cls
                            ON table_cls.oid = constraint_record.conrelid
                        JOIN pg_namespace namespace
                            ON namespace.oid = table_cls.relnamespace
                        JOIN LATERAL unnest(constraint_record.conkey)
                            WITH ORDINALITY AS constraint_key(attnum, position)
                            ON true
                        JOIN pg_attribute attr
                            ON attr.attrelid = table_cls.oid
                            AND attr.attnum = constraint_key.attnum
                        WHERE namespace.nspname = :schema_name
                        AND table_cls.relname = :table_name
                        AND constraint_record.conname = :constraint_name
                        AND constraint_record.contype = 'u'
                        ORDER BY constraint_key.position
                        """
                    ),
                    {
                        "schema_name": schema_name,
                        "table_name": table_name,
                        "constraint_name": constraint_name,
                    },
                ).scalars()
            )

        assert column_names == expected_columns


@pytest.mark.parametrize(
    ("table_name", "vector_columns"),
    REQUIRED_VECTOR_DIMENSIONS.items(),
)
def test_postgres_create_all_preserves_required_vector_dimensions(
    postgres_schema_engine,
    table_name: str,
    vector_columns: dict[str, int],
) -> None:
    engine, schema_name = postgres_schema_engine

    for column_name, expected_dim in vector_columns.items():
        with engine.connect() as connection:
            formatted_type = connection.execute(
                text(
                    """
                    SELECT format_type(attr.atttypid, attr.atttypmod)
                    FROM pg_class table_cls
                    JOIN pg_namespace namespace
                        ON namespace.oid = table_cls.relnamespace
                    JOIN pg_attribute attr
                        ON attr.attrelid = table_cls.oid
                    WHERE namespace.nspname = :schema_name
                    AND table_cls.relname = :table_name
                    AND attr.attname = :column_name
                    """
                ),
                {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "column_name": column_name,
                },
            ).scalar_one()

        assert formatted_type == f"vector({expected_dim})"
