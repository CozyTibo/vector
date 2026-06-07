"""Phase 01 Step 2 — enumerate tenant×connector pairs eligible for scheduled live-lane sync."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.cortex_ingestion_policy import (
    SUPPORTED_CONNECTOR_IDS,
    should_route_ingestion_to_cortex,
)
from vector.domains.cortex.ingestion.checkpoint_contract import checkpoint_last_incremental_at
from vector.domains.cortex.ingestion.live_queue_pending import (
    clear_live_queue_pending,
    is_live_queue_pending,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import Settings

SCOPE_DEFAULT = "default"


class RoutedSyncJob(NamedTuple):
    tenant_id: uuid.UUID
    connection_id: uuid.UUID
    connector_id: str


def _parse_last_incremental_at(state: dict[str, object]) -> datetime | None:
    raw = checkpoint_last_incremental_at(state)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        s = raw.strip().replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


_RUNNING_STATUSES = frozenset({"running", "RUNNING"})


def _has_running_ingestion_run(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector_id: str,
) -> bool:
    """Skip enqueue when a scheduled sync is already in flight for this connection."""
    row = session.scalar(
        select(IngestionRun.id)
        .where(
            IngestionRun.tenant_id == tenant_id,
            IngestionRun.connection_id == connection_id,
            IngestionRun.connector == connector_id,
            IngestionRun.status.in_(tuple(sorted(_RUNNING_STATUSES))),
        )
        .limit(1),
    )
    return row is not None


def _past_min_gap(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector_id: str,
) -> bool:
    """True when we should enqueue another sync (cooldown elapsed)."""
    gap = max(0, settings.cortex_ingestion_min_gap_seconds)
    if gap == 0:
        return True
    stmt = select(ConnectorSyncState).where(
        ConnectorSyncState.tenant_id == tenant_id,
        ConnectorSyncState.connection_id == connection_id,
        ConnectorSyncState.connector == connector_id,
        ConnectorSyncState.scope_key == SCOPE_DEFAULT,
    )
    row = session.scalar(stmt)
    if row is None:
        return True
    last = _parse_last_incremental_at(dict(row.state))
    if last is None:
        return True
    return datetime.now(tz=UTC) - last >= timedelta(seconds=gap)


def iter_routed_live_sync_jobs(session: Session, settings: Settings) -> list[RoutedSyncJob]:
    """Active connections whose tenant×connector is flagged onto Cortex and past min-gap."""
    if not settings.cortex_ingestion_scheduler_enabled:
        return []

    stmt = select(TenantConnection).where(
        TenantConnection.status == "active",
        TenantConnection.provider.in_(tuple(sorted(SUPPORTED_CONNECTOR_IDS))),
    )
    conns = list(session.scalars(stmt).all())
    out: list[RoutedSyncJob] = []
    for tc in conns:
        if not should_route_ingestion_to_cortex(settings, tc.provider, tc.tenant_id):
            continue
        if not _past_min_gap(
            session,
            settings,
            tenant_id=tc.tenant_id,
            connection_id=tc.id,
            connector_id=tc.provider,
        ):
            continue
        if _has_running_ingestion_run(
            session,
            tenant_id=tc.tenant_id,
            connection_id=tc.id,
            connector_id=tc.provider,
        ):
            continue
        out.append(RoutedSyncJob(tenant_id=tc.tenant_id, connection_id=tc.id, connector_id=tc.provider))
    return out


def reconcile_orphan_live_queue_pending(
    session: Session,
    settings: Settings,
    jobs: list[RoutedSyncJob],
) -> int:
    """Drop stale Redis reservations left when a worker dies before releasing pending."""
    cleared = 0
    for job in jobs:
        if not is_live_queue_pending(
            settings,
            tenant_id=job.tenant_id,
            connection_id=job.connection_id,
        ):
            continue
        if _has_running_ingestion_run(
            session,
            tenant_id=job.tenant_id,
            connection_id=job.connection_id,
            connector_id=job.connector_id,
        ):
            continue
        clear_live_queue_pending(
            settings,
            tenant_id=job.tenant_id,
            connection_id=job.connection_id,
        )
        cleared += 1
    return cleared


def filter_jobs_without_broker_pending(
    jobs: list[RoutedSyncJob],
    settings: Settings,
) -> list[RoutedSyncJob]:
    """Drop tenant×connector pairs that already have a ``cortex_live`` reservation."""
    return [
        job
        for job in jobs
        if not is_live_queue_pending(
            settings,
            tenant_id=job.tenant_id,
            connection_id=job.connection_id,
        )
    ]


def apply_per_tenant_fair_enqueue_cap(
    jobs: list[RoutedSyncJob],
    settings: Settings,
) -> list[RoutedSyncJob]:
    """Round-robin across tenants so one workspace cannot monopolize FIFO ``cortex_live``."""
    if not jobs:
        return []
    cap = max(1, int(settings.cortex_ingestion_scheduler_max_jobs_per_tenant_per_tick))
    by_tenant: dict[uuid.UUID, list[RoutedSyncJob]] = defaultdict(list)
    for job in jobs:
        by_tenant[job.tenant_id].append(job)
    for bucket in by_tenant.values():
        bucket.sort(key=lambda j: (j.connector_id, str(j.connection_id)))

    tenant_ids = sorted(by_tenant.keys(), key=str)
    taken: dict[uuid.UUID, int] = dict.fromkeys(tenant_ids, 0)
    out: list[RoutedSyncJob] = []
    while True:
        progressed = False
        for tenant_id in tenant_ids:
            if taken[tenant_id] >= cap:
                continue
            bucket = by_tenant[tenant_id]
            idx = taken[tenant_id]
            if idx >= len(bucket):
                continue
            out.append(bucket[idx])
            taken[tenant_id] += 1
            progressed = True
        if not progressed:
            break
    return out


def select_sync_jobs_to_enqueue(
    session: Session,
    settings: Settings,
) -> tuple[list[RoutedSyncJob], list[RoutedSyncJob]]:
    """Eligible jobs after DB checks, broker-pending filter, and per-tenant fair cap."""
    candidates = iter_routed_live_sync_jobs(session, settings)
    reconcile_orphan_live_queue_pending(session, settings, candidates)
    eligible = filter_jobs_without_broker_pending(candidates, settings)
    to_enqueue = apply_per_tenant_fair_enqueue_cap(eligible, settings)
    return candidates, to_enqueue
