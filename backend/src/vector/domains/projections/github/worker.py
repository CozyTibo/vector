"""Backlog-driven GitHub projection drain (cursor + lease)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.domains.projections.github.handlers import handle_github_raw_row
from vector.domains.projections.github.metrics import GithubProjectionMetrics
from vector.domains.projections.github.resource_types import GITHUB_RESOURCE_TYPES
from vector.domains.replay_drain import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_BATCHES,
    run_projection_replay_drain,
)
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB


def drain_github_projections(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_batches: int = DEFAULT_MAX_BATCHES,
    lock_owner: str | None = None,
    connector: str = CONNECTOR_GITHUB,
) -> GithubProjectionMetrics:
    """Process raw rows after cursor until empty or max_batches. Commits per batch."""
    if connector != CONNECTOR_GITHUB:
        msg = f"unsupported connector for github drain: {connector}"
        raise ValueError(msg)

    metrics = GithubProjectionMetrics()
    return run_projection_replay_drain(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_types=GITHUB_RESOURCE_TYPES,
        handle_row=lambda s, r: handle_github_raw_row(s, r, metrics),
        metrics=metrics,
        batch_size=batch_size,
        max_batches=max_batches,
        lock_owner=lock_owner,
        log_prefix="github projection",
    )
