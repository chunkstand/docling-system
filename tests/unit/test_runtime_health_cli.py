from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.runtime_health_cli import main


def test_runtime_health_cli_returns_zero_for_healthy_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "app.runtime_health_cli.build_runtime_health_report",
        lambda **_kwargs: type(
            "Report",
            (),
            {"status": "ok", "model_dump": lambda self: {"status": "ok"}},
        )(),
    )

    exit_code = main(["--process-kind", "api", "--compact"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"status": "ok"}


def test_runtime_health_cli_returns_non_zero_for_unhealthy_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "app.runtime_health_cli.build_runtime_health_report",
        lambda **_kwargs: type(
            "Report",
            (),
            {"status": "error", "model_dump": lambda self: {"status": "error"}},
        )(),
    )

    exit_code = main(["--process-kind", "worker", "--compact"])

    assert exit_code == 1
    assert json.loads(capsys.readouterr().out) == {"status": "error"}


def test_compose_runtime_health_checks_allow_enough_time_for_cli() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    for service_name, process_kind in (
        ("api", "api"),
        ("worker", "worker"),
        ("agent-worker", "agent_worker"),
    ):
        healthcheck = compose["services"][service_name]["healthcheck"]

        assert healthcheck["test"] == [
            "CMD",
            "docling-system-runtime-health",
            "--process-kind",
            process_kind,
            "--compact",
        ]
        assert healthcheck["timeout"] == "10s"
