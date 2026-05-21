"""Celery tasks — Cortex Phase 01 connector ingestion sync (live + replay lanes)."""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

_TASK_RUN_SYNC = "vector.cortex.ingestion.run_sync"
_TASK_RUN_REPLAY = "vector.cortex.ingestion.run_sync_replay"


def _maybe_enqueue_post_ingestion_substrate_refresh(
    *,
    tenant_id: uuid.UUID,
    sync_result: dict[str, object],
    sync_mode: str,
) -> None:
    """Schedule debounced substrate refresh after a successful live incremental sync."""
    if sync_mode not in ("incremental", "live"):
        return
    if sync_result.get("status") != "completed":
        return
    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )

    schedule_post_ingestion_substrate_refresh(
        tenant_id=tenant_id,
        settings=get_settings(),
        reason="incremental_sync_complete",
    )


@celery_app.task(name=_TASK_RUN_SYNC, queue="cortex_live")
def run_cortex_connector_sync_task(
    tenant_id: str,
    connector_id: str,
    source_trigger: str = "scheduled",
    sync_mode: str = "incremental",
    connection_id: str | None = None,
) -> dict[str, object]:
    """Execute one incremental sync for a tenant connection (runs + raw rows)."""
    tid = uuid.UUID(tenant_id)
    ctx = (
        IngestionSyncContext.backfill()
        if sync_mode == "backfill"
        else IngestionSyncContext.live_incremental()
    )
    settings = get_settings()
    with session_scope() as session:
        out = execute_connector_sync(
            session,
            settings,
            tenant_id=tid,
            connector_id=connector_id,
            source_trigger=source_trigger,
            ingestion_sync_context=ctx,
            connection_id=uuid.UUID(connection_id) if connection_id else None,
        )
    _maybe_enqueue_post_ingestion_substrate_refresh(
        tenant_id=tid,
        sync_result=out,
        sync_mode=sync_mode,
    )
    return out


@celery_app.task(name=_TASK_RUN_REPLAY, queue="cortex_replay")
def run_cortex_connector_replay_sync_task(
    tenant_id: str,
    connector_id: str,
    replay_job_id: str,
    replay_version: int = 1,
    source_trigger: str = "replay",
    connection_id: str | None = None,
) -> dict[str, object]:
    """Replay-scoped sync: isolated checkpoints + idempotent raw rows per replay_job_id."""
    tid = uuid.UUID(tenant_id)
    rid = uuid.UUID(replay_job_id)
    ctx = IngestionSyncContext.replay(replay_job_id=rid, replay_version=replay_version)
    settings = get_settings()
    with session_scope() as session:
        return execute_connector_sync(
            session,
            settings,
            tenant_id=tid,
            connector_id=connector_id,
            source_trigger=source_trigger,
            ingestion_sync_context=ctx,
            connection_id=uuid.UUID(connection_id) if connection_id else None,
        )
