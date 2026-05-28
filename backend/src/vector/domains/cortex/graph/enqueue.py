"""Graph dirty queue enqueue helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue

GRAPH_SCOPED_ENTITY_TYPES = frozenset(
    {
        "actor",
        "message",
        "conversation",
        "pull_request",
        "work_item",
        "commit",
        "deployment",
        "release",
        "document",
        "issue_relation",
    },
)

_ENRICH_ONLY_REASONS = frozenset({"identity_linked"})


def enqueue_graph_entity(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
    reason: str,
    entity_type: str | None = None,
) -> None:
    if entity_type is not None and entity_type not in GRAPH_SCOPED_ENTITY_TYPES:
        if reason not in _ENRICH_ONLY_REASONS:
            return
    reason = reason[:32]
    existing = session.scalar(
        select(GraphDirtyQueue)
        .where(
            GraphDirtyQueue.tenant_id == tenant_id,
            GraphDirtyQueue.canon_entity_id == canon_entity_id,
            GraphDirtyQueue.processed_at.is_(None),
        )
        .limit(1),
    )
    if existing is not None:
        if reason == "identity_linked" and existing.reason == "canon_materialized":
            existing.reason = reason
        return
    session.add(
        GraphDirtyQueue(
            tenant_id=tenant_id,
            canon_entity_id=canon_entity_id,
            reason=reason,
        ),
    )


def enqueue_graph_actor_for_enrich(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
    reason: str = "identity_linked",
) -> None:
    enqueue_graph_entity(
        session,
        tenant_id=tenant_id,
        canon_entity_id=canon_entity_id,
        reason=reason,
        entity_type="actor",
    )
