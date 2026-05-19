from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.models import AgentTaskArtifact


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


def build_context_artifact(*, task_id, payload) -> AgentTaskArtifact:
    return AgentTaskArtifact(
        id=uuid4(),
        task_id=task_id,
        attempt_id=None,
        artifact_kind="context",
        storage_path=None,
        payload_json=payload,
        created_at=datetime.now(UTC),
    )


def build_task_context_payload(
    *,
    task_id,
    task_type: str,
    output_schema_name: str,
    output: dict,
    updated_at: datetime | None = None,
) -> dict:
    timestamp = (updated_at or datetime.now(UTC)).isoformat()
    return {
        "schema_name": "agent_task_context",
        "schema_version": "1.0",
        "task_id": str(task_id),
        "task_type": task_type,
        "task_status": "completed",
        "workflow_version": "v1",
        "generated_at": timestamp,
        "task_updated_at": timestamp,
        "output_schema_name": output_schema_name,
        "output_schema_version": "1.0",
        "freshness_status": "fresh",
        "summary": {"headline": f"{task_type} ready"},
        "refs": [],
        "output": output,
    }


def prepare_generation_brief_output(*, task_id) -> dict:
    document_id = uuid4()
    return {
        "brief": {
            "document_kind": "knowledge_brief",
            "title": "Integration Governance Brief",
            "goal": "Summarize the knowledge base guidance on integration governance.",
            "audience": "Operators",
            "review_policy": "allow_candidate_with_disclosure",
            "target_length": "medium",
            "document_refs": [
                {
                    "document_id": str(document_id),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "source_filename": "integration-one.pdf",
                    "title": "Integration One",
                    "registry_version": "semantics-layer-foundation-alpha.3",
                    "registry_sha256": "registry-sha",
                    "evaluation_fixture_name": "integration_fixture",
                    "evaluation_status": "completed",
                    "assertion_count": 1,
                    "evidence_count": 2,
                    "all_expectations_passed": True,
                }
            ],
            "selected_concept_keys": ["integration_threshold"],
            "selected_category_keys": ["integration_governance"],
            "semantic_dossier": [],
            "sections": [
                {
                    "section_id": "section:integration_governance",
                    "title": "Integration Governance",
                    "summary": (
                        "This section covers one semantic concept from the selected corpus scope."
                    ),
                    "focus_concept_keys": ["integration_threshold"],
                    "focus_category_keys": ["integration_governance"],
                    "claim_ids": ["claim:integration_threshold"],
                }
            ],
            "claim_candidates": [
                {
                    "claim_id": "claim:integration_threshold",
                    "section_id": "section:integration_governance",
                    "summary": "Integration Threshold appears in Integration One.",
                    "concept_keys": ["integration_threshold"],
                    "assertion_ids": [str(uuid4())],
                    "evidence_labels": ["E1"],
                    "source_document_ids": [str(document_id)],
                    "support_level": "supported",
                    "review_policy_status": "candidate_disclosed",
                    "disclosure_note": "Candidate-backed support requires review.",
                }
            ],
            "evidence_pack": [],
            "warnings": [],
            "success_metrics": [
                {
                    "metric_key": "agent_legibility",
                    "stakeholder": "Lopopolo",
                    "passed": True,
                    "summary": "Typed brief ready",
                    "details": {},
                }
            ],
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "semantic_generation_brief",
        "artifact_path": "/tmp/semantic_generation_brief.json",
    }


def draft_grounded_document_output(*, brief_task_id, artifact_id) -> dict:
    return {
        "draft": {
            "document_kind": "knowledge_brief",
            "title": "Integration Governance Brief",
            "goal": "Summarize the knowledge base guidance on integration governance.",
            "audience": "Operators",
            "review_policy": "allow_candidate_with_disclosure",
            "target_length": "medium",
            "brief_task_id": str(brief_task_id),
            "generator_name": "structured_fallback",
            "generator_model": None,
            "used_fallback": True,
            "required_concept_keys": ["integration_threshold"],
            "document_refs": [],
            "assertion_index": [],
            "sections": [
                {
                    "section_id": "section:integration_governance",
                    "title": "Integration Governance",
                    "body_markdown": "- Integration Threshold appears in Integration One.",
                    "claim_ids": ["claim:integration_threshold"],
                }
            ],
            "claims": [
                {
                    "claim_id": "claim:integration_threshold",
                    "section_id": "section:integration_governance",
                    "rendered_text": "Integration Threshold appears in Integration One.",
                    "concept_keys": ["integration_threshold"],
                    "assertion_ids": [str(uuid4())],
                    "evidence_labels": ["E1"],
                    "source_document_ids": [str(uuid4())],
                    "support_level": "supported",
                    "review_policy_status": "candidate_disclosed",
                    "disclosure_note": "Candidate-backed support requires review.",
                }
            ],
            "evidence_pack": [],
            "markdown": "# Integration Governance Brief\n",
            "markdown_path": "/tmp/semantic_grounded_document.md",
            "warnings": [],
            "success_metrics": [
                {
                    "metric_key": "agent_legibility",
                    "stakeholder": "Lopopolo",
                    "passed": True,
                    "summary": "Typed draft ready",
                    "details": {},
                }
            ],
        },
        "artifact_id": str(artifact_id),
        "artifact_kind": "semantic_grounded_document_draft",
        "artifact_path": "/tmp/semantic_grounded_document_draft.json",
    }


def claim_support_judge_evaluation_output_payload(
    *,
    artifact_id=None,
    gate_outcome: str = "passed",
    failed_case_count: int = 0,
) -> dict:
    evaluation_id = uuid4()
    artifact_id = artifact_id or uuid4()
    reasons = ["Overall accuracy 0.0000 is below 1.0000."] if gate_outcome == "failed" else []
    return {
        "evaluation_id": str(evaluation_id),
        "evaluation_name": "claim_support_judge_calibration",
        "fixture_set_name": "default_claim_support_v1",
        "fixture_set_sha256": "fixture-set-sha",
        "judge_name": "technical_report_claim_support_judge",
        "judge_version": "deterministic_claim_support_v1",
        "thresholds": {
            "min_overall_accuracy": 1.0,
            "min_verdict_precision": 1.0,
            "min_verdict_recall": 1.0,
            "min_support_score": 0.34,
        },
        "summary": {
            "case_count": 1,
            "passed_case_count": 1 - failed_case_count,
            "failed_case_count": failed_case_count,
            "overall_accuracy": 0.0 if gate_outcome == "failed" else 1.0,
            "gate_outcome": gate_outcome,
            "hard_case_kind_count": 1,
            "hard_case_kinds": ["exact_source_support"],
        },
        "verdict_metrics": {},
        "case_results": [],
        "reasons": reasons,
        "success_metrics": [],
        "operator_run_id": None,
        "artifact_id": str(artifact_id),
        "artifact_kind": "claim_support_judge_evaluation",
        "artifact_path": "/tmp/claim_support_judge_evaluation.json",
    }
