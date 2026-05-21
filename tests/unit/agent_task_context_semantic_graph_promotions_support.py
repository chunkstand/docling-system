from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.public.agent_tasks import AgentTaskArtifact


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


def graph_support_ref_payload(*, document_id=None) -> dict:
    return {
        "support_ref_id": f"graph-support:{uuid4()}",
        "document_id": str(document_id or uuid4()),
        "run_id": str(uuid4()),
        "semantic_pass_id": str(uuid4()),
        "assertion_ids": [str(uuid4()), str(uuid4())],
        "evidence_ids": [str(uuid4())],
        "concept_keys": ["integration_owner", "integration_threshold"],
        "source_types": ["chunk", "table"],
        "shared_category_keys": ["integration_governance"],
        "score": 0.72,
    }


def shadow_graph_output_payload(*, artifact_id=None) -> dict:
    document_ids = [uuid4(), uuid4()]
    support_refs = [
        graph_support_ref_payload(document_id=document_id) for document_id in document_ids
    ]
    return {
        "shadow_graph": {
            "graph_name": "workspace_semantic_graph",
            "graph_version": "portable-upper-ontology-v1.graph.1",
            "ontology_snapshot_id": str(uuid4()),
            "ontology_version": "portable-upper-ontology-v1",
            "ontology_sha256": "ontology-sha",
            "upper_ontology_version": "portable-upper-ontology-v1",
            "extractor": {
                "extractor_name": "relation_ranker_v1",
                "backing_model": "hashing_embedding_v1",
                "match_strategy": "relation_ranker_v1",
                "shadow_mode": True,
                "provider_name": "local_hashing",
            },
            "shadow_mode": True,
            "minimum_review_status": "approved",
            "document_ids": [str(document_id) for document_id in document_ids],
            "document_count": 2,
            "document_refs": [],
            "node_count": 2,
            "edge_count": 1,
            "nodes": [
                {
                    "entity_key": "concept:integration_owner",
                    "concept_key": "integration_owner",
                    "preferred_label": "Integration Owner",
                },
                {
                    "entity_key": "concept:integration_threshold",
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                },
            ],
            "edges": [
                {
                    "edge_id": (
                        "graph_edge:concept_related_to_concept:"
                        "concept:integration_owner:concept:integration_threshold"
                    ),
                    "relation_key": "concept_related_to_concept",
                    "relation_label": "Concept Related To Concept",
                    "subject_entity_key": "concept:integration_owner",
                    "subject_label": "Integration Owner",
                    "object_entity_key": "concept:integration_threshold",
                    "object_label": "Integration Threshold",
                    "epistemic_status": "shadow_candidate",
                    "review_status": "candidate",
                    "support_level": "supported",
                    "extractor_name": "relation_ranker_v1",
                    "extractor_score": 0.72,
                    "supporting_document_ids": [str(document_id) for document_id in document_ids],
                    "supporting_document_count": 2,
                    "supporting_assertion_count": 4,
                    "supporting_evidence_count": 2,
                    "support_refs": support_refs,
                }
            ],
            "summary": {"relation_key_counts": {"concept_related_to_concept": 1}},
            "success_metrics": [],
        },
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "shadow_semantic_graph",
        "artifact_path": "/tmp/shadow_semantic_graph.json",
    }


def graph_evaluation_output_payload(*, artifact_id=None) -> dict:
    shadow_output = shadow_graph_output_payload()
    edge = shadow_output["shadow_graph"]["edges"][0]
    return {
        "baseline_extractor": {
            "extractor_name": "cooccurrence_v1",
            "backing_model": "none",
            "match_strategy": "cooccurrence_min_shared_documents_v1",
            "shadow_mode": True,
            "provider_name": None,
        },
        "candidate_extractor": {
            "extractor_name": "relation_ranker_v1",
            "backing_model": "hashing_embedding_v1",
            "match_strategy": "relation_ranker_v1",
            "shadow_mode": True,
            "provider_name": "local_hashing",
        },
        "ontology_snapshot_id": str(uuid4()),
        "ontology_version": "portable-upper-ontology-v1.1",
        "document_refs": [],
        "edge_reports": [
            {
                "edge_id": edge["edge_id"],
                "relation_key": edge["relation_key"],
                "subject_entity_key": edge["subject_entity_key"],
                "subject_label": edge["subject_label"],
                "object_entity_key": edge["object_entity_key"],
                "object_label": edge["object_label"],
                "expected_edge": True,
                "in_live_graph": False,
                "baseline_found": False,
                "candidate_found": True,
                "baseline_score": 0.0,
                "candidate_score": 0.72,
                "supporting_document_ids": edge["supporting_document_ids"],
                "support_refs": edge["support_refs"],
            }
        ],
        "summary": {
            "document_count": 2,
            "expected_edge_count": 1,
            "baseline_expected_recall": 0.0,
            "candidate_expected_recall": 1.0,
            "candidate_only_edge_count": 1,
            "graph_memory_compaction_ratio": 2.0,
            "document_specific_rule_count_delta": 0,
            "traceable_candidate_edge_ratio": 1.0,
            "unsupported_candidate_edge_count": 0,
        },
        "success_metrics": [],
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "semantic_relation_evaluation",
        "artifact_path": "/tmp/semantic_relation_evaluation.json",
    }


def graph_triage_output_payload(*, evaluation_task_id, verification_id, artifact_id=None) -> dict:
    evaluation = graph_evaluation_output_payload()
    edge = evaluation["edge_reports"][0]
    return {
        "evaluation_task_id": str(evaluation_task_id),
        "disagreement_report": {
            "issue_count": 1,
            "issues": [
                {
                    "issue_id": "graph-issue:1",
                    "edge_id": edge["edge_id"],
                    "relation_key": edge["relation_key"],
                    "subject_entity_key": edge["subject_entity_key"],
                    "subject_label": edge["subject_label"],
                    "object_entity_key": edge["object_entity_key"],
                    "object_label": edge["object_label"],
                    "severity": "high",
                    "expected_edge": True,
                    "in_live_graph": False,
                    "baseline_found": False,
                    "candidate_found": True,
                    "candidate_score": 0.72,
                    "supporting_document_ids": edge["supporting_document_ids"],
                    "support_refs": edge["support_refs"],
                    "summary": "Promote the cross-document graph edge.",
                    "details": {},
                }
            ],
            "recommended_followups": [
                {
                    "followup_kind": "draft_graph_promotions",
                    "reason": "candidate_expected_edge_missing_from_live_graph",
                    "edge_id": edge["edge_id"],
                }
            ],
            "success_metrics": [],
        },
        "verification": {
            "verification_id": str(verification_id),
            "target_task_id": str(uuid4()),
            "verification_task_id": str(uuid4()),
            "verifier_type": "semantic_graph_shadow_gate",
            "outcome": "passed",
            "metrics": {"issue_count": 1},
            "reasons": [],
            "details": {"issue_count": 1},
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        },
        "recommendation": {"next_action": "draft_graph_promotions", "priority": "high"},
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "semantic_graph_disagreement_report",
        "artifact_path": "/tmp/semantic_graph_disagreement_report.json",
    }


def draft_graph_promotions_output_payload(
    *,
    source_task_id,
    source_task_type: str,
    artifact_id=None,
) -> dict:
    shadow_output = shadow_graph_output_payload()
    promoted_edge = {
        **shadow_output["shadow_graph"]["edges"][0],
        "epistemic_status": "approved_graph",
        "review_status": "approved",
    }
    return {
        "draft": {
            "base_snapshot_id": None,
            "base_graph_version": None,
            "proposed_graph_version": "portable-upper-ontology-v1.graph.1",
            "ontology_snapshot_id": shadow_output["shadow_graph"]["ontology_snapshot_id"],
            "ontology_version": "portable-upper-ontology-v1",
            "ontology_sha256": "ontology-sha",
            "source_task_id": str(source_task_id),
            "source_task_type": source_task_type,
            "rationale": "Promote approved cross-document graph memory.",
            "promoted_edges": [promoted_edge],
            "effective_graph": {
                **shadow_output["shadow_graph"],
                "graph_version": "portable-upper-ontology-v1.graph.1",
                "shadow_mode": False,
                "extractor": {
                    "extractor_name": "approved_graph_memory",
                    "backing_model": "none",
                    "match_strategy": "approved_promotion",
                    "shadow_mode": False,
                    "provider_name": None,
                },
                "edges": [promoted_edge],
            },
            "success_metrics": [],
        },
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "semantic_graph_promotion_draft",
        "artifact_path": "/tmp/semantic_graph_promotion_draft.json",
    }


def verify_graph_promotions_output_payload(
    *,
    draft_task_id,
    verification_task_id,
    artifact_id=None,
) -> dict:
    return {
        "draft": draft_graph_promotions_output_payload(
            source_task_id=uuid4(),
            source_task_type="triage_semantic_graph_disagreements",
        )["draft"],
        "summary": {
            "promoted_edge_count": 1,
            "supported_edge_count": 1,
            "stale_edge_count": 0,
            "unsupported_edge_count": 0,
            "ontology_mismatch_count": 0,
            "conflict_count": 0,
        },
        "success_metrics": [],
        "verification": {
            "verification_id": str(uuid4()),
            "target_task_id": str(draft_task_id),
            "verification_task_id": str(verification_task_id),
            "verifier_type": "semantic_graph_promotion_gate",
            "outcome": "passed",
            "metrics": {"supported_edge_count": 1},
            "reasons": [],
            "details": {"supported_edge_count": 1},
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        },
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "semantic_graph_promotion_verification",
        "artifact_path": "/tmp/semantic_graph_promotion_verification.json",
    }


def apply_graph_promotions_output_payload(
    *,
    draft_task_id,
    verification_task_id,
    artifact_id=None,
) -> dict:
    return {
        "draft_task_id": str(draft_task_id),
        "verification_task_id": str(verification_task_id),
        "applied_snapshot_id": str(uuid4()),
        "applied_graph_version": "portable-upper-ontology-v1.graph.1",
        "applied_graph_sha256": "graph-sha",
        "ontology_snapshot_id": str(uuid4()),
        "reason": "Publish the verified semantic graph memory snapshot.",
        "applied_edge_count": 1,
        "success_metrics": [],
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "applied_semantic_graph_snapshot",
        "artifact_path": "/tmp/applied_semantic_graph_snapshot.json",
    }
