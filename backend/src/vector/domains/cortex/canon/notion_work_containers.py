"""Notion work database allowlist for declared domain seeds."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.declared_container_registry import (
    ATTR_DECLARED_CONTAINER_EXTERNAL_ID,
    ATTR_DECLARED_CONTAINER_KIND,
)
from vector.domains.cortex.canon.materialize import materialize_raw_row
from vector.domains.cortex.declared_domains.enqueue import (
    REASON_MEMBER_MATERIALIZED,
    REASON_SEED_MATERIALIZED,
    enqueue_declared_domain_entity,
)
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.notion_connection_detail import NotionConnectionDetail
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories import notion_connection as notion_repo

MAX_NOTION_WORK_CONTAINER_PINS = 30


def notion_work_db_allowlist_for_connection(
    session: Session,
    connection_id: uuid.UUID,
) -> frozenset[str]:
    detail = session.get(NotionConnectionDetail, connection_id)
    if detail is None:
        return frozenset()
    return pinned_database_ids(detail.work_container_pins)


def pinned_database_ids(pins: list | None) -> frozenset[str]:
    if not isinstance(pins, list):
        return frozenset()
    out: set[str] = set()
    for pin in pins:
        if isinstance(pin, dict):
            db_id = pin.get("id")
            if isinstance(db_id, str) and db_id.strip():
                out.add(db_id.strip())
    return frozenset(out)


def normalize_work_container_pins(
    *,
    database_ids: list[str],
    labels_by_id: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if len(database_ids) > MAX_NOTION_WORK_CONTAINER_PINS:
        msg = f"max_pins_exceeded:{MAX_NOTION_WORK_CONTAINER_PINS}"
        raise ValueError(msg)
    now = utc_now().isoformat()
    labels = labels_by_id or {}
    seen: set[str] = set()
    pins: list[dict[str, Any]] = []
    for raw_id in database_ids:
        db_id = raw_id.strip()
        if not db_id or db_id in seen:
            continue
        seen.add(db_id)
        pins.append(
            {
                "id": db_id,
                "label_snapshot": labels.get(db_id),
                "pinned_at": now,
            },
        )
    return pins


def list_notion_canon_databases(session: Session, *, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    pinned = pinned_database_ids(link.detail.work_container_pins) if link is not None else frozenset()
    rows = session.scalars(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.connector == "notion",
            CanonEntity.entity_type == "project",
        ),
    ).all()
    out: list[dict[str, Any]] = []
    for entity in rows:
        attrs = entity.attrs_json if isinstance(entity.attrs_json, dict) else {}
        external_id = attrs.get(ATTR_DECLARED_CONTAINER_EXTERNAL_ID) or attrs.get("external_id") or attrs.get(
            "notion_id",
        )
        if not isinstance(external_id, str):
            continue
        row_count = int(
            session.scalar(
                select(func.count())
                .select_from(CanonEntity)
                .where(
                    CanonEntity.tenant_id == tenant_id,
                    CanonEntity.entity_type == "document",
                    CanonEntity.connector == "notion",
                    CanonEntity.attrs_json["database_id"].astext == external_id,
                ),
            )
            or 0,
        )
        out.append(
            {
                "canon_entity_id": str(entity.id),
                "database_id": external_id,
                "display_name": entity.display_label,
                "row_count": row_count,
                "is_pinned": external_id in pinned,
                "is_declared_seed": attrs.get(ATTR_DECLARED_CONTAINER_KIND) == "work_database",
            },
        )
    out.sort(key=lambda item: (not item["is_pinned"], -item["row_count"], item["display_name"].lower()))
    return out


def _raw_row_database_id(payload_body: dict[str, Any]) -> str | None:
    for key in ("row", "database_row"):
        segment = payload_body.get(key)
        if not isinstance(segment, dict):
            continue
        direct = segment.get("database_id")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        parent = segment.get("parent")
        if isinstance(parent, dict) and parent.get("type") == "database_id":
            parent_db = parent.get("database_id")
            if isinstance(parent_db, str) and parent_db.strip():
                return parent_db.strip()
    return None


def prepare_notion_work_container_backfill(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    database_ids: list[str],
) -> dict[str, int]:
    """Re-materialize affected Notion database + row raw rows and enqueue declared-domain work."""
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        return {
            "rematerialized_raw_rows": 0,
            "enqueued_declared_domain_entities": 0,
        }
    connection_id = link.connection.id
    target_ids = {db_id.strip() for db_id in database_ids if isinstance(db_id, str) and db_id.strip()}
    rematerialized = 0
    enqueued_declared = 0

    for db_id in sorted(target_ids):
        db_raw = session.scalar(
            select(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.connection_id == connection_id,
                RawIngestionRecord.resource_type == "notion.database",
                RawIngestionRecord.external_id == db_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
            .order_by(RawIngestionRecord.id.desc())
            .limit(1),
        )
        if db_raw is not None:
            materialize_raw_row(session, db_raw)
            rematerialized += 1
            entity = session.scalar(
                select(CanonEntity.id).where(
                    CanonEntity.tenant_id == tenant_id,
                    CanonEntity.connection_id == connection_id,
                    CanonEntity.entity_type == "project",
                    CanonEntity.attrs_json[ATTR_DECLARED_CONTAINER_EXTERNAL_ID].astext == db_id,
                ),
            )
            if entity is not None:
                enqueue_declared_domain_entity(
                    session,
                    tenant_id=tenant_id,
                    canon_entity_id=entity,
                    reason=REASON_SEED_MATERIALIZED,
                )
                enqueued_declared += 1

    row_raws = session.scalars(
        select(RawIngestionRecord)
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.connection_id == connection_id,
            RawIngestionRecord.resource_type == "notion.database_row",
            RawIngestionRecord.replay_job_id.is_(None),
        )
        .order_by(RawIngestionRecord.id.asc()),
    ).all()
    for row_raw in row_raws:
        body = row_raw.payload_body if isinstance(row_raw.payload_body, dict) else {}
        row_db_id = _raw_row_database_id(body)
        if row_db_id not in target_ids:
            continue
        materialize_raw_row(session, row_raw)
        rematerialized += 1
        entity_id = session.scalar(
            select(CanonEntity.id).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_key.like(f"%:{row_raw.external_id}"),
            ),
        )
        if entity_id is None:
            entity_id = session.scalar(
                select(CanonEntity.id).where(
                    CanonEntity.tenant_id == tenant_id,
                    CanonEntity.attrs_json["external_id"].astext == row_raw.external_id,
                ),
            )
        if entity_id is not None:
            enqueue_declared_domain_entity(
                session,
                tenant_id=tenant_id,
                canon_entity_id=entity_id,
                reason=REASON_MEMBER_MATERIALIZED,
            )
            enqueued_declared += 1

    return {
        "rematerialized_raw_rows": rematerialized,
        "enqueued_declared_domain_entities": enqueued_declared,
    }


def update_notion_work_container_pins(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    database_ids: list[str],
    labels_by_id: dict[str, str] | None = None,
) -> dict[str, Any]:
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        msg = "notion_not_connected"
        raise ValueError(msg)
    old_ids = pinned_database_ids(link.detail.work_container_pins)
    new_pins = normalize_work_container_pins(database_ids=database_ids, labels_by_id=labels_by_id)
    new_ids = pinned_database_ids(new_pins)
    link.detail.work_container_pins = new_pins
    session.flush()
    affected_ids = sorted(old_ids | new_ids)
    backfill = prepare_notion_work_container_backfill(
        session,
        tenant_id=tenant_id,
        database_ids=affected_ids,
    )
    return {
        "pinned_count": len(new_ids),
        "affected_database_ids": affected_ids,
        **backfill,
    }
