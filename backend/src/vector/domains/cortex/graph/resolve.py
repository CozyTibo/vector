"""Resolve canon entity ids for graph projection."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key
from vector.infrastructure.db.models.canon_entity import CanonEntity


def resolve_entity_id_by_source_identity_key(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_identity_key: str,
) -> uuid.UUID | None:
    entity_key = f"{tenant_id}:{source_identity_key}"[:512]
    return session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.entity_key == entity_key,
        ),
    )


def resolve_linear_issue_id(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    issue_id: str,
) -> uuid.UUID | None:
    if not issue_id.strip():
        return None
    key = derive_source_identity_key(
        connector="linear",
        resource_type="linear.issue",
        external_id=issue_id.strip(),
    )
    return resolve_entity_id_by_source_identity_key(
        session,
        tenant_id=tenant_id,
        source_identity_key=key,
    )
