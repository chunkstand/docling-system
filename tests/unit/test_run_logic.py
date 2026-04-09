from __future__ import annotations

from app.services.runs import is_retryable_error


def test_value_errors_are_terminal() -> None:
    assert is_retryable_error(ValueError("bad input")) is False


def test_unknown_errors_are_retryable() -> None:
    assert is_retryable_error(RuntimeError("transient")) is True
