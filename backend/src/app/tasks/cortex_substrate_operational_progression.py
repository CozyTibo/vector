"""Celery — periodic substrate operational progression tick (eventual convergence)."""

from __future__ import annotations

import logging
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.substrate_operational_progression import (
    CELERY_SUBSTRATE_PROGRESSION_TICK_TASK_NAME_V1,
    run_substrate_progression_tick_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_SUBSTRATE_PROGRESSION_TICK_TASK_NAME_V1


@celery_app.task(name=_TASK, queue="vector")
def run_substrate_operational_progression_tick_task() -> dict[str, Any]:
    """Sweep active pipeline runs and continue downstream phases (**G-P085-PROG-CLOSE**)."""
    from vector.settings import get_settings

    cfg = get_settings()
    if cfg.cortex_convergence_disable_legacy_progression_beat:
        return {"skipped": True, "reason": "convergence_runtime_authoritative"}
    if not cfg.cortex_substrate_operational_progression_tick_enabled:
        return {"skipped": True, "reason": "progression_tick_disabled"}

    limit = max(1, min(int(cfg.cortex_substrate_operational_progression_tick_limit), 200))
    _LOGGER.info("substrate_progression_tick_start limit=%s", limit)
    with session_scope() as session:
        out = run_substrate_progression_tick_v1(session, limit=limit)
        session.commit()
    _LOGGER.info(
        "substrate_progression_tick_done examined=%s",
        out.get("pipeline_runs_examined"),
    )
    return out
