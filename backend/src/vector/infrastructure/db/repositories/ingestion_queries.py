"""Read paths for Step 1 ingestion (tenant-scoped)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB


def list_github_ingestion_runs_for_tenant(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 100,
) -> list[IngestionRun]:
    stmt = (
        select(IngestionRun)
        .where(
            IngestionRun.tenant_id == tenant_id,
            IngestionRun.connector == CONNECTOR_GITHUB,
        )
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def record_counts_for_run_ids(
    session: Session,
    run_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not run_ids:
        return {}
    stmt = (
        select(RawIngestionRecord.run_id, func.count().label("cnt"))
        .where(RawIngestionRecord.run_id.in_(run_ids))
        .group_by(RawIngestionRecord.run_id)
    )
    rows = session.execute(stmt).all()
    return {rid: int(cnt) for rid, cnt in rows}


def get_github_ingestion_run_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    run_id: uuid.UUID,
) -> IngestionRun | None:
    run = session.get(IngestionRun, run_id)
    if run is None:
        return None
    if run.tenant_id != tenant_id or run.connector != CONNECTOR_GITHUB:
        return None
    return run


def count_raw_records_for_run(session: Session, run_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(RawIngestionRecord)
        .where(RawIngestionRecord.run_id == run_id)
    )
    return int(session.scalar(stmt) or 0)


@dataclass(frozen=True)
class RawRecordPage:
    items: list[RawIngestionRecord]
    total: int


def list_raw_records_for_run(
    session: Session,
    *,
    run_id: uuid.UUID,
    limit: int,
    offset: int,
) -> RawRecordPage:
    total = count_raw_records_for_run(session, run_id)
    stmt = (
        select(RawIngestionRecord)
        .where(RawIngestionRecord.run_id == run_id)
        .order_by(RawIngestionRecord.replay_sequence.asc(), RawIngestionRecord.id.asc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt).all())
    return RawRecordPage(items=items, total=total)
