"""Step 3 canonical drain — same replay order as Step 2 (raw_ingestion_records)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from vector.domains.canonical.github_mapper import handle_github_canonical_row
from vector.domains.canonical.linear_mapper import handle_linear_canonical_row
from vector.domains.projections.github.resource_types import GITHUB_RESOURCE_TYPES
from vector.domains.projections.linear.resource_types import LINEAR_RESOURCE_TYPES
from vector.domains.replay_drain import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_BATCHES,
    CanonicalDrainMetrics,
    run_canonical_replay_drain,
)
from vector.infrastructure.db.models.canonical import Step3CanonicalCursor
from vector.infrastructure.db.models.connector_projection_progress import (
    ConnectorProjectionProgress,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB, CONNECTOR_LINEAR


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

    return run_canonical_replay_drain(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_types=GITHUB_RESOURCE_TYPES,
        handle_row=handle_github_canonical_row,
        batch_size=batch_size,
        max_batches=max_batches,
        log_prefix="github canonical",
    )


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

    return run_canonical_replay_drain(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        resource_types=LINEAR_RESOURCE_TYPES,
        handle_row=handle_linear_canonical_row,
        batch_size=batch_size,
        max_batches=max_batches,
        log_prefix="linear canonical",
    )


def count_canonical_lag(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str = CONNECTOR_GITHUB,
) -> tuple[int, dict[str, Any]]:
    """Rows in (step3_cursor, step2_watermark] by replay order; plus watermarks dict."""
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

