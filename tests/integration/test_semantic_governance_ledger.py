from __future__ import annotations

import importlib.util
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.models import (
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchReplayRun,
    SemanticGovernanceEvent,
    SemanticGraphSourceKind,
    SemanticOntologySourceKind,
)
from app.services.semantic_governance import (
    record_semantic_governance_event,
    semantic_governance_chain_for_audit,
    semantic_governance_event_integrity,
)
from app.services.semantic_graph import persist_semantic_graph_snapshot
from app.services.semantic_registry import (
    clear_semantic_registry_cache,
    ensure_workspace_semantic_registry,
    get_active_semantic_ontology_snapshot,
    persist_semantic_ontology_snapshot,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def _load_revision_0045():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0045_semantic_governance_events.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0045_semantic_governance", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0045 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts: []
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
  - relation_key: concept_related_to_concept
    preferred_label: Concept Related To Concept
"""
    )


def _replay_run(*, replay_run_id, harness_name: str) -> SearchReplayRun:
    now = datetime.now(UTC)
    return SearchReplayRun(
        id=replay_run_id,
        source_type="evaluation_queries",
        status="completed",
        harness_name=harness_name,
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name=harness_name,
        harness_config_json={},
        query_count=3,
        passed_count=3,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        error_message=None,
        created_at=now,
        completed_at=now + timedelta(seconds=1),
    )


def test_semantic_governance_ledger_records_lifecycle_events_and_is_append_only(
    postgres_integration_harness,
    postgres_schema_engine,
    monkeypatch,
    tmp_path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    _write_registry(registry_path)
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    monkeypatch.setattr(
        "app.services.audit_bundles.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="semantic-governance-secret",
            audit_bundle_signing_key_id="semantic-governance-key",
        ),
    )
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        base_snapshot = get_active_semantic_ontology_snapshot(session)
        ontology_snapshot = persist_semantic_ontology_snapshot(
            session,
            {
                "registry_name": "portable_upper_ontology",
                "registry_version": "portable-upper-ontology-v2",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "categories": [],
                "concepts": [
                    {
                        "concept_key": "governance_control",
                        "preferred_label": "Governance Control",
                    }
                ],
                "relations": [
                    {
                        "relation_key": "document_mentions_concept",
                        "preferred_label": "Document Mentions Concept",
                    },
                    {
                        "relation_key": "concept_related_to_concept",
                        "preferred_label": "Concept Related To Concept",
                    },
                ],
            },
            source_kind=SemanticOntologySourceKind.ONTOLOGY_EXTENSION_APPLY.value,
            parent_snapshot_id=base_snapshot.id,
            activate=True,
        )
        graph_snapshot = persist_semantic_graph_snapshot(
            session,
            {
                "graph_name": "workspace_semantic_graph",
                "graph_version": "portable-upper-ontology-v2.graph.1",
                "ontology_snapshot_id": str(ontology_snapshot.id),
                "nodes": [],
                "edges": [],
            },
            source_kind=SemanticGraphSourceKind.GRAPH_PROMOTION_APPLY.value,
            activate=True,
        )
        ontology_snapshot_id = ontology_snapshot.id
        graph_snapshot_id = graph_snapshot.id
        session.commit()

    now = datetime.now(UTC)
    evaluation_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()
    with postgres_integration_harness.session_factory() as session:
        session.add_all(
            [
                _replay_run(
                    replay_run_id=baseline_replay_run_id,
                    harness_name="default_v1",
                ),
                _replay_run(
                    replay_run_id=candidate_replay_run_id,
                    harness_name="wide_v2",
                ),
                SearchHarnessEvaluation(
                    id=evaluation_id,
                    status="completed",
                    baseline_harness_name="default_v1",
                    candidate_harness_name="wide_v2",
                    limit=3,
                    source_types_json=["evaluation_queries"],
                    harness_overrides_json={},
                    total_shared_query_count=3,
                    total_improved_count=1,
                    total_regressed_count=0,
                    total_unchanged_count=2,
                    summary_json={},
                    error_message=None,
                    created_at=now,
                    completed_at=now + timedelta(seconds=2),
                ),
            ]
        )
        session.flush()
        session.add(
            SearchHarnessEvaluationSource(
                id=uuid4(),
                search_harness_evaluation_id=evaluation_id,
                source_index=0,
                source_type="evaluation_queries",
                baseline_replay_run_id=baseline_replay_run_id,
                candidate_replay_run_id=candidate_replay_run_id,
                baseline_status="completed",
                candidate_status="completed",
                baseline_query_count=3,
                candidate_query_count=3,
                baseline_passed_count=3,
                candidate_passed_count=3,
                baseline_zero_result_count=0,
                candidate_zero_result_count=0,
                baseline_table_hit_count=1,
                candidate_table_hit_count=1,
                baseline_top_result_changes=0,
                candidate_top_result_changes=0,
                baseline_mrr=1.0,
                candidate_mrr=1.0,
                baseline_foreign_top_result_count=0,
                candidate_foreign_top_result_count=0,
                acceptance_checks_json={"no_regressions": True},
                shared_query_count=3,
                improved_count=1,
                regressed_count=0,
                unchanged_count=2,
                created_at=now,
            )
        )
        session.commit()

    release_response = postgres_integration_harness.client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "min_total_shared_query_count": 1,
            "requested_by": "integration",
            "review_note": "semantic governance ledger",
        },
    )
    assert release_response.status_code == 200
    release_id = release_response.json()["release_id"]

    with postgres_integration_harness.session_factory() as session:
        events = list(
            session.scalars(
                select(SemanticGovernanceEvent).order_by(
                    SemanticGovernanceEvent.event_sequence.asc()
                )
            )
        )
        event_kinds = {row.event_kind for row in events}
        assert {
            "ontology_snapshot_recorded",
            "ontology_snapshot_activated",
            "semantic_graph_snapshot_recorded",
            "semantic_graph_snapshot_activated",
            "search_harness_release_recorded",
        }.issubset(event_kinds)
        assert any(row.ontology_snapshot_id == ontology_snapshot_id for row in events)
        assert any(row.semantic_graph_snapshot_id == graph_snapshot_id for row in events)
        assert any(str(row.search_harness_release_id) == release_id for row in events)
        assert all(semantic_governance_event_integrity(row)["complete"] for row in events)
        protected_event_id = events[0].id

    revision_0045 = _load_revision_0045()
    _engine, schema_name = postgres_schema_engine
    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        session.execute(
            text(revision_0045.PREVENT_SEMANTIC_GOVERNANCE_EVENT_MUTATION_FUNCTION_SQL)
        )
        session.execute(
            text(revision_0045.PREVENT_SEMANTIC_GOVERNANCE_EVENT_MUTATION_TRIGGER_SQL)
        )
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        with pytest.raises(IntegrityError, match="semantic_governance_events rows are immutable"):
            session.execute(
                text(
                    "UPDATE semantic_governance_events "
                    "SET event_payload = jsonb_build_object('tampered', true) "
                    "WHERE id = :event_id"
                ),
                {"event_id": str(protected_event_id)},
            )
            session.commit()
        session.rollback()

    with postgres_integration_harness.session_factory() as session:
        session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
        with pytest.raises(IntegrityError, match="semantic_governance_events rows are immutable"):
            session.execute(
                text("DELETE FROM semantic_governance_events WHERE id = :event_id"),
                {"event_id": str(protected_event_id)},
            )
            session.commit()
        session.rollback()


def test_semantic_governance_chain_expands_previous_event_closure(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    _write_registry(registry_path)
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    task_scope_id = uuid4()
    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        ontology_snapshot = get_active_semantic_ontology_snapshot(session)
        anchor = record_semantic_governance_event(
            session,
            event_kind="ontology_snapshot_recorded",
            governance_scope=f"agent_task:{task_scope_id}",
            subject_table="semantic_ontology_snapshots",
            subject_id=ontology_snapshot.id,
            ontology_snapshot_id=ontology_snapshot.id,
            event_payload={
                "ontology_snapshot": {
                    "ontology_snapshot_id": str(ontology_snapshot.id),
                    "sha256": ontology_snapshot.sha256,
                }
            },
            deduplication_key=f"test-anchor:{task_scope_id}",
            created_by="test",
        )
        matched = record_semantic_governance_event(
            session,
            event_kind="technical_report_prov_export_frozen",
            governance_scope=f"agent_task:{task_scope_id}",
            subject_table="agent_task_artifacts",
            subject_id=uuid4(),
            receipt_sha256="receipt-closure-test",
            event_payload={
                "technical_report_prov_export": {
                    "artifact_id": str(uuid4()),
                    "receipt_sha256": "receipt-closure-test",
                },
                "change_impact": {"impacted": False, "impact_count": 0, "impacts": []},
            },
            deduplication_key=f"test-report:{task_scope_id}",
            created_by="test",
        )
        anchor_id = anchor.id
        matched_id = matched.id
        matched_previous_event_id = matched.previous_event_id
        session.commit()
        chain = semantic_governance_chain_for_audit(
            session,
            task_ids=[],
            artifact_ids=[],
            evidence_manifest_ids=[],
            receipt_sha256s=["receipt-closure-test"],
        )

    assert matched_previous_event_id == anchor_id
    assert chain["event_count"] == 2
    assert {row["event_id"] for row in chain["events"]} == {str(anchor_id), str(matched_id)}
    assert chain["integrity"]["external_previous_event_count"] == 0
    assert chain["integrity"]["hash_links_verified"] is True
    assert chain["integrity"]["change_impact_evaluated"] is True
    assert chain["integrity"]["complete"] is True
