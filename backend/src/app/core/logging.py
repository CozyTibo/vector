"""Stdout logging for ECS / CloudWatch (Uvicorn-aligned)."""

from __future__ import annotations

import logging
import sys

_configured = False


def setup_logging() -> None:
    """Configure root logging once: single StreamHandler on stdout, no duplicates."""
    global _configured
    if _configured:
        return
    _configured = True

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn.error").propagate = True
    logging.getLogger("uvicorn.access").propagate = True
