from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskVerification,
)
from app.services.agent_task_context import (
    build_agent_task_context,
)


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def one(self):
        if len(self._rows) != 1:
            raise AssertionError("Expected one row")
        return self._rows[0]

    def all(self):
        return list(self._rows)


class FakeExecuteResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return FakeScalarResult(self._rows)


class FakeSession:
    def __init__(
        self,
        *,
        tasks=None,
        artifacts=None,
        dependencies=None,
        verifications=None,
        replay_runs=None,
    ) -> None:
        self.tasks = tasks or {}
        self.artifacts = artifacts or {}
        self.dependencies = dependencies or {}
        self.verifications = verifications or {}
        self.replay_runs = replay_runs or {}

    def get(self, model, key):
        if model.__name__ == "AgentTask":
            return self.tasks.get(key)
        if model.__name__ == "AgentTaskArtifact":
            return self.artifacts.get(key)
        if model.__name__ == "AgentTaskVerification":
            return self.verifications.get(key)
        if model.__name__ == "SearchReplayRun":
            return self.replay_runs.get(key)
        return None

    def execute(self, statement):
        rendered = str(statement)
        compiled = statement.compile()
        params = compiled.params
        if "agent_task_artifacts" in rendered:
            rows = list(self.artifacts.values())
            task_id = params.get("task_id_1")
            artifact_kind = params.get("artifact_kind_1")
            if task_id is not None:
                rows = [row for row in rows if row.task_id == task_id]
            if artifact_kind is not None:
                rows = [row for row in rows if row.artifact_kind == artifact_kind]
            return FakeExecuteResult(rows)
        if "agent_task_dependencies" in rendered:
            rows = list(self.dependencies.values())
            task_id = params.get("task_id_1")
            depends_on_task_id = params.get("depends_on_task_id_1")
            if task_id is not None:
                rows = [row for row in rows if row.task_id == task_id]
            if depends_on_task_id is not None:
                rows = [row for row in rows if row.depends_on_task_id == depends_on_task_id]
            return FakeExecuteResult(rows)
        raise AssertionError(f"Unexpected statement: {rendered}")


def _build_context_artifact(*, task_id, payload) -> AgentTaskArtifact:
    return AgentTaskArtifact(
        id=uuid4(),
        task_id=task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json=payload,
        created_at=datetime.now(UTC),
    )


def _candidate_evaluation_output_payload(*, document_id) -> dict:
    return {
        "baseline_extractor": {
            "extractor_name": "registry_lexical_v1",
            "backing_model": "none",
            "match_strategy": "normalized_phrase_contains",
            "shadow_mode": True,
            "provider_name": None,
        },
        "candidate_extractor": {
            "extractor_name": "concept_ranker_v1",
            "backing_model": "hashing_embedding_v1",
            "match_strategy": "token_set_ranker_v1",
            "shadow_mode": True,
            "provider_name": "local_hashing",
        },
        "document_reports": [
            {
                "document_id": str(document_id),
                "run_id": str(uuid4()),
                "semantic_pass_id": str(uuid4()),
                "registry_version": "semantics-layer-foundation-alpha.4",
                "registry_sha256": "registry-sha",
                "evaluation_fixture_name": "integration-fixture",
                "expected_concept_keys": ["integration_threshold", "integration_owner"],
                "live_concept_keys": ["integration_threshold"],
                "baseline_predicted_concept_keys": ["integration_threshold"],
                "candidate_predicted_concept_keys": [
                    "integration_owner",
                    "integration_threshold",
                ],
                "improved_expected_concept_keys": ["integration_owner"],
                "regressed_expected_concept_keys": [],
                "candidate_only_concept_keys": ["integration_owner"],
                "shadow_candidates": [
                    {
                        "concept_key": "integration_owner",
                        "preferred_label": "Integration Owner",
                        "max_score": 0.71,
                        "source_count": 1,
                        "source_types": ["chunk"],
                        "category_keys": ["integration_governance"],
                        "expected_by_evaluation": True,
                        "evidence_refs": [],
                        "note": None,
                    }
                ],
                "source_predictions": [],
                "summary": {
                    "baseline_expected_recall": 0.5,
                    "candidate_expected_recall": 1.0,
                    "expected_concept_count": 2,
                    "candidate_source_prediction_count": 1,
                    "baseline_source_prediction_count": 1,
                    "improved_expected_concept_count": 1,
                    "regressed_expected_concept_count": 0,
                },
            }
        ],
        "summary": {
            "document_count": 1,
            "expected_concept_count": 2,
            "baseline_expected_recall": 0.5,
            "candidate_expected_recall": 1.0,
            "improved_expected_concept_count": 1,
            "regressed_expected_concept_count": 0,
            "candidate_only_concept_count": 1,
            "live_mutation_performed": False,
            "score_threshold": 0.34,
            "max_candidates_per_source": 3,
        },
        "success_metrics": [
            {
                "metric_key": "agent_legibility",
                "stakeholder": "Lopopolo",
                "passed": True,
                "summary": "Typed evaluation ready",
                "details": {},
            }
        ],
        "artifact_id": str(uuid4()),
        "artifact_kind": "semantic_candidate_evaluation",
        "artifact_path": "/tmp/semantic_candidate_evaluation.json",
    }


def test_build_agent_task_context_for_evaluate_semantic_candidate_extractor_artifact_ref() -> None:
    now = datetime.now(UTC)
    task_id = uuid4()
    document_id = uuid4()
    task = AgentTask(
        id=task_id,
        task_type="evaluate_semantic_candidate_extractor",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    output = _candidate_evaluation_output_payload(document_id=document_id)
    artifact_id = UUID(output["artifact_id"])
    artifact = AgentTaskArtifact(
        id=artifact_id,
        task_id=task_id,
        attempt_id=None,
        artifact_kind="semantic_candidate_evaluation",
        storage_path=output["artifact_path"],
        payload_json=output,
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(tasks={task_id: task}, artifacts={artifact_id: artifact}),
        task,
        {"payload": output},
    )

    assert context.summary.next_action == (
        "Create triage_semantic_candidate_disagreements to compact useful shadow gaps."
    )
    assert context.refs[0].artifact_kind == "semantic_candidate_evaluation"


def test_build_agent_task_context_for_triage_semantic_candidate_disagreements_tracks_refs() -> None:
    now = datetime.now(UTC)
    evaluation_task_id = uuid4()
    triage_task_id = uuid4()
    verification_id = uuid4()
    document_id = uuid4()
    evaluation_task = AgentTask(
        id=evaluation_task_id,
        task_type="evaluate_semantic_candidate_extractor",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    triage_task = AgentTask(
        id=triage_task_id,
        task_type="triage_semantic_candidate_disagreements",
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={"target_task_id": str(evaluation_task_id)},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    evaluation_output = _candidate_evaluation_output_payload(document_id=document_id)
    evaluation_context_artifact = _build_context_artifact(
        task_id=evaluation_task_id,
        payload={
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "task_id": str(evaluation_task_id),
            "task_type": "evaluate_semantic_candidate_extractor",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": now.isoformat(),
            "task_updated_at": now.isoformat(),
            "output_schema_name": "evaluate_semantic_candidate_extractor_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Shadow evaluation ready"},
            "refs": [],
            "output": evaluation_output,
        },
    )
    verification_row = AgentTaskVerification(
        id=verification_id,
        target_task_id=triage_task_id,
        verification_task_id=triage_task_id,
        verifier_type="semantic_candidate_shadow_gate",
        outcome="passed",
        metrics_json={"issue_count": 1},
        reasons_json=[],
        details_json={"min_score": 0.34},
        created_at=now,
        completed_at=now,
    )
    triage_artifact_id = uuid4()
    triage_artifact = AgentTaskArtifact(
        id=triage_artifact_id,
        task_id=triage_task_id,
        attempt_id=None,
        artifact_kind="semantic_candidate_disagreement_report",
        storage_path="/tmp/semantic_candidate_disagreement_report.json",
        payload_json={"issue_count": 1},
        created_at=now,
    )
    dependency = AgentTaskDependency(
        task_id=triage_task_id,
        depends_on_task_id=evaluation_task_id,
        dependency_kind="target_task",
        created_at=now,
    )

    context = build_agent_task_context(
        FakeSession(
            tasks={evaluation_task_id: evaluation_task, triage_task_id: triage_task},
            artifacts={
                evaluation_context_artifact.id: evaluation_context_artifact,
                triage_artifact_id: triage_artifact,
            },
            dependencies={uuid4(): dependency},
            verifications={verification_id: verification_row},
        ),
        triage_task,
        {
            "payload": {
                "evaluation_task_id": str(evaluation_task_id),
                "disagreement_report": {
                    "baseline_extractor_name": "registry_lexical_v1",
                    "candidate_extractor_name": "concept_ranker_v1",
                    "issue_count": 1,
                    "issues": [
                        {
                            "issue_id": "shadow:1",
                            "document_id": str(document_id),
                            "concept_key": "integration_owner",
                            "severity": "high",
                            "expected_by_evaluation": True,
                            "in_live_semantics": False,
                            "baseline_found": False,
                            "max_score": 0.71,
                            "summary": "Shadow candidate surfaced outside live semantics.",
                            "evidence_refs": [],
                            "details": {},
                        }
                    ],
                    "recommended_followups": [],
                    "success_metrics": [],
                },
                "verification": {
                    "verification_id": str(verification_id),
                    "target_task_id": str(triage_task_id),
                    "verification_task_id": str(triage_task_id),
                    "verifier_type": "semantic_candidate_shadow_gate",
                    "outcome": "passed",
                    "metrics": {"issue_count": 1},
                    "reasons": [],
                    "details": {"min_score": 0.34},
                    "created_at": now.isoformat(),
                    "completed_at": now.isoformat(),
                },
                "recommendation": {
                    "next_action": "review_shadow_candidates",
                    "confidence": 0.7,
                    "summary": "Review the disagreement report.",
                },
                "artifact_id": str(triage_artifact_id),
                "artifact_kind": "semantic_candidate_disagreement_report",
                "artifact_path": "/tmp/semantic_candidate_disagreement_report.json",
            }
        },
    )

    assert context.summary.verification_state == "passed"
    assert {ref.ref_key for ref in context.refs} == {
        "target_task_output",
        "verification_record",
        "disagreement_artifact",
    }
