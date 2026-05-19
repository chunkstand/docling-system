from __future__ import annotations

import pytest

import app.db.models as model_module
from app.db.base import Base
from tests.db_model_contract import CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS

EXPECTED_MODEL_MODULES = {
    "ClaimSupportReplayAlertFixtureCoverageWaiverLedger": (
        "app.db.model_domains.claim_support_waivers"
    ),
    "ClaimSupportReplayAlertFixtureCoverageWaiverEscalation": (
        "app.db.model_domains.claim_support_waivers"
    ),
    "ClaimSupportFixtureSet": "app.db.model_domains.claim_support_fixtures",
    "ClaimSupportReplayAlertFixtureCorpusSnapshot": ("app.db.model_domains.claim_support_fixtures"),
    "ClaimSupportReplayAlertFixtureCorpusRow": "app.db.model_domains.claim_support_fixtures",
    "ClaimSupportCalibrationPolicy": "app.db.model_domains.claim_support_evaluations",
    "ClaimSupportEvaluation": "app.db.model_domains.claim_support_evaluations",
    "ClaimSupportEvaluationCase": "app.db.model_domains.claim_support_evaluations",
    "ClaimSupportPolicyChangeImpact": "app.db.model_domains.claim_support_policy_impacts",
}


@pytest.mark.parametrize(("model_name", "expected_module"), EXPECTED_MODEL_MODULES.items())
def test_claim_support_models_are_owned_by_family_local_modules(
    model_name: str, expected_module: str
) -> None:
    model = getattr(model_module, model_name)

    assert model.__module__ == expected_module
    assert model.__table__ is Base.metadata.tables[model.__table__.name]


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_claim_support_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns
