"""Declared domain pass scheduling helpers."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.declared_container_registry import ATTR_DECLARED_CONTAINER_KIND
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain_dirty_queue import DeclaredDomainDirtyQueue


def iter_tenants_with_declared_domain_backlog(session: Session) -> Iterator[uuid.UUID]:
    """Tenants with pending dirty rows or canon seeds needing processing."""
    dirty_tenants = session.scalars(
        select(DeclaredDomainDirtyQueue.tenant_id)
        .where(DeclaredDomainDirtyQueue.processed_at.is_(None))
        .distinct(),
    ).all()
    seen: set[uuid.UUID] = set()
    for tid in dirty_tenants:
        seen.add(tid)
        yield tid

    seed_tenants = session.scalars(
        select(CanonEntity.tenant_id)
        .where(CanonEntity.attrs_json[ATTR_DECLARED_CONTAINER_KIND].astext.isnot(None))
        .distinct(),
    ).all()
    for tid in seed_tenants:
        if tid not in seen:
            yield tid
