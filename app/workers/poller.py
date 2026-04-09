from __future__ import annotations

from app.core.logging import get_logger
from app.services.runs import run_worker_loop

logger = get_logger(__name__)

def run() -> None:
    logger.info("worker_starting")
    run_worker_loop()
