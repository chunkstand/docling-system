from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from app.db.models import Document
from app.schemas.semantics import (
    DocumentSemanticPassResponse,
    SemanticAssertionCategoryBindingResponse,
    SemanticAssertionEvidenceResponse,
    SemanticAssertionResponse,
    SemanticConceptCategoryBindingResponse,
)
from app.services.semantic_generation import (
    draft_semantic_grounded_document,
    prepare_semantic_generation_brief,
    verify_semantic_grounded_document,
)


class FakeSession:
    def __init__(self, documents: dict) -> None:
        self.documents = documents

    def get(self, model, key):
        if model.__name__ == "Document":
            return self.documents.get(key)
        return None


def _document(*, document_id, source_filename: str, title: str) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=document_id,
        source_filename=source_filename,
        source_path=f"/tmp/{source_filename}",
        sha256=f"sha-{source_filename}",
        mime_type="application/pdf",
        title=title,
        page_count=1,
        active_run_id=uuid4(),
        latest_run_id=uuid4(),
        created_at=now,
        updated_at=now,
    )


def _semantic_pass(
    *,
    document_id,
    run_id,
    review_status: str,
    source_filename: str,
    concept_key: str = "integration_threshold",
    preferred_label: str = "Integration Threshold",
    category_key: str = "integration_governance",
    category_label: str = "Integration Governance",
) -> DocumentSemanticPassResponse:
    now = datetime.now(UTC)
    matched_term = preferred_label.lower()
    assertion_id = uuid4()
    evidence = [
        SemanticAssertionEvidenceResponse(
            evidence_id=uuid4(),
            source_type="chunk",
            chunk_id=uuid4(),
            table_id=None,
            figure_id=None,
            page_from=1,
            page_to=1,
            matched_terms=[matched_term],
            excerpt=f"{preferred_label} guidance remains in force.",
            source_label="Section 1",
            source_artifact_api_path="/documents/example/chunks/1",
            source_artifact_sha256="chunk-sha",
            details={},
        ),
        SemanticAssertionEvidenceResponse(
            evidence_id=uuid4(),
            source_type="table",
            chunk_id=None,
            table_id=uuid4(),
            figure_id=None,
            page_from=1,
            page_to=1,
            matched_terms=[matched_term],
            excerpt=f"Tier | {preferred_label}",
            source_label="Threshold Matrix",
            source_artifact_api_path="/documents/example/tables/1",
            source_artifact_sha256="table-sha",
            details={},
        ),
    ]
    return DocumentSemanticPassResponse(
        semantic_pass_id=uuid4(),
        document_id=document_id,
        run_id=run_id,
        status="completed",
        registry_version="semantics-layer-foundation-alpha.3",
        registry_sha256="registry-sha",
        extractor_version="semantics_sidecar_v2_1",
        artifact_schema_version="2.1",
        baseline_run_id=None,
        baseline_semantic_pass_id=None,
        has_json_artifact=True,
        has_yaml_artifact=True,
        artifact_json_sha256="json-sha",
        artifact_yaml_sha256="yaml-sha",
        assertion_count=1,
        evidence_count=2,
        summary={"concept_keys": [concept_key]},
        evaluation_status="completed",
        evaluation_fixture_name=f"{source_filename}-fixture",
        evaluation_version=2,
        evaluation_summary={
            "all_expectations_passed": True,
            "expectations": [{"concept_key": concept_key, "passed": True}],
        },
        continuity_summary={"reason": "steady_state", "change_count": 0},
        error_message=None,
        created_at=now,
        completed_at=now,
        concept_category_bindings=[
            SemanticConceptCategoryBindingResponse(
                binding_id=uuid4(),
                concept_key=concept_key,
                category_key=category_key,
                category_label=category_label,
                binding_type="concept_category",
                created_from="registry",
                review_status=review_status,
                details={},
            )
        ],
        assertions=[
            SemanticAssertionResponse(
                assertion_id=assertion_id,
                concept_key=concept_key,
                preferred_label=preferred_label,
                scope_note=None,
                assertion_kind="concept_mention",
                epistemic_status="observed",
                context_scope="document_run",
                review_status=review_status,
                matched_terms=[matched_term],
                source_types=["chunk", "table"],
                evidence_count=len(evidence),
                confidence=0.9,
                details={},
                category_bindings=[
                    SemanticAssertionCategoryBindingResponse(
                        binding_id=uuid4(),
                        category_key=category_key,
                        category_label=category_label,
                        binding_type="assertion_category",
                        created_from="derived",
                        review_status=review_status,
                        details={},
                    )
                ],
                evidence=evidence,
            )
        ],
    )


def test_prepare_semantic_generation_brief_builds_cross_document_dossier(monkeypatch) -> None:
    document_id_one = uuid4()
    document_id_two = uuid4()
    documents = {
        document_id_one: _document(
            document_id=document_id_one,
            source_filename="integration-one.pdf",
            title="Integration One",
        ),
        document_id_two: _document(
            document_id=document_id_two,
            source_filename="integration-two.pdf",
            title="Integration Two",
        ),
    }
    passes = {
        document_id_one: _semantic_pass(
            document_id=document_id_one,
            run_id=uuid4(),
            review_status="approved",
            source_filename="integration-one.pdf",
        ),
        document_id_two: _semantic_pass(
            document_id=document_id_two,
            run_id=uuid4(),
            review_status="candidate",
            source_filename="integration-two.pdf",
        ),
    }
    monkeypatch.setattr(
        "app.services.semantic_generation.get_active_semantic_pass_detail",
        lambda session, document_id: passes[document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_generation.list_document_semantic_facts",
        lambda session, document_id: [],
    )

    brief = prepare_semantic_generation_brief(
        FakeSession(documents),
        title="Integration Governance Brief",
        goal="Summarize the knowledge base guidance on integration governance.",
        audience="Operators",
        document_ids=[document_id_one, document_id_two],
        concept_keys=[],
        category_keys=[],
        target_length="medium",
        review_policy="allow_candidate_with_disclosure",
    )

    assert brief["document_kind"] == "knowledge_brief"
    assert len(brief["document_refs"]) == 2
    assert len(brief["semantic_dossier"]) == 1
    assert brief["semantic_dossier"][0]["document_count"] == 2
    assert brief["claim_candidates"][0]["review_policy_status"] == "mixed_support_disclosed"
    assert brief["claim_candidates"][0]["evidence_labels"] == ["E1", "E2", "E3"]
    assert brief["sections"][0]["focus_concept_keys"] == ["integration_threshold"]
    assert any(metric["stakeholder"] == "Lopopolo" for metric in brief["success_metrics"])


def test_prepare_semantic_generation_brief_keeps_shadow_candidates_additive(monkeypatch) -> None:
    document_id = uuid4()
    documents = {
        document_id: _document(
            document_id=document_id,
            source_filename="integration-one.pdf",
            title="Integration One",
        )
    }
    passes = {
        document_id: _semantic_pass(
            document_id=document_id,
            run_id=uuid4(),
            review_status="approved",
            source_filename="integration-one.pdf",
        )
    }
    monkeypatch.setattr(
        "app.services.semantic_generation.get_active_semantic_pass_detail",
        lambda session, requested_document_id: passes[requested_document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_generation.list_document_semantic_facts",
        lambda session, document_id: [],
    )
    monkeypatch.setattr(
        "app.services.semantic_generation.collect_shadow_candidates_for_brief",
        lambda *args, **kwargs: (
            [
                {
                    "concept_key": "integration_owner",
                    "preferred_label": "Integration Owner",
                    "max_score": 0.71,
                    "source_count": 1,
                    "source_types": ["chunk"],
                    "category_keys": ["integration_governance"],
                    "expected_by_evaluation": True,
                    "evidence_refs": [
                        {
                            "source_type": "chunk",
                            "source_locator": "chunk-1",
                            "page_from": 1,
                            "page_to": 1,
                            "excerpt": "Owners for integration approve changes.",
                            "source_artifact_api_path": None,
                            "source_artifact_sha256": "chunk-sha",
                            "score": 0.71,
                        }
                    ],
                    "note": "Shadow candidate aligns with a semantic evaluation expectation.",
                }
            ],
            {
                "candidate_count": 1,
                "candidate_only_concept_count": 1,
                "expected_shadow_candidate_count": 1,
            },
        ),
    )

    brief = prepare_semantic_generation_brief(
        FakeSession(documents),
        title="Integration Governance Brief",
        goal="Summarize the knowledge base guidance on integration governance.",
        audience="Operators",
        document_ids=[document_id],
        concept_keys=[],
        category_keys=[],
        target_length="medium",
        review_policy="allow_candidate_with_disclosure",
        include_shadow_candidates=True,
        candidate_extractor_name="concept_ranker_v1",
        candidate_score_threshold=0.34,
        max_shadow_candidates=8,
    )

    assert brief["shadow_mode"] is True
    assert brief["shadow_candidate_extractor_name"] == "concept_ranker_v1"
    assert brief["selected_concept_keys"] == ["integration_threshold"]
    assert [row["concept_key"] for row in brief["shadow_candidates"]] == ["integration_owner"]
    assert any(
        metric["metric_key"] == "explicit_shadow_boundary"
        for metric in brief["success_metrics"]
    )


def test_prepare_semantic_generation_brief_includes_approved_fact_support(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    documents = {
        document_id: _document(
            document_id=document_id,
            source_filename="integration-one.pdf",
            title="Integration One",
        )
    }
    passes = {
        document_id: _semantic_pass(
            document_id=document_id,
            run_id=run_id,
            review_status="approved",
            source_filename="integration-one.pdf",
        )
    }
    monkeypatch.setattr(
        "app.services.semantic_generation.get_active_semantic_pass_detail",
        lambda session, requested_document_id: passes[requested_document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_generation.list_document_semantic_facts",
        lambda session, requested_document_id: [
            {
                "fact_id": uuid4(),
                "document_id": requested_document_id,
                "run_id": run_id,
                "semantic_pass_id": passes[requested_document_id].semantic_pass_id,
                "relation_key": "document_mentions_concept",
                "relation_label": "Document Mentions Concept",
                "subject_entity_key": f"document:{requested_document_id}",
                "subject_label": "Integration One",
                "object_entity_key": "concept:integration_threshold",
                "object_label": "Integration Threshold",
                "object_value_text": None,
                "review_status": "approved",
                "assertion_id": passes[requested_document_id].assertions[0].assertion_id,
                "evidence_ids": [
                    evidence.evidence_id
                    for evidence in passes[requested_document_id].assertions[0].evidence
                ],
            }
        ],
    )

    brief = prepare_semantic_generation_brief(
        FakeSession(documents),
        title="Integration Governance Brief",
        goal="Summarize the knowledge base guidance on integration governance.",
        audience="Operators",
        document_ids=[document_id],
        concept_keys=[],
        category_keys=[],
        target_length="medium",
        review_policy="approved_only",
    )
    draft = draft_semantic_grounded_document(brief, brief_task_id=uuid4())
    verification = verify_semantic_grounded_document(draft)

    assert len(brief["semantic_dossier"][0]["facts"]) == 1
    assert draft["claims"][0]["fact_ids"]
    assert draft["fact_index"][0]["relation_key"] == "document_mentions_concept"
    assert verification.verification_outcome == "passed"
    assert verification.summary["fact_ref_coverage_ratio"] == 1.0


def test_draft_and_verify_semantic_grounded_document_roundtrip(monkeypatch) -> None:
    document_id = uuid4()
    documents = {
        document_id: _document(
            document_id=document_id,
            source_filename="integration-one.pdf",
            title="Integration One",
        )
    }
    passes = {
        document_id: _semantic_pass(
            document_id=document_id,
            run_id=uuid4(),
            review_status="approved",
            source_filename="integration-one.pdf",
        )
    }
    monkeypatch.setattr(
        "app.services.semantic_generation.get_active_semantic_pass_detail",
        lambda session, requested_document_id: passes[requested_document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_generation.list_document_semantic_facts",
        lambda session, document_id: [],
    )
    brief = prepare_semantic_generation_brief(
        FakeSession(documents),
        title="Integration Governance Brief",
        goal="Summarize the knowledge base guidance on integration governance.",
        audience="Operators",
        document_ids=[document_id],
        concept_keys=[],
        category_keys=[],
        target_length="medium",
        review_policy="allow_candidate_with_disclosure",
    )

    brief_task_id = uuid4()
    draft = draft_semantic_grounded_document(
        brief,
        brief_task_id=brief_task_id,
    )

    assert draft["brief_task_id"] == brief_task_id
    assert draft["generator_name"] == "structured_fallback"
    assert "# Integration Governance Brief" in draft["markdown"]
    assert "## Evidence Appendix" in draft["markdown"]
    assert len(draft["claims"]) == 1

    verification = verify_semantic_grounded_document(draft)

    assert verification.verification_outcome == "passed"
    assert verification.summary["traceable_claim_ratio"] == 1.0
    assert verification.summary["unsupported_claim_count"] == 0


def test_verify_semantic_grounded_document_fails_when_claim_loses_evidence(monkeypatch) -> None:
    document_id = uuid4()
    documents = {
        document_id: _document(
            document_id=document_id,
            source_filename="integration-one.pdf",
            title="Integration One",
        )
    }
    passes = {
        document_id: _semantic_pass(
            document_id=document_id,
            run_id=uuid4(),
            review_status="candidate",
            source_filename="integration-one.pdf",
        )
    }
    monkeypatch.setattr(
        "app.services.semantic_generation.get_active_semantic_pass_detail",
        lambda session, requested_document_id: passes[requested_document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_generation.list_document_semantic_facts",
        lambda session, document_id: [],
    )
    brief = prepare_semantic_generation_brief(
        FakeSession(documents),
        title="Integration Governance Brief",
        goal="Summarize the knowledge base guidance on integration governance.",
        audience="Operators",
        document_ids=[document_id],
        concept_keys=[],
        category_keys=[],
        target_length="medium",
        review_policy="allow_candidate_with_disclosure",
    )
    draft = draft_semantic_grounded_document(brief, brief_task_id=uuid4())
    broken_draft = deepcopy(draft)
    broken_draft["claims"][0]["evidence_labels"] = []

    verification = verify_semantic_grounded_document(broken_draft)

    assert verification.verification_outcome == "failed"
    assert verification.summary["unsupported_claim_count"] == 1
    assert any("Unsupported claim count" in reason for reason in verification.verification_reasons)


def test_verify_semantic_grounded_document_fails_when_requested_concept_is_omitted(
    monkeypatch,
) -> None:
    document_id = uuid4()
    documents = {
        document_id: _document(
            document_id=document_id,
            source_filename="integration-one.pdf",
            title="Integration One",
        )
    }
    requested_pass = _semantic_pass(
        document_id=document_id,
        run_id=uuid4(),
        review_status="candidate",
        source_filename="integration-one.pdf",
        concept_key="integration_threshold",
        preferred_label="Integration Threshold",
    )
    category_pass = _semantic_pass(
        document_id=document_id,
        run_id=requested_pass.run_id,
        review_status="approved",
        source_filename="integration-one.pdf",
        concept_key="integration_owner",
        preferred_label="Integration Owner",
    )
    requested_pass.concept_category_bindings.extend(category_pass.concept_category_bindings)
    requested_pass.assertions.extend(category_pass.assertions)
    requested_pass.assertion_count = len(requested_pass.assertions)
    requested_pass.evidence_count = sum(
        assertion.evidence_count for assertion in requested_pass.assertions
    )
    requested_pass.summary = {
        "concept_keys": [assertion.concept_key for assertion in requested_pass.assertions]
    }
    requested_pass.evaluation_summary = {
        "all_expectations_passed": False,
        "expectations": [
            {"concept_key": "integration_threshold", "passed": False},
            {"concept_key": "integration_owner", "passed": True},
        ],
    }

    monkeypatch.setattr(
        "app.services.semantic_generation.get_active_semantic_pass_detail",
        lambda session, requested_document_id: {document_id: requested_pass}[requested_document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_generation.list_document_semantic_facts",
        lambda session, document_id: [],
    )

    brief = prepare_semantic_generation_brief(
        FakeSession(documents),
        title="Integration Governance Brief",
        goal="Summarize the knowledge base guidance on integration governance.",
        audience="Operators",
        document_ids=[document_id],
        concept_keys=["integration_threshold"],
        category_keys=["integration_governance"],
        target_length="medium",
        review_policy="approved_only",
    )
    draft = draft_semantic_grounded_document(brief, brief_task_id=uuid4())
    verification = verify_semantic_grounded_document(draft)

    assert brief["required_concept_keys"] == ["integration_threshold", "integration_owner"]
    assert brief["selected_concept_keys"] == ["integration_owner"]
    assert any("Integration Threshold" in warning for warning in brief["warnings"])
    assert verification.verification_outcome == "failed"
    assert verification.summary["required_concept_coverage_ratio"] == 0.5
    assert "integration_threshold" in verification.verification_details["required_concept_keys"]
    assert "integration_owner" in verification.verification_details["supported_concept_keys"]
    assert any(
        "does not cover every required concept" in reason
        for reason in verification.verification_reasons
    )


def test_verify_semantic_grounded_document_requires_supported_concept_coverage(monkeypatch) -> None:
    document_id = uuid4()
    documents = {
        document_id: _document(
            document_id=document_id,
            source_filename="integration-one.pdf",
            title="Integration One",
        )
    }
    passes = {
        document_id: _semantic_pass(
            document_id=document_id,
            run_id=uuid4(),
            review_status="approved",
            source_filename="integration-one.pdf",
        )
    }
    monkeypatch.setattr(
        "app.services.semantic_generation.get_active_semantic_pass_detail",
        lambda session, requested_document_id: passes[requested_document_id],
    )
    monkeypatch.setattr(
        "app.services.semantic_generation.list_document_semantic_facts",
        lambda session, document_id: [],
    )
    brief = prepare_semantic_generation_brief(
        FakeSession(documents),
        title="Integration Governance Brief",
        goal="Summarize the knowledge base guidance on integration governance.",
        audience="Operators",
        document_ids=[document_id],
        concept_keys=[],
        category_keys=[],
        target_length="medium",
        review_policy="allow_candidate_with_disclosure",
    )
    draft = draft_semantic_grounded_document(brief, brief_task_id=uuid4())
    broken_draft = deepcopy(draft)
    broken_draft["claims"][0]["evidence_labels"] = []

    verification = verify_semantic_grounded_document(
        broken_draft,
        max_unsupported_claim_count=1,
        require_full_claim_traceability=False,
        require_full_concept_coverage=True,
    )

    assert verification.verification_outcome == "failed"
    assert verification.summary["required_concept_coverage_ratio"] == 0.0
    assert verification.verification_details["supported_concept_keys"] == []
    assert any(
        "does not cover every required concept" in reason
        for reason in verification.verification_reasons
    )
