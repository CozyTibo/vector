"""Graph pass scheduling helpers."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.materialize import tenant_has_canon_backlog
from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue


def iter_tenants_with_graph_backlog(session: Session) -> Iterator[uuid.UUID]:
    """Tenants with pending graph dirty rows and no blocking canon backlog."""
    tenant_ids = session.scalars(
        select(GraphDirtyQueue.tenant_id)
        .where(GraphDirtyQueue.processed_at.is_(None))
        .distinct(),
    ).all()
    for tid in tenant_ids:
        if tenant_has_canon_backlog(session, tid):
            continue
        yield tid
