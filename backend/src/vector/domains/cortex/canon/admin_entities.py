"""Admin canon entity list and drilldown."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

from vector.domains.cortex.canon.notion_display_labels import enrich_notion_display_labels

MANUAL_CANON_PASS_CONFIRMATION = "RUN CANON MATERIALIZATION PASS"


def list_canon_entities(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
    connector: str | None = None,
    entity_type: str | None = None,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    stmt = select(CanonEntity).where(CanonEntity.tenant_id == tenant_id)
    count_stmt = select(func.count()).select_from(CanonEntity).where(CanonEntity.tenant_id == tenant_id)
    if connector:
        stmt = stmt.where(CanonEntity.connector == connector)
        count_stmt = count_stmt.where(CanonEntity.connector == connector)
    if entity_type:
        stmt = stmt.where(CanonEntity.entity_type == entity_type)
        count_stmt = count_stmt.where(CanonEntity.entity_type == entity_type)
    if search and search.strip():
        q = f"%{search.strip()}%"
        stmt = stmt.where(
            CanonEntity.display_label.ilike(q) | CanonEntity.entity_key.ilike(q),
        )
        count_stmt = count_stmt.where(
            CanonEntity.display_label.ilike(q) | CanonEntity.entity_key.ilike(q),
        )
    total = int(session.scalar(count_stmt) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(CanonEntity.materialized_at.desc()).offset(offset).limit(limit),
        ).all(),
    )
    labels = enrich_notion_display_labels(session, rows)
    return [_entity_summary(e, display_label=labels.get(e.id, e.display_label)) for e in rows], total


def _entity_summary(e: CanonEntity, *, display_label: str | None = None) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "entity_type": e.entity_type,
        "entity_key": e.entity_key,
        "display_label": display_label if display_label is not None else e.display_label,
        "connector": e.connector,
        "connection_id": str(e.connection_id),
        "materialized_at": e.materialized_at.isoformat(),
        "mapper_version": e.mapper_version,
        "author_entity_id": str(e.author_entity_id) if e.author_entity_id else None,
        "conversation_entity_id": str(e.conversation_entity_id) if e.conversation_entity_id else None,
        "parent_message_entity_id": str(e.parent_message_entity_id) if e.parent_message_entity_id else None,
        "repository_entity_id": str(e.repository_entity_id) if e.repository_entity_id else None,
        "assignee_entity_id": str(e.assignee_entity_id) if e.assignee_entity_id else None,
        "parent_document_entity_id": str(e.parent_document_entity_id) if e.parent_document_entity_id else None,
        "work_item_entity_id": str(e.work_item_entity_id) if e.work_item_entity_id else None,
    }


def get_canon_entity_detail(
    session: Session,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> dict[str, Any] | None:
    entity = session.scalar(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.id == entity_id,
        ),
    )
    if entity is None:
        return None
    sources = list(
        session.scalars(
            select(CanonEntitySource)
            .where(CanonEntitySource.canon_entity_id == entity.id)
            .order_by(CanonEntitySource.observed_at.desc()),
        ).all(),
    )
    source_payloads: list[dict[str, Any]] = []
    for src in sources:
        raw = session.get(RawIngestionRecord, src.raw_id)
        source_payloads.append(
            {
                "raw_id": int(src.raw_id),
                "connector": src.connector,
                "resource_type": src.resource_type,
                "external_id": src.external_id,
                "source_identity_key": src.source_identity_key,
                "source_revision_key": src.source_revision_key,
                "observed_at": src.observed_at.isoformat(),
                "is_latest": src.is_latest,
                "payload_preview": _preview_payload(raw.payload_body if raw else {}),
            },
        )
    out = _entity_summary(
        entity,
        display_label=enrich_notion_display_labels(session, [entity]).get(entity.id, entity.display_label),
    )
    out["attrs_json"] = dict(entity.attrs_json)
    out["sources"] = source_payloads
    return out


def _preview_payload(body: dict[str, Any]) -> dict[str, Any]:
    if not body:
        return {}
    keys = list(body.keys())[:12]
    return {k: body[k] for k in keys if k in body}
