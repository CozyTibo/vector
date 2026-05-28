"""Admin-facing canon readiness builders."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.inventory import build_tenant_canon_readiness
from vector.domains.cortex.runtime.lane_scheduler_status import build_canon_lane_scheduler_status
from vector.settings import Settings


def _dirty_queue_depth(session: Session, tenant_id: uuid.UUID) -> int:
    try:
        from vector.infrastructure.db.models.canon_dirty_queue import CanonDirtyQueue
    except ImportError:
        return 0
    return int(
        session.scalar(
            select(func.count())
            .select_from(CanonDirtyQueue)
            .where(
                CanonDirtyQueue.tenant_id == tenant_id,
                CanonDirtyQueue.processed_at.is_(None),
            ),
        )
        or 0,
    )


def _registry_disposition() -> dict[str, str]:
    try:
        from vector.domains.cortex.canon.resource_type_registry import disposition_by_resource_type

        return disposition_by_resource_type()
    except ImportError:
        return {}


def build_canon_admin_readiness(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    payload = build_tenant_canon_readiness(
        session,
        tenant_id,
        registry_disposition=_registry_disposition(),
        dirty_queue_depth=_dirty_queue_depth(session, tenant_id),
    )
    interval = max(60, int(settings.cortex_canon_scheduler_interval_seconds))
    payload["scheduler"] = build_canon_lane_scheduler_status(
        session,
        tenant_id=tenant_id,
        enabled=settings.cortex_canon_scheduler_enabled,
        interval_seconds=interval,
    )
    return payload


def list_recent_canon_pass_runs(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    from vector.infrastructure.db.models.canon_pass_run import CanonPassRun

    total = session.scalar(
        select(func.count()).where(CanonPassRun.tenant_id == tenant_id),
    ) or 0
    rows = list(
        session.scalars(
            select(CanonPassRun)
            .where(CanonPassRun.tenant_id == tenant_id)
            .order_by(CanonPassRun.started_at.desc())
            .offset(offset)
            .limit(limit),
        ).all(),
    )
    items = [
        {
            "id": str(r.id),
            "status": r.status,
            "source_trigger": r.source_trigger,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "error_summary": r.error_summary,
            "stats": r.stats,
        }
        for r in rows
    ]
    return items, int(total)
