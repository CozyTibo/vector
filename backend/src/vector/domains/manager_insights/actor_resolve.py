"""Resolve Manager insights external identities to canonical actors (ActorExternalIdentity)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.canonical import ActorExternalIdentity

ActorResolveFn = Callable[[str, str | None], uuid.UUID | None]


def make_actor_resolver(session: Session, tenant_id: uuid.UUID) -> ActorResolveFn:
    """Return ``resolve_actor(connector, external_id)`` backed by ``actor_external_identity``."""

    def resolve_actor(connector: str, external_id: str | None) -> uuid.UUID | None:
        if not external_id or not str(external_id).strip():
            return None
        ext = str(external_id).strip()
        aid = session.scalar(
            select(ActorExternalIdentity.actor_id).where(
                ActorExternalIdentity.tenant_id == tenant_id,
                ActorExternalIdentity.connector == connector,
                ActorExternalIdentity.external_id == ext,
            ).limit(1)
        )
        return aid if isinstance(aid, uuid.UUID) else None

    return resolve_actor
