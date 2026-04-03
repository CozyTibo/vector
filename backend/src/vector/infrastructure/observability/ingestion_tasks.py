"""Structured logging for Celery ingestion tasks (log aggregation / metrics from logs).

Uses ``extra=`` keys prefixed with ``ing_`` to avoid clashes with :class:`logging.LogRecord`
built-in attributes. Downstream stacks (Datadog, CloudWatch, Loki) can index ``ing_*`` fields.
"""

from __future__ import annotations

import logging
from typing import Any

# Phases (pipeline position), not Celery lifecycle.
PHASE_SWEEP = "sweep"
PHASE_STEP1 = "step1"
PHASE_STEP2 = "step2"
PHASE_STEP3 = "step3"


def log_ingestion_event(
    logger: logging.Logger,
    level: int,
    message: str,
    *,
    task_name: str,
    phase: str,
    outcome: str,
    run_id: str | None = None,
    tenant_id: str | None = None,
    connector: str | None = None,
    run_status: str | None = None,
    **extra: Any,
) -> None:
    """Emit one structured log line; extra kwargs become ``ing_*`` fields when unprefixed."""
    payload: dict[str, Any] = {
        "ing_task": task_name,
        "ing_phase": phase,
        "ing_outcome": outcome,
        "ing_run_id": run_id or "",
        "ing_tenant_id": tenant_id or "",
        "ing_connector": connector or "",
        "ing_run_status": run_status or "",
    }
    for k, v in extra.items():
        key = k if k.startswith("ing_") else f"ing_{k}"
        payload[key] = v
    logger.log(level, message, extra=payload)
