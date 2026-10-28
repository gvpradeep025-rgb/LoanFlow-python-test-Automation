"""Centralised logging configuration for the LoanFlow framework."""

from __future__ import annotations

import logging

from loanflow.config import LoanFlowConfig, load_config

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(config: LoanFlowConfig | None = None) -> logging.Logger:
    """Configure and return the ``loanflow`` logger."""
    resolved = config or load_config()
    level = getattr(logging, str(resolved.log_level).upper(), logging.INFO)

    logger = logging.getLogger("loanflow")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    return logger
