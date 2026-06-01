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


def resolve_notion_external_id(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    external_id: str,
) -> uuid.UUID | None:
    """Resolve a Notion page/row/block id to a canon entity id."""
    needle = external_id.replace("-", "").lower()
    if not needle:
        return None
    rows = list(
        session.scalars(
            select(CanonEntity).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.connector == "notion",
                CanonEntity.entity_type.in_(("document", "work_item", "project")),
            ),
        ).all(),
    )
    for ent in rows:
        attrs = ent.attrs_json if isinstance(ent.attrs_json, dict) else {}
        for raw_id in (attrs.get("notion_id"), attrs.get("external_id")):
            if isinstance(raw_id, str) and raw_id.replace("-", "").lower() == needle:
                return ent.id
        if ent.entity_key.endswith(f":{external_id}") or ent.entity_key.endswith(f":{needle}"):
            return ent.id
    return None
