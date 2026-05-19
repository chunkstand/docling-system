from __future__ import annotations

from app.services.agent_actions import search_harness


def test_search_harness_action_module_exposes_executor_seams() -> None:
    assert callable(search_harness._draft_harness_config_update_executor)
    assert callable(search_harness._verify_draft_harness_config_executor)
    assert callable(search_harness._apply_harness_config_update_executor)
    assert callable(search_harness._triage_replay_regression_executor)
