"""Convergence Celery tasks — sweeper only (S5.1: ``run_tenant`` alias removed).

Tenant execution uses ``app.tasks.cortex_execution.run_execution_slice_task`` exclusively.
"""

from __future__ import annotations

import logging
from typing import Any

from app.celery_app import celery_app
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger("app")

_TASK_SWEEP = "vector.cortex.convergence.sweep"

CELERY_CONVERGENCE_SWEEP_TASK_NAME_V1 = _TASK_SWEEP


@celery_app.task(name=_TASK_SWEEP, queue="vector")
def run_convergence_sweep_task() -> dict[str, Any]:
    from vector.domains.cortex.execution.sweep import run_convergence_sweep_v1

    cfg = get_settings()
    if not cfg.cortex_convergence_sweeper_enabled:
        return {"skipped": True, "reason": "sweeper_disabled"}
    with session_scope() as session:
        out = run_convergence_sweep_v1(session, settings=cfg)
        session.commit()
    return out
