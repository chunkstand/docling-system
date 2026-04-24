from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.db.models import AgentTask, Document
from app.schemas.semantics import (
    DocumentSemanticPassResponse,
    SemanticAssertionCategoryBindingResponse,
    SemanticAssertionEvidenceResponse,
    SemanticAssertionResponse,
    SemanticConceptCategoryBindingResponse,
)
from app.services.semantic_candidates import (
    evaluate_semantic_candidate_extractor,
    export_semantic_supervision_corpus,
)
from app.services.semantic_registry import normalize_semantic_text, semantic_registry_from_payload
from app.services.semantics import SemanticSourceItem


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class FakeExecuteResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return FakeScalarResult(self._rows)


class FakeSession:
    def __init__(self, *, documents=None, tasks=None) -> None:
        self.documents = documents or {}
        self.tasks = tasks or {}

    def get(self, model, key):
        if model.__name__ == "Document":
            return self.documents.get(key)
        if model.__name__ == "AgentTask":
            return self.tasks.get(key)
        return None

    def execute(self, statement):
        rendered = str(statement)
        if "FROM agent_tasks" in rendered:
            return FakeExecuteResult(self.tasks.values())
        if "FROM documents" in rendered:
            return FakeExecuteResult(self.documents.values())
        raise AssertionError(f"Unexpected statement: {rendered}")


def _document(*, document_id: UUID, source_filename: str, title: str) -> Document:
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
    document_id: UUID,
    run_id: UUID,
    reviewed: bool = False,
) -> DocumentSemanticPassResponse:
    now = datetime.now(UTC)
    assertion_id = uuid4()
    binding_id = uuid4()
    evidence = [
        SemanticAssertionEvidenceResponse(
            evidence_id=uuid4(),
            source_type="chunk",
            chunk_id=uuid4(),
            table_id=None,
            figure_id=None,
            page_from=1,
            page_to=1,
            matched_terms=["integration threshold"],
            excerpt="Integration threshold remains in force.",
            source_label="Section 1",
            source_artifact_api_path=None,
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
            matched_terms=["integration threshold"],
            excerpt="Tier | Integration threshold",
            source_label="Threshold Matrix",
            source_artifact_api_path="/documents/example/tables/1",
            source_artifact_sha256="table-sha",
            details={},
        ),
    ]
    review_overlay = (
        {
            "review_id": str(uuid4()),
            "review_status": "approved",
            "review_note": "Confirmed by operator.",
            "reviewed_by": "operator@example.com",
            "created_at": now.isoformat(),
        }
        if reviewed
        else None
    )
    details = {"review_overlay": review_overlay} if review_overlay else {}
    return DocumentSemanticPassResponse(
        semantic_pass_id=uuid4(),
        document_id=document_id,
        run_id=run_id,
        status="completed",
        registry_version="semantics-layer-foundation-alpha.4",
        registry_sha256="registry-sha",
        extractor_version="semantics_sidecar_v2_1",
        artifact_schema_version="2.1",
        baseline_run_id=uuid4(),
        baseline_semantic_pass_id=uuid4(),
        has_json_artifact=True,
        has_yaml_artifact=True,
        artifact_json_sha256="json-sha",
        artifact_yaml_sha256="yaml-sha",
        assertion_count=1,
        evidence_count=2,
        summary={"concept_keys": ["integration_threshold"]},
        evaluation_status="completed",
        evaluation_fixture_name="integration-fixture",
        evaluation_version=2,
        evaluation_summary={
            "all_expectations_passed": False,
            "expectations": [
                {"concept_key": "integration_threshold", "passed": True},
                {"concept_key": "integration_owner", "passed": False},
            ],
        },
        continuity_summary={
            "has_baseline": True,
            "change_count": 1,
            "removed_concept_keys": ["legacy_owner"],
        },
        error_message=None,
        created_at=now,
        completed_at=now,
        concept_category_bindings=[
            SemanticConceptCategoryBindingResponse(
                binding_id=uuid4(),
                concept_key="integration_threshold",
                category_key="integration_governance",
                category_label="Integration Governance",
                binding_type="concept_category",
                created_from="registry",
                review_status="approved",
                details=details,
            )
        ],
        assertions=[
            SemanticAssertionResponse(
                assertion_id=assertion_id,
                concept_key="integration_threshold",
                preferred_label="Integration Threshold",
                scope_note=None,
                assertion_kind="concept_mention",
                epistemic_status="observed",
                context_scope="document_run",
                review_status="approved" if reviewed else "candidate",
                matched_terms=["integration threshold"],
                source_types=["chunk", "table"],
                evidence_count=2,
                confidence=0.9,
                details=details,
                category_bindings=[
                    SemanticAssertionCategoryBindingResponse(
                        binding_id=binding_id,
                        category_key="integration_governance",
                        category_label="Integration Governance",
                        binding_type="assertion_category",
                        created_from="derived",
                        review_status="approved" if reviewed else "candidate",
                        details=details,
                    )
                ],
                evidence=evidence,
            )
        ],
    )


def _registry():
    return semantic_registry_from_payload(
        {
            "registry_name": "semantic_registry",
            "registry_version": "semantics-layer-foundation-alpha.4",
            "categories": [
                {
                    "category_key": "integration_governance",
                    "preferred_label": "Integration Governance",
                }
            ],
            "concepts": [
                {
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "category_keys": ["integration_governance"],
                    "aliases": ["integration threshold"],
                },
                {
                    "concept_key": "integration_owner",
                    "preferred_label": "Integration Owner",
                    "category_keys": ["integration_governance"],
                },
            ],
        }
    )


def test_evaluate_semantic_candidate_extractor_improves_expected_recall(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    session = FakeSession(
        documents={
            document_id: _document(
                document_id=document_id,
                source_filename="integration-shadow.pdf",
                title="Integration Shadow",
            )
        }
    )
    semantic_pass = _semantic_pass(document_id=document_id, run_id=run_id)

    monkeypatch.setattr(
        "app.services.semantic_candidates.get_semantic_registry",
        lambda session: _registry(),
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.get_active_semantic_pass_detail",
        lambda _session, _document_id: semantic_pass,
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.build_semantic_sources",
        lambda _session, _run_id: [
            SemanticSourceItem(
                source_type="chunk",
                source_locator="chunk-1",
                chunk_id=uuid4(),
                table_id=None,
                figure_id=None,
                page_from=1,
                page_to=1,
                normalized_text=normalize_semantic_text(
                    "Integration threshold remains in force. "
                    "Owners for integration approve changes."
                ),
                excerpt=(
                    "Integration threshold remains in force. "
                    "Owners for integration approve changes."
                ),
                source_label="Section 1",
                source_artifact_path=None,
                source_artifact_sha256="chunk-sha",
                details={},
            ),
            SemanticSourceItem(
                source_type="table",
                source_locator="table-1",
                chunk_id=None,
                table_id=uuid4(),
                figure_id=None,
                page_from=1,
                page_to=1,
                normalized_text=normalize_semantic_text("Threshold matrix integration threshold"),
                excerpt="Threshold matrix",
                source_label="Threshold Matrix",
                source_artifact_path="/tmp/table.json",
                source_artifact_sha256="table-sha",
                details={},
            ),
        ],
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.latest_concept_review_overlays",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.latest_category_review_overlays",
        lambda *_args, **_kwargs: {},
    )

    def _fake_semantic_eval(_document, assertions, _bindings):
        concept_keys = {row["concept_key"] for row in assertions}
        expectations = [
            {
                "concept_key": "integration_threshold",
                "passed": "integration_threshold" in concept_keys,
            },
            {"concept_key": "integration_owner", "passed": "integration_owner" in concept_keys},
        ]
        return (
            "completed",
            "integration-shadow-fixture",
            {
                "all_expectations_passed": all(item["passed"] for item in expectations),
                "expectations": expectations,
            },
        )

    monkeypatch.setattr(
        "app.services.semantic_candidates.semantic_evaluation_result",
        _fake_semantic_eval,
    )

    payload = evaluate_semantic_candidate_extractor(
        session,
        document_ids=[document_id],
        baseline_extractor_name="registry_lexical_v1",
        candidate_extractor_name="concept_ranker_v1",
        score_threshold=0.34,
        max_candidates_per_source=3,
    )

    assert (
        payload["summary"]["candidate_expected_recall"]
        > payload["summary"]["baseline_expected_recall"]
    )
    report = payload["document_reports"][0]
    assert report["improved_expected_concept_keys"] == ["integration_owner"]
    assert report["candidate_only_concept_keys"] == ["integration_owner"]
    assert any(row["concept_key"] == "integration_owner" for row in report["shadow_candidates"])


def test_export_semantic_supervision_corpus_includes_reviews_and_generation_verifications(
    monkeypatch,
    tmp_path: Path,
) -> None:
    document_id = uuid4()
    run_id = uuid4()
    semantic_pass = _semantic_pass(document_id=document_id, run_id=run_id, reviewed=True)
    task_id = uuid4()
    session = FakeSession(
        documents={
            document_id: _document(
                document_id=document_id,
                source_filename="integration-shadow.pdf",
                title="Integration Shadow",
            )
        },
        tasks={
            task_id: AgentTask(
                id=task_id,
                task_type="verify_semantic_grounded_document",
                status="completed",
                priority=100,
                side_effect_level="read_only",
                requires_approval=False,
                input_json={},
                result_json={
                    "payload": {
                        "draft": {
                            "document_refs": [
                                {
                                    "document_id": str(document_id),
                                    "run_id": str(run_id),
                                    "semantic_pass_id": str(semantic_pass.semantic_pass_id),
                                    "registry_version": semantic_pass.registry_version,
                                    "registry_sha256": semantic_pass.registry_sha256,
                                }
                            ]
                        },
                        "summary": {"unsupported_claim_count": 0},
                        "verification": {
                            "outcome": "passed",
                            "metrics": {"claim_count": 1, "traceable_claim_ratio": 1.0},
                            "details": {
                                "required_concept_keys": [
                                    "integration_threshold",
                                    "integration_owner",
                                ],
                                "supported_concept_keys": ["integration_threshold"],
                                "missing_concept_keys": ["integration_owner"],
                            },
                        },
                    }
                },
                workflow_version="v1",
                model_settings_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
        },
    )

    monkeypatch.setattr(
        "app.services.semantic_candidates.get_active_semantic_pass_detail",
        lambda _session, _document_id: semantic_pass,
    )

    output_path = tmp_path / "semantic_supervision_corpus.jsonl"
    payload = export_semantic_supervision_corpus(
        session,
        document_ids=[document_id],
        reviewed_only=True,
        include_generation_verifications=True,
        output_path=output_path,
    )

    assert output_path.exists()
    assert payload["row_type_counts"]["semantic_assertion_review"] == 1
    assert payload["row_type_counts"]["semantic_category_review"] == 1
    assert payload["row_type_counts"]["semantic_evaluation_expectation"] == 2
    assert payload["row_type_counts"]["grounded_document_verification"] == 1
    assert payload["row_type_counts"]["semantic_continuity"] == 1
    lines = output_path.read_text().strip().splitlines()
    assert len(lines) == payload["row_count"]
    assert json.loads(lines[0])["row_id"]


def test_export_semantic_supervision_corpus_dedupes_document_ids_and_ignores_stale_verifications(
    monkeypatch,
    tmp_path: Path,
) -> None:
    document_id = uuid4()
    run_id = uuid4()
    stale_run_id = uuid4()
    semantic_pass = _semantic_pass(document_id=document_id, run_id=run_id, reviewed=True)
    current_task_id = uuid4()
    stale_task_id = uuid4()
    session = FakeSession(
        documents={
            document_id: _document(
                document_id=document_id,
                source_filename="integration-shadow.pdf",
                title="Integration Shadow",
            )
        },
        tasks={
            current_task_id: AgentTask(
                id=current_task_id,
                task_type="verify_semantic_grounded_document",
                status="completed",
                priority=100,
                side_effect_level="read_only",
                requires_approval=False,
                input_json={},
                result_json={
                    "payload": {
                        "draft": {
                            "document_refs": [
                                {
                                    "document_id": str(document_id),
                                    "run_id": str(run_id),
                                    "semantic_pass_id": str(semantic_pass.semantic_pass_id),
                                    "registry_version": semantic_pass.registry_version,
                                    "registry_sha256": semantic_pass.registry_sha256,
                                }
                            ]
                        },
                        "summary": {"unsupported_claim_count": 0},
                        "verification": {
                            "outcome": "passed",
                            "metrics": {"claim_count": 1, "traceable_claim_ratio": 1.0},
                            "details": {
                                "required_concept_keys": ["integration_threshold"],
                                "supported_concept_keys": ["integration_threshold"],
                                "missing_concept_keys": [],
                            },
                        },
                    }
                },
                workflow_version="v1",
                model_settings_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            ),
            stale_task_id: AgentTask(
                id=stale_task_id,
                task_type="verify_semantic_grounded_document",
                status="completed",
                priority=100,
                side_effect_level="read_only",
                requires_approval=False,
                input_json={},
                result_json={
                    "payload": {
                        "draft": {
                            "document_refs": [
                                {
                                    "document_id": str(document_id),
                                    "run_id": str(stale_run_id),
                                    "semantic_pass_id": str(uuid4()),
                                    "registry_version": semantic_pass.registry_version,
                                    "registry_sha256": semantic_pass.registry_sha256,
                                }
                            ]
                        },
                        "summary": {"unsupported_claim_count": 2},
                        "verification": {
                            "outcome": "failed",
                            "metrics": {"claim_count": 3, "traceable_claim_ratio": 0.0},
                            "details": {
                                "required_concept_keys": ["integration_owner"],
                                "supported_concept_keys": [],
                                "missing_concept_keys": ["integration_owner"],
                            },
                        },
                    }
                },
                workflow_version="v1",
                model_settings_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            ),
        },
    )

    monkeypatch.setattr(
        "app.services.semantic_candidates.get_active_semantic_pass_detail",
        lambda _session, _document_id: semantic_pass,
    )

    output_path = tmp_path / "semantic_supervision_corpus.jsonl"
    payload = export_semantic_supervision_corpus(
        session,
        document_ids=[document_id, document_id],
        reviewed_only=True,
        include_generation_verifications=True,
        output_path=output_path,
    )

    assert payload["document_count"] == 1
    assert payload["row_type_counts"]["grounded_document_verification"] == 1
    grounded_rows = [
        row for row in payload["rows"] if row["row_type"] == "grounded_document_verification"
    ]
    assert grounded_rows == [
        {
            "row_id": f"grounded_verification:{current_task_id}:{document_id}",
            "row_type": "grounded_document_verification",
            "label_type": "grounded_claim_support",
            "document_id": document_id,
            "run_id": run_id,
            "semantic_pass_id": semantic_pass.semantic_pass_id,
            "source_ref": f"agent_task:{current_task_id}",
            "concept_key": None,
            "category_key": None,
            "review_status": None,
            "registry_version": semantic_pass.registry_version,
            "registry_sha256": semantic_pass.registry_sha256,
            "evidence_span": {
                "claim_count": 1,
                "traceable_claim_ratio": 1.0,
            },
            "verification_outcome": "passed",
            "details": {
                "required_concept_keys": ["integration_threshold"],
                "supported_concept_keys": ["integration_threshold"],
                "missing_concept_keys": [],
                "unsupported_claim_count": 0,
            },
        }
    ]


def test_evaluate_semantic_candidate_extractor_reports_role_specific_descriptors(
    monkeypatch,
) -> None:
    document_id = uuid4()
    run_id = uuid4()
    session = FakeSession(
        documents={
            document_id: _document(
                document_id=document_id,
                source_filename="integration-shadow.pdf",
                title="Integration Shadow",
            )
        }
    )
    semantic_pass = _semantic_pass(document_id=document_id, run_id=run_id)

    monkeypatch.setattr(
        "app.services.semantic_candidates.get_semantic_registry",
        lambda session: _registry(),
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.get_active_semantic_pass_detail",
        lambda _session, _document_id: semantic_pass,
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.build_semantic_sources",
        lambda _session, _run_id: [
            SemanticSourceItem(
                source_type="chunk",
                source_locator="chunk-1",
                chunk_id=uuid4(),
                table_id=None,
                figure_id=None,
                page_from=1,
                page_to=1,
                normalized_text=normalize_semantic_text(
                    "Integration threshold remains in force. "
                    "Owners for integration approve changes."
                ),
                excerpt=(
                    "Integration threshold remains in force. "
                    "Owners for integration approve changes."
                ),
                source_label="Section 1",
                source_artifact_path=None,
                source_artifact_sha256="chunk-sha",
                details={},
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.latest_concept_review_overlays",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.latest_category_review_overlays",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        "app.services.semantic_candidates.semantic_evaluation_result",
        lambda _document, assertions, _bindings: (
            "completed",
            "integration-shadow-fixture",
            {
                "all_expectations_passed": any(
                    row["concept_key"] == "integration_threshold" for row in assertions
                ),
                "expectations": [
                    {
                        "concept_key": "integration_threshold",
                        "passed": any(
                            row["concept_key"] == "integration_threshold" for row in assertions
                        ),
                    }
                ],
            },
        ),
    )

    payload = evaluate_semantic_candidate_extractor(
        session,
        document_ids=[document_id],
        baseline_extractor_name="concept_ranker_v1",
        candidate_extractor_name="registry_lexical_v1",
        score_threshold=0.34,
        max_candidates_per_source=3,
    )

    assert payload["baseline_extractor"] == {
        "extractor_name": "concept_ranker_v1",
        "backing_model": "hashing_embedding_v1",
        "match_strategy": "token_set_ranker_v1",
        "provider_name": "local_hashing",
        "shadow_mode": True,
    }
    assert payload["candidate_extractor"] == {
        "extractor_name": "registry_lexical_v1",
        "backing_model": "none",
        "match_strategy": "normalized_phrase_contains",
        "provider_name": None,
        "shadow_mode": True,
    }
