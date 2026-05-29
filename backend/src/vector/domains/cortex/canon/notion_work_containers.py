"""Notion work database allowlist for declared domain seeds."""

from __future__ import annotations

import re
import uuid
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.declared_container_registry import (
    ATTR_DECLARED_CONTAINER_EXTERNAL_ID,
    ATTR_DECLARED_CONTAINER_KIND,
)
from vector.domains.cortex.canon.mappers._common import notion_plain_text
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


_NOTION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _looks_like_notion_id(value: str) -> bool:
    compact = value.replace("-", "")
    return bool(_NOTION_ID_RE.match(value)) or (len(compact) == 32 and compact.isalnum())


def notion_database_title_from_payload(payload_body: dict[str, Any]) -> str | None:
    segment = payload_body.get("database")
    if not isinstance(segment, dict):
        return None
    title = notion_plain_text(segment.get("title"))
    if title:
        return title
    name = segment.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _raw_notion_database_titles(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> dict[str, str]:
    """Latest ingested title per Notion database external_id."""
    raws = session.scalars(
        select(RawIngestionRecord)
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.connection_id == connection_id,
            RawIngestionRecord.resource_type == "notion.database",
            RawIngestionRecord.replay_job_id.is_(None),
        )
        .order_by(RawIngestionRecord.id.desc()),
    ).all()
    titles: dict[str, str] = {}
    for raw in raws:
        db_id = raw.external_id
        if not isinstance(db_id, str) or not db_id.strip() or db_id in titles:
            continue
        body = raw.payload_body if isinstance(raw.payload_body, dict) else {}
        title = notion_database_title_from_payload(body)
        if title:
            titles[db_id] = title
    return titles


def _raw_notion_database_row_counts(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> dict[str, int]:
    """Row counts keyed by parent database_id from raw notion.database_row payloads."""
    payloads = session.scalars(
        select(RawIngestionRecord.payload_body).where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.connection_id == connection_id,
            RawIngestionRecord.resource_type == "notion.database_row",
            RawIngestionRecord.replay_job_id.is_(None),
        ),
    ).all()
    counts: Counter[str] = Counter()
    for body in payloads:
        if not isinstance(body, dict):
            continue
        db_id = _raw_row_database_id(body)
        if db_id:
            counts[db_id] += 1
    return dict(counts)


def _pin_label_snapshots(pins: list | None) -> dict[str, str]:
    labels: dict[str, str] = {}
    if not isinstance(pins, list):
        return labels
    for pin in pins:
        if not isinstance(pin, dict):
            continue
        db_id = pin.get("id")
        label = pin.get("label_snapshot")
        if isinstance(db_id, str) and isinstance(label, str) and label.strip():
            labels[db_id.strip()] = label.strip()
    return labels


def _resolve_database_display_name(
    *,
    database_id: str,
    raw_title: str | None,
    pin_label: str | None,
    canon_label: str | None,
) -> str:
    if raw_title:
        return raw_title
    if pin_label:
        return pin_label
    if canon_label and not _looks_like_notion_id(canon_label):
        return canon_label
    return database_id


def list_notion_canon_databases(session: Session, *, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    pinned = pinned_database_ids(link.detail.work_container_pins) if link is not None else frozenset()
    pin_labels = _pin_label_snapshots(link.detail.work_container_pins) if link is not None else {}

    raw_titles: dict[str, str] = {}
    row_counts: dict[str, int] = {}
    if link is not None:
        raw_titles = _raw_notion_database_titles(
            session,
            tenant_id=tenant_id,
            connection_id=link.connection.id,
        )
        row_counts = _raw_notion_database_row_counts(
            session,
            tenant_id=tenant_id,
            connection_id=link.connection.id,
        )

    canon_entities = session.scalars(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.connector == "notion",
            CanonEntity.entity_type == "project",
        ),
    ).all()
    canon_by_id: dict[str, CanonEntity] = {}
    for entity in canon_entities:
        attrs = entity.attrs_json if isinstance(entity.attrs_json, dict) else {}
        external_id = attrs.get(ATTR_DECLARED_CONTAINER_EXTERNAL_ID) or attrs.get("external_id") or attrs.get(
            "notion_id",
        )
        if isinstance(external_id, str) and external_id.strip():
            canon_by_id[external_id.strip()] = entity

    database_ids = set(canon_by_id) | set(raw_titles) | set(row_counts) | pinned
    out: list[dict[str, Any]] = []
    for database_id in database_ids:
        entity = canon_by_id.get(database_id)
        attrs = entity.attrs_json if entity is not None and isinstance(entity.attrs_json, dict) else {}
        display_name = _resolve_database_display_name(
            database_id=database_id,
            raw_title=raw_titles.get(database_id),
            pin_label=pin_labels.get(database_id),
            canon_label=entity.display_label if entity is not None else None,
        )
        out.append(
            {
                "canon_entity_id": str(entity.id) if entity is not None else None,
                "database_id": database_id,
                "display_name": display_name,
                "row_count": int(row_counts.get(database_id, 0)),
                "is_pinned": database_id in pinned,
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
