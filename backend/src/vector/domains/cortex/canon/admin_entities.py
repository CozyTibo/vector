"""Admin canon entity list and drilldown."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

from vector.domains.cortex.canon.notion_display_labels import (
    enrich_notion_display_labels,
    resource_type_from_entity_key,
)

MANUAL_CANON_PASS_CONFIRMATION = "RUN CANON MATERIALIZATION PASS"


def _notion_row_external_ids_matching_search(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    database_id: str,
    search: str,
) -> set[str]:
    from vector.domains.cortex.canon.notion_display_labels import notion_title_from_payload

    q_fold = search.strip().casefold()
    if not q_fold:
        return set()
    raws = session.scalars(
        select(RawIngestionRecord)
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.resource_type == "notion.database_row",
            RawIngestionRecord.replay_job_id.is_(None),
            RawIngestionRecord.payload_body["row"]["parent"]["database_id"].astext == database_id,
        )
        .order_by(RawIngestionRecord.id.desc()),
    ).all()
    seen: set[str] = set()
    matched: set[str] = set()
    for raw in raws:
        ext = raw.external_id.strip() if isinstance(raw.external_id, str) else ""
        if not ext or ext in seen:
            continue
        seen.add(ext)
        body = raw.payload_body if isinstance(raw.payload_body, dict) else {}
        title = notion_title_from_payload(resource_type="notion.database_row", payload_body=body)
        haystack = " ".join(
            part for part in (title, ext, raw.external_id) if isinstance(part, str) and part
        ).casefold()
        if q_fold in haystack:
            matched.add(ext)
    return matched


def notion_database_id_from_entity(entity: CanonEntity) -> str | None:
    """External Notion database id when this canon row is a notion.database seed."""
    if entity.connector != "notion":
        return None
    if resource_type_from_entity_key(entity.entity_key) != "notion.database":
        return None
    attrs = entity.attrs_json if isinstance(entity.attrs_json, dict) else {}
    for key in ("external_id", "notion_id", "declared_container_external_id"):
        value = attrs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    parts = entity.entity_key.split(":")
    if len(parts) >= 4 and parts[3].strip():
        return parts[3].strip()
    return None


def list_notion_database_members(
    session: Session,
    tenant_id: uuid.UUID,
    database_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Paginated canon documents belonging to a Notion database (Level 0 rows)."""
    db_id = database_id.strip()
    base = (
        CanonEntity.tenant_id == tenant_id,
        CanonEntity.connector == "notion",
        CanonEntity.entity_type == "document",
        CanonEntity.attrs_json["database_id"].astext == db_id,
    )
    stmt = select(CanonEntity).where(*base)
    count_stmt = select(func.count()).select_from(CanonEntity).where(*base)
    if search and search.strip():
        q = search.strip()
        q_fold = q.casefold()
        matching_external_ids = _notion_row_external_ids_matching_search(
            session,
            tenant_id=tenant_id,
            database_id=db_id,
            search=q,
        )
        from sqlalchemy import or_

        search_filters = [
            CanonEntity.display_label.ilike(f"%{q}%"),
            CanonEntity.entity_key.ilike(f"%{q}%"),
        ]
        search_filters.extend(
            CanonEntity.entity_key.endswith(f":{ext}") for ext in matching_external_ids
        )
        stmt = stmt.where(or_(*search_filters))
        all_rows = list(
            session.scalars(stmt.order_by(CanonEntity.display_label.asc(), CanonEntity.id.asc())).all(),
        )
        labels = enrich_notion_display_labels(session, all_rows)
        filtered = [
            entity
            for entity in all_rows
            if q_fold in labels.get(entity.id, entity.display_label).casefold()
            or q_fold in entity.entity_key.casefold()
            or q_fold in (entity.display_label or "").casefold()
        ]
        total = len(filtered)
        page_rows = filtered[offset : offset + limit]
        items = [
            _entity_summary(entity, display_label=labels.get(entity.id, entity.display_label))
            for entity in page_rows
        ]
        return items, total

    total = int(session.scalar(count_stmt) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(CanonEntity.display_label.asc(), CanonEntity.id.asc())
            .offset(offset)
            .limit(limit),
        ).all(),
    )
    labels = enrich_notion_display_labels(session, rows)
    items = [_entity_summary(e, display_label=labels.get(e.id, e.display_label)) for e in rows]
    items.sort(key=lambda row: row["display_label"].casefold())
    return items, total


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
