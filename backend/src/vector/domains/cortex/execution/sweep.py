"""Execution sweeper — authoritative scheduler for dirty tenants."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.lease import list_tenants_for_convergence_sweep_v1
from vector.domains.cortex.execution.tcre_waiting_sweep import (
    list_tenants_waiting_on_tcre_for_sweep_v1,
    sweep_tcre_waiting_tenant_v1,
)
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)


def run_convergence_sweep_v1(
    session: Session,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    limit = max(1, min(int(cfg.cortex_convergence_sweeper_limit), 500))
    tenant_ids = list_tenants_for_convergence_sweep_v1(session, limit=limit, settings=cfg)
    waiting_ids = list_tenants_waiting_on_tcre_for_sweep_v1(
        session,
        limit=max(1, limit // 4),
        settings=cfg,
    )
    merged: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for tid in [*tenant_ids, *waiting_ids]:
        if tid not in seen:
            seen.add(tid)
            merged.append(tid)
    enqueued: list[str] = []
    tcre_swept: list[str] = []
    for tid in merged:
        if tid in waiting_ids:
            try:
                sweep_tcre_waiting_tenant_v1(session, tenant_id=tid, settings=cfg)
                session.commit()
                tcre_swept.append(str(tid))
            except Exception:  # noqa: BLE001
                session.rollback()
                _LOGGER.warning(
                    "execution_sweep_tcre_waiting_failed tenant_id=%s",
                    tid,
                    exc_info=True,
                )
        try:
            enqueue_tenant_convergence_v1(tid, reason="sweep")
            enqueued.append(str(tid))
        except Exception:  # noqa: BLE001
            _LOGGER.warning("execution_sweep_enqueue_failed tenant_id=%s", tid, exc_info=True)
    _LOGGER.info(
        "execution_sweep_done candidates=%s waiting_tcre=%s enqueued=%s",
        len(merged),
        len(waiting_ids),
        len(enqueued),
    )
    return {
        "candidates": len(merged),
        "dirty_stalled_candidates": len(tenant_ids),
        "waiting_tcre_candidates": len(waiting_ids),
        "tcre_waiting_swept": len(tcre_swept),
        "enqueued": len(enqueued),
        "tenant_ids": enqueued,
    }


run_execution_sweep_v1 = run_convergence_sweep_v1
