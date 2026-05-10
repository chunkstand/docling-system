from __future__ import annotations

from importlib import import_module
from typing import Any

from pydantic import BaseModel


def _actions_module() -> Any:
    return import_module("app.services.agent_task_actions")


def list_agent_task_actions() -> list[Any]:
    return list(_actions_module().list_agent_task_actions())


def get_agent_task_action(task_type: str) -> Any:
    return _actions_module().get_agent_task_action(task_type)


def validate_agent_task_input(task_type: str, raw_input: dict) -> BaseModel:
    return _actions_module().validate_agent_task_input(task_type, raw_input)


def validate_agent_task_output(task_type: str, raw_output: dict) -> dict:
    return _actions_module().validate_agent_task_output(task_type, raw_output)
