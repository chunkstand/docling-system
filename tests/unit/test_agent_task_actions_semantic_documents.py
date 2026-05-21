from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_tasks import (
    DraftSemanticGroundedDocumentTaskInput,
    EvaluateSemanticCandidateExtractorTaskInput,
    ExportSemanticSupervisionCorpusTaskInput,
    PrepareSemanticGenerationBriefTaskInput,
    TriageSemanticCandidateDisagreementsTaskInput,
    VerifySemanticGroundedDocumentTaskInput,
)
from app.services.agent_actions.semantic_analysis_actions import (
    _evaluate_semantic_candidate_extractor_executor,
    _export_semantic_supervision_corpus_executor,
)
from app.services.agent_actions.semantic_drafting_actions import (
    _draft_semantic_grounded_document_executor,
    _prepare_semantic_generation_brief_executor,
)
from app.services.agent_actions.semantic_verification_actions import (
    _triage_semantic_candidate_disagreements_executor,
    _verify_semantic_grounded_document_executor,
)
from tests.unit.agent_task_actions_support import (
    _semantic_candidate_evaluation_output_payload,
    _semantic_generation_brief_output_payload,
)


def test_prepare_semantic_generation_brief_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="prepare_semantic_generation_brief",
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
        "app.services.agent_actions.semantic_drafting_actions.prepare_semantic_generation_brief",
        lambda session, **kwargs: _semantic_generation_brief_output_payload(
            task_id=task.id,
            document_id=document_id,
        )["brief"],
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_drafting_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_generation_brief.json",
            },
        )(),
    )

    result = _prepare_semantic_generation_brief_executor(
        session=object(),
        task=task,
        payload=PrepareSemanticGenerationBriefTaskInput(
            title="Integration Governance Brief",
            goal="Summarize the knowledge base guidance on integration governance.",
            audience="Operators",
            document_ids=[document_id],
            target_length="medium",
            review_policy="allow_candidate_with_disclosure",
        ),
    )

    assert result["brief"]["title"] == "Integration Governance Brief"
    assert result["artifact_kind"] == "semantic_generation_brief"

def test_prepare_semantic_generation_brief_executor_passes_shadow_arguments(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="prepare_semantic_generation_brief",
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
    captured: dict = {}

    def _fake_prepare(_session, **kwargs):
        captured.update(kwargs)
        payload = _semantic_generation_brief_output_payload(
            task_id=task.id,
            document_id=document_id,
        )["brief"]
        payload["shadow_mode"] = True
        payload["shadow_candidate_extractor_name"] = kwargs["candidate_extractor_name"]
        payload["shadow_candidate_summary"] = {"candidate_count": 1}
        payload["shadow_candidates"] = [
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
        ]
        return payload

    monkeypatch.setattr(
        "app.services.agent_actions.semantic_drafting_actions.prepare_semantic_generation_brief",
        _fake_prepare,
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_drafting_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_generation_brief.json",
            },
        )(),
    )

    _prepare_semantic_generation_brief_executor(
        session=object(),
        task=task,
        payload=PrepareSemanticGenerationBriefTaskInput(
            title="Integration Governance Brief",
            goal="Summarize the knowledge base guidance on integration governance.",
            audience="Operators",
            document_ids=[document_id],
            target_length="medium",
            review_policy="allow_candidate_with_disclosure",
            include_shadow_candidates=True,
            candidate_extractor_name="concept_ranker_v1",
            candidate_score_threshold=0.4,
            max_shadow_candidates=5,
        ),
    )

    assert captured["include_shadow_candidates"] is True
    assert captured["candidate_extractor_name"] == "concept_ranker_v1"
    assert captured["candidate_score_threshold"] == 0.4
    assert captured["max_shadow_candidates"] == 5

def test_export_semantic_supervision_corpus_executor_writes_artifact(monkeypatch, tmp_path) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="export_semantic_supervision_corpus",
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
        "app.services.agent_actions.semantic_analysis_actions.export_semantic_supervision_corpus",
        lambda session, **kwargs: {
            "corpus_name": "semantic_supervision_corpus",
            "document_count": 1,
            "row_count": 4,
            "row_type_counts": {"semantic_evaluation_expectation": 2},
            "label_type_counts": {"expected_concept": 2},
            "rows": [],
            "jsonl_path": str(tmp_path / "semantic_supervision_corpus.jsonl"),
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_supervision_corpus.json",
            },
        )(),
    )

    result = _export_semantic_supervision_corpus_executor(
        session=object(),
        task=task,
        payload=ExportSemanticSupervisionCorpusTaskInput(document_ids=[document_id]),
    )

    assert result["corpus"]["document_count"] == 1
    assert result["artifact_kind"] == "semantic_supervision_corpus"

def test_evaluate_semantic_candidate_extractor_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="evaluate_semantic_candidate_extractor",
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
        "app.services.agent_actions.semantic_analysis_actions.evaluate_semantic_candidate_extractor",
        lambda session, **kwargs: {
            key: value
            for key, value in _semantic_candidate_evaluation_output_payload(
                document_id=str(document_id)
            ).items()
            if key not in {"artifact_id", "artifact_kind", "artifact_path"}
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_analysis_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_candidate_evaluation.json",
            },
        )(),
    )

    result = _evaluate_semantic_candidate_extractor_executor(
        session=object(),
        task=task,
        payload=EvaluateSemanticCandidateExtractorTaskInput(document_ids=[document_id]),
    )

    assert result["summary"]["candidate_expected_recall"] == 1.0
    assert result["artifact_kind"] == "semantic_candidate_evaluation"

def test_triage_semantic_candidate_disagreements_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="triage_semantic_candidate_disagreements",
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
    evaluation_task_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output=_semantic_candidate_evaluation_output_payload(),
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.triage_semantic_candidate_disagreements",
        lambda payload, min_score, include_expected_only: (
            {
                "baseline_extractor_name": "registry_lexical_v1",
                "candidate_extractor_name": "concept_ranker_v1",
                "issue_count": 1,
                "issues": [
                    {
                        "issue_id": "shadow:1",
                        "document_id": str(uuid4()),
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
            {
                "outcome": "passed",
                "metrics": {"issue_count": 1},
                "reasons": [],
                "details": {"min_score": min_score, "include_expected_only": include_expected_only},
            },
            {"next_action": "review_shadow_candidates", "confidence": 0.7, "summary": "Review it."},
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            verification_id=uuid4(),
            target_task_id=task.id,
            verification_task_id=task.id,
            outcome=kwargs["outcome"],
            metrics=kwargs["metrics"],
            reasons=kwargs["reasons"],
            details=kwargs["details"],
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
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_candidate_disagreement_report.json",
            },
        )(),
    )

    result = _triage_semantic_candidate_disagreements_executor(
        session=object(),
        task=task,
        payload=TriageSemanticCandidateDisagreementsTaskInput(
            target_task_id=evaluation_task_id,
        ),
    )

    assert result["disagreement_report"]["issue_count"] == 1
    assert result["recommendation"]["next_action"] == "review_shadow_candidates"
    assert result["artifact_kind"] == "semantic_candidate_disagreement_report"

def test_draft_semantic_grounded_document_executor_writes_artifact_and_markdown(
    monkeypatch,
    tmp_path,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_semantic_grounded_document",
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
    brief_task_id = uuid4()
    document_id = uuid4()
    brief_output = _semantic_generation_brief_output_payload(
        task_id=brief_task_id,
        document_id=document_id,
    )
    draft_payload = {
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
        "document_refs": brief_output["brief"]["document_refs"],
        "assertion_index": brief_output["brief"]["semantic_dossier"][0]["assertions"],
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
                "assertion_ids": [
                    brief_output["brief"]["semantic_dossier"][0]["assertions"][0]["assertion_id"]
                ],
                "evidence_labels": ["E1"],
                "source_document_ids": [str(document_id)],
                "support_level": "supported",
                "review_policy_status": "candidate_disclosed",
                "disclosure_note": "Candidate-backed support requires review.",
            }
        ],
        "evidence_pack": brief_output["brief"]["evidence_pack"],
        "markdown": "# Integration Governance Brief\n\n## Evidence Appendix\n",
        "markdown_path": None,
        "warnings": [],
        "success_metrics": [],
    }

    monkeypatch.setattr(
        "app.services.agent_actions.semantic_drafting_actions.resolve_required_dependency_task_output_context",
        lambda session, **kwargs: SimpleNamespace(output=brief_output),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_drafting_actions.draft_semantic_grounded_document",
        lambda brief_payload, *, brief_task_id: {
            **draft_payload,
            "brief_task_id": brief_task_id,
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_drafting_actions.StorageService",
        lambda: type(
            "FakeStorage",
            (),
            {"get_agent_task_dir": lambda self, _task_id: tmp_path},
        )(),
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_drafting_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_grounded_document_draft.json",
            },
        )(),
    )

    result = _draft_semantic_grounded_document_executor(
        session=object(),
        task=task,
        payload=DraftSemanticGroundedDocumentTaskInput(target_task_id=brief_task_id),
    )

    assert result["draft"]["brief_task_id"] == brief_task_id
    assert result["artifact_kind"] == "semantic_grounded_document_draft"
    assert Path(result["draft"]["markdown_path"]).name == "semantic_grounded_document.md"
    assert (
        Path(result["draft"]["markdown_path"])
        .read_text()
        .startswith("# Integration Governance Brief")
    )

def test_verify_semantic_grounded_document_executor_writes_verification_artifact(
    monkeypatch,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_semantic_grounded_document",
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
    draft_task_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.verify_semantic_grounded_document_task",
        lambda session, task, payload: {
            "draft": {
                "document_kind": "knowledge_brief",
                "title": "Integration Governance Brief",
                "goal": "Summarize the knowledge base guidance on integration governance.",
                "audience": "Operators",
                "review_policy": "allow_candidate_with_disclosure",
                "target_length": "medium",
                "brief_task_id": str(uuid4()),
                "generator_name": "structured_fallback",
                "generator_model": None,
                "used_fallback": True,
                "required_concept_keys": ["integration_threshold"],
                "document_refs": [],
                "assertion_index": [],
                "sections": [],
                "claims": [],
                "evidence_pack": [],
                "markdown": "# Integration Governance Brief\n",
                "markdown_path": "/tmp/semantic_grounded_document.md",
                "warnings": [],
                "success_metrics": [],
            },
            "summary": {
                "claim_count": 1,
                "unsupported_claim_count": 0,
                "required_concept_coverage_ratio": 1.0,
            },
            "success_metrics": [],
            "verification": {
                "verification_id": str(uuid4()),
                "target_task_id": str(draft_task_id),
                "verification_task_id": str(task.id),
                "verifier_type": "semantic_grounded_document_gate",
                "outcome": "passed",
                "metrics": {"claim_count": 1},
                "reasons": [],
                "details": {},
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    monkeypatch.setattr(
        "app.services.agent_actions.semantic_verification_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_grounded_document_verification.json",
            },
        )(),
    )

    result = _verify_semantic_grounded_document_executor(
        session=object(),
        task=task,
        payload=VerifySemanticGroundedDocumentTaskInput(target_task_id=draft_task_id),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "semantic_grounded_document_verification"
