"""Step 3 canonical drain — same replay order as Step 2 (raw_ingestion_records)."""

from __future__ import annotations

import logging
import os
import socket
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.domains.canonical.github_mapper import handle_github_canonical_row
from vector.domains.canonical.linear_mapper import handle_linear_canonical_row
from vector.domains.projections.github.resource_types import GITHUB_RESOURCE_TYPES
from vector.domains.projections.linear.resource_types import LINEAR_RESOURCE_TYPES
from vector.infrastructure.db.models.canonical import Step3CanonicalCursor
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB, CONNECTOR_LINEAR

_logger = logging.getLogger(__name__)

LEASE_TTL = timedelta(minutes=5)
DEFAULT_BATCH_SIZE = 500
DEFAULT_MAX_BATCHES = 10_000


class CanonicalDrainMetrics:
    def __init__(self) -> None:
        self.raw_rows_processed = 0
        self.batches_committed = 0


def _lock_owner_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:10]}"


def ensure_step3_cursor_row(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
) -> None:
    now = datetime.now(tz=UTC)
    stmt = pg_insert(Step3CanonicalCursor).values(
        connection_id=connection_id,
        connector=connector,
        tenant_id=tenant_id,
        last_replay_sequence=0,
        last_raw_record_id=0,
        updated_at=now,
    ).on_conflict_do_nothing(constraint="step3_canonical_cursor_pkey")
    session.execute(stmt)
    session.flush()


def drain_github_canonical(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_batches: int = DEFAULT_MAX_BATCHES,
    connector: str = CONNECTOR_GITHUB,
) -> CanonicalDrainMetrics:
    """Process raw rows after Step 3 cursor until caught up or max_batches."""
    if connector != CONNECTOR_GITHUB:
        msg = f"unsupported connector for canonical drain: {connector}"
        raise ValueError(msg)

    metrics = CanonicalDrainMetrics()
    batches = 0

    ensure_step3_cursor_row(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
    )

    while batches < max_batches:
        cursor = session.get(Step3CanonicalCursor, (connection_id, connector))
        if cursor is None:
            msg = "step3_canonical_cursor row missing after ensure"
            raise RuntimeError(msg)
        if cursor.tenant_id != tenant_id:
            msg = "step3 canonical cursor tenant mismatch"
            raise ValueError(msg)

        last_rs = cursor.last_replay_sequence
        last_rid = cursor.last_raw_record_id

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
                        RawIngestionRecord.id > last_rid,
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
            session.commit()
            return metrics

        try:
            for raw in batch:
                handle_github_canonical_row(session, raw)
                metrics.raw_rows_processed += 1

            tail = batch[-1]
            now = datetime.now(tz=UTC)
            session.execute(
                update(Step3CanonicalCursor)
                .where(
                    Step3CanonicalCursor.connection_id == connection_id,
                    Step3CanonicalCursor.connector == connector,
                )
                .values(
                    last_replay_sequence=tail.replay_sequence,
                    last_raw_record_id=tail.id,
                    last_processed_at=now,
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
        "github canonical drain stopped at max_batches=%s connection_id=%s",
        max_batches,
        connection_id,
    )
    return metrics


def drain_linear_canonical(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_batches: int = DEFAULT_MAX_BATCHES,
    connector: str = CONNECTOR_LINEAR,
) -> CanonicalDrainMetrics:
    """Process Linear raw rows after Step 3 cursor until caught up or max_batches."""
    if connector != CONNECTOR_LINEAR:
        msg = f"unsupported connector for linear canonical drain: {connector}"
        raise ValueError(msg)

    metrics = CanonicalDrainMetrics()
    batches = 0

    ensure_step3_cursor_row(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
    )

    while batches < max_batches:
        cursor = session.get(Step3CanonicalCursor, (connection_id, connector))
        if cursor is None:
            msg = "step3_canonical_cursor row missing after ensure"
            raise RuntimeError(msg)
        if cursor.tenant_id != tenant_id:
            msg = "step3 canonical cursor tenant mismatch"
            raise ValueError(msg)

        last_rs = cursor.last_replay_sequence
        last_rid = cursor.last_raw_record_id

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
                        RawIngestionRecord.id > last_rid,
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
            session.commit()
            return metrics

        try:
            for raw in batch:
                handle_linear_canonical_row(session, raw)
                metrics.raw_rows_processed += 1

            tail = batch[-1]
            now = datetime.now(tz=UTC)
            session.execute(
                update(Step3CanonicalCursor)
                .where(
                    Step3CanonicalCursor.connection_id == connection_id,
                    Step3CanonicalCursor.connector == connector,
                )
                .values(
                    last_replay_sequence=tail.replay_sequence,
                    last_raw_record_id=tail.id,
                    last_processed_at=now,
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
        "linear canonical drain stopped at max_batches=%s connection_id=%s",
        max_batches,
        connection_id,
    )
    return metrics


def count_canonical_lag(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str = CONNECTOR_GITHUB,
) -> tuple[int, dict[str, Any]]:
    """Rows in (step3_cursor, step2_watermark] by replay order; plus watermarks dict."""
    from vector.infrastructure.db.models.connector_projection_progress import (
        ConnectorProjectionProgress,
    )

    rtypes = (
        GITHUB_RESOURCE_TYPES
        if connector == CONNECTOR_GITHUB
        else LINEAR_RESOURCE_TYPES
        if connector == CONNECTOR_LINEAR
        else None
    )
    if rtypes is None:
        msg = f"unsupported connector for canonical lag: {connector}"
        raise ValueError(msg)

    step3 = session.get(Step3CanonicalCursor, (connection_id, connector))
    step2 = session.get(ConnectorProjectionProgress, (connection_id, connector))
    if step3 is not None and step3.tenant_id != tenant_id:
        msg = "step3 canonical cursor tenant mismatch"
        raise ValueError(msg)
    s3_rs = step3.last_replay_sequence if step3 else 0
    s3_id = step3.last_raw_record_id if step3 else 0
    s2_rs = step2.last_replay_sequence if step2 else 0
    s2_id = step2.last_id if step2 else 0

    q = select(func.count()).select_from(RawIngestionRecord).where(
        RawIngestionRecord.connection_id == connection_id,
        RawIngestionRecord.connector == connector,
        RawIngestionRecord.http_status >= 200,
        RawIngestionRecord.http_status <= 299,
        RawIngestionRecord.resource_type.in_(rtypes),
        or_(
            RawIngestionRecord.replay_sequence > s3_rs,
            and_(
                RawIngestionRecord.replay_sequence == s3_rs,
                RawIngestionRecord.id > s3_id,
            ),
        ),
        or_(
            RawIngestionRecord.replay_sequence < s2_rs,
            and_(
                RawIngestionRecord.replay_sequence == s2_rs,
                RawIngestionRecord.id <= s2_id,
            ),
        ),
    )
    lag = int(session.scalar(q) or 0)
    meta = {
        "step3_last_processed_replay_sequence": s3_rs,
        "step3_last_processed_id": s3_id,
        "step2_watermark_replay_sequence": s2_rs,
        "step2_watermark_id": s2_id,
    }
    return lag, meta
