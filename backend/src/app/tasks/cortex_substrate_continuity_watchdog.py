"""Periodic watchdog for stalled substrate pipeline continuations (**G-P085-WATCH-01**)."""

from __future__ import annotations

import logging
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.substrate_continuity_watchdog import (
    CELERY_CONTINUITY_WATCHDOG_TASK_NAME_V1,
    get_watchdog_auto_recover_enabled_v1,
    get_watchdog_stall_threshold_seconds_v1,
)
from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
    run_stalled_pipeline_watchdog_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK = CELERY_CONTINUITY_WATCHDOG_TASK_NAME_V1

CELERY_TASK_NAME_SUBSTRATE_CONTINUITY_WATCHDOG = _TASK


@celery_app.task(name=_TASK, queue="vector")
def run_substrate_continuity_watchdog_task() -> dict[str, Any]:
    """Celery beat entry — default **600s** schedule in ``celery_app.conf.beat_schedule``."""
    from vector.settings import get_settings

    cfg = get_settings()
    if cfg.cortex_convergence_runtime_enabled and cfg.cortex_convergence_disable_legacy_progression_beat:
        return {"skipped": True, "reason": "convergence_runtime_authoritative"}

    threshold = get_watchdog_stall_threshold_seconds_v1()
    auto_recover = get_watchdog_auto_recover_enabled_v1()
    _LOGGER.info(
        "substrate_continuity_watchdog_start threshold_s=%s auto_recover=%s task=%s",
        threshold,
        auto_recover,
        _TASK,
    )
    with session_scope() as session:
        out = run_stalled_pipeline_watchdog_v1(
            session,
            stall_threshold_seconds=threshold,
            auto_recover=auto_recover,
            limit=50,
        )
    audit = dict(out.get("audit") or {})
    _LOGGER.info(
        "substrate_continuity_watchdog_done watchdog_run_id=%s stalled=%s recovered_ok=%s",
        out.get("watchdog_run_id"),
        out.get("stalled_count"),
        audit.get("recoveries_succeeded"),
    )
    return out
