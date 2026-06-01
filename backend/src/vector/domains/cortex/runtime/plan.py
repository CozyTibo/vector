"""Plan pending cortex_pass rows from domain signals."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.scheduler import iter_tenants_with_live_raw
from vector.domains.cortex.canon.scheduler_dedup import should_skip_scheduled_canon_pass
from vector.domains.cortex.graph.scheduler import iter_tenants_with_graph_backlog
from vector.domains.cortex.graph.scheduler_dedup import should_skip_scheduled_graph_pass
from vector.domains.cortex.declared_domains.scheduler import iter_tenants_with_declared_domain_backlog
from vector.domains.cortex.declared_domains.scheduler_dedup import (
    should_skip_scheduled_declared_domain_pass,
)
from vector.domains.cortex.identity.scheduler import iter_tenants_with_actor_entities
from vector.domains.cortex.identity.scheduler_dedup import should_skip_scheduled_identity_pass
from vector.domains.cortex.runtime.pass_types import (
    CANON_PASS,
    DECLARED_DOMAIN_PASS,
    GRAPH_PROJECTION_PASS,
    IDENTITY_PASS,
)
from vector.domains.cortex.runtime.queue import upsert_pending_pass_v1
from vector.domains.cortex.clear_derived_lock import tenant_clear_derived_in_progress
from vector.infrastructure.cortex_lane_pause import read_lane_paused_flag
from vector.infrastructure.db.models.canon_dirty_queue import CanonDirtyQueue
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.settings import Settings


def _tenant_canon_has_backlog(session: Session, tenant_id: uuid.UUID) -> bool:
    dirty = int(
        session.scalar(
            select(func.count())
            .select_from(CanonDirtyQueue)
            .where(
                CanonDirtyQueue.tenant_id == tenant_id,
                CanonDirtyQueue.processed_at.is_(None),
            ),
        )
        or 0,
    )
    if dirty > 0:
        return True
    cursor = session.scalar(
        select(CanonMaterializationCursor).where(
            CanonMaterializationCursor.tenant_id == tenant_id,
            CanonMaterializationCursor.scope_key == "live",
        ),
    )
    last_raw = int(cursor.last_raw_id) if cursor is not None else 0
    max_raw = session.scalar(
        select(func.max(RawIngestionRecord.id)).where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.replay_job_id.is_(None),
        ),
    )
    return int(max_raw or 0) > last_raw


def _skip_tenant_during_clear_derived(settings: Settings, tenant_id: uuid.UUID) -> bool:
    return tenant_clear_derived_in_progress(settings, tenant_id)


def plan_cortex_passes_v1(session: Session, settings: Settings) -> dict[str, Any]:
    """Enqueue pending pass rows for tenants that need work (no Celery fan-out)."""
    if read_lane_paused_flag(settings, "orchestrator"):
        return {
            "canon_planned": 0,
            "canon_skipped": 0,
            "identity_planned": 0,
            "identity_skipped": 0,
            "graph_planned": 0,
            "graph_skipped": 0,
            "declared_domain_planned": 0,
            "declared_domain_skipped": 0,
            "skipped_reason": "orchestrator_paused",
        }
    canon_planned = 0
    canon_skipped = 0
    identity_planned = 0
    identity_skipped = 0
    graph_planned = 0
    graph_skipped = 0
    declared_domain_planned = 0
    declared_domain_skipped = 0
    canon_interval = max(60, int(settings.cortex_canon_scheduler_interval_seconds))
    identity_interval = max(60, int(settings.cortex_identity_scheduler_interval_seconds))
    graph_interval = max(60, int(settings.cortex_graph_scheduler_interval_seconds))
    declared_domain_interval = max(
        60,
        int(settings.cortex_declared_domain_scheduler_interval_seconds),
    )

    if settings.cortex_canon_scheduler_enabled and not read_lane_paused_flag(settings, "canon"):
        for tid in iter_tenants_with_live_raw(session, settings):
            if _skip_tenant_during_clear_derived(settings, tid):
                continue
            if not _tenant_canon_has_backlog(session, tid):
                continue
            if should_skip_scheduled_canon_pass(
                session,
                tenant_id=tid,
                interval_seconds=canon_interval,
            ):
                canon_skipped += 1
                continue
            upsert_pending_pass_v1(
                session,
                tenant_id=tid,
                pass_type=CANON_PASS,
                source_trigger="scheduled",
            )
            canon_planned += 1

    if settings.cortex_identity_scheduler_enabled and not read_lane_paused_flag(settings, "identity"):
        for tid in iter_tenants_with_actor_entities(session):
            if _skip_tenant_during_clear_derived(settings, tid):
                continue
            if should_skip_scheduled_identity_pass(
                session,
                tenant_id=tid,
                interval_seconds=identity_interval,
            ):
                identity_skipped += 1
                continue
            upsert_pending_pass_v1(
                session,
                tenant_id=tid,
                pass_type=IDENTITY_PASS,
                source_trigger="scheduled",
            )
            identity_planned += 1

    if settings.cortex_graph_scheduler_enabled and not read_lane_paused_flag(settings, "graph"):
        for tid in iter_tenants_with_graph_backlog(session):
            if _skip_tenant_during_clear_derived(settings, tid):
                continue
            if should_skip_scheduled_graph_pass(
                session,
                tenant_id=tid,
                interval_seconds=graph_interval,
            ):
                graph_skipped += 1
                continue
            upsert_pending_pass_v1(
                session,
                tenant_id=tid,
                pass_type=GRAPH_PROJECTION_PASS,
                source_trigger="scheduled",
            )
            graph_planned += 1

    if settings.cortex_declared_domain_scheduler_enabled and not read_lane_paused_flag(
        settings,
        "declared_domains",
    ):
        for tid in iter_tenants_with_declared_domain_backlog(session):
            if _skip_tenant_during_clear_derived(settings, tid):
                continue
            if should_skip_scheduled_declared_domain_pass(
                session,
                tenant_id=tid,
                interval_seconds=declared_domain_interval,
            ):
                declared_domain_skipped += 1
                continue
            upsert_pending_pass_v1(
                session,
                tenant_id=tid,
                pass_type=DECLARED_DOMAIN_PASS,
                source_trigger="scheduled",
            )
            declared_domain_planned += 1

    return {
        "canon_planned": canon_planned,
        "canon_skipped": canon_skipped,
        "identity_planned": identity_planned,
        "identity_skipped": identity_skipped,
        "graph_planned": graph_planned,
        "graph_skipped": graph_skipped,
        "declared_domain_planned": declared_domain_planned,
        "declared_domain_skipped": declared_domain_skipped,
    }
