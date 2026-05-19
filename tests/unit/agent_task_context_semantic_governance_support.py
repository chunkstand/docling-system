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


def bootstrap_discovery_output_payload(*, document_id) -> dict:
    return {
        "report": {
            "report_name": "semantic_bootstrap_candidate_report",
            "extraction_strategy": "corpus_phrase_mining_v1",
            "input_document_ids": [str(document_id)],
            "document_count": 1,
            "total_source_count": 3,
            "existing_registry_term_exclusion": True,
            "candidate_count": 1,
            "candidates": [
                {
                    "candidate_id": "bootstrap:incident_response_latency",
                    "concept_key": "incident_response_latency",
                    "preferred_label": "Incident Response Latency",
                    "normalized_phrase": "incident response latency",
                    "phrase_tokens": ["incident", "response", "latency"],
                    "epistemic_status": "candidate_bootstrap",
                    "document_ids": [str(document_id)],
                    "document_count": 1,
                    "source_count": 3,
                    "source_types": ["chunk", "table"],
                    "score": 0.88,
                    "evidence_refs": [],
                    "details": {},
                }
            ],
            "warnings": [],
            "success_metrics": [
                {
                    "metric_key": "semantic_integrity",
                    "stakeholder": "Figay",
                    "passed": True,
                    "summary": "Candidates remain evidence-backed and provisional.",
                    "details": {},
                }
            ],
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "semantic_bootstrap_candidate_report",
        "artifact_path": "/tmp/semantic_bootstrap_candidate_report.json",
    }


def active_ontology_snapshot_payload(*, snapshot_id=None) -> dict:
    snapshot_id = snapshot_id or uuid4()
    now = datetime.now(UTC).isoformat()
    return {
        "snapshot_id": str(snapshot_id),
        "ontology_name": "portable_upper_ontology",
        "ontology_version": "portable-upper-ontology-v1",
        "upper_ontology_version": "portable-upper-ontology-v1",
        "sha256": "ontology-sha",
        "source_kind": "upper_seed",
        "source_task_id": None,
        "source_task_type": None,
        "concept_count": 0,
        "category_count": 0,
        "relation_count": 1,
        "relation_keys": ["document_mentions_concept"],
        "created_at": now,
        "activated_at": now,
    }


def initialize_ontology_output_payload(*, artifact_id=None) -> dict:
    return {
        "snapshot": active_ontology_snapshot_payload(),
        "success_metrics": [],
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "active_ontology_snapshot",
        "artifact_path": "/tmp/active_ontology_snapshot.json",
    }


def draft_ontology_output_payload(
    *,
    source_task_id,
    source_task_type: str,
    artifact_id=None,
) -> dict:
    return {
        "draft": {
            "base_snapshot_id": str(uuid4()),
            "base_ontology_version": "portable-upper-ontology-v1",
            "proposed_ontology_version": "portable-upper-ontology-v1.1",
            "upper_ontology_version": "portable-upper-ontology-v1",
            "source_task_id": str(source_task_id),
            "source_task_type": source_task_type,
            "rationale": "Extend the portable ontology from corpus evidence.",
            "document_ids": [str(uuid4())],
            "operations": [
                {
                    "operation_id": "op-1",
                    "operation_type": "add_concept",
                    "concept_key": "incident_response_latency",
                    "preferred_label": "Incident Response Latency",
                    "source_issue_ids": ["issue-1"],
                    "rationale": "Derived from corpus evidence.",
                }
            ],
            "effective_ontology": {
                "registry_name": "portable_upper_ontology",
                "registry_version": "portable-upper-ontology-v1.1",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "categories": [],
                "concepts": [],
                "relations": [
                    {
                        "relation_key": "document_mentions_concept",
                        "preferred_label": "Document Mentions Concept",
                    }
                ],
            },
            "success_metrics": [],
        },
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "ontology_extension_draft",
        "artifact_path": "/tmp/ontology_extension_draft.json",
    }


def verify_draft_ontology_output_payload(*, draft_task_id, artifact_id=None) -> dict:
    now = datetime.now(UTC).isoformat()
    draft_output = draft_ontology_output_payload(
        source_task_id=uuid4(),
        source_task_type="discover_semantic_bootstrap_candidates",
    )["draft"]
    return {
        "draft": draft_output,
        "document_deltas": [],
        "summary": {
            "document_count": 1,
            "improved_document_count": 1,
            "regressed_document_count": 0,
        },
        "success_metrics": [],
        "verification": {
            "verification_id": str(uuid4()),
            "target_task_id": str(draft_task_id),
            "verification_task_id": str(uuid4()),
            "verifier_type": "ontology_extension_gate",
            "outcome": "passed",
            "metrics": {"improved_document_count": 1, "regressed_document_count": 0},
            "reasons": [],
            "details": {},
            "created_at": now,
            "completed_at": now,
        },
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "ontology_extension_verification",
        "artifact_path": "/tmp/ontology_extension_verification.json",
    }


def apply_ontology_output_payload(
    *,
    draft_task_id,
    verification_task_id,
    artifact_id=None,
) -> dict:
    return {
        "draft_task_id": str(draft_task_id),
        "verification_task_id": str(verification_task_id),
        "applied_snapshot_id": str(uuid4()),
        "applied_ontology_version": "portable-upper-ontology-v1.1",
        "applied_ontology_sha256": "applied-ontology-sha",
        "upper_ontology_version": "portable-upper-ontology-v1",
        "reason": "Publish the verified ontology extension.",
        "applied_operations": [
            {
                "operation_id": "op-1",
                "operation_type": "add_concept",
                "concept_key": "incident_response_latency",
                "preferred_label": "Incident Response Latency",
                "source_issue_ids": ["issue-1"],
                "rationale": "Derived from corpus evidence.",
            }
        ],
        "success_metrics": [],
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "applied_ontology_extension",
        "artifact_path": "/tmp/applied_ontology_extension.json",
    }
