from __future__ import annotations

import app.services.agent_tasks as agent_task_service


def test_agent_tasks_facade_exposes_core_entrypoints() -> None:
    assert callable(agent_task_service.create_agent_task)
    assert callable(agent_task_service.list_agent_tasks)
    assert callable(agent_task_service.get_agent_task_detail)
    assert callable(agent_task_service.create_agent_task_outcome)
    assert callable(agent_task_service.approve_agent_task)
    assert callable(agent_task_service.reject_agent_task)
