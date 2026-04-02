"""Delete Step 1 data for a tenant (raw envelopes + runs + sync watermarks only)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

# Typed in the admin UI before reset runs (must match exactly, case-sensitive).
STEP1_RAW_RESET_CONFIRMATION_PHRASE = "DELETE ALL STEP1 RAW DATA"


def wipe_step1_raw_for_tenant(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    """Remove all ingestion runs (cascades ``raw_ingestion_records``) and ``connector_sync_state``.

    Does not call connectors, alter OAuth tokens, or touch Step 2/3 tables.
    Returns counts captured **before** deletes.
    """
    n_raw = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(RawIngestionRecord.tenant_id == tenant_id),
        )
        or 0,
    )
    n_runs = int(
        session.scalar(
            select(func.count())
            .select_from(IngestionRun)
            .where(IngestionRun.tenant_id == tenant_id),
        )
        or 0,
    )
    n_sync = int(
        session.scalar(
            select(func.count())
            .select_from(ConnectorSyncState)
            .where(ConnectorSyncState.tenant_id == tenant_id),
        )
        or 0,
    )
    session.execute(delete(IngestionRun).where(IngestionRun.tenant_id == tenant_id))
    session.execute(delete(ConnectorSyncState).where(ConnectorSyncState.tenant_id == tenant_id))
    return {
        "deleted_raw_records": n_raw,
        "deleted_ingestion_runs": n_runs,
        "deleted_sync_state_rows": n_sync,
    }
