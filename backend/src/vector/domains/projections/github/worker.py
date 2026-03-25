"""Backlog-driven GitHub projection drain (cursor + lease)."""

from __future__ import annotations

import logging
import os
import socket
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from vector.domains.projections.github.handlers import handle_github_raw_row
from vector.domains.projections.github.metrics import GithubProjectionMetrics
from vector.domains.projections.github.resource_types import GITHUB_RESOURCE_TYPES
from vector.infrastructure.db.models.connector_projection_progress import (
    ConnectorProjectionProgress,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB

_logger = logging.getLogger(__name__)

LEASE_TTL = timedelta(minutes=5)
DEFAULT_BATCH_SIZE = 500
DEFAULT_MAX_BATCHES = 10_000


def _lock_owner_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:10]}"


def ensure_projection_progress_row(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
) -> None:
    """Idempotent progress row insert (same transaction as subsequent batch work)."""
    now = datetime.now(tz=UTC)
    stmt = pg_insert(ConnectorProjectionProgress).values(
        connection_id=connection_id,
        connector=connector,
        tenant_id=tenant_id,
        last_replay_sequence=0,
        last_id=0,
        updated_at=now,
    ).on_conflict_do_nothing(constraint="connector_projection_progress_pkey")
    session.execute(stmt)
    session.flush()


def _try_acquire_lease(
    session: Session,
    *,
    progress: ConnectorProjectionProgress,
    lock_owner: str,
) -> bool:
    now = datetime.now(tz=UTC)
    expires = now + LEASE_TTL
    res = session.execute(
        update(ConnectorProjectionProgress)
        .where(
            ConnectorProjectionProgress.connection_id == progress.connection_id,
            ConnectorProjectionProgress.connector == progress.connector,
            or_(
                ConnectorProjectionProgress.lock_expires_at.is_(None),
                ConnectorProjectionProgress.lock_expires_at < now,
                ConnectorProjectionProgress.lock_owner == lock_owner,
            ),
        )
        .values(
            lock_owner=lock_owner,
            lock_expires_at=expires,
            updated_at=now,
        ),
    )
    session.flush()
    if not isinstance(res, CursorResult):
        return False
    return int(res.rowcount or 0) == 1


def _release_lease(session: Session, *, progress: ConnectorProjectionProgress) -> None:
    now = datetime.now(tz=UTC)
    session.execute(
        update(ConnectorProjectionProgress)
        .where(
            ConnectorProjectionProgress.connection_id == progress.connection_id,
            ConnectorProjectionProgress.connector == progress.connector,
        )
        .values(
            lock_owner=None,
            lock_expires_at=None,
            updated_at=now,
        ),
    )


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
                "github projection lease busy connection_id=%s connector=%s",
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
                RawIngestionRecord.resource_type.in_(GITHUB_RESOURCE_TYPES),
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
                handle_github_raw_row(session, raw, metrics)
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
        "github projection drain stopped at max_batches=%s connection_id=%s",
        max_batches,
        connection_id,
    )
    progress = session.get(ConnectorProjectionProgress, (connection_id, connector))
    if progress is not None:
        _release_lease(session, progress=progress)
        session.commit()
    return metrics
