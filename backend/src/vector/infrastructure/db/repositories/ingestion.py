"""Persistence for Step 1 ingestion (runs, raw records, checkpoints)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.domains.ingestion.payload import canonical_payload_hash, idempotency_key
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

__all__ = [
    "CONNECTOR_GITHUB",
    "CONNECTOR_LINEAR",
    "SOURCE_TRIGGER_POLL",
    "RUN_STATUS_FAILED",
    "RUN_STATUS_PARTIAL",
    "RUN_STATUS_RUNNING",
    "RUN_STATUS_SUCCEEDED",
    "IngestionRun",
    "create_ingestion_run",
    "delete_sync_state",
    "finish_ingestion_run",
    "get_sync_state",
    "insert_raw_records_ignore_conflict",
    "upsert_sync_state",
]

CONNECTOR_GITHUB = "github"
CONNECTOR_LINEAR = "linear"
SOURCE_TRIGGER_POLL = "poll"

RUN_STATUS_RUNNING = "running"
RUN_STATUS_SUCCEEDED = "succeeded"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_PARTIAL = "partial"


def create_ingestion_run(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    source_trigger: str,
) -> IngestionRun:
    run = IngestionRun(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        source_trigger=source_trigger,
        status=RUN_STATUS_RUNNING,
        started_at=datetime.now(tz=UTC),
    )
    session.add(run)
    session.flush()
    return run


def finish_ingestion_run(
    session: Session,
    run: IngestionRun,
    *,
    status: str,
    error_summary: str | None,
    stats: dict[str, Any] | None,
) -> None:
    run.status = status
    run.finished_at = datetime.now(tz=UTC)
    run.error_summary = error_summary
    run.stats = stats


def get_sync_state(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    scope_key: str,
) -> dict[str, Any] | None:
    row = session.get(
        ConnectorSyncState,
        (tenant_id, connection_id, connector, scope_key),
    )
    if row is None:
        return None
    return dict(row.state)


def upsert_sync_state(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    scope_key: str,
    state: dict[str, Any],
) -> None:
    now = datetime.now(tz=UTC)
    ins = pg_insert(ConnectorSyncState).values(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=connector,
        scope_key=scope_key,
        state=state,
        updated_at=now,
    )
    stmt = ins.on_conflict_do_update(
        index_elements=[
            "tenant_id",
            "connection_id",
            "connector",
            "scope_key",
        ],
        set_={
            "state": ins.excluded.state,
            "updated_at": ins.excluded.updated_at,
        },
    )
    session.execute(stmt)


def delete_sync_state(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    scope_key: str,
) -> None:
    row = session.get(
        ConnectorSyncState,
        (tenant_id, connection_id, connector, scope_key),
    )
    if row is not None:
        session.delete(row)


def insert_raw_records_ignore_conflict(
    session: Session,
    *,
    run: IngestionRun,
    connector: str,
    source_trigger: str,
    batch: list[dict[str, Any]],
) -> int:
    """Insert envelopes; skip duplicate (run_id, idempotency_key). Returns attempted count."""
    if not batch:
        return 0
    rows: list[dict[str, Any]] = []
    for item in batch:
        payload = item["payload_body"]
        qp = item["query_params"]
        ep = item["api_endpoint"]
        ext = item["external_id"]
        rtype = item["resource_type"]
        status = item["http_status"]
        rows.append(
            {
                "tenant_id": run.tenant_id,
                "connection_id": run.connection_id,
                "connector": connector,
                "resource_type": rtype,
                "external_id": ext,
                "api_endpoint": ep,
                "query_params": qp,
                "payload_body": payload,
                "payload_hash": canonical_payload_hash(payload),
                "http_status": status,
                "run_id": run.id,
                "source_trigger": source_trigger,
                "idempotency_key": idempotency_key(
                    run_id=run.id,
                    resource_type=rtype,
                    external_id=ext,
                    api_endpoint=ep,
                    query_params=qp,
                ),
            },
        )
    stmt = pg_insert(RawIngestionRecord).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_raw_ingestion_records_run_idempotency")
    session.execute(stmt)
    return len(rows)
