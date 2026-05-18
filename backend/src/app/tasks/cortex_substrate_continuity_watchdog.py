"""Periodic watchdog for stalled substrate pipeline continuations."""

from __future__ import annotations

import logging
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
    run_stalled_pipeline_watchdog_v1,
)
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger("app")

_TASK = "vector.cortex.substrate_pipeline.continuity_watchdog"


@celery_app.task(name=_TASK, queue="vector")
def run_substrate_continuity_watchdog_task() -> dict[str, Any]:
    cfg = get_settings()
    threshold = int(getattr(cfg, "cortex_substrate_continuation_stall_seconds", 1800))
    auto_recover = bool(getattr(cfg, "cortex_substrate_continuation_auto_recover", True))
    _LOGGER.info(
        "substrate_continuity_watchdog_start threshold_s=%s auto_recover=%s",
        threshold,
        auto_recover,
    )
    with session_scope() as session:
        out = run_stalled_pipeline_watchdog_v1(
            session,
            stall_threshold_seconds=threshold,
            auto_recover=auto_recover,
            limit=50,
        )
    _LOGGER.info(
        "substrate_continuity_watchdog_done stalled=%s recovered=%s",
        out.get("stalled_count"),
        len(out.get("recovered") or []),
    )
    return out
