from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text


def _load_revision_0062():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0062_claim_support_impact_replay_governance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0062_claim_support_impact_replay_governance",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0062 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enable_claim_support_governance_signing(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.claim_support_policy_governance.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="claim-support-secret",
            audit_bundle_signing_key_id="claim-support-key",
        ),
    )


def _install_claim_support_governance_immutability_trigger(
    postgres_integration_harness,
    postgres_schema_engine,
) -> str:
    revision_0062 = _load_revision_0062()
    _engine, schema_name = postgres_schema_engine
    trigger_sql = """
    DROP TRIGGER IF EXISTS trg_agent_task_artifacts_prevent_frozen_prov_mutation
    ON agent_task_artifacts;
    CREATE TRIGGER trg_agent_task_artifacts_prevent_frozen_prov_mutation
    BEFORE UPDATE OR DELETE ON agent_task_artifacts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_frozen_agent_task_artifact_mutation();
    """
    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(text(revision_0062.PROTECTED_ARTIFACT_MUTATION_FUNCTION_SQL))
        session.execute(text(trigger_sql))
        session.commit()
    return schema_name


def _drop_claim_support_governance_immutability_trigger(
    postgres_integration_harness,
    schema_name: str,
) -> None:
    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(
            text(
                """
                DROP TRIGGER IF EXISTS trg_agent_task_artifacts_prevent_frozen_prov_mutation
                ON agent_task_artifacts;
                DROP FUNCTION IF EXISTS prevent_frozen_agent_task_artifact_mutation();
                """
            )
        )
        session.commit()
