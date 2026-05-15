from __future__ import annotations

from pathlib import Path

import pytest

from app.release_gate_cli import (
    COMPOSE_PROJECT_POSTGRES_PORT,
    build_release_gate_steps,
    main,
)


def test_release_gate_cli_lists_the_canonical_step_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: Path.cwd())
    tmpdir = Path.cwd().joinpath(".tmp", "release-gate").as_posix()
    compose_up = (
        "compose-up: DOCLING_SYSTEM_POSTGRES_PORT=5434 "
        "docker compose up -d db api worker agent-worker"
    )

    exit_code = main(["--list-steps"])

    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines == [
        "ruff: uv run ruff check",
        "improvement-case-validate: uv run docling-system-improvement-case-validate",
        "alembic-upgrade-head: uv run --extra dev alembic upgrade head",
        "alembic-current: uv run --extra dev alembic current",
        "db-model-metadata: DOCLING_SYSTEM_RUN_INTEGRATION=1 TMPDIR="
        f"{tmpdir} "
        "uv run --extra dev python -m pytest -q tests/integration/test_db_model_metadata.py -rs",
        "compose-config: docker compose config --quiet",
        compose_up,
        "full-integration: DOCLING_SYSTEM_RUN_INTEGRATION=1 TMPDIR="
        f"{tmpdir} "
        "uv run --extra dev python -m pytest -q -rs",
    ]


def test_release_gate_steps_capture_required_contracts(tmp_path: Path) -> None:
    steps = build_release_gate_steps(project_root=tmp_path)
    step_map = {step.name: step for step in steps}

    assert tuple(step_map) == (
        "ruff",
        "improvement-case-validate",
        "alembic-upgrade-head",
        "alembic-current",
        "db-model-metadata",
        "compose-config",
        "compose-up",
        "full-integration",
    )
    assert step_map["db-model-metadata"].env == (
        ("DOCLING_SYSTEM_RUN_INTEGRATION", "1"),
        ("TMPDIR", tmp_path.joinpath(".tmp", "release-gate").as_posix()),
    )
    assert step_map["compose-up"].env == (
        ("DOCLING_SYSTEM_POSTGRES_PORT", COMPOSE_PROJECT_POSTGRES_PORT),
    )


def test_release_gate_cli_waits_for_compose_health_and_tears_down(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executed: list[str] = []
    waits: list[Path] = []
    downs: list[Path] = []

    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "app.release_gate_cli.run_step",
        lambda step, *, project_root=None: executed.append(step.name),
    )
    monkeypatch.setattr(
        "app.release_gate_cli.wait_for_compose_health",
        lambda *, project_root=None, **_kwargs: waits.append(project_root or tmp_path),
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: downs.append(project_root or tmp_path),
    )

    exit_code = main([])

    assert exit_code == 0
    assert executed == [
        "ruff",
        "improvement-case-validate",
        "alembic-upgrade-head",
        "alembic-current",
        "db-model-metadata",
        "compose-config",
        "compose-up",
        "full-integration",
    ]
    assert waits == [tmp_path]
    assert downs == [tmp_path]


def test_release_gate_cli_tears_down_after_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executed: list[str] = []
    downs: list[Path] = []

    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)

    def fake_run_step(step, *, project_root=None):
        executed.append(step.name)
        if step.name == "full-integration":
            raise SystemExit(1)

    monkeypatch.setattr("app.release_gate_cli.run_step", fake_run_step)
    monkeypatch.setattr(
        "app.release_gate_cli.wait_for_compose_health",
        lambda *, project_root=None, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: downs.append(project_root or tmp_path),
    )

    with pytest.raises(SystemExit) as excinfo:
        main([])

    assert excinfo.value.code == 1
    assert executed[-1] == "full-integration"
    assert downs == [tmp_path]


def test_release_gate_cli_returns_non_zero_when_compose_health_never_converges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    executed: list[str] = []
    downs: list[Path] = []

    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "app.release_gate_cli.run_step",
        lambda step, *, project_root=None: executed.append(step.name),
    )
    monkeypatch.setattr(
        "app.release_gate_cli.wait_for_compose_health",
        lambda *, project_root=None, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("compose health timed out")
        ),
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: downs.append(project_root or tmp_path),
    )

    exit_code = main([])

    assert exit_code == 1
    assert executed[-1] == "compose-up"
    assert downs == [tmp_path]
    assert "compose health timed out" in capsys.readouterr().err
