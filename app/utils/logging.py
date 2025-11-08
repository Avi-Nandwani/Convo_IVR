# app/utils/logging.py
"""
Small logging helper.

Usage:
    from app.utils.logging import get_logger
    logger = get_logger("module.name")

This sets a simple console formatter if no handlers are configured.
"""
import logging
from typing import Optional

DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    # If root has no handlers, configure a default one (useful in scripts)
    if not logging.getLogger().handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(DEFAULT_FORMAT)
        handler.setFormatter(fmt)
        logging.getLogger().addHandler(handler)

    if level:
        logger.setLevel(level.upper())
    return logger
