from __future__ import annotations

from app.core.logging import get_logger
from app.services.agent_task_worker import run_agent_task_worker_loop

logger = get_logger(__name__)


def run() -> None:
    logger.info("agent_worker_starting")
    run_agent_task_worker_loop()


if __name__ == "__main__":
    run()
