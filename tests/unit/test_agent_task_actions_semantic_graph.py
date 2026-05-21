from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_semantic_graph import (
    ApplyGraphPromotionsTaskInput,
    BuildDocumentFactGraphTaskInput,
    BuildShadowSemanticGraphTaskInput,
    DraftGraphPromotionsTaskInput,
    EvaluateSemanticRelationExtractorTaskInput,
    TriageSemanticGraphDisagreementsTaskInput,
    VerifyDraftGraphPromotionsTaskInput,
)
from app.services.agent_actions.semantic_analysis_actions import (
    _build_document_fact_graph_executor,
    _build_shadow_semantic_graph_executor,
    _evaluate_semantic_relation_extractor_executor,
)
from app.services.agent_actions.semantic_governance_actions import (
    _apply_graph_promotions_executor,
    _draft_graph_promotions_executor,
    _verify_draft_graph_promotions_executor,
)
from app.services.agent_actions.semantic_verification_actions import (
    _triage_semantic_graph_disagreements_executor,
)
from tests.unit.agent_task_actions_support import (
    _draft_graph_output_payload,
    _graph_triage_output_payload,
    _semantic_relation_evaluation_output_payload,
    _shadow_graph_output_payload,
    _verify_graph_output_payload,
)


def test_build_document_fact_graph_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="build_document_fact_graph",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.build_document_fact_graph",
        lambda session, **kwargs: {
            "document_id": document_id,
            "run_id": uuid4(),
            "semantic_pass_id": uuid4(),
            "ontology_snapshot_id": uuid4(),
            "ontology_version": "portable-upper-ontology-v1.1",
            "fact_count": 1,
            "approved_fact_count": 1,
            "entity_count": 2,
            "relation_counts": {"document_mentions_concept": 1},
            "facts": [
                {
                    "fact_id": uuid4(),
                    "document_id": document_id,
                    "run_id": uuid4(),
                    "semantic_pass_id": uuid4(),
                    "relation_key": "document_mentions_concept",
                    "relation_label": "Document Mentions Concept",
                    "subject_entity_key": f"document:{document_id}",
                    "subject_label": "Integration One",
                    "object_entity_key": "concept:integration_threshold",
                    "object_label": "Integration Threshold",
                    "object_value_text": None,
                    "review_status": "approved",
                    "assertion_id": uuid4(),
                    "evidence_ids": [uuid4()],
                }
            ],
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_fact_graph.json",
        ),
    )

    result = _build_document_fact_graph_executor(
        session=object(),
        task=task,
        payload=BuildDocumentFactGraphTaskInput(document_id=document_id),
    )

    assert result["fact_count"] == 1
    assert result["artifact_kind"] == "semantic_fact_graph"

def test_build_shadow_semantic_graph_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="build_shadow_semantic_graph",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_ids = [uuid4(), uuid4()]
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.build_shadow_semantic_graph",
        lambda session, **kwargs: _shadow_graph_output_payload(document_ids=document_ids)[
            "shadow_graph"
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/shadow_semantic_graph.json",
        ),
    )

    result = _build_shadow_semantic_graph_executor(
        session=object(),
        task=task,
        payload=BuildShadowSemanticGraphTaskInput(
            document_ids=document_ids,
            minimum_review_status="approved",
            min_shared_documents=2,
            score_threshold=0.45,
        ),
    )

    assert result["shadow_graph"]["edge_count"] == 1
    assert result["artifact_kind"] == "shadow_semantic_graph"

def test_evaluate_semantic_relation_extractor_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="evaluate_semantic_relation_extractor",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_ids = [uuid4(), uuid4()]
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.evaluate_semantic_relation_extractor",
        lambda session, **kwargs: {
            key: value
            for key, value in _semantic_relation_evaluation_output_payload(
                document_ids=document_ids
            ).items()
            if key not in {"artifact_id", "artifact_kind", "artifact_path"}
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_relation_evaluation.json",
        ),
    )

    result = _evaluate_semantic_relation_extractor_executor(
        session=object(),
        task=task,
        payload=EvaluateSemanticRelationExtractorTaskInput(
            document_ids=document_ids,
            minimum_review_status="approved",
            baseline_min_shared_documents=2,
            candidate_score_threshold=0.45,
            expected_min_shared_documents=1,
        ),
    )

    assert result["summary"]["candidate_expected_recall"] == 1.0
    assert result["artifact_kind"] == "semantic_relation_evaluation"

def test_triage_semantic_graph_disagreements_executor_writes_artifact(monkeypatch) -> None:
    evaluation_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="triage_semantic_graph_disagreements",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_ids = [uuid4(), uuid4()]
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output=_semantic_relation_evaluation_output_payload(document_ids=document_ids),
            task_type="evaluate_semantic_relation_extractor",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.triage_semantic_graph_disagreements",
        lambda evaluation, **kwargs: _graph_triage_output_payload(
            evaluation_task_id=evaluation_task_id,
            verification_task_id=task.id,
        )["disagreement_report"],
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(task.id),
                "verification_task_id": str(task.id),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_graph_disagreement_report.json",
        ),
    )

    result = _triage_semantic_graph_disagreements_executor(
        session=object(),
        task=task,
        payload=TriageSemanticGraphDisagreementsTaskInput(
            target_task_id=evaluation_task_id,
            min_score=0.45,
            expected_only=True,
        ),
    )

    assert result["disagreement_report"]["issue_count"] == 1
    assert result["recommendation"]["next_action"] == "draft_graph_promotions"
    assert result["artifact_kind"] == "semantic_graph_disagreement_report"

def test_draft_graph_promotions_executor_writes_artifact(monkeypatch) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_graph_promotions",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output=_graph_triage_output_payload(
                evaluation_task_id=uuid4(),
                verification_task_id=uuid4(),
            ),
            task_type="triage_semantic_graph_disagreements",
        ),
    )
    session = SimpleNamespace(
        get=lambda model, key: (
            SimpleNamespace(task_type="triage_semantic_graph_disagreements")
            if model is AgentTask and key == source_task_id
            else None
        )
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.draft_graph_promotions",
        lambda session, **kwargs: _draft_graph_output_payload(
            source_task_id=source_task_id,
            source_task_type="triage_semantic_graph_disagreements",
        )["draft"],
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_graph_promotion_draft.json",
        ),
    )

    result = _draft_graph_promotions_executor(
        session=session,
        task=task,
        payload=DraftGraphPromotionsTaskInput(
            source_task_id=source_task_id,
            rationale="Promote approved graph memory.",
            min_score=0.45,
        ),
    )

    assert result["draft"]["proposed_graph_version"] == "portable-upper-ontology-v1.1.graph.1"
    assert result["artifact_kind"] == "semantic_graph_promotion_draft"

def test_verify_draft_graph_promotions_executor_writes_artifact(monkeypatch) -> None:
    draft_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_graph_promotions",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output=_draft_graph_output_payload(
                source_task_id=uuid4(),
                source_task_type="triage_semantic_graph_disagreements",
            ),
            task_type="draft_graph_promotions",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.verify_draft_graph_promotions",
        lambda session, draft, **kwargs: (
            {
                "promoted_edge_count": 1,
                "supported_edge_count": 1,
                "stale_edge_count": 0,
                "unsupported_edge_count": 0,
                "ontology_mismatch_count": 0,
                "conflict_count": 0,
                "traceable_edge_ratio": 1.0,
            },
            {
                "promoted_edge_count": 1,
                "supported_edge_count": 1,
                "stale_edge_count": 0,
                "unsupported_edge_count": 0,
                "ontology_mismatch_count": 0,
                "conflict_count": 0,
            },
            [],
            "passed",
            _verify_graph_output_payload(
                draft_task_id=draft_task_id,
                verification_task_id=task.id,
            )["success_metrics"],
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(draft_task_id),
                "verification_task_id": str(task.id),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_graph_promotion_verification.json",
        ),
    )

    result = _verify_draft_graph_promotions_executor(
        session=object(),
        task=task,
        payload=VerifyDraftGraphPromotionsTaskInput(target_task_id=draft_task_id),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "semantic_graph_promotion_verification"

def test_apply_graph_promotions_executor_writes_artifact(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="apply_graph_promotions",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    dependencies = {
        ("draft_graph_promotions", draft_task_id): SimpleNamespace(
            output=_draft_graph_output_payload(
                source_task_id=uuid4(),
                source_task_type="triage_semantic_graph_disagreements",
            )
        ),
        ("verify_draft_graph_promotions", verification_task_id): SimpleNamespace(
            output=_verify_graph_output_payload(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.resolve_required_dependency_task_output_context",
        lambda session, task_id, depends_on_task_id, expected_task_type, **kwargs: dependencies[
            (expected_task_type, depends_on_task_id)
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.apply_graph_promotions",
        lambda session, draft, **kwargs: {
            "applied_snapshot_id": uuid4(),
            "applied_graph_version": "portable-upper-ontology-v1.1.graph.1",
            "applied_graph_sha256": "graph-sha",
            "ontology_snapshot_id": uuid4(),
            "reason": kwargs["reason"],
            "applied_edge_count": 1,
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_governance_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/applied_semantic_graph_snapshot.json",
        ),
    )

    result = _apply_graph_promotions_executor(
        session=object(),
        task=task,
        payload=ApplyGraphPromotionsTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="Publish the verified semantic graph memory snapshot.",
        ),
    )

    assert result["applied_graph_version"] == "portable-upper-ontology-v1.1.graph.1"
    assert result["artifact_kind"] == "applied_semantic_graph_snapshot"
