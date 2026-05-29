"""Declared domain dirty-queue enqueue."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.declared_domain_dirty_queue import DeclaredDomainDirtyQueue

REASON_SEED_MATERIALIZED = "seed_materialized"
REASON_MEMBER_MATERIALIZED = "member_materialized"
REASON_GRAPH_UPDATED = "graph_updated"
REASON_EXTRACTOR_BUMP = "extractor_bump"


def enqueue_declared_domain_entity(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
    reason: str,
) -> None:
    existing = session.scalar(
        select(DeclaredDomainDirtyQueue.id)
        .where(
            DeclaredDomainDirtyQueue.tenant_id == tenant_id,
            DeclaredDomainDirtyQueue.canon_entity_id == canon_entity_id,
            DeclaredDomainDirtyQueue.processed_at.is_(None),
        )
        .limit(1),
    )
    if existing is not None:
        return
    session.add(
        DeclaredDomainDirtyQueue(
            tenant_id=tenant_id,
            canon_entity_id=canon_entity_id,
            reason=reason,
            enqueued_at=utc_now(),
        ),
    )
