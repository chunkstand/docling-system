from __future__ import annotations

from fastapi import HTTPException
from pydantic import ValidationError

from app.services import agent_task_worker


def test_agent_task_worker_facade_exposes_core_entrypoints() -> None:
    assert callable(agent_task_worker.claim_next_agent_task)
    assert callable(agent_task_worker.process_agent_task)
    assert callable(agent_task_worker.run_agent_task_worker_loop)
    assert callable(agent_task_worker.finalize_agent_task_failure)
    assert agent_task_worker.PROMOTABLE_SIDE_EFFECT_APPLIED_KEY == "_side_effect_status"
    assert agent_task_worker.PROMOTABLE_SIDE_EFFECT_CHECKPOINT_KEY == "_checkpointed_result"


def test_agent_task_value_errors_are_terminal() -> None:
    assert agent_task_worker.is_retryable_agent_task_error(ValueError("bad input")) is False


def test_agent_task_unknown_errors_are_retryable() -> None:
    assert agent_task_worker.is_retryable_agent_task_error(RuntimeError("transient")) is True


def test_agent_task_validation_errors_are_terminal() -> None:
    try:
        raise ValidationError.from_exception_data(
            "SearchReplayRunRequest",
            [{"type": "missing", "loc": ("source_type",), "input": {}, "msg": "Field required"}],
        )
    except ValidationError as exc:
        assert agent_task_worker.is_retryable_agent_task_error(exc) is False


def test_agent_task_http_errors_are_terminal() -> None:
    assert (
        agent_task_worker.is_retryable_agent_task_error(
            HTTPException(status_code=404, detail="missing")
        )
        is False
    )
