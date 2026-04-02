"""Backlog-driven Linear projection drain (cursor + lease)."""

from __future__ import annotations

import logging
import os
import socket
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from vector.domains.projections.github.worker import (
    _release_lease,
    _try_acquire_lease,
    ensure_projection_progress_row,
)
from vector.domains.projections.linear.handlers import handle_linear_raw_row
from vector.domains.projections.linear.metrics import LinearProjectionMetrics
from vector.domains.projections.linear.resource_types import LINEAR_RESOURCE_TYPES
from vector.infrastructure.db.models.connector_projection_progress import (
    ConnectorProjectionProgress,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_LINEAR

_logger = logging.getLogger(__name__)

LEASE_TTL = timedelta(minutes=5)
DEFAULT_BATCH_SIZE = 500
DEFAULT_MAX_BATCHES = 10_000


def _lock_owner_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:10]}"


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
    owner = lock_owner or _lock_owner_id()
    batches = 0

    ensure_projection_progress_row(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
    )

    while batches < max_batches:
        progress = session.get(
            ConnectorProjectionProgress,
            (connection_id, connector),
        )
        if progress is None:
            msg = "connector_projection_progress row missing after ensure"
            raise RuntimeError(msg)
        if progress.tenant_id != tenant_id:
            msg = "connection projection progress tenant mismatch"
            raise ValueError(msg)

        if not _try_acquire_lease(session, progress=progress, lock_owner=owner):
            _logger.info(
                "linear projection lease busy connection_id=%s connector=%s",
                connection_id,
                connector,
            )
            session.rollback()
            return metrics

        last_rs = progress.last_replay_sequence
        last_id = progress.last_id

        stmt = (
            select(RawIngestionRecord)
            .where(
                RawIngestionRecord.connection_id == connection_id,
                RawIngestionRecord.connector == connector,
                RawIngestionRecord.http_status >= 200,
                RawIngestionRecord.http_status <= 299,
                RawIngestionRecord.resource_type.in_(LINEAR_RESOURCE_TYPES),
                or_(
                    RawIngestionRecord.replay_sequence > last_rs,
                    and_(
                        RawIngestionRecord.replay_sequence == last_rs,
                        RawIngestionRecord.id > last_id,
                    ),
                ),
            )
            .order_by(
                RawIngestionRecord.replay_sequence.asc(),
                RawIngestionRecord.id.asc(),
            )
            .limit(batch_size)
        )
        batch = list(session.scalars(stmt).all())

        if not batch:
            _release_lease(session, progress=progress)
            session.commit()
            return metrics

        try:
            for raw in batch:
                handle_linear_raw_row(session, raw)
                metrics.raw_rows_processed += 1

            tail = batch[-1]
            now = datetime.now(tz=UTC)
            session.execute(
                update(ConnectorProjectionProgress)
                .where(
                    ConnectorProjectionProgress.connection_id == connection_id,
                    ConnectorProjectionProgress.connector == connector,
                )
                .values(
                    last_replay_sequence=tail.replay_sequence,
                    last_id=tail.id,
                    lock_owner=owner,
                    lock_expires_at=now + LEASE_TTL,
                    updated_at=now,
                ),
            )
            session.commit()
            metrics.batches_committed += 1
            batches += 1
        except Exception:
            session.rollback()
            raise

    _logger.warning(
        "linear projection drain stopped at max_batches=%s connection_id=%s",
        max_batches,
        connection_id,
    )
    progress = session.get(ConnectorProjectionProgress, (connection_id, connector))
    if progress is not None:
        _release_lease(session, progress=progress)
        session.commit()
    return metrics
