from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.release_gate_cli import (
    COMPOSE_PROJECT_POSTGRES_PORT,
    RELEASE_GATE_REPORT_RELATIVE_PATH,
    build_release_gate_steps,
    capture_failure_artifacts,
    main,
    wait_for_compose_health,
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

    def fake_wait_for_compose_health(*, project_root=None, **_kwargs):
        waits.append(project_root or tmp_path)
        return {
            "db": "healthy",
            "api": "healthy",
            "worker": "healthy",
            "agent-worker": "healthy",
        }

    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "app.release_gate_cli.run_step",
        lambda step, *, project_root=None: executed.append(step.name),
    )
    monkeypatch.setattr(
        "app.release_gate_cli.wait_for_compose_health",
        fake_wait_for_compose_health,
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


def test_release_gate_cli_cleans_tmpdir_after_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tmpdir = tmp_path / ".tmp" / "release-gate"
    tmpdir.mkdir(parents=True)
    tmpdir.joinpath("stale.txt").write_text("stale")

    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "app.release_gate_cli.run_step",
        lambda step, *, project_root=None: None,
    )
    monkeypatch.setattr(
        "app.release_gate_cli.wait_for_compose_health",
        lambda *, project_root=None, **_kwargs: {
            name: "healthy" for name in ("db", "api", "worker", "agent-worker")
        },
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: None,
    )

    exit_code = main([])

    assert exit_code == 0
    assert not tmpdir.exists()


def test_release_gate_cli_preserves_active_inherited_tmpdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tmpdir = tmp_path / ".tmp" / "release-gate"
    active_tmpdir = tmpdir / "pytest-of-chunkstand" / "pytest-0"
    active_tmpdir.mkdir(parents=True)
    active_tmpdir.joinpath("active.txt").write_text("active")

    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setenv("TMPDIR", active_tmpdir.as_posix())
    monkeypatch.setattr(
        "app.release_gate_cli.run_step",
        lambda step, *, project_root=None: None,
    )
    monkeypatch.setattr(
        "app.release_gate_cli.wait_for_compose_health",
        lambda *, project_root=None, **_kwargs: {
            name: "healthy" for name in ("db", "api", "worker", "agent-worker")
        },
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: None,
    )

    exit_code = main([])

    assert exit_code == 0
    assert active_tmpdir.exists()


def test_release_gate_cli_captures_failure_artifacts_and_tears_down_after_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executed: list[str] = []
    captures: list[tuple[Path, str | None, int, str | None]] = []
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
    def fake_capture_failure_artifacts(
        *,
        project_root=None,
        failing_step,
        exit_code,
        failure_message,
        **_kwargs,
    ):
        captures.append((project_root or tmp_path, failing_step, exit_code, failure_message))

    monkeypatch.setattr(
        "app.release_gate_cli.capture_failure_artifacts",
        fake_capture_failure_artifacts,
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: downs.append(project_root or tmp_path),
    )

    exit_code = main([])

    assert exit_code == 1
    assert executed[-1] == "full-integration"
    assert captures == [(tmp_path, "full-integration", 1, None)]
    assert downs == [tmp_path]


def test_release_gate_cli_returns_non_zero_when_compose_health_never_converges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    executed: list[str] = []
    captures: list[tuple[Path, str | None, int, str | None]] = []
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
    def fake_capture_failure_artifacts(
        *,
        project_root=None,
        failing_step,
        exit_code,
        failure_message,
        **_kwargs,
    ):
        captures.append((project_root or tmp_path, failing_step, exit_code, failure_message))

    monkeypatch.setattr(
        "app.release_gate_cli.capture_failure_artifacts",
        fake_capture_failure_artifacts,
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: downs.append(project_root or tmp_path),
    )

    exit_code = main([])

    assert exit_code == 1
    assert executed[-1] == "compose-up"
    assert captures == [(tmp_path, "compose-up", 1, "compose health timed out")]
    assert downs == [tmp_path]
    assert "compose health timed out" in capsys.readouterr().err


def test_wait_for_compose_health_returns_last_healthy_statuses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "app.release_gate_cli._container_health_status",
        lambda service_name, *, project_root, env: "healthy",
    )

    statuses = wait_for_compose_health(
        project_root=tmp_path,
        timeout_seconds=1,
        poll_interval_seconds=0,
    )

    assert statuses == {
        "db": "healthy",
        "api": "healthy",
        "worker": "healthy",
        "agent-worker": "healthy",
    }


def test_wait_for_compose_health_times_out_with_last_statuses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    health_statuses = {
        "db": "healthy",
        "api": "starting",
        "worker": "healthy",
        "agent-worker": "starting",
    }
    monotonic_values = iter((0.0, 0.0, 1.0))

    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "app.release_gate_cli._container_health_status",
        lambda service_name, *, project_root, env: health_statuses[service_name],
    )
    monkeypatch.setattr("app.release_gate_cli.time.monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr("app.release_gate_cli.time.sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="api=starting, worker=healthy, agent-worker=starting"):
        wait_for_compose_health(
            project_root=tmp_path,
            timeout_seconds=1,
            poll_interval_seconds=0,
        )


def test_release_gate_cli_writes_report_artifact_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "app.release_gate_cli.run_step",
        lambda step, *, project_root=None: None,
    )
    monkeypatch.setattr(
        "app.release_gate_cli.wait_for_compose_health",
        lambda *, project_root=None, **_kwargs: {
            "db": "healthy",
            "api": "healthy",
            "worker": "healthy",
            "agent-worker": "healthy",
        },
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: None,
    )

    exit_code = main([])

    assert exit_code == 0
    payload = json.loads(tmp_path.joinpath(RELEASE_GATE_REPORT_RELATIVE_PATH).read_text())
    assert payload["status"] == "passed"
    assert payload["exit_code"] == 0
    assert payload["artifacts"]["diagnostics_captured"] is False
    assert payload["compose"]["health_statuses"] == {
        "db": "healthy",
        "api": "healthy",
        "worker": "healthy",
        "agent-worker": "healthy",
    }
    assert [step["name"] for step in payload["steps"]] == [
        "ruff",
        "improvement-case-validate",
        "alembic-upgrade-head",
        "alembic-current",
        "db-model-metadata",
        "compose-config",
        "compose-up",
        "full-integration",
    ]


def test_release_gate_cli_writes_report_artifact_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)

    def fake_run_step(step, *, project_root=None):
        if step.name == "full-integration":
            raise SystemExit(1)

    monkeypatch.setattr("app.release_gate_cli.run_step", fake_run_step)
    monkeypatch.setattr(
        "app.release_gate_cli.wait_for_compose_health",
        lambda *, project_root=None, **_kwargs: {
            "db": "healthy",
            "api": "healthy",
            "worker": "healthy",
            "agent-worker": "healthy",
        },
    )
    monkeypatch.setattr(
        "app.release_gate_cli.capture_failure_artifacts",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.release_gate_cli.compose_down",
        lambda *, project_root=None: None,
    )

    exit_code = main([])

    assert exit_code == 1
    payload = json.loads(tmp_path.joinpath(RELEASE_GATE_REPORT_RELATIVE_PATH).read_text())
    assert payload["status"] == "failed"
    assert payload["exit_code"] == 1
    assert payload["failing_step"] == "full-integration"
    assert payload["artifacts"]["diagnostics_captured"] is True
    assert payload["steps"][-1]["name"] == "full-integration"
    assert payload["steps"][-1]["status"] == "failed"


def test_capture_failure_artifacts_writes_summary_and_compose_outputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command, *, cwd, env, check, capture_output, text):
        commands.append(command)
        stdout = ""
        if command[:4] == ["docker", "compose", "ps", "-q"]:
            stdout = f"{command[-1]}-container-id\n"
        elif command[:3] == ["docker", "compose", "ps"]:
            stdout = "NAME IMAGE COMMAND SERVICE CREATED STATUS PORTS\n"
        elif command[:2] == ["docker", "inspect"]:
            stdout = '{"Status":"healthy"}\n'
        elif command[:3] == ["docker", "compose", "logs"]:
            stdout = f"{command[-1]} logs\n"
        return type("CompletedProcess", (), {"returncode": 0, "stdout": stdout, "stderr": ""})()

    monkeypatch.setattr("app.release_gate_cli.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.release_gate_cli.subprocess.run", fake_run)

    capture_failure_artifacts(
        project_root=tmp_path,
        failing_step="compose-up",
        exit_code=1,
        failure_message="compose health timed out",
    )

    artifact_dir = tmp_path / "build" / "release-gate-parity" / "failure"
    assert artifact_dir.joinpath("summary.txt").read_text() == (
        "release_gate_failure\n"
        "exit_code=1\n"
        "failing_step=compose-up\n"
        "message=compose health timed out\n"
    )
    assert artifact_dir.joinpath("docker-compose-ps.txt").exists()
    for service_name in ("db", "api", "worker", "agent-worker"):
        assert artifact_dir.joinpath(f"{service_name}-container-id.txt").exists()
        assert artifact_dir.joinpath(f"{service_name}-health.txt").exists()
        assert artifact_dir.joinpath(f"{service_name}-logs.txt").exists()
    assert ["docker", "compose", "ps"] in commands
