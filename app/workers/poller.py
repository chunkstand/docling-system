from __future__ import annotations

from app.core.logging import get_logger
from app.services.capabilities import run_lifecycle

logger = get_logger(__name__)


def run() -> None:
    logger.info("worker_starting")
    run_lifecycle.run_worker_loop()


if __name__ == "__main__":
    run()
