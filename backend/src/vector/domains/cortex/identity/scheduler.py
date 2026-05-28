"""Identity scheduler tenant selection."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.canon_entity import CanonEntity


def iter_tenants_with_actor_entities(session: Session) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(CanonEntity.tenant_id)
            .where(CanonEntity.entity_type == "actor")
            .distinct()
            .order_by(CanonEntity.tenant_id.asc()),
        ).all(),
    )

