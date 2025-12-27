from __future__ import annotations

import sys
from loguru import logger

from app.config import settings


def configure_logging() -> None:
    """Configure Loguru once for the whole app."""
    # Avoid duplicate handlers if imported multiple times
    logger.remove()

    level = (settings.LOG_LEVEL or "INFO").upper()

    # Console
    logger.add(sys.stderr, level=level, backtrace=False, diagnose=False)

    # File (rotates, keeps a few backups)
    logger.add(
        "lifeos.log",
        level=level,
        rotation="5 MB",
        retention=3,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )


__all__ = ["logger", "configure_logging"]
