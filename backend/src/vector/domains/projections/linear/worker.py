"""Backlog-driven Linear projection drain (cursor + lease)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.domains.projections.linear.handlers import handle_linear_raw_row
from vector.domains.projections.linear.metrics import LinearProjectionMetrics
from vector.domains.projections.linear.resource_types import LINEAR_RESOURCE_TYPES
from vector.domains.replay_drain import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_BATCHES,
    run_projection_replay_drain,
)
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_LINEAR


def drain_linear_projections(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_batches: int = DEFAULT_MAX_BATCHES,
    lock_owner: str | None = None,
    connector: str = CONNECTOR_LINEAR,
) -> LinearProjectionMetrics:
    """Process raw rows after cursor until empty or max_batches. Commits per batch."""
    if connector != CONNECTOR_LINEAR:
        msg = f"unsupported connector for linear drain: {connector}"
        raise ValueError(msg)

    metrics = LinearProjectionMetrics()
    return run_projection_replay_drain(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_types=LINEAR_RESOURCE_TYPES,
        handle_row=handle_linear_raw_row,
        metrics=metrics,
        batch_size=batch_size,
        max_batches=max_batches,
        lock_owner=lock_owner,
        log_prefix="linear projection",
    )
