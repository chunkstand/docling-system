from __future__ import annotations

from enum import StrEnum

import pytest
from sqlalchemy import UniqueConstraint

import app.db.models as model_module
from app.db.base import Base
from tests.db_model_contract import (
    ENUM_SYMBOLS,
    EXPECTED_TABLE_NAMES,
    MODEL_DOMAIN_SYMBOLS,
    MODEL_SYMBOLS,
    PUBLIC_MODEL_IMPORT_SYMBOLS,
    REQUIRED_TABLE_INDEX_NAMES,
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
)


@pytest.mark.parametrize("symbol_name", PUBLIC_MODEL_IMPORT_SYMBOLS)
def test_public_model_symbol_remains_importable(symbol_name: str) -> None:
    module = __import__("app.db.models", fromlist=[symbol_name])

    symbol = getattr(module, symbol_name)

    assert symbol.__name__ == symbol_name


@pytest.mark.parametrize("symbol_name", ENUM_SYMBOLS)
def test_public_model_enum_remains_str_enum(symbol_name: str) -> None:
    symbol = getattr(model_module, symbol_name)

    assert issubclass(symbol, StrEnum)


@pytest.mark.parametrize("symbol_name", MODEL_SYMBOLS)
def test_public_model_class_remains_registered_orm_model(symbol_name: str) -> None:
    symbol = getattr(model_module, symbol_name)

    assert issubclass(symbol, Base)
    assert symbol.__table__.name in EXPECTED_TABLE_NAMES
    assert symbol.__table__ is Base.metadata.tables[symbol.__table__.name]


def test_public_model_domain_contract_is_complete() -> None:
    assert len(MODEL_SYMBOLS) == 80
    assert len(set(MODEL_SYMBOLS)) == len(MODEL_SYMBOLS)
    assert len(PUBLIC_MODEL_IMPORT_SYMBOLS) == 109
    assert set(MODEL_DOMAIN_SYMBOLS) == {
        "agent_tasks",
        "audit_and_evidence",
        "claim_support",
        "document_artifacts",
        "evaluation_feedback",
        "ingest",
        "platform_support",
        "retrieval",
        "semantic_memory",
    }


def test_platform_support_model_is_owned_by_domain_module() -> None:
    from app.db.model_domains.platform import ApiIdempotencyKey

    assert model_module.ApiIdempotencyKey is ApiIdempotencyKey
    assert model_module.ApiIdempotencyKey.__module__ == "app.db.model_domains.platform"


def test_base_metadata_table_contract_is_complete() -> None:
    assert frozenset(Base.metadata.tables) == EXPECTED_TABLE_NAMES


@pytest.mark.parametrize(
    ("table_name", "expected_index_names"),
    REQUIRED_TABLE_INDEX_NAMES.items(),
)
def test_base_metadata_preserves_required_indexes(
    table_name: str, expected_index_names: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert {index.name for index in table.indexes} >= expected_index_names


@pytest.mark.parametrize(
    ("table_name", "expected_constraint_names"),
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES.items(),
)
def test_base_metadata_preserves_required_unique_constraints(
    table_name: str, expected_constraint_names: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]
    unique_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert unique_constraint_names >= expected_constraint_names
