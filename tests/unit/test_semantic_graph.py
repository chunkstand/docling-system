from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.semantics import (
    DocumentSemanticPassResponse,
    SemanticAssertionCategoryBindingResponse,
    SemanticAssertionEvidenceResponse,
    SemanticAssertionResponse,
    SemanticConceptCategoryBindingResponse,
)
from app.services.semantic_graph import (
    build_shadow_semantic_graph,
    draft_graph_promotions,
    evaluate_semantic_relation_extractor,
    graph_memory_for_brief,
    triage_semantic_graph_disagreements,
    verify_draft_graph_promotions,
)


class FakeSession:
    def __init__(self) -> None:
        self.graph_state = None
        self.graph_snapshot = None

    def get(self, model, key):
        if model.__name__ == "WorkspaceSemanticGraphState":
            return self.graph_state if key == "default" else None
        if model.__name__ == "SemanticGraphSnapshot":
            return (
                self.graph_snapshot
                if self.graph_snapshot and self.graph_snapshot.id == key
                else None
            )
        return None


def _semantic_pass(
    *,
    document_id,
    run_id,
    concepts: list[tuple[str, str]],
    shared_excerpt: str | None = None,
) -> DocumentSemanticPassResponse:
    now = datetime.now(UTC)
    concept_bindings = []
    assertions = []
    for index, (concept_key, preferred_label) in enumerate(concepts):
        assertion_id = uuid4()
        binding_id = uuid4()
        evidence_id = uuid4()
        concept_bindings.append(
            SemanticConceptCategoryBindingResponse(
                binding_id=uuid4(),
                concept_key=concept_key,
                category_key="integration_governance",
                category_label="Integration Governance",
                binding_type="concept_category",
                created_from="registry",
                review_status="approved",
                details={},
            )
        )
        assertions.append(
            SemanticAssertionResponse(
                assertion_id=assertion_id,
                concept_key=concept_key,
                preferred_label=preferred_label,
                scope_note=None,
                assertion_kind="concept_mention",
                epistemic_status="observed",
                context_scope="document_run",
                review_status="approved",
                matched_terms=[preferred_label.lower()],
                source_types=["chunk", "table"] if index == 0 else ["chunk"],
                evidence_count=1,
                confidence=0.95,
                details={},
                category_bindings=[
                    SemanticAssertionCategoryBindingResponse(
                        binding_id=binding_id,
                        category_key="integration_governance",
                        category_label="Integration Governance",
                        binding_type="assertion_category",
                        created_from="derived",
                        review_status="approved",
                        details={},
                    )
                ],
                evidence=[
                    SemanticAssertionEvidenceResponse(
                        evidence_id=evidence_id,
                        source_type="chunk",
                        chunk_id=uuid4(),
                        table_id=None,
                        figure_id=None,
                        page_from=1,
                        page_to=1,
                        matched_terms=[preferred_label.lower()],
                        excerpt=shared_excerpt
                        or f"{preferred_label} remains active in the current policy set.",
                        source_label="Section 1",
                        source_artifact_api_path=f"/documents/{document_id}/chunks/{index + 1}",
                        source_artifact_sha256=f"sha-{concept_key}",
                        details={},
                    )
                ],
            )
        )
    return DocumentSemanticPassResponse(
        semantic_pass_id=uuid4(),
        document_id=document_id,
        run_id=run_id,
        ontology_snapshot_id=uuid4(),
        upper_ontology_version="portable-upper-ontology-v1",
        status="completed",
        registry_version="portable-upper-ontology-v1",
        registry_sha256="ontology-sha",
        extractor_version="semantics_sidecar_v2_1",
        artifact_schema_version="2.1",
        baseline_run_id=None,
        baseline_semantic_pass_id=None,
        has_json_artifact=True,
        has_yaml_artifact=True,
        artifact_json_sha256="json-sha",
        artifact_yaml_sha256="yaml-sha",
        assertion_count=len(assertions),
        evidence_count=len(assertions),
        fact_count=0,
        summary={"concept_keys": [concept for concept, _label in concepts]},
        evaluation_status="completed",
        evaluation_fixture_name=None,
        evaluation_version=2,
        evaluation_summary={},
        continuity_summary={},
        error_message=None,
        created_at=now,
        completed_at=now,
        concept_category_bindings=concept_bindings,
        assertions=assertions,
    )


def _ontology_snapshot():
    return SimpleNamespace(
        id=uuid4(),
        ontology_version="portable-upper-ontology-v1",
        sha256="ontology-sha",
        upper_ontology_version="portable-upper-ontology-v1",
        payload_json={
            "registry_name": "portable_upper_ontology",
            "registry_version": "portable-upper-ontology-v1",
            "upper_ontology_version": "portable-upper-ontology-v1",
            "categories": [],
            "concepts": [],
            "relations": [
                {
                    "relation_key": "document_mentions_concept",
                    "preferred_label": "Document Mentions Concept",
                    "domain_entity_types": ["document"],
                    "range_entity_types": ["concept"],
                    "symmetric": False,
                    "allow_literal_object": False,
                },
                {
                    "relation_key": "concept_related_to_concept",
                    "preferred_label": "Concept Related To Concept",
                    "domain_entity_types": ["concept"],
                    "range_entity_types": ["concept"],
                    "symmetric": True,
                    "allow_literal_object": False,
                    "inverse_relation_key": "concept_related_to_concept",
                },
                {
                    "relation_key": "concept_depends_on_concept",
                    "preferred_label": "Concept Depends On Concept",
                    "domain_entity_types": ["concept"],
                    "range_entity_types": ["concept"],
                    "symmetric": False,
                    "allow_literal_object": False,
                    "inverse_relation_key": "concept_enables_concept",
                },
                {
                    "relation_key": "concept_enables_concept",
                    "preferred_label": "Concept Enables Concept",
                    "domain_entity_types": ["concept"],
                    "range_entity_types": ["concept"],
                    "symmetric": False,
                    "allow_literal_object": False,
                    "inverse_relation_key": "concept_depends_on_concept",
                },
            ],
        },
    )


def test_build_shadow_semantic_graph_emits_traceable_edges(monkeypatch) -> None:
    session = FakeSession()
    document_id_one = uuid4()
    document_id_two = uuid4()
    semantic_passes = {
        document_id_one: _semantic_pass(
            document_id=document_id_one,
            run_id=uuid4(),
            concepts=[
                ("integration_threshold", "Integration Threshold"),
                ("integration_guardrail", "Integration Guardrail"),
            ],
        ),
        document_id_two: _semantic_pass(
            document_id=document_id_two,
            run_id=uuid4(),
            concepts=[
                ("integration_threshold", "Integration Threshold"),
            ],
        ),
    }
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_pass_detail",
        lambda _session, document_id: semantic_passes[document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_ontology_snapshot",
        lambda _session: _ontology_snapshot(),
    )

    shadow_graph = build_shadow_semantic_graph(
        session,
        document_ids=[document_id_one, document_id_two],
        relation_extractor_name="relation_ranker_v1",
        minimum_review_status="approved",
        min_shared_documents=2,
        score_threshold=0.3,
    )

    assert shadow_graph["node_count"] == 2
    assert shadow_graph["edge_count"] == 1
    edge = shadow_graph["edges"][0]
    assert edge["epistemic_status"] == "shadow_candidate"
    assert edge["review_status"] == "candidate"
    assert edge["support_refs"]
    assert any(
        metric["metric_key"] == "semantic_integrity" and metric["passed"]
        for metric in shadow_graph["success_metrics"]
    )


def test_evaluate_semantic_relation_extractor_improves_expected_recall(monkeypatch) -> None:
    session = FakeSession()
    document_id_one = uuid4()
    document_id_two = uuid4()
    semantic_passes = {
        document_id_one: _semantic_pass(
            document_id=document_id_one,
            run_id=uuid4(),
            concepts=[
                ("integration_threshold", "Integration Threshold"),
                ("integration_guardrail", "Integration Guardrail"),
            ],
        ),
        document_id_two: _semantic_pass(
            document_id=document_id_two,
            run_id=uuid4(),
            concepts=[("integration_threshold", "Integration Threshold")],
        ),
    }
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_pass_detail",
        lambda _session, document_id: semantic_passes[document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_ontology_snapshot",
        lambda _session: _ontology_snapshot(),
    )

    evaluation = evaluate_semantic_relation_extractor(
        session,
        document_ids=[document_id_one, document_id_two],
        baseline_extractor_name="cooccurrence_v1",
        candidate_extractor_name="relation_ranker_v1",
        minimum_review_status="approved",
        baseline_min_shared_documents=2,
        candidate_score_threshold=0.3,
        expected_min_shared_documents=1,
    )

    assert evaluation["summary"]["expected_edge_count"] == 1
    assert evaluation["summary"]["baseline_expected_recall"] == 0.0
    assert evaluation["summary"]["candidate_expected_recall"] == 1.0
    assert any(
        metric["metric_key"] == "bitter_lesson_alignment" and metric["passed"]
        for metric in evaluation["success_metrics"]
    )


def test_build_shadow_semantic_graph_emits_typed_dependency_edges(monkeypatch) -> None:
    session = FakeSession()
    document_id = uuid4()
    semantic_passes = {
        document_id: _semantic_pass(
            document_id=document_id,
            run_id=uuid4(),
            concepts=[
                ("integration_owner", "Integration Owner"),
                ("integration_threshold", "Integration Threshold"),
            ],
            shared_excerpt=(
                "Integration Owner depends on Integration Threshold for every rollout."
            ),
        ),
    }
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_pass_detail",
        lambda _session, current_document_id: semantic_passes[current_document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_ontology_snapshot",
        lambda _session: _ontology_snapshot(),
    )

    shadow_graph = build_shadow_semantic_graph(
        session,
        document_ids=[document_id],
        relation_extractor_name="relation_ranker_v1",
        minimum_review_status="approved",
        min_shared_documents=2,
        score_threshold=0.45,
    )

    dependency_edge = next(
        edge
        for edge in shadow_graph["edges"]
        if edge["relation_key"] == "concept_depends_on_concept"
    )
    assert dependency_edge["subject_entity_key"] == "concept:integration_owner"
    assert dependency_edge["object_entity_key"] == "concept:integration_threshold"
    assert dependency_edge["relation_label"] == "Concept Depends On Concept"
    assert dependency_edge["details"]["cue_match_count"] >= 1


def test_triage_draft_and_verify_graph_promotions(monkeypatch) -> None:
    session = FakeSession()
    ontology_snapshot = _ontology_snapshot()
    document_id_one = uuid4()
    document_id_two = uuid4()
    semantic_passes = {
        document_id_one: _semantic_pass(
            document_id=document_id_one,
            run_id=uuid4(),
            concepts=[
                ("integration_threshold", "Integration Threshold"),
                ("integration_guardrail", "Integration Guardrail"),
            ],
        ),
        document_id_two: _semantic_pass(
            document_id=document_id_two,
            run_id=uuid4(),
            concepts=[("integration_threshold", "Integration Threshold")],
        ),
    }
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_pass_detail",
        lambda _session, document_id: semantic_passes[document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_ontology_snapshot",
        lambda _session: ontology_snapshot,
    )

    evaluation = evaluate_semantic_relation_extractor(
        session,
        document_ids=[document_id_one, document_id_two],
        baseline_extractor_name="cooccurrence_v1",
        candidate_extractor_name="relation_ranker_v1",
        minimum_review_status="approved",
        baseline_min_shared_documents=2,
        candidate_score_threshold=0.3,
        expected_min_shared_documents=1,
    )
    disagreement_report = triage_semantic_graph_disagreements(
        evaluation,
        min_score=0.3,
        expected_only=True,
    )
    draft = draft_graph_promotions(
        session,
        source_payload=disagreement_report,
        source_task_id=uuid4(),
        source_task_type="triage_semantic_graph_disagreements",
        proposed_graph_version=None,
        rationale="promote approved cross-document graph memory",
        edge_ids=[],
        min_score=0.3,
    )
    summary, _metrics, reasons, outcome, success_metrics = verify_draft_graph_promotions(
        session,
        draft,
        min_supporting_document_count=1,
        max_conflict_count=0,
        require_current_ontology_snapshot=True,
    )

    assert disagreement_report["issue_count"] == 1
    assert draft["promoted_edges"]
    assert draft["promoted_edges"][0]["relation_label"] == "Concept Related To Concept"
    assert outcome == "passed"
    assert not reasons
    assert summary["supported_edge_count"] == 1
    assert any(
        metric["metric_key"] == "semantic_integrity" and metric["passed"]
        for metric in success_metrics
    )


def test_verify_draft_graph_promotions_rejects_constraint_violations(monkeypatch) -> None:
    session = FakeSession()
    ontology_snapshot = _ontology_snapshot()
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_ontology_snapshot",
        lambda _session: ontology_snapshot,
    )

    summary, _metrics, reasons, outcome, _success_metrics = verify_draft_graph_promotions(
        session,
        {
            "ontology_snapshot_id": ontology_snapshot.id,
            "promoted_edges": [
                {
                    "edge_id": "graph_edge:concept_depends_on_concept:document:a:concept:b",
                    "relation_key": "concept_depends_on_concept",
                    "relation_label": "Concept Depends On Concept",
                    "subject_entity_key": "document:123",
                    "subject_label": "Bad Subject",
                    "object_entity_key": "concept:integration_threshold",
                    "object_label": "Integration Threshold",
                    "support_refs": [{"support_ref_id": "support:1"}],
                    "supporting_document_ids": [uuid4()],
                }
            ],
        },
        min_supporting_document_count=1,
        max_conflict_count=0,
        require_current_ontology_snapshot=True,
    )

    assert outcome == "failed"
    assert summary["constraint_violation_count"] == 1
    assert any("relation constraints" in reason for reason in reasons)


def test_graph_memory_for_brief_returns_related_concepts_from_active_snapshot() -> None:
    session = FakeSession()
    graph_snapshot_id = uuid4()
    session.graph_state = SimpleNamespace(
        workspace_key="default",
        active_graph_snapshot_id=graph_snapshot_id,
    )
    session.graph_snapshot = SimpleNamespace(
        id=graph_snapshot_id,
        graph_version="portable-upper-ontology-v1.graph.1",
        payload_json={
            "edges": [
                {
                    "edge_id": (
                        "graph_edge:concept_related_to_concept:"
                        "concept:integration_threshold:concept:integration_guardrail"
                    ),
                    "relation_key": "concept_related_to_concept",
                    "relation_label": "Concept Related To Concept",
                    "subject_entity_key": "concept:integration_threshold",
                    "subject_label": "Integration Threshold",
                    "object_entity_key": "concept:integration_guardrail",
                    "object_label": "Integration Guardrail",
                    "review_status": "approved",
                    "support_level": "supported",
                    "extractor_score": 0.62,
                    "supporting_document_ids": [uuid4()],
                    "support_refs": [{"support_ref_id": "support:1"}],
                }
            ]
        },
    )

    related_concepts, edge_refs, summary, warnings = graph_memory_for_brief(
        session,
        document_ids=session.graph_snapshot.payload_json["edges"][0]["supporting_document_ids"],
        requested_concept_keys={"integration_threshold"},
        available_concept_keys={"integration_threshold", "integration_guardrail"},
    )

    assert related_concepts == ["integration_guardrail", "integration_threshold"]
    assert edge_refs[0]["edge_id"].startswith("graph_edge:")
    assert summary["edge_count"] == 1
    assert warnings


def test_draft_graph_promotions_refreshes_existing_node_support_metadata(monkeypatch) -> None:
    session = FakeSession()
    ontology_snapshot = _ontology_snapshot()
    graph_snapshot_id = uuid4()
    document_id_one = uuid4()
    document_id_two = uuid4()
    session.graph_state = SimpleNamespace(
        workspace_key="default",
        active_graph_snapshot_id=graph_snapshot_id,
    )
    session.graph_snapshot = SimpleNamespace(
        id=graph_snapshot_id,
        graph_version="portable-upper-ontology-v1.graph.1",
        payload_json={
            "nodes": [
                {
                    "entity_key": "concept:integration_threshold",
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "category_keys": [],
                    "document_ids": [document_id_one],
                    "document_count": 1,
                    "source_types": ["chunk"],
                    "review_status_counts": {"approved": 1},
                    "assertion_count": 1,
                    "evidence_count": 1,
                }
            ],
            "edges": [],
        },
    )
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_ontology_snapshot",
        lambda _session: ontology_snapshot,
    )

    draft = draft_graph_promotions(
        session,
        source_payload={
            "edges": [
                {
                    "edge_id": (
                        "graph_edge:concept_related_to_concept:"
                        "concept:integration_threshold:concept:integration_guardrail"
                    ),
                    "relation_key": "concept_related_to_concept",
                    "relation_label": "Concept Related To Concept",
                    "subject_entity_key": "concept:integration_threshold",
                    "subject_label": "Integration Threshold",
                    "object_entity_key": "concept:integration_guardrail",
                    "object_label": "Integration Guardrail",
                    "review_status": "candidate",
                    "extractor_score": 0.74,
                    "supporting_document_ids": [document_id_two],
                    "support_refs": [
                        {
                            "support_ref_id": "support:threshold-guardrail",
                            "document_id": document_id_two,
                            "assertion_ids": [uuid4(), uuid4()],
                            "evidence_ids": [uuid4()],
                            "source_types": ["table"],
                            "shared_category_keys": [],
                        }
                    ],
                }
            ]
        },
        source_task_id=uuid4(),
        source_task_type="build_shadow_semantic_graph",
        proposed_graph_version=None,
        rationale="refresh graph memory",
        edge_ids=[],
        min_score=0.3,
    )

    threshold_node = next(
        node
        for node in draft["effective_graph"]["nodes"]
        if node["entity_key"] == "concept:integration_threshold"
    )
    assert threshold_node["document_ids"] == sorted([document_id_one, document_id_two], key=str)
    assert threshold_node["document_count"] == 2
    assert threshold_node["source_types"] == ["chunk", "table"]


def test_draft_graph_promotions_recomputes_node_review_counts_for_new_nodes(monkeypatch) -> None:
    session = FakeSession()
    ontology_snapshot = _ontology_snapshot()
    document_id_one = uuid4()
    document_id_two = uuid4()
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_ontology_snapshot",
        lambda _session: ontology_snapshot,
    )

    draft = draft_graph_promotions(
        session,
        source_payload={
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
                    "review_status": "candidate",
                    "extractor_score": 0.74,
                    "supporting_document_ids": [document_id_one],
                    "support_refs": [
                        {
                            "support_ref_id": "support:owner-threshold",
                            "document_id": document_id_one,
                            "assertion_ids": [uuid4(), uuid4()],
                            "evidence_ids": [uuid4()],
                            "source_types": ["chunk"],
                            "shared_category_keys": [],
                        }
                    ],
                },
                {
                    "edge_id": (
                        "graph_edge:concept_depends_on_concept:"
                        "concept:integration_owner:concept:integration_threshold"
                    ),
                    "relation_key": "concept_depends_on_concept",
                    "relation_label": "Concept Depends On Concept",
                    "subject_entity_key": "concept:integration_owner",
                    "subject_label": "Integration Owner",
                    "object_entity_key": "concept:integration_threshold",
                    "object_label": "Integration Threshold",
                    "review_status": "candidate",
                    "extractor_score": 0.83,
                    "supporting_document_ids": [document_id_two],
                    "support_refs": [
                        {
                            "support_ref_id": "support:owner-depends-threshold",
                            "document_id": document_id_two,
                            "assertion_ids": [uuid4(), uuid4()],
                            "evidence_ids": [uuid4()],
                            "source_types": ["table"],
                            "shared_category_keys": [],
                        }
                    ],
                },
            ]
        },
        source_task_id=uuid4(),
        source_task_type="build_shadow_semantic_graph",
        proposed_graph_version=None,
        rationale="refresh graph memory",
        edge_ids=[],
        min_score=0.3,
    )

    owner_node = next(
        node
        for node in draft["effective_graph"]["nodes"]
        if node["entity_key"] == "concept:integration_owner"
    )
    assert owner_node["review_status_counts"] == {"approved": 2}


def test_verify_draft_graph_promotions_rejects_inverse_conflicts_in_effective_graph(
    monkeypatch,
) -> None:
    session = FakeSession()
    ontology_snapshot = _ontology_snapshot()
    monkeypatch.setattr(
        "app.services.semantic_graph.get_active_semantic_ontology_snapshot",
        lambda _session: ontology_snapshot,
    )

    summary, _metrics, reasons, outcome, _success_metrics = verify_draft_graph_promotions(
        session,
        {
            "ontology_snapshot_id": ontology_snapshot.id,
            "promoted_edges": [
                {
                    "edge_id": (
                        "graph_edge:concept_depends_on_concept:"
                        "concept:integration_owner:concept:integration_threshold"
                    ),
                    "relation_key": "concept_depends_on_concept",
                    "relation_label": "Concept Depends On Concept",
                    "subject_entity_key": "concept:integration_owner",
                    "subject_label": "Integration Owner",
                    "object_entity_key": "concept:integration_threshold",
                    "object_label": "Integration Threshold",
                    "support_refs": [{"support_ref_id": "support:1"}],
                    "supporting_document_ids": [uuid4()],
                }
            ],
            "effective_graph": {
                "edges": [
                    {
                        "edge_id": (
                            "graph_edge:concept_depends_on_concept:"
                            "concept:integration_owner:concept:integration_threshold"
                        ),
                        "relation_key": "concept_depends_on_concept",
                        "relation_label": "Concept Depends On Concept",
                        "subject_entity_key": "concept:integration_owner",
                        "subject_label": "Integration Owner",
                        "object_entity_key": "concept:integration_threshold",
                        "object_label": "Integration Threshold",
                    },
                    {
                        "edge_id": (
                            "graph_edge:concept_enables_concept:"
                            "concept:integration_threshold:concept:integration_owner"
                        ),
                        "relation_key": "concept_enables_concept",
                        "relation_label": "Concept Enables Concept",
                        "subject_entity_key": "concept:integration_threshold",
                        "subject_label": "Integration Threshold",
                        "object_entity_key": "concept:integration_owner",
                        "object_label": "Integration Owner",
                    },
                ]
            },
        },
        min_supporting_document_count=1,
        max_conflict_count=0,
        require_current_ontology_snapshot=True,
    )

    assert outcome == "failed"
    assert summary["conflict_count"] == 2
    assert any("conflicting graph edges" in reason for reason in reasons)
