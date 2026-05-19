from __future__ import annotations

import pytest

import app.db.models as model_module
from app.db.base import Base
from tests.db_model_contract import SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS

EXPECTED_MODEL_MODULES = {
    "SemanticOntologySnapshot": "app.db.model_domains.semantic_memory_snapshots",
    "WorkspaceSemanticState": "app.db.model_domains.semantic_memory_snapshots",
    "SemanticGraphSnapshot": "app.db.model_domains.semantic_memory_snapshots",
    "WorkspaceSemanticGraphState": "app.db.model_domains.semantic_memory_snapshots",
    "SemanticConcept": "app.db.model_domains.semantic_memory_registry",
    "SemanticCategory": "app.db.model_domains.semantic_memory_registry",
    "SemanticTerm": "app.db.model_domains.semantic_memory_registry",
    "SemanticConceptTerm": "app.db.model_domains.semantic_memory_registry",
    "SemanticConceptCategoryBinding": "app.db.model_domains.semantic_memory_registry",
    "DocumentSemanticConceptReview": "app.db.model_domains.semantic_memory_reviews",
    "DocumentSemanticCategoryReview": "app.db.model_domains.semantic_memory_reviews",
    "DocumentRunSemanticPass": "app.db.model_domains.semantic_memory_reviews",
    "SemanticAssertion": "app.db.model_domains.semantic_memory_assertions",
    "SemanticAssertionCategoryBinding": "app.db.model_domains.semantic_memory_assertions",
    "SemanticAssertionEvidence": "app.db.model_domains.semantic_memory_assertions",
    "SemanticEntity": "app.db.model_domains.semantic_memory_facts",
    "SemanticFact": "app.db.model_domains.semantic_memory_facts",
    "SemanticFactEvidence": "app.db.model_domains.semantic_memory_facts",
    "SemanticGovernanceEvent": "app.db.model_domains.semantic_memory_governance",
}


@pytest.mark.parametrize(("model_name", "expected_module"), EXPECTED_MODEL_MODULES.items())
def test_semantic_memory_models_are_owned_by_family_local_modules(
    model_name: str, expected_module: str
) -> None:
    model = getattr(model_module, model_name)

    assert model.__module__ == expected_module
    assert model.__table__ is Base.metadata.tables[model.__table__.name]


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_semantic_memory_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns
