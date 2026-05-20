from __future__ import annotations

from app.services import agent_task_verifications


def test_agent_task_verifications_facade_exposes_draft_entrypoints() -> None:
    assert callable(agent_task_verifications.verify_draft_harness_config_task)
    assert callable(agent_task_verifications.verify_draft_semantic_registry_update_task)
    assert callable(agent_task_verifications.verify_semantic_grounded_document_task)
