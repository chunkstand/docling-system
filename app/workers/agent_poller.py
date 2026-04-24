from __future__ import annotations

from app.core.logging import get_logger
from app.services.capabilities import agent_orchestration

logger = get_logger(__name__)


def run() -> None:
    logger.info("agent_worker_starting")
    agent_orchestration.run_worker_loop()


if __name__ == "__main__":
    run()
