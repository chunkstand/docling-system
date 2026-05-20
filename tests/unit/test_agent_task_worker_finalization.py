from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.db.models import AgentTask, AgentTaskStatus
from app.services.agent_task_worker import finalize_agent_task_failure
from app.services.storage import StorageService


def test_finalize_agent_task_failure_writes_replayable_failure_artifact(
    monkeypatch, tmp_path: Path
) -> None:
    task_id = uuid4()
    now = datetime.now(UTC)
    storage_service = StorageService(storage_root=tmp_path / "storage")
    task = AgentTask(
        id=task_id,
        task_type="evaluate_search_harness",
        status=AgentTaskStatus.PROCESSING.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={"candidate_harness_name": "prose_v3"},
        result_json={},
        attempts=3,
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )

    class FakeSession:
        def __init__(self) -> None:
            self.committed = False

        def commit(self) -> None:
            self.committed = True

    monkeypatch.setattr(
        "app.services.agent_task_worker_finalization.current_attempt",
        lambda *args: None,
    )

    session = FakeSession()
    finalize_agent_task_failure(
        session,
        task,
        RuntimeError("boom"),
        failure_stage="execute",
        storage_service=storage_service,
    )

    assert session.committed is True
    assert task.failure_artifact_path is not None
    artifact_path = Path(task.failure_artifact_path)
    assert artifact_path.exists() is True
    artifact = artifact_path.read_text()
    assert "boom" in artifact
    assert "execute" in artifact
