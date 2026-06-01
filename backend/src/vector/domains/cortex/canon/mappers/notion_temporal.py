"""Notion object-level temporal fields for canon attrs."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.canon.lifecycle_substrate import apply_temporal_attrs


def notion_segment_iso_timestamp(segment: dict[str, Any], field: str) -> str | None:
    value = segment.get(field)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def apply_notion_object_temporal_attrs(segment: dict[str, Any], attrs: dict[str, Any]) -> None:
    apply_temporal_attrs(
        attrs,
        provider_created_at=notion_segment_iso_timestamp(segment, "created_time"),
        provider_updated_at=notion_segment_iso_timestamp(segment, "last_edited_time"),
        archived=bool(segment.get("archived")) if "archived" in segment else None,
        in_trash=bool(segment.get("in_trash")) if "in_trash" in segment else None,
    )


def enrich_payload_with_notion_timestamps(payload_body: dict[str, Any]) -> dict[str, Any]:
    """Promote nested Notion timestamps for observed_at derivation."""
    if not isinstance(payload_body, dict):
        return payload_body
    if payload_body.get("provider_updated_at") or payload_body.get("updated_at"):
        return payload_body
    for key in ("page", "row", "database_row", "database", "block", "user"):
        segment = payload_body.get(key)
        if not isinstance(segment, dict):
            continue
        updated = notion_segment_iso_timestamp(segment, "last_edited_time")
        created = notion_segment_iso_timestamp(segment, "created_time")
        if updated or created:
            out = dict(payload_body)
            if updated:
                out["provider_updated_at"] = updated
            if created:
                out["provider_created_at"] = created
            return out
    return payload_body
