"""Authoritative tenant substrate convergence (lease + worker + sweeper)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.convergence.run_convergence import run_tenant_convergence_v1
from vector.domains.cortex.convergence.sweep import run_convergence_sweep_v1
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger("app")

_TASK_RUN = "vector.cortex.convergence.run_tenant"
_TASK_SWEEP = "vector.cortex.convergence.sweep"


@celery_app.task(name=_TASK_RUN, queue="vector", bind=True, max_retries=2)
def run_tenant_convergence_task(
    self,
    tenant_id: str,
    reason: str = "worker",
) -> dict[str, Any]:
    cfg = get_settings()
    if not cfg.cortex_convergence_runtime_enabled:
        return {"skipped": True, "reason": "convergence_runtime_disabled"}
    tid = uuid.UUID(tenant_id)
    _LOGGER.info("convergence_worker_start tenant_id=%s reason=%s", tenant_id, reason)
    with session_scope() as session:
        out = run_tenant_convergence_v1(
            session,
            tenant_id=tid,
            settings=cfg,
            reason=reason,
            celery_task_id=str(self.request.id),
        )
        session.commit()
    _LOGGER.info("convergence_worker_done tenant_id=%s outcome=%s", tenant_id, out.get("outcome"))
    return out


@celery_app.task(name=_TASK_SWEEP, queue="vector")
def run_convergence_sweep_task() -> dict[str, Any]:
    cfg = get_settings()
    if not cfg.cortex_convergence_runtime_enabled:
        return {"skipped": True, "reason": "convergence_runtime_disabled"}
    if not cfg.cortex_convergence_sweeper_enabled:
        return {"skipped": True, "reason": "sweeper_disabled"}
    _LOGGER.info("convergence_sweep_start")
    with session_scope() as session:
        out = run_convergence_sweep_v1(session, settings=cfg)
        session.commit()
    return out
