"""Thin connector sync router ."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.provider_keys import (
    CONNECTION_PROVIDER_CALLS,
    CONNECTION_PROVIDER_GITHUB,
    CONNECTION_PROVIDER_LINEAR,
    CONNECTION_PROVIDER_NOTION,
    CONNECTION_PROVIDER_SLACK,
)
from vector.domains.cortex.ingestion.connectors.calls.sync import run_calls_connector_sync
from vector.domains.cortex.ingestion.connectors.github.sync import run_github_connector_sync
from vector.domains.cortex.ingestion.connectors.linear.sync import run_linear_connector_sync
from vector.domains.cortex.ingestion.connectors.notion.sync import run_notion_connector_sync
from vector.domains.cortex.ingestion.connectors.slack.sync import run_slack_connector_sync
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_shared import (
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_RUNNING,
    resolve_connection,
    upsert_checkpoint,
    utc_now,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.observability.ingestion_tasks import (
    PHASE_STEP1,
    PHASE_STEP3,
    PHASE_STEP5,
    log_ingestion_event,
)
from vector.settings import Settings

_logger = logging.getLogger("app")

def execute_connector_sync(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connector_id: str,
    source_trigger: str,
    ingestion_sync_context: IngestionSyncContext | None = None,
    connection_id: uuid.UUID | None = None,
    scheduler_tick_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Create an ingestion run, fetch normalized snapshots, persist raw rows, update checkpoint."""
    ctx = ingestion_sync_context or IngestionSyncContext.live_incremental()
    ctx.validate()

    conn = resolve_connection(
        session,
        tenant_id,
        connector_id,
        connection_id=connection_id,
    )
    phase = PHASE_STEP3 if ctx.replay_mode else PHASE_STEP1
    if conn is None:
        log_ingestion_event(
            _logger,
            logging.INFO,
            "cortex sync skipped — no active tenant_connection",
            task_name="execute_connector_sync",
            phase=phase,
            outcome="skipped",
            tenant_id=str(tenant_id),
            connector=connector_id,
        )
        return {"status": "skipped", "reason": "no_connection", "connector": connector_id}

    run_id = uuid.uuid4()
    started = utc_now()
    initial_stats: dict[str, Any] | None = None
    if scheduler_tick_id is not None:
        initial_stats = {"scheduler_tick_id": str(scheduler_tick_id)}
    run = IngestionRun(
        id=run_id,
        tenant_id=tenant_id,
        connection_id=conn.id,
        connector=connector_id,
        source_trigger=source_trigger,
        sync_mode=ctx.checkpoint_sync_mode,
        replay_mode=ctx.replay_mode,
        replay_job_id=ctx.replay_job_id,
        replay_version=ctx.replay_version,
        status=RUN_RUNNING,
        started_at=started,
        stats=initial_stats,
    )
    session.add(run)
    session.flush()

    log_ingestion_event(
        _logger,
        logging.INFO,
        "cortex sync started",
        task_name="execute_connector_sync",
        phase=phase,
        outcome="started",
        run_id=str(run_id),
        tenant_id=str(tenant_id),
        connector=connector_id,
        run_status=RUN_RUNNING,
        replay_job_id=str(ctx.replay_job_id) if ctx.replay_job_id else "",
        sync_mode=ctx.checkpoint_sync_mode,
    )

    records_written = 0
    try:
        if connector_id == CONNECTION_PROVIDER_GITHUB:
            records_written = run_github_connector_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_LINEAR:
            records_written = run_linear_connector_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_SLACK:
            records_written = run_slack_connector_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_NOTION:
            records_written = run_notion_connector_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        elif connector_id == CONNECTION_PROVIDER_CALLS:
            records_written = run_calls_connector_sync(
                session,
                settings,
                ctx=ctx,
                tenant_id=tenant_id,
                connection_id=conn.id,
                run_id=run_id,
                source_trigger=source_trigger,
            )
        else:
            raise ValueError(f"unsupported connector for sync: {connector_id!r}")

        finished = utc_now()
        # Defense-in-depth: always materialize/update the scoped checkpoint row at run
        # completion so live/replay scope isolation is observable even if a connector
        # branch produced zero records or skipped its detailed checkpoint patch path.
        upsert_checkpoint(
            session,
            tenant_id=tenant_id,
            connection_id=conn.id,
            connector=connector_id,
            scope_key=ctx.checkpoint_scope_key(),
            patch={"last_incremental_at": finished.isoformat()},
            sync_mode=ctx.checkpoint_sync_mode,
        )
        run.status = RUN_COMPLETED
        run.finished_at = finished
        run.stats = {
            **(run.stats if isinstance(run.stats, dict) else {}),
            "records_written": records_written,
            "sync_mode": ctx.sync_mode,
            "checkpoint_lane": ctx.checkpoint_sync_mode,
            "checkpoint_scope": ctx.checkpoint_scope_key(),
        }
        # Ensure new raw/checkpoint rows are materialized even when caller uses a
        # non-autoflush session and immediately queries in the same transaction.
        session.flush()
        log_ingestion_event(
            _logger,
            logging.INFO,
            "cortex sync completed",
            task_name="execute_connector_sync",
            phase=phase,
            outcome="completed",
            run_id=str(run_id),
            tenant_id=str(tenant_id),
            connector=connector_id,
            run_status=RUN_COMPLETED,
            records_written=records_written,
        )
        vrep: dict[str, Any] | None = None
        if settings.cortex_ingestion_verify_after_sync:
            from vector.domains.cortex.ingestion import verification as ingestion_verification

            vrep = ingestion_verification.verify_ingestion_run(session, run_id)
            if not vrep["passed"]:
                log_ingestion_event(
                    _logger,
                    logging.WARNING,
                    "cortex sync verification reported issues",
                    task_name="execute_connector_sync",
                    phase=PHASE_STEP5,
                    outcome="verification_failed",
                    run_id=str(run_id),
                    tenant_id=str(tenant_id),
                    connector=connector_id,
                )
        out: dict[str, Any] = {
            "status": "completed",
            "run_id": str(run_id),
            "connector": connector_id,
            "records_written": records_written,
            "sync_mode": ctx.sync_mode,
            "checkpoint_scope": ctx.checkpoint_scope_key(),
        }
        if ctx.replay_job_id is not None:
            out["replay_job_id"] = str(ctx.replay_job_id)
            out["replay_version"] = ctx.replay_version
        if vrep is not None:
            out["verification"] = vrep
        return out
    except Exception as e:
        _logger.exception("cortex sync failed")
        run.status = RUN_FAILED
        run.finished_at = utc_now()
        run.error_summary = str(e)[:8000]
        log_ingestion_event(
            _logger,
            logging.ERROR,
            "cortex sync failed",
            task_name="execute_connector_sync",
            phase=phase,
            outcome="failed",
            run_id=str(run_id),
            tenant_id=str(tenant_id),
            connector=connector_id,
            run_status=RUN_FAILED,
            error=str(e),
        )
        return {
            "status": "failed",
            "run_id": str(run_id),
            "connector": connector_id,
            "error": str(e),
        }
