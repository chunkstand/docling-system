from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.files import repo_root

COMPOSE_PROJECT_POSTGRES_PORT = "5434"
COMPOSE_SMOKE_TIMEOUT_SECONDS = 180
COMPOSE_SMOKE_POLL_INTERVAL_SECONDS = 2


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
    path = project_root / ".tmp" / "release-gate"
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def run_step(
    step: ReleaseGateStep,
    *,
    project_root: Path | None = None,
) -> None:
    root = project_root or repo_root()
    print(f"==> {step.name}: {_format_step(step)}")
    completed = subprocess.run(
        list(step.command),
        cwd=root,
        env=_step_env(step),
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


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
    env = os.environ.copy()
    env["DOCLING_SYSTEM_POSTGRES_PORT"] = postgres_port
    service_names = ("db", "api", "worker", "agent-worker")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        statuses = {
            service_name: _container_health_status(service_name, project_root=root, env=env)
            for service_name in service_names
        }
        if all(status == "healthy" for status in statuses.values()):
            return
        time.sleep(poll_interval_seconds)
    rendered = ", ".join(f"{name}={status}" for name, status in statuses.items())
    raise RuntimeError(f"Compose health did not converge within {timeout_seconds}s: {rendered}")


def compose_down(*, project_root: Path | None = None) -> None:
    root = project_root or repo_root()
    env = os.environ.copy()
    env["DOCLING_SYSTEM_POSTGRES_PORT"] = COMPOSE_PROJECT_POSTGRES_PORT
    subprocess.run(
        ["docker", "compose", "down"],
        cwd=root,
        env=env,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root()
    steps = build_release_gate_steps(project_root=root)
    if args.list_steps:
        for step in steps:
            print(f"{step.name}: {_format_step(step)}")
        return 0

    compose_started = False
    try:
        for step in steps:
            if step.name == "compose-up":
                compose_started = True
            run_step(step, project_root=root)
            if step.name == "compose-up":
                wait_for_compose_health(project_root=root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        if compose_started:
            compose_down(project_root=root)
    return 0


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
