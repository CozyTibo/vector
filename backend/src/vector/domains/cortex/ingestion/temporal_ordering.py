"""Temporal ordering helpers for Phase 02 Step 3."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _parse_iso_or_epoch(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.isdigit():
        try:
            if len(raw) >= 13:
                return datetime.fromtimestamp(int(raw) / 1000.0, tz=UTC)
            return datetime.fromtimestamp(int(raw), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def derive_provider_event_timestamp(payload_body: dict[str, Any]) -> datetime | None:
    candidates = (
        payload_body.get("provider_event_timestamp"),
        payload_body.get("provider_updated_at"),
        payload_body.get("provider_created_at"),
        payload_body.get("updated_at"),
        payload_body.get("updatedAt"),
        payload_body.get("created_at"),
        payload_body.get("createdAt"),
        payload_body.get("ts"),
        payload_body.get("event_ts"),
        payload_body.get("timestamp"),
    )
    for candidate in candidates:
        parsed = _parse_iso_or_epoch(candidate)
        if parsed is not None:
            return parsed
    return None


def derive_deletion_observed(payload_body: dict[str, Any]) -> bool:
    if payload_body.get("deleted") is True or payload_body.get("is_deleted") is True:
        return True
    if payload_body.get("tombstone") is True:
        return True
    subtype = str(payload_body.get("subtype", "")).strip().lower()
    if subtype in {"message_deleted", "deleted"}:
        return True
    status = str(payload_body.get("status", "")).strip().lower()
    return status in {"deleted", "archived_deleted"}
