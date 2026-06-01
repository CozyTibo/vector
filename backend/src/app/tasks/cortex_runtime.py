"""Cortex DB-backed pass planner and worker poll loop."""

from __future__ import annotations

import logging
import socket
from datetime import UTC, datetime

from app.celery_app import celery_app
from vector.domains.cortex.runtime.claim import claim_next_pass_v1
from vector.domains.cortex.runtime.execute import (
    complete_pass_v1,
    execute_claimed_pass_v1,
    fail_pass_v1,
)
from vector.domains.cortex.runtime.lane_scheduler_tick import complete_lane_scheduler_tick_v1
from vector.domains.cortex.runtime.plan import plan_cortex_passes_v1
from vector.domains.cortex.runtime.queue import recover_expired_leases_v1
from vector.infrastructure.cortex_lane_pause import read_lane_paused_flag
from vector.infrastructure.db.models.canon_scheduler_tick import CanonSchedulerTick
from vector.infrastructure.db.models.graph_scheduler_tick import GraphSchedulerTick
from vector.infrastructure.db.models.identity_scheduler_tick import IdentitySchedulerTick
from vector.infrastructure.db.models.orchestrator_run import OrchestratorRun
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

_TASK_PLAN = "vector.cortex.runtime.plan_passes"
_TASK_POLL = "vector.cortex.runtime.poll_passes"
_TASK_ORCHESTRATOR = "vector.cortex.runtime.orchestrator_tick"
_TASK_CLEAR_DERIVED = "vector.cortex.admin.clear_derived"


def _worker_id() -> str:
    return f"celery-{socket.gethostname()}"


@celery_app.task(name=_TASK_PLAN, queue="vector")
def plan_cortex_passes_task() -> dict[str, object]:
    """Beat: plan pending canon/identity passes in Postgres (replaces per-lane tick fan-out)."""
    settings = get_settings()
    canon_interval = max(60, int(settings.cortex_canon_scheduler_interval_seconds))
    identity_interval = max(60, int(settings.cortex_identity_scheduler_interval_seconds))
    graph_interval = max(60, int(settings.cortex_graph_scheduler_interval_seconds))

    with session_scope() as session:
        canon_tick = CanonSchedulerTick(
            started_at=datetime.now(tz=UTC),
            outcome="running",
            beat_interval_seconds=canon_interval,
        )
        identity_tick = IdentitySchedulerTick(
            started_at=datetime.now(tz=UTC),
            outcome="running",
            beat_interval_seconds=identity_interval,
        )
        graph_tick = GraphSchedulerTick(
            started_at=datetime.now(tz=UTC),
            outcome="running",
            beat_interval_seconds=graph_interval,
        )
        session.add(canon_tick)
        session.add(identity_tick)
        session.add(graph_tick)
        session.flush()
        canon_tick_id = canon_tick.id
        identity_tick_id = identity_tick.id
        graph_tick_id = graph_tick.id

    with session_scope() as session:
        counts = plan_cortex_passes_v1(session, settings)

    canon_outcome = "enqueued" if counts["canon_planned"] else "noop"
    identity_outcome = "enqueued" if counts["identity_planned"] else "noop"
    graph_outcome = "enqueued" if counts["graph_planned"] else "noop"
    with session_scope() as session:
        canon_tick = session.get(CanonSchedulerTick, canon_tick_id)
        if canon_tick is not None:
            complete_lane_scheduler_tick_v1(
                session,
                canon_tick,
                outcome=canon_outcome,
                enqueued_count=counts["canon_planned"],
                candidate_count=counts["canon_planned"] + counts["canon_skipped"],
                skipped_count=counts["canon_skipped"],
            )
        identity_tick = session.get(IdentitySchedulerTick, identity_tick_id)
        if identity_tick is not None:
            complete_lane_scheduler_tick_v1(
                session,
                identity_tick,
                outcome=identity_outcome,
                enqueued_count=counts["identity_planned"],
                candidate_count=counts["identity_planned"] + counts["identity_skipped"],
                skipped_count=counts["identity_skipped"],
            )
        graph_tick = session.get(GraphSchedulerTick, graph_tick_id)
        if graph_tick is not None:
            complete_lane_scheduler_tick_v1(
                session,
                graph_tick,
                outcome=graph_outcome,
                enqueued_count=counts["graph_planned"],
                candidate_count=counts["graph_planned"] + counts["graph_skipped"],
                skipped_count=counts["graph_skipped"],
            )

    return {
        **counts,
        "canon_tick_id": str(canon_tick_id),
        "identity_tick_id": str(identity_tick_id),
        "graph_tick_id": str(graph_tick_id),
    }


@celery_app.task(name=_TASK_POLL, queue="vector")
def poll_cortex_passes_task() -> dict[str, object]:
    """Claim and execute pending passes from ``cortex_passes`` (pull worker)."""
    settings = get_settings()
    lease_ttl = max(60, int(settings.cortex_runtime_lease_ttl_seconds))
    batch_limit = max(1, int(settings.cortex_runtime_poll_batch_limit))
    retry_delay = max(30, int(settings.cortex_runtime_retry_delay_seconds))
    worker = _worker_id()
    processed = 0
    failed = 0

    with session_scope() as session:
        recover_expired_leases_v1(session, lease_ttl_seconds=lease_ttl)

    while processed < batch_limit:
        with session_scope() as session:
            row = claim_next_pass_v1(session, worker_id=worker, lease_ttl_seconds=lease_ttl)
            if row is None:
                break
            pass_id = row.id
            try:
                stats = execute_claimed_pass_v1(
                    session,
                    settings,
                    row,
                    lease_ttl_seconds=lease_ttl,
                )
                complete_pass_v1(session, row, stats=stats)
                session.commit()
                processed += 1
            except Exception as exc:
                session.rollback()
                failed += 1
                _LOGGER.exception("cortex pass %s failed", pass_id)
                from vector.infrastructure.db.models.cortex_pass import CortexPass

                with session_scope() as session2:
                    row2 = session2.get(CortexPass, pass_id)
                    if row2 is not None:
                        fail_pass_v1(
                            session2,
                            row2,
                            error_summary=str(exc),
                            retry_delay_seconds=retry_delay,
                        )
                if failed >= batch_limit:
                    break

    return {"processed": processed, "failed": failed, "worker_id": worker}


@celery_app.task(name=_TASK_ORCHESTRATOR, queue="vector")
def orchestrator_tick_task() -> dict[str, object]:
    """Unified Beat: ingestion tick, pass planning, and pass polling."""
    settings = get_settings()
    interval = max(60, int(settings.cortex_orchestrator_interval_seconds))

    with session_scope() as session:
        run = OrchestratorRun(
            started_at=datetime.now(tz=UTC),
            outcome="running",
            beat_interval_seconds=interval,
        )
        session.add(run)
        session.flush()
        run_id = run.id

    detail: dict[str, object] = {}
    ingestion_enqueued = 0
    passes_planned = 0
    passes_processed = 0
    error_summary: str | None = None
    outcome = "ok"

    try:
        if settings.cortex_ingestion_scheduler_enabled and not read_lane_paused_flag(
            settings,
            "ingestion",
        ):
            from app.tasks.cortex_ingestion_scheduler import tick_cortex_ingestion_scheduler

            ingestion_out = tick_cortex_ingestion_scheduler()
            detail["ingestion"] = ingestion_out
            ingestion_enqueued = int(ingestion_out.get("enqueued") or 0)
        else:
            detail["ingestion"] = {"skipped": True}

        plan_out = plan_cortex_passes_task()
        poll_out = poll_cortex_passes_task()
        detail["plan"] = plan_out
        detail["poll"] = poll_out
        passes_planned = (
            int(plan_out.get("canon_planned") or 0)
            + int(plan_out.get("identity_planned") or 0)
            + int(plan_out.get("graph_planned") or 0)
        )
        passes_processed = int(poll_out.get("processed") or 0)
    except Exception as exc:
        outcome = "error"
        error_summary = str(exc)[:500]
        _LOGGER.exception("orchestrator tick failed")
    finally:
        with session_scope() as session:
            row = session.get(OrchestratorRun, run_id)
            if row is not None:
                row.completed_at = datetime.now(tz=UTC)
                row.outcome = outcome
                row.ingestion_enqueued = ingestion_enqueued
                row.passes_planned = passes_planned
                row.passes_processed = passes_processed
                row.detail_json = detail
                row.error_summary = error_summary

    return {
        "orchestrator_run_id": str(run_id),
        "outcome": outcome,
        "ingestion_enqueued": ingestion_enqueued,
        "detail": detail,
    }


@celery_app.task(name=_TASK_CLEAR_DERIVED, queue="vector", bind=True, max_retries=2, default_retry_delay=30)
def clear_derived_cortex_task(self, tenant_id: str) -> dict[str, object]:
    """Delete derived Cortex rows for one tenant, then enqueue canon rematerialization."""
    import uuid as uuid_mod

    from sqlalchemy.exc import OperationalError

    from vector.domains.cortex.clear_derived import (
        _is_deadlock,
        enqueue_cortex_rematerialization_after_clear,
        execute_clear_derived_cortex_for_tenant,
    )

    tid = uuid_mod.UUID(tenant_id)
    try:
        out = execute_clear_derived_cortex_for_tenant(tenant_id=tid)
    except OperationalError as exc:
        if _is_deadlock(exc) and self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        raise
    with session_scope() as session:
        pass_id = enqueue_cortex_rematerialization_after_clear(session, tenant_id=tid)
    poll_cortex_passes_task.delay()
    return {
        "tenant_id": str(tid),
        "canon_pass_id": str(pass_id),
        "deleted_rows_total": out["deleted_rows_total"],
        "deleted_rows_by_table": out["deleted_rows_by_table"],
        "raw_ingestion_rows_remaining": out["raw_ingestion_rows_remaining"],
    }
