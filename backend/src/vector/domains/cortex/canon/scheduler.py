"""Canon scheduler — tenants eligible for materialization passes."""

from __future__ import annotations

import uuid

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.settings import Settings


def iter_tenants_with_live_raw(session: Session, settings: Settings) -> list[uuid.UUID]:
    """Tenants that have at least one live raw row (canon input)."""
    _ = settings
    rows = session.execute(
        select(distinct(RawIngestionRecord.tenant_id)).where(
            RawIngestionRecord.replay_job_id.is_(None),
        ),
    ).all()
    return [uuid.UUID(str(r[0])) for r in rows]
