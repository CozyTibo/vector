"""Human-readable Notion titles for admin display (read-time enrichment)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.mappers._common import notion_plain_text
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

_NOTION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$",
    re.IGNORECASE,
)

NOTION_PAYLOAD_SEGMENT_BY_RESOURCE: dict[str, str] = {
    "notion.page": "page",
    "notion.database_row": "row",
    "notion.database": "database",
    "notion.block": "block",
    "notion.user": "user",
}


def looks_like_notion_id(value: str) -> bool:
    compact = value.replace("-", "")
    return bool(_NOTION_ID_RE.match(value)) or (len(compact) == 32 and compact.isalnum())


def resource_type_from_entity_key(entity_key: str) -> str | None:
    parts = entity_key.split(":")
    if len(parts) >= 3:
        return parts[2]
    return None


def notion_title_from_properties(properties: object) -> str | None:
    if not isinstance(properties, dict):
        return None
    title_props = [
        name
        for name, prop in properties.items()
        if isinstance(prop, dict) and prop.get("type") == "title"
    ]
    for prop_name in sorted(title_props, key=str.lower):
        prop = properties[prop_name]
        if isinstance(prop, dict):
            text = notion_plain_text(prop.get("title"))
            if text:
                return text
    for prop_name in ("Name", "Title", "Task", "name", "title"):
        prop = properties.get(prop_name)
        if isinstance(prop, dict):
            text = notion_plain_text(prop.get("title")) or notion_plain_text(prop.get("rich_text"))
            if text:
                return text
    return None


def notion_block_title_from_segment(segment: dict[str, Any]) -> str | None:
    block_type = segment.get("type")
    if not isinstance(block_type, str):
        return None
    content = segment.get(block_type)
    if isinstance(content, dict):
        text = notion_plain_text(content.get("rich_text"))
        if text:
            return text
        if block_type == "link_preview":
            url = content.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()[:512]
    return None


def notion_title_from_segment(*, resource_type: str, segment: dict[str, Any]) -> str | None:
    if resource_type in ("notion.database_row", "notion.page"):
        return notion_title_from_properties(segment.get("properties"))
    if resource_type == "notion.database":
        title = notion_plain_text(segment.get("title"))
        if title:
            return title
        name = segment.get("name")
        return name.strip() if isinstance(name, str) and name.strip() else None
    if resource_type == "notion.block":
        return notion_block_title_from_segment(segment)
    if resource_type == "notion.user":
        name = segment.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        return notion_plain_text(name)
    return None


def notion_database_title_from_payload(payload_body: dict[str, Any]) -> str | None:
    segment = payload_body.get("database")
    if isinstance(segment, dict):
        return notion_title_from_segment(resource_type="notion.database", segment=segment)
    return None


def notion_row_title_from_payload(payload_body: dict[str, Any]) -> str | None:
    for key in ("row", "database_row", "page"):
        segment = payload_body.get(key)
        if isinstance(segment, dict):
            resource_type = "notion.page" if key == "page" else "notion.database_row"
            title = notion_title_from_segment(resource_type=resource_type, segment=segment)
            if title:
                return title
    return None


def notion_title_from_payload(*, resource_type: str, payload_body: dict[str, Any]) -> str | None:
    segment_key = NOTION_PAYLOAD_SEGMENT_BY_RESOURCE.get(resource_type)
    if segment_key is None:
        return None
    segment = payload_body.get(segment_key)
    if isinstance(segment, dict):
        return notion_title_from_segment(resource_type=resource_type, segment=segment)
    return None


def notion_display_label_needs_enrichment(entity: CanonEntity) -> bool:
    if entity.connector != "notion":
        return False
    label = (entity.display_label or "").strip()
    if not label:
        return True
    attrs = entity.attrs_json if isinstance(entity.attrs_json, dict) else {}
    for key in ("external_id", "notion_id"):
        ext = attrs.get(key)
        if isinstance(ext, str) and label == ext.strip():
            return True
    return looks_like_notion_id(label)


def enrich_notion_display_labels(
    session: Session,
    entities: Iterable[CanonEntity],
) -> dict[uuid.UUID, str]:
    """Resolve human-readable labels for Notion canon entities from latest raw payloads."""
    entity_list = list(entities)
    if not entity_list:
        return {}

    need = [entity for entity in entity_list if notion_display_label_needs_enrichment(entity)]
    resolved: dict[uuid.UUID, str] = {
        entity.id: entity.display_label for entity in entity_list if entity not in need
    }
    if not need:
        return resolved

    entity_ids = [entity.id for entity in need]
    sources = {
        row.canon_entity_id: row
        for row in session.scalars(
            select(CanonEntitySource).where(
                CanonEntitySource.canon_entity_id.in_(entity_ids),
                CanonEntitySource.is_latest.is_(True),
            ),
        ).all()
    }
    raw_ids = {src.raw_id for src in sources.values()}
    raws: dict[int, RawIngestionRecord] = {}
    if raw_ids:
        raws = {
            row.id: row
            for row in session.scalars(
                select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids)),
            ).all()
        }

    for entity in need:
        label = entity.display_label
        src = sources.get(entity.id)
        if src is not None:
            raw = raws.get(src.raw_id)
            body = raw.payload_body if raw is not None and isinstance(raw.payload_body, dict) else {}
            title = notion_title_from_payload(resource_type=src.resource_type, payload_body=body)
            if title:
                label = title[:512]
        resolved[entity.id] = label

    return resolved
