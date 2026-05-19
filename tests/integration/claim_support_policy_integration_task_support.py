from __future__ import annotations

from uuid import UUID

from app.services.agent_task_worker import claim_next_agent_task, process_agent_task


def _process_next_task(postgres_integration_harness) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "claim-support-eval-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id
