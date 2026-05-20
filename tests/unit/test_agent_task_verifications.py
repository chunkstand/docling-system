from __future__ import annotations

from app.services import agent_task_verifications


def test_agent_task_verifications_facade_exposes_core_entrypoints() -> None:
    assert (
        agent_task_verifications.VerificationOutcome.__name__
        == "SearchHarnessReleaseGateOutcome"
    )
    assert callable(agent_task_verifications.get_agent_task_verifications)
    assert callable(agent_task_verifications.list_agent_task_verifications)
    assert callable(agent_task_verifications.verify_search_harness_evaluation_task)
    assert callable(agent_task_verifications.verify_draft_harness_config_task)
    assert callable(agent_task_verifications.verify_draft_semantic_registry_update_task)
    assert callable(agent_task_verifications.verify_semantic_grounded_document_task)
