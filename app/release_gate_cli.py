from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.files import repo_root

COMPOSE_PROJECT_POSTGRES_PORT = "5434"
COMPOSE_SMOKE_TIMEOUT_SECONDS = 180
COMPOSE_SMOKE_POLL_INTERVAL_SECONDS = 2
FAILURE_ARTIFACTS_RELATIVE_PATH = Path("build/release-gate-parity/failure")
COMPOSE_SERVICE_NAMES = ("db", "api", "worker", "agent-worker")


@dataclass(frozen=True)
class ReleaseGateStep:
    name: str
    command: tuple[str, ...]
    env: tuple[tuple[str, str], ...] = ()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the canonical local release gate used for CI parity."
    )
    parser.add_argument(
        "--list-steps",
        action="store_true",
        help="Print the canonical step names and commands without executing them.",
    )
    return parser


def _tmpdir(project_root: Path) -> Path:
    return project_root / ".tmp" / "release-gate"


def _failure_artifact_dir(project_root: Path) -> Path:
    return project_root / FAILURE_ARTIFACTS_RELATIVE_PATH


def build_release_gate_steps(*, project_root: Path | None = None) -> tuple[ReleaseGateStep, ...]:
    root = project_root or repo_root()
    tmpdir = _tmpdir(root)
    integration_env = (
        ("DOCLING_SYSTEM_RUN_INTEGRATION", "1"),
        ("TMPDIR", tmpdir.as_posix()),
    )
    compose_env = (("DOCLING_SYSTEM_POSTGRES_PORT", COMPOSE_PROJECT_POSTGRES_PORT),)
    return (
        ReleaseGateStep("ruff", ("uv", "run", "ruff", "check")),
        ReleaseGateStep(
            "improvement-case-validate",
            ("uv", "run", "docling-system-improvement-case-validate"),
        ),
        ReleaseGateStep(
            "alembic-upgrade-head",
            ("uv", "run", "--extra", "dev", "alembic", "upgrade", "head"),
        ),
        ReleaseGateStep(
            "alembic-current",
            ("uv", "run", "--extra", "dev", "alembic", "current"),
        ),
        ReleaseGateStep(
            "db-model-metadata",
            (
                "uv",
                "run",
                "--extra",
                "dev",
                "python",
                "-m",
                "pytest",
                "-q",
                "tests/integration/test_db_model_metadata.py",
                "-rs",
            ),
            env=integration_env,
        ),
        ReleaseGateStep(
            "compose-config",
            ("docker", "compose", "config", "--quiet"),
        ),
        ReleaseGateStep(
            "compose-up",
            ("docker", "compose", "up", "-d", "db", "api", "worker", "agent-worker"),
            env=compose_env,
        ),
        ReleaseGateStep(
            "full-integration",
            (
                "uv",
                "run",
                "--extra",
                "dev",
                "python",
                "-m",
                "pytest",
                "-q",
                "-rs",
            ),
            env=integration_env,
        ),
    )


def _format_step(step: ReleaseGateStep) -> str:
    env_prefix = " ".join(f"{key}={value}" for key, value in step.env)
    command = " ".join(step.command)
    if env_prefix:
        return f"{env_prefix} {command}"
    return command


def _step_env(step: ReleaseGateStep) -> dict[str, str]:
    env = os.environ.copy()
    env.update(dict(step.env))
    return env


def _prepare_step_dirs(step: ReleaseGateStep) -> None:
    for key, value in step.env:
        if key == "TMPDIR":
            Path(value).mkdir(parents=True, exist_ok=True)


def _compose_env(*, postgres_port: str = COMPOSE_PROJECT_POSTGRES_PORT) -> dict[str, str]:
    env = os.environ.copy()
    env["DOCLING_SYSTEM_POSTGRES_PORT"] = postgres_port
    return env


def run_step(
    step: ReleaseGateStep,
    *,
    project_root: Path | None = None,
) -> None:
    root = project_root or repo_root()
    _prepare_step_dirs(step)
    print(f"==> {step.name}: {_format_step(step)}")
    completed = subprocess.run(
        list(step.command),
        cwd=root,
        env=_step_env(step),
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def reset_failure_artifacts(*, project_root: Path | None = None) -> None:
    root = project_root or repo_root()
    shutil.rmtree(_failure_artifact_dir(root), ignore_errors=True)


def cleanup_tmpdir(*, project_root: Path | None = None) -> None:
    root = project_root or repo_root()
    target = _tmpdir(root).resolve()
    active_tmpdir = os.environ.get("TMPDIR")
    if active_tmpdir:
        active_path = Path(active_tmpdir).resolve()
        if active_path == target or active_path.is_relative_to(target):
            return
    shutil.rmtree(target, ignore_errors=True)


def _write_command_output(
    path: Path,
    command: list[str],
    *,
    project_root: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=project_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    rendered = f"$ {' '.join(command)}\nexit_code={completed.returncode}\n"
    if completed.stdout:
        rendered += f"\n[stdout]\n{completed.stdout}"
    if completed.stderr:
        rendered += f"\n[stderr]\n{completed.stderr}"
    path.write_text(rendered)
    return completed


def capture_failure_artifacts(
    *,
    project_root: Path | None = None,
    failing_step: str | None,
    exit_code: int,
    failure_message: str | None,
    postgres_port: str = COMPOSE_PROJECT_POSTGRES_PORT,
) -> None:
    root = project_root or repo_root()
    artifact_dir = _failure_artifact_dir(root)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary = [
        "release_gate_failure",
        f"exit_code={exit_code}",
        f"failing_step={failing_step or 'unknown'}",
    ]
    if failure_message:
        summary.append(f"message={failure_message}")
    artifact_dir.joinpath("summary.txt").write_text("\n".join(summary) + "\n")

    env = _compose_env(postgres_port=postgres_port)
    _write_command_output(
        artifact_dir / "docker-compose-ps.txt",
        ["docker", "compose", "ps"],
        project_root=root,
        env=env,
    )
    for service_name in COMPOSE_SERVICE_NAMES:
        container_id_result = _write_command_output(
            artifact_dir / f"{service_name}-container-id.txt",
            ["docker", "compose", "ps", "-q", service_name],
            project_root=root,
            env=env,
        )
        container_id = container_id_result.stdout.strip()
        if container_id:
            _write_command_output(
                artifact_dir / f"{service_name}-health.txt",
                ["docker", "inspect", container_id, "--format", "{{json .State.Health}}"],
                project_root=root,
                env=env,
            )
        _write_command_output(
            artifact_dir / f"{service_name}-logs.txt",
            ["docker", "compose", "logs", "--no-color", service_name],
            project_root=root,
            env=env,
        )


def _compose_container_id(service_name: str, *, project_root: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        ["docker", "compose", "ps", "-q", service_name],
        cwd=project_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"docker compose ps -q {service_name} failed")
    container_id = completed.stdout.strip()
    if not container_id:
        raise RuntimeError(f"No running container id found for compose service '{service_name}'.")
    return container_id


def _container_health_status(
    service_name: str,
    *,
    project_root: Path,
    env: dict[str, str],
) -> str:
    container_id = _compose_container_id(service_name, project_root=project_root, env=env)
    completed = subprocess.run(
        ["docker", "inspect", container_id, "--format", "{{.State.Health.Status}}"],
        cwd=project_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"docker inspect health status failed for '{service_name}'.")
    return completed.stdout.strip()


def wait_for_compose_health(
    *,
    project_root: Path | None = None,
    timeout_seconds: int = COMPOSE_SMOKE_TIMEOUT_SECONDS,
    poll_interval_seconds: int = COMPOSE_SMOKE_POLL_INTERVAL_SECONDS,
    postgres_port: str = COMPOSE_PROJECT_POSTGRES_PORT,
) -> None:
    root = project_root or repo_root()
    env = _compose_env(postgres_port=postgres_port)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        statuses = {
            service_name: _container_health_status(service_name, project_root=root, env=env)
            for service_name in COMPOSE_SERVICE_NAMES
        }
        if all(status == "healthy" for status in statuses.values()):
            return
        time.sleep(poll_interval_seconds)
    rendered = ", ".join(f"{name}={status}" for name, status in statuses.items())
    raise RuntimeError(f"Compose health did not converge within {timeout_seconds}s: {rendered}")


def compose_down(*, project_root: Path | None = None) -> None:
    root = project_root or repo_root()
    subprocess.run(
        ["docker", "compose", "down"],
        cwd=root,
        env=_compose_env(),
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root()
    reset_failure_artifacts(project_root=root)
    cleanup_tmpdir(project_root=root)
    steps = build_release_gate_steps(project_root=root)
    if args.list_steps:
        for step in steps:
            print(f"{step.name}: {_format_step(step)}")
        return 0

    compose_started = False
    exit_code = 0
    failure_message: str | None = None
    failing_step: str | None = None
    try:
        for step in steps:
            failing_step = step.name
            if step.name == "compose-up":
                compose_started = True
            run_step(step, project_root=root)
            if step.name == "compose-up":
                wait_for_compose_health(project_root=root)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
    except RuntimeError as exc:
        exit_code = 1
        failure_message = str(exc)
    finally:
        if exit_code != 0:
            capture_failure_artifacts(
                project_root=root,
                failing_step=failing_step,
                exit_code=exit_code,
                failure_message=failure_message,
            )
        if compose_started:
            compose_down(project_root=root)
        cleanup_tmpdir(project_root=root)
    if failure_message:
        print(failure_message, file=sys.stderr)
    return exit_code


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
