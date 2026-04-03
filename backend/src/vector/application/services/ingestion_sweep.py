"""Periodic repair: drain Step 2 + Step 3 when canonical backlog is non-zero."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.canonical.worker import (
    count_canonical_lag,
    drain_github_canonical,
    drain_linear_canonical,
)
from vector.domains.projections.github.worker import drain_github_projections
from vector.domains.projections.linear.worker import drain_linear_projections
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB, CONNECTOR_LINEAR


def sweep_canonical_lag_once(session: Session) -> dict[str, Any]:
    """When Step 3 lags Step 2, run projection + canonical drains per active connection."""
    rows = session.scalars(
        select(TenantConnection).where(
            TenantConnection.status == "active",
            TenantConnection.provider.in_(["github", "linear"]),
        ),
    ).all()

    connections_seen = 0
    connections_swept = 0
    total_rows = 0

    for tc in rows:
        connections_seen += 1
        connector = tc.provider
        if connector == "github":
            lag, _ = count_canonical_lag(
                session,
                tenant_id=tc.tenant_id,
                connection_id=tc.id,
                connector=CONNECTOR_GITHUB,
            )
            if lag <= 0:
                continue
            drain_github_projections(
                session,
                tenant_id=tc.tenant_id,
                connection_id=tc.id,
            )
            m = drain_github_canonical(
                session,
                tenant_id=tc.tenant_id,
                connection_id=tc.id,
            )
            connections_swept += 1
            total_rows += m.raw_rows_processed
        elif connector == "linear":
            lag, _ = count_canonical_lag(
                session,
                tenant_id=tc.tenant_id,
                connection_id=tc.id,
                connector=CONNECTOR_LINEAR,
            )
            if lag <= 0:
                continue
            drain_linear_projections(
                session,
                tenant_id=tc.tenant_id,
                connection_id=tc.id,
            )
            m = drain_linear_canonical(
                session,
                tenant_id=tc.tenant_id,
                connection_id=tc.id,
            )
            connections_swept += 1
            total_rows += m.raw_rows_processed
        else:
            continue

    return {
        "connections_seen": connections_seen,
        "connections_swept": connections_swept,
        "canonical_rows_processed": total_rows,
    }
