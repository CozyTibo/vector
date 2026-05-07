"""Phase 01 Step 2 — enumerate tenant×connector pairs eligible for scheduled live-lane sync."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.cortex_ingestion_policy import (
    SUPPORTED_CONNECTOR_IDS,
    should_route_ingestion_to_cortex,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import Settings

SCOPE_DEFAULT = "default"


class RoutedSyncJob(NamedTuple):
    tenant_id: uuid.UUID
    connection_id: uuid.UUID
    connector_id: str


def _parse_last_incremental_at(state: dict[str, object]) -> datetime | None:
    raw = state.get("last_incremental_at")
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
        out.append(RoutedSyncJob(tenant_id=tc.tenant_id, connection_id=tc.id, connector_id=tc.provider))
    return out
