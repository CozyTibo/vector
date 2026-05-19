"""Convergence sweeper — only authoritative scheduler for dirty tenants."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.convergence.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.convergence.lease import list_tenants_for_convergence_sweep_v1
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
    enqueued: list[str] = []
    for tid in tenant_ids:
        try:
            enqueue_tenant_convergence_v1(tid, reason="sweep")
            enqueued.append(str(tid))
        except Exception:  # noqa: BLE001
            _LOGGER.warning("convergence_sweep_enqueue_failed tenant_id=%s", tid, exc_info=True)
    _LOGGER.info(
        "convergence_sweep_done candidates=%s enqueued=%s",
        len(tenant_ids),
        len(enqueued),
    )
    return {
        "candidates": len(tenant_ids),
        "enqueued": len(enqueued),
        "tenant_ids": enqueued,
    }
