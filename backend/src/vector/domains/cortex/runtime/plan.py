"""Plan pending cortex_pass rows from domain signals."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.scheduler import iter_tenants_with_live_raw
from vector.domains.cortex.canon.scheduler_dedup import should_skip_scheduled_canon_pass
from vector.domains.cortex.identity.scheduler import iter_tenants_with_actor_entities
from vector.domains.cortex.runtime.pass_types import CANON_PASS, IDENTITY_PASS
from vector.domains.cortex.runtime.queue import upsert_pending_pass_v1
from vector.infrastructure.db.models.canon_dirty_queue import CanonDirtyQueue
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.domains.cortex.identity.scheduler_dedup import should_skip_scheduled_identity_pass
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


def plan_cortex_passes_v1(session: Session, settings: Settings) -> dict[str, Any]:
    """Enqueue pending pass rows for tenants that need work (no Celery fan-out)."""
    canon_planned = 0
    canon_skipped = 0
    identity_planned = 0
    identity_skipped = 0
    canon_interval = max(60, int(settings.cortex_canon_scheduler_interval_seconds))
    identity_interval = max(60, int(settings.cortex_identity_scheduler_interval_seconds))

    if settings.cortex_canon_scheduler_enabled:
        for tid in iter_tenants_with_live_raw(session, settings):
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

    if settings.cortex_identity_scheduler_enabled:
        for tid in iter_tenants_with_actor_entities(session):
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

    return {
        "canon_planned": canon_planned,
        "canon_skipped": canon_skipped,
        "identity_planned": identity_planned,
        "identity_skipped": identity_skipped,
    }
