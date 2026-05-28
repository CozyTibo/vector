"""Graph pass run recovery helpers."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.graph_pass_run import GraphPassRun

RUN_RUNNING = "RUNNING"


def abandon_stuck_running_graph_passes(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    interval_seconds: int,
) -> int:
    window = max(120, int(interval_seconds) * 2)
    cutoff = utc_now() - timedelta(seconds=window)
    rows = list(
        session.scalars(
            select(GraphPassRun).where(
                GraphPassRun.tenant_id == tenant_id,
                GraphPassRun.status == RUN_RUNNING,
                GraphPassRun.started_at < cutoff,
            ),
        ).all(),
    )
    for row in rows:
        row.status = "FAILED"
        row.finished_at = utc_now()
        row.error_summary = "abandoned_stuck_running"
    return len(rows)
